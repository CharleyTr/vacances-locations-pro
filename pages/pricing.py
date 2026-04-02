"""
Page Revenus & Pricing — Pricing dynamique, concurrents, prévisions.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import calendar
import numpy as np

import requests
import json
import os
from services.reservation_service import load_reservations
from services.analytics_service import compute_monthly
from services.auth_service import is_unlocked
from database.proprietes_repo import fetch_all, fetch_dict
from database.pricing_repo import (
    get_evenements, save_evenement, delete_evenement,
    get_concurrents, save_concurrent, delete_concurrent,
)

MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]


# ─────────────────────────────────────────────────────────────────────────────
# Analyse IA (Claude)
# ─────────────────────────────────────────────────────────────────────────────

def _analyse_ia(prop_nom, prix_base, stats_df, evenements, concurrents):
    """Envoie les données à Claude et retourne une analyse pricing."""
    
    # Préparer le contexte
    stats_resume = ""
    if not stats_df.empty:
        for _, r in stats_df.iterrows():
            stats_resume += f"  - {r['mois_str']} {r['annee']}: taux occ={r['taux_occ']}%, rev/nuit={r['rev_nuit']}€, CA net={r['ca_net']:,.0f}€\n"
    
    evts_resume = ""
    for e in evenements[:10]:
        evts_resume += f"  - {e['nom']} ({e['date_debut']} → {e['date_fin']}): impact {e['impact']} +{e.get('pct_impact',0)}%\n"
    
    conc_resume = ""
    if concurrents:
        prix_conc = [c['prix_nuit'] for c in concurrents]
        conc_resume = f"  Prix concurrents observés: min={min(prix_conc):.0f}€, moy={sum(prix_conc)/len(prix_conc):.0f}€, max={max(prix_conc):.0f}€\n"
        for c in concurrents[-5:]:
            conc_resume += f"  - {c['concurrent']} ({c['plateforme']}): {c['prix_nuit']}€/nuit le {c['date_releve']}\n"

    prompt = f"""Tu es un expert en revenue management pour la location saisonnière en France.

Propriété : {prop_nom}
Prix de base actuel : {prix_base}€/nuit

Historique des performances (données réelles) :
{stats_resume if stats_resume else "  Pas encore de données historiques."}

Événements locaux programmés :
{evts_resume if evts_resume else "  Aucun événement saisi."}

Concurrents observés :
{conc_resume if conc_resume else "  Pas de données concurrentes saisies."}

Donne une analyse concise en 4 parties :
1. **Diagnostic** (2-3 phrases sur les performances actuelles)
2. **Opportunités** (mois ou périodes où le prix pourrait être augmenté)
3. **Points d'attention** (périodes creuses, prix trop élevés vs concurrents)
4. **3 recommandations concrètes** avec chiffres précis

Réponds en français, de façon pratique et directe. Maximum 300 mots."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 600,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if resp.status_code == 200:
            data = resp.json()
            return data["content"][0]["text"]
        else:
            return f"Erreur API ({resp.status_code})"
    except Exception as e:
        return f"Erreur de connexion : {e}"
MOIS_LONG = ["Janvier","Février","Mars","Avril","Mai","Juin",
             "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]


# ─────────────────────────────────────────────────────────────────────────────
# Calculs internes
# ─────────────────────────────────────────────────────────────────────────────

def _stats_historiques(df, prop_id):
    """Retourne stats mensuelles multi-années par propriété."""
    df_p = df[df["propriete_id"] == prop_id].copy() if prop_id else df.copy()
    df_p = df_p[df_p["plateforme"] != "Fermeture"]
    if df_p.empty:
        return pd.DataFrame()

    df_p["mois"]  = pd.to_datetime(df_p["date_arrivee"]).dt.month
    df_p["annee"] = pd.to_datetime(df_p["date_arrivee"]).dt.year

    rows = []
    for (an, m), grp in df_p.groupby(["annee", "mois"]):
        nuits  = float(grp["nuitees"].fillna(0).sum()) if "nuitees" in grp.columns else 0
        jours  = calendar.monthrange(int(an), int(m))[1]
        ca_net = float(grp["prix_net"].fillna(0).sum()) if "prix_net" in grp.columns else 0
        ca_brut= float(grp["prix_brut"].fillna(0).sum()) if "prix_brut" in grp.columns else 0
        rev_nuit = ca_net / nuits if nuits > 0 else 0
        rows.append({
            "annee": int(an), "mois": int(m),
            "mois_str": MOIS_FR[int(m)-1],
            "nuitees": nuits, "jours": jours,
            "taux_occ": round(nuits / jours * 100, 1),
            "ca_brut": ca_brut, "ca_net": ca_net,
            "rev_nuit": round(rev_nuit, 2),
        })
    return pd.DataFrame(rows)


def _prix_suggere(prix_base, taux_occ_hist, evenements_mois, taux_occ_actuel):
    """Calcule un prix suggéré avec ajustements dynamiques."""
    prix = prix_base

    # Ajustement taux occupation historique
    if taux_occ_hist > 85:
        prix *= 1.15   # forte demande → +15%
    elif taux_occ_hist > 70:
        prix *= 1.08   # bonne demande → +8%
    elif taux_occ_hist < 40:
        prix *= 0.90   # faible demande → -10%
    elif taux_occ_hist < 25:
        prix *= 0.80   # très faible → -20%

    # Ajustement événements
    for evt in evenements_mois:
        pct = evt.get("pct_impact", 0) / 100
        if evt.get("impact") == "hausse":
            prix *= (1 + pct)
        elif evt.get("impact") == "baisse":
            prix *= (1 - pct)

    # Ajustement taux occupation actuel (si année en cours)
    if taux_occ_actuel is not None:
        if taux_occ_actuel > 80:
            prix *= 1.05
        elif taux_occ_actuel < 30:
            prix *= 0.95

    return round(prix)


def _projection_ca(df_prop, tarifs_dict, annee_proj):
    """Projette le CA pour une année basée sur historique + réservations confirmées."""
    df_all = df_prop.copy()
    df_all["date_arrivee"] = pd.to_datetime(df_all["date_arrivee"])
    df_all["mois_num"]  = df_all["date_arrivee"].dt.month
    df_all["annee_num"] = df_all["date_arrivee"].dt.year

    df_conf = df_all[df_all["annee_num"] == annee_proj].copy()
    df_hist = df_all[df_all["annee_num"] <  annee_proj].copy()

    today = date.today()
    rows = []
    for m in range(1, 13):
        mois_str = MOIS_FR[m-1]
        nb_jours = calendar.monthrange(annee_proj, m)[1]
        mois_date = date(annee_proj, m, 1)
        passe = mois_date < date(today.year, today.month, 1)
        en_cours = mois_date.year == today.year and mois_date.month == today.month

        # CA confirmé — réservations de ce mois dans l'année projetée
        df_m = df_conf[df_conf["mois_num"] == m] if not df_conf.empty else pd.DataFrame()
        ca_confirme = float(df_m["prix_brut"].fillna(0).sum()) if not df_m.empty and "prix_brut" in df_m.columns else 0
        nuits_conf  = float(df_m["nuitees"].fillna(0).sum())   if not df_m.empty and "nuitees" in df_m.columns else 0

        # Moyenne historique même mois (3 dernières années)
        if not df_hist.empty:
            df_hist_m = df_hist[df_hist["mois_num"] == m]
            annees_hist = sorted(df_hist["annee"].unique())[-3:]
            ca_hist_vals = []
            for ah in annees_hist:
                df_ah = df_hist_m[df_hist_m["annee"] == ah]
                ca_hist_vals.append(float(df_ah["prix_brut"].fillna(0).sum()) if not df_ah.empty else 0)
            ca_hist_moy = np.mean(ca_hist_vals) if ca_hist_vals else 0
        else:
            ca_hist_moy = 0

        # Taux occupation historique
        nuits_hist = 0
        if not df_hist.empty and "nuitees" in df_hist.columns:
            nuits_hist = float(df_hist[df_hist["mois_num"] == m]["nuitees"].fillna(0).sum())
            nb_annees_hist = max(1, len(df_hist["annee_num"].unique()))
            nuits_hist_moy = nuits_hist / nb_annees_hist
            taux_occ_hist = round(nuits_hist_moy / nb_jours * 100, 1)
        else:
            taux_occ_hist = 0

        rows.append({
            "mois": m, "mois_str": mois_str, "nb_jours": nb_jours,
            "statut": "Passé" if passe else ("En cours" if en_cours else "À venir"),
            "ca_confirme": ca_confirme,
            "nuits_confirmees": nuits_conf,
            "ca_hist_moy": ca_hist_moy,
            "taux_occ_hist": taux_occ_hist,
            "taux_occ_confirme": round(nuits_conf / nb_jours * 100, 1),
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def show():
    st.title("📈 Revenus & Pricing")
    st.caption("Pricing dynamique · Benchmark concurrents · Prévisions de revenus")

    props_list = fetch_all()
    props_dict = {p["id"]: p for p in props_list}

    col1, col2 = st.columns(2)
    with col1:
        prop_id = st.selectbox(
            "🏠 Propriété",
            options=[p["id"] for p in props_list],
            format_func=lambda x: props_dict[x]["nom"],
            key="pricing_prop"
        )
    with col2:
        annee_proj = st.selectbox(
            "📅 Année",
            options=list(range(date.today().year + 1, date.today().year - 3, -1)),
            index=0, key="pricing_annee"
        )

    prop_nom = props_dict[prop_id]["nom"]

    df_all = load_reservations()
    if df_all.empty:
        st.warning("Aucune réservation disponible.")
        return
    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)
    # Accès limité aux propriétés déverrouillées
    from database.proprietes_repo import fetch_all as _fa
    _autorises = [p["id"] for p in _fa() if not p.get("mot_de_passe") or is_unlocked(p["id"])]
    df_all = df_all[df_all["propriete_id"].isin(_autorises)]
    df_prop = df_all[df_all["propriete_id"] == prop_id].copy()
    if "annee" not in df_prop.columns:
        df_prop["annee"] = pd.to_datetime(df_prop["date_arrivee"]).dt.year

    stats = _stats_historiques(df_prop, prop_id)

    tab1, tab2, tab3 = st.tabs([
        "💡 Pricing dynamique",
        "🏆 Benchmark concurrents",
        "🔮 Prévisions de revenus",
    ])

    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader(f"💡 Suggestions de prix — {prop_nom}")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            prix_base = st.number_input(
                "💶 Prix de base / nuit (€)",
                min_value=20, max_value=1000, value=100, step=5,
                key="prix_base",
                help="Votre prix standard hors saison"
            )
        with col_p2:
            annee_ref_prix = st.selectbox(
                "Basé sur historique",
                options=sorted(df_prop["annee"].dropna().unique().tolist(), reverse=True),
                key="annee_ref_prix"
            ) if not df_prop.empty else date.today().year

        evenements = get_evenements(prop_id)

        # Calcul suggestions par mois
        st.markdown("#### 📅 Prix suggérés mois par mois")
        sugg_rows = []
        for m in range(1, 13):
            stats_m = stats[(stats["annee"] == annee_ref_prix) & (stats["mois"] == m)] if not stats.empty else pd.DataFrame()
            taux_hist = float(stats_m["taux_occ"].iloc[0]) if not stats_m.empty else 0
            rev_nuit_hist = float(stats_m["rev_nuit"].iloc[0]) if not stats_m.empty else 0

            # Événements ce mois
            evts_m = [e for e in evenements if
                      pd.to_datetime(e["date_debut"]).month <= m <= pd.to_datetime(e["date_fin"]).month]

            prix_s = _prix_suggere(prix_base, taux_hist, evts_m, None)
            variation = round((prix_s - prix_base) / prix_base * 100) if prix_base > 0 else 0
            evts_noms = ", ".join([e["nom"] for e in evts_m]) if evts_m else "—"

            nb_jours_m = calendar.monthrange(annee_ref_prix, m)[1]
            ca_moy_hist  = float(stats_m["ca_net"].iloc[0]) if not stats_m.empty else 0
            ca_suggere   = round(prix_s * nb_jours_m * taux_hist / 100)
            sign = "+" if variation >= 0 else ""
            sugg_rows.append({
                "Mois":              MOIS_LONG[m-1],
                "Taux occ. hist.":   f"{taux_hist:.0f}%",
                "Rev. moy./nuit":    f"{rev_nuit_hist:.0f} €",
                "CA moy. mensuel":   f"{ca_moy_hist:,.0f} €",
                "Prix suggéré":      f"{prix_s} €",
                "CA suggéré":        f"{ca_suggere:,.0f} €",
                "Variation":         f"{sign}{variation}%",
                "Événements":        evts_noms,
            })

        df_sugg = pd.DataFrame(sugg_rows)

        # Ligne TOTAL
        def _num(s): 
            return float(s.replace(" €","").replace(",","").replace("%","")) if s not in ("—","") else 0
        
        total_row = {
            "Mois":             "**TOTAL / MOY.**",
            "Taux occ. hist.":  f"{sum(_num(r['Taux occ. hist.']) for r in sugg_rows)/12:.0f}%",
            "Rev. moy./nuit":   f"{sum(_num(r['Rev. moy./nuit']) for r in sugg_rows)/12:.0f} €",
            "CA moy. mensuel":  f"{sum(_num(r['CA moy. mensuel']) for r in sugg_rows):,.0f} €",
            "Prix suggéré":     f"{sum(_num(r['Prix suggéré']) for r in sugg_rows)/12:.0f} €",
            "CA suggéré":       f"{sum(_num(r['CA suggéré']) for r in sugg_rows):,.0f} €",
            "Variation":        f"{sum(_num(r['Variation']) for r in sugg_rows)/12:+.0f}%",
            "Événements":       "",
        }
        df_sugg = pd.concat([df_sugg, pd.DataFrame([total_row])], ignore_index=True)
        st.dataframe(df_sugg, use_container_width=True, hide_index=True)

        # Graphique
        prix_vals = [int(r["Prix suggéré"].replace(" €","").replace(",","")) for r in sugg_rows]
        colors    = ["#C62828" if v > prix_base * 1.1 else
                     "#2E7D32" if v < prix_base * 0.95 else
                     "#1565C0" for v in prix_vals]
        fig = go.Figure()
        fig.add_hline(y=prix_base, line_dash="dot", line_color="#888",
                      annotation_text="Prix base", annotation_position="right")
        fig.add_trace(go.Bar(
            x=MOIS_FR, y=prix_vals,
            marker_color=colors,
            text=[f"{v}€" for v in prix_vals],
            textposition="outside",
        ))
        fig.update_layout(height=320, margin=dict(t=30,b=10),
                          yaxis_title="€/nuit", showlegend=False,
                          yaxis=dict(range=[0, max(prix_vals)*1.2]))
        st.plotly_chart(fig, use_container_width=True)

        # ── Analyse IA ────────────────────────────────────────────────────
        st.divider()
        st.subheader("🤖 Analyse & recommandations IA")
        st.caption("Claude analyse votre historique, vos événements et vos concurrents pour vous conseiller.")

        if st.button("🤖 Générer l'analyse IA", type="primary", key="btn_ia_pricing"):
            with st.spinner("Claude analyse vos données..."):
                analyse = _analyse_ia(
                    prop_nom=prop_nom,
                    prix_base=prix_base,
                    stats_df=stats,
                    evenements=evenements,
                    concurrents=get_concurrents(prop_id),
                )
            st.markdown(analyse)
            st.caption("⚠️ Analyse indicative — à croiser avec votre connaissance du marché local.")

        # Gestion événements
        st.divider()
        st.subheader("📌 Événements locaux")
        st.caption("Les événements ajustent automatiquement les prix suggérés.")

        if evenements:
            df_evts = pd.DataFrame(evenements)
            st.dataframe(
                df_evts[["nom","date_debut","date_fin","impact","pct_impact","notes"]].rename(columns={
                    "nom":"Événement","date_debut":"Début","date_fin":"Fin",
                    "impact":"Impact","pct_impact":"% ajust.","notes":"Notes"
                }),
                use_container_width=True, hide_index=True
            )
            with st.expander("🗑️ Supprimer un événement"):
                del_e_opts = {e["id"]: f"{e['nom']} ({e['date_debut']})" for e in evenements}
                del_e_id = st.selectbox("Événement", list(del_e_opts.keys()),
                                         format_func=lambda x: del_e_opts[x], key="del_evt")
                if st.button("🗑️ Supprimer", key="btn_del_evt"):
                    delete_evenement(del_e_id); st.rerun()

        with st.expander("➕ Ajouter un événement", expanded=not evenements):
            with st.form("form_evt", clear_on_submit=True):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    e_nom    = st.text_input("Nom *", placeholder="Ex: Fête du Vin Bordeaux")
                    e_debut  = st.date_input("Date début", value=date.today())
                    e_impact = st.radio("Impact", ["hausse","baisse","neutre"], horizontal=True)
                with e_col2:
                    e_scope  = st.selectbox("Propriété concernée",
                                             ["Toutes"] + [p["nom"] for p in props_list])
                    e_fin    = st.date_input("Date fin",  value=date.today() + timedelta(days=3))
                    e_pct    = st.slider("Ajustement %", 0, 50, 20)
                e_notes  = st.text_input("Notes (optionnel)")
                if st.form_submit_button("➕ Ajouter", type="primary", use_container_width=True):
                    if e_nom:
                        pid_evt = None if e_scope == "Toutes" else next(
                            (p["id"] for p in props_list if p["nom"] == e_scope), None)
                        if save_evenement({"nom": e_nom, "date_debut": str(e_debut),
                                           "date_fin": str(e_fin), "impact": e_impact,
                                           "pct_impact": e_pct, "notes": e_notes,
                                           "propriete_id": pid_evt}):
                            st.success("✅ Événement ajouté !"); st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader(f"🏆 Benchmark concurrents — {prop_nom}")
        st.caption("Relevez manuellement les prix observés sur Airbnb / Booking pour comparer.")

        concurrents = get_concurrents(prop_id)

        # Statistiques si données
        if concurrents:
            df_conc = pd.DataFrame(concurrents)
            df_conc["date_releve"] = pd.to_datetime(df_conc["date_releve"])

            # Prix moyen concurrent vs nos prix
            prix_conc_moy = float(df_conc["prix_nuit"].mean())
            stats_notre = stats[(stats["annee"] == date.today().year)] if not stats.empty else pd.DataFrame()
            notre_prix_moy = float(stats_notre["rev_nuit"].mean()) if not stats_notre.empty else 0

            col_b1, col_b2, col_b3 = st.columns(3)
            col_b1.metric("💶 Prix moyen concurrents", f"{prix_conc_moy:.0f} €")
            col_b2.metric("💵 Notre prix moyen/nuit", f"{notre_prix_moy:.0f} €")
            delta = notre_prix_moy - prix_conc_moy
            col_b3.metric("📊 Écart", f"{delta:+.0f} €",
                          delta_color="normal" if delta >= 0 else "inverse")

            # Graphique prix par concurrent
            st.markdown("#### Prix observés par concurrent")
            fig_conc = px.scatter(
                df_conc,
                x="date_releve", y="prix_nuit",
                color="concurrent",
                symbol="plateforme",
                size_max=15,
                labels={"date_releve": "Date relevé", "prix_nuit": "Prix/nuit (€)",
                        "concurrent": "Concurrent", "plateforme": "Plateforme"},
                hover_data=["notes"]
            )
            if notre_prix_moy > 0:
                fig_conc.add_hline(y=notre_prix_moy, line_dash="dash",
                                   line_color="#1565C0",
                                   annotation_text="Notre prix moy.",
                                   annotation_position="right")
            fig_conc.update_layout(height=320, margin=dict(t=10,b=10))
            st.plotly_chart(fig_conc, use_container_width=True)

            # Tableau récap par concurrent
            st.markdown("#### Récapitulatif")
            recap_conc = df_conc.groupby(["concurrent","plateforme"])["prix_nuit"].agg(
                Relevés="count", Min="min", Moy="mean", Max="max"
            ).reset_index()
            recap_conc["Moy"] = recap_conc["Moy"].map("{:.0f} €".format)
            recap_conc["Min"] = recap_conc["Min"].map("{:.0f} €".format)
            recap_conc["Max"] = recap_conc["Max"].map("{:.0f} €".format)
            st.dataframe(recap_conc.rename(columns={
                "concurrent":"Concurrent","plateforme":"Plateforme"
            }), use_container_width=True, hide_index=True)

            # Suppression
            with st.expander("🗑️ Supprimer un relevé"):
                del_c_opts = {c["id"]: f"{c['concurrent']} — {c['date_releve']} — {c['prix_nuit']}€"
                               for c in concurrents}
                del_c_id = st.selectbox("Relevé", list(del_c_opts.keys()),
                                         format_func=lambda x: del_c_opts[x], key="del_conc")
                if st.button("🗑️ Supprimer", key="btn_del_conc"):
                    delete_concurrent(del_c_id); st.rerun()
        else:
            st.info("Aucun relevé concurrent. Ajoutez des prix ci-dessous.")

        st.divider()
        with st.expander("➕ Ajouter un relevé concurrent", expanded=not concurrents):
            with st.form("form_conc", clear_on_submit=True):
                c_col1, c_col2 = st.columns(2)
                with c_col1:
                    c_nom   = st.text_input("Nom du concurrent *", placeholder="Ex: Studio Port Vieux")
                    c_plat  = st.selectbox("Plateforme", ["Airbnb","Booking","Abritel","Direct","Autre"])
                    c_prix  = st.number_input("Prix/nuit observé (€)", min_value=0.0, step=5.0)
                with c_col2:
                    c_date  = st.date_input("Date du relevé", value=date.today())
                    c_lien  = st.text_input("Lien (optionnel)")
                    c_notes = st.text_input("Notes (dates concernées, type logement...)")
                if st.form_submit_button("➕ Ajouter", type="primary", use_container_width=True):
                    if c_nom and c_prix > 0:
                        if save_concurrent({"propriete_id": prop_id, "concurrent": c_nom,
                                            "plateforme": c_plat, "date_releve": str(c_date),
                                            "prix_nuit": float(c_prix), "lien": c_lien,
                                            "notes": c_notes}):
                            st.success("✅ Relevé ajouté !"); st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader(f"🔮 Prévisions de revenus — {prop_nom} — {annee_proj}")

        proj = _projection_ca(df_prop, {}, annee_proj)

        if proj.empty:
            st.warning("Données insuffisantes pour la projection.")
        else:
            # KPIs synthèse
            ca_confirme_total = proj["ca_confirme"].sum()
            ca_hist_total     = proj["ca_hist_moy"].sum()
            mois_restants     = proj[proj["statut"] == "À venir"]
            ca_proj_reste     = mois_restants["ca_hist_moy"].sum()
            ca_proj_total     = ca_confirme_total + ca_proj_reste

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("✅ CA confirmé",     f"{ca_confirme_total:,.0f} €",
                      help="Réservations déjà enregistrées")
            c2.metric("📅 Projection reste",f"{ca_proj_reste:,.0f} €",
                      help="Basé sur moyenne historique mois restants")
            c3.metric("🔮 Total projeté",   f"{ca_proj_total:,.0f} €")
            c4.metric("📊 Moy. historique", f"{ca_hist_total:,.0f} €",
                      delta=f"{(ca_proj_total-ca_hist_total)/ca_hist_total*100:+.1f}%" if ca_hist_total > 0 else None)

            st.divider()

            # Graphique waterfall mensuel
            fig = go.Figure()
            colors_bar = []
            for _, r in proj.iterrows():
                if r["statut"] == "Passé":
                    colors_bar.append("#1565C0")
                elif r["statut"] == "En cours":
                    colors_bar.append("#E65100")
                else:
                    colors_bar.append("#90CAF9")

            fig.add_trace(go.Bar(
                name="CA confirmé",
                x=proj["mois_str"], y=proj["ca_confirme"],
                marker_color="#1565C0",
                text=proj["ca_confirme"].apply(lambda v: f"{v:,.0f}€" if v > 0 else ""),
                textposition="outside",
            ))
            fig.add_trace(go.Bar(
                name="Projection historique",
                x=proj["mois_str"], y=proj["ca_hist_moy"],
                marker_color="#90CAF9",
                marker_pattern_shape="/",
                opacity=0.7,
            ))
            fig.add_trace(go.Scatter(
                name="Taux occupation hist. (%)",
                x=proj["mois_str"], y=proj["taux_occ_hist"],
                mode="lines+markers",
                line=dict(color="#E65100", width=2, dash="dot"),
                yaxis="y2",
            ))
            fig.update_layout(
                barmode="overlay",
                height=380, margin=dict(t=20,b=10),
                legend=dict(orientation="h", y=1.08),
                yaxis=dict(title="CA (€)"),
                yaxis2=dict(title="Taux occ. (%)", overlaying="y", side="right",
                            range=[0,100]),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Légende couleurs
            st.markdown(
                "🔵 **Passé** (réservations confirmées) &nbsp;|&nbsp; "
                "🟠 **Mois en cours** &nbsp;|&nbsp; "
                "🔷 **À venir** (projection historique)"
            )

            # Tableau détail
            st.markdown("#### 📋 Détail mensuel")

            # Ligne TOTAL avant formatage
            total_row = pd.DataFrame([{
                "mois_str":           "**TOTAL**",
                "statut":             "",
                "ca_confirme":        proj["ca_confirme"].sum(),
                "ca_hist_moy":        proj["ca_hist_moy"].sum(),
                "taux_occ_confirme":  proj["taux_occ_confirme"].mean(),
                "taux_occ_hist":      proj["taux_occ_hist"].mean(),
                "nuits_confirmees":   proj["nuits_confirmees"].sum(),
            }])
            df_with_total = pd.concat([proj, total_row], ignore_index=True)

            df_display = df_with_total.copy()
            df_display["ca_confirme"]       = df_display["ca_confirme"].map("{:,.0f} €".format)
            df_display["ca_hist_moy"]       = df_display["ca_hist_moy"].map("{:,.0f} €".format)
            df_display["taux_occ_hist"]     = df_display["taux_occ_hist"].map("{:.0f}%".format)
            df_display["taux_occ_confirme"] = df_display["taux_occ_confirme"].map("{:.0f}%".format)
            df_display["nuits_confirmees"]  = df_display["nuits_confirmees"].map("{:.0f}".format)

            st.dataframe(
                df_display[["mois_str","statut","ca_confirme","ca_hist_moy",
                             "taux_occ_confirme","taux_occ_hist","nuits_confirmees"]].rename(columns={
                    "mois_str": "Mois", "statut": "Statut",
                    "ca_confirme": "CA confirmé", "ca_hist_moy": "Moy. historique",
                    "taux_occ_confirme": "Taux occ. conf.", "taux_occ_hist": "Taux occ. hist.",
                    "nuits_confirmees": "Nuits conf.",
                }),
                use_container_width=True, hide_index=True
            )

            st.caption(
                "💡 La **projection** est basée sur la moyenne des 3 dernières années pour chaque mois. "
                "Plus vous avez d'historique, plus la projection est fiable."
            )
