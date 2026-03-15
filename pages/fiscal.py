"""
Page Tableau de bord fiscal — LMNP / Meublé tourisme
Suivi seuils micro-BIC, estimation impôt, cotisations sociales
"""
import streamlit as st
from datetime import date
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from services.reservation_service import load_reservations
from database.proprietes_repo import fetch_all

# ─── Barèmes fiscaux 2024/2025 ───────────────────────────────────────────────

# ─── Loi de finances 2024 (applicable revenus 2025+) ────────────────────────
# Avant 2025 : classé 71% / seuil 188 700€ — non classé 50% / seuil 77 700€
# Après 2025  : classé 50% / seuil 77 700€  — non classé 30% / seuil 15 000€
# Source : art. 45 LFR 2024 — applicable déclarations 2025 sur revenus 2024
#          MAIS report partiel : loi 2024 votée fin 2024, revenus 2023 non touchés
#          Revenus 2024 : anciens taux maintenus (report voté)
#          Revenus 2025+ : nouveaux taux applicables

BAREMES = {
    2026: {
        # Nouveaux taux LFR 2024 — applicables revenus 2025+
        "micro_bic_classe_seuil":      77700,   # abaissé (= niveau non classé avant)
        "micro_bic_non_classe_seuil":  15000,   # très fortement abaissé
        "abattement_classe":           0.50,    # réduit de 71% → 50%
        "abattement_non_classe":       0.30,    # réduit de 50% → 30%
        "abattement_min_classe":       305,
        "loi_note": "LFR 2024 — nouveaux taux (revenus 2025+)",
        "tranches_ir": [
            (0,     11497,  0.00),
            (11497, 29315,  0.11),
            (29315, 83823,  0.30),
            (83823, 180294, 0.41),
            (180294, None,  0.45),
        ],
        "cotisations_ssi_taux":    0.231,
        "cotisations_urssaf_taux": 0.172,
        "csg_crds":                0.172,
        "seuil_cotisations":       23000,
    },
    2025: {
        # Nouveaux taux LFR 2024 — applicables revenus 2025
        "micro_bic_classe_seuil":      77700,
        "micro_bic_non_classe_seuil":  15000,
        "abattement_classe":           0.50,
        "abattement_non_classe":       0.30,
        "abattement_min_classe":       305,
        "loi_note": "LFR 2024 — nouveaux taux (revenus 2025+)",
        "tranches_ir": [
            (0,     11294,  0.00),
            (11294, 28797,  0.11),
            (28797, 82341,  0.30),
            (82341, 177106, 0.41),
            (177106, None,  0.45),
        ],
        "cotisations_ssi_taux":    0.231,
        "cotisations_urssaf_taux": 0.172,
        "csg_crds":                0.172,
        "seuil_cotisations":       23000,
    },
    2024: {
        # Anciens taux — revenus 2024 (report voté, ancienne loi maintenue)
        "micro_bic_classe_seuil":      188700,
        "micro_bic_non_classe_seuil":   77700,
        "abattement_classe":            0.71,
        "abattement_non_classe":        0.50,
        "abattement_min_classe":        305,
        "loi_note": "Ancienne loi — taux 2024 (71%/50%)",
        "tranches_ir": [
            (0,     11294,  0.00),
            (11294, 28797,  0.11),
            (28797, 82341,  0.30),
            (82341, 177106, 0.41),
            (177106, None,  0.45),
        ],
        "cotisations_ssi_taux":    0.231,
        "cotisations_urssaf_taux": 0.172,
        "csg_crds":                0.172,
        "seuil_cotisations":       23000,
    },
    2023: {
        # Anciens taux
        "micro_bic_classe_seuil":      188700,
        "micro_bic_non_classe_seuil":   77700,
        "abattement_classe":            0.71,
        "abattement_non_classe":        0.50,
        "abattement_min_classe":        305,
        "loi_note": "Ancienne loi — taux 2023 (71%/50%)",
        "tranches_ir": [
            (0,     10777,  0.00),
            (10777, 27478,  0.11),
            (27478, 78570,  0.30),
            (78570, 168994, 0.41),
            (168994, None,  0.45),
        ],
        "cotisations_ssi_taux":    0.231,
        "cotisations_urssaf_taux": 0.172,
        "csg_crds":                0.172,
        "seuil_cotisations":       23000,
    },
}


def _impot_tranche(revenu_imposable: float, b: dict) -> float:
    """Calcule l'IR sur 1 part fiscale (célibataire) — à ajuster selon quotient."""
    impot = 0.0
    for bas, haut, taux in b["tranches_ir"]:
        if revenu_imposable <= bas:
            break
        plafond = haut if haut else float("inf")
        impot += min(revenu_imposable, plafond) - bas if revenu_imposable > bas else 0
        impot_tranche = (min(revenu_imposable, plafond) - bas) * taux if revenu_imposable > bas else 0
        # recalcul propre
    # recalcul correct
    impot = 0.0
    for bas, haut, taux in b["tranches_ir"]:
        plafond = haut if haut is not None else revenu_imposable + 1
        if revenu_imposable > bas:
            impot += (min(revenu_imposable, plafond) - bas) * taux
    return round(impot, 2)


def _micro_bic(ca: float, classe: bool, b: dict):
    abatt_taux = b["abattement_classe"] if classe else b["abattement_non_classe"]
    abatt_min  = b["abattement_min_classe"] if classe else 0
    abattement = max(ca * abatt_taux, abatt_min)
    revenu_net = max(0, ca - abattement)
    return abattement, revenu_net


def _couleur_seuil(pct):
    if pct < 0.70: return "#4CAF50"
    if pct < 0.90: return "#FF9800"
    return "#F44336"


def _jauge(label, valeur, seuil, unite="€"):
    pct = min(valeur / seuil, 1.0) if seuil > 0 else 0
    couleur = _couleur_seuil(pct)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=valeur,
        delta={"reference": seuil, "valueformat": ",.0f", "suffix": unite},
        number={"valueformat": ",.0f", "suffix": f" {unite}"},
        title={"text": label, "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, seuil * 1.1], "tickformat": ",.0f"},
            "bar":  {"color": couleur},
            "steps": [
                {"range": [0, seuil * 0.70], "color": "#E8F5E9"},
                {"range": [seuil * 0.70, seuil * 0.90], "color": "#FFF3E0"},
                {"range": [seuil * 0.90, seuil * 1.1],  "color": "#FFEBEE"},
            ],
            "threshold": {
                "line": {"color": "#B71C1C", "width": 3},
                "thickness": 0.85,
                "value": seuil
            }
        }
    ))
    fig.update_layout(height=220, margin=dict(t=40, b=10, l=20, r=20))
    return fig


# ─────────────────────────────────────────────────────────────────────────────

def show():
    st.title("🏛️ Tableau de bord fiscal")
    st.caption("LMNP — Meublé de tourisme — Suivi micro-BIC & estimation fiscale")

    # ── Paramètres ────────────────────────────────────────────────────────
    with st.expander("⚙️ Paramètres fiscaux", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            annee = st.selectbox("Année fiscale",
                                  list(range(date.today().year, 2022, -1)), key="fisc_annee",
                                  help="2025+ : nouveaux taux LFR 2024 (50%/30%) | 2024 et avant : anciens taux (71%/50%)")
        with col2:
            classement = st.radio("Classement meublé tourisme",
                                   ["Non classé", "Classé / Gîte de France"],
                                   index=1,
                                   key="fisc_class")
        with col3:
            nb_parts = st.number_input("Quotient familial (parts)",
                                        min_value=1.0, max_value=5.0, value=1.0,
                                        step=0.5, key="fisc_parts")
        with col4:
            autres_revenus = st.number_input("Autres revenus imposables (€)",
                                              min_value=0, value=0, step=1000,
                                              key="fisc_autres",
                                              help="Salaires, pensions, autres BIC...")

    b = BAREMES.get(annee, BAREMES[2025])
    classe = "Classé" in classement or "Gîte" in classement
    seuil_applicable = b["micro_bic_classe_seuil"] if classe else b["micro_bic_non_classe_seuil"]
    abatt_taux = b["abattement_classe"] if classe else b["abattement_non_classe"]

    # Badge récapitulatif taux applicables
    loi = b.get("loi_note","")
    st.caption(f"📋 **{loi}** — Abattement applicable : **{abatt_taux*100:.0f}%** | Seuil : **{seuil_applicable:,.0f} €**")

    # ── Chargement données ────────────────────────────────────────────────
    df_all = load_reservations()
    props  = {p["id"]: p for p in fetch_all()}

    if df_all.empty:
        st.warning("Aucune réservation disponible.")
        return

    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)
    df_an = df_all[df_all["annee"] == annee] if "annee" in df_all.columns else df_all
    df_an = df_an[df_an["plateforme"] != "Fermeture"].copy()

    # ── Filtre plateforme global ──────────────────────────────────────────
    plateformes_dispo = sorted(df_an["plateforme"].dropna().unique().tolist())
    plat_fisc = st.multiselect(
        "🔀 Filtrer par plateforme",
        options=plateformes_dispo,
        default=[],
        key="fisc_plat",
        placeholder="Toutes les plateformes"
    )
    if plat_fisc:
        df_an = df_an[df_an["plateforme"].isin(plat_fisc)]

    ca_total = float(df_an["prix_brut"].fillna(0).sum()) if "prix_brut" in df_an.columns else 0.0
    # Recettes = CA brut total (ce que le locataire a payé)
    # Pour LMNP le CA déclaré = recettes brutes encaissées

    # ── Onglets ───────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Seuils & Alertes",
        "💶 Estimation fiscale",
        "⚖️ Micro-BIC vs Réel",
        "🧾 Cotisations sociales",
        "📅 Projection annuelle",
    ])

    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader(f"📊 Seuils micro-BIC {annee}")

        # CA par propriété
        ca_par_prop = {}
        for pid, prop in props.items():
            df_p = df_an[df_an["propriete_id"] == pid]
            ca_par_prop[pid] = float(df_p["prix_brut"].fillna(0).sum()) if not df_p.empty else 0.0

        # Jauges
        cols = st.columns(max(1, len(props)))
        for i, (pid, prop) in enumerate(props.items()):
            ca = ca_par_prop.get(pid, 0)
            pct = ca / seuil_applicable if seuil_applicable > 0 else 0
            couleur = _couleur_seuil(pct)
            with cols[i % len(cols)]:
                st.plotly_chart(
                    _jauge(prop["nom"], ca, seuil_applicable),
                    use_container_width=True, key=f"jauge_{pid}"
                )
                reste = seuil_applicable - ca
                if reste > 0:
                    st.markdown(
                        f"<div style='background:{couleur}22;border-left:4px solid {couleur};"
                        f"padding:8px;border-radius:4px;font-size:13px'>"
                        f"<b>{pct*100:.1f}%</b> du seuil utilisé<br>"
                        f"Reste disponible : <b>{reste:,.0f} €</b></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.error(f"⚠️ Seuil dépassé de {abs(reste):,.0f} € — passage au réel obligatoire !")

        st.divider()

        # Tableau récap seuils
        st.subheader("📋 Récapitulatif des seuils")
        seuils_data = {
            "Régime": [
                "Micro-BIC non classé",
                "Micro-BIC classé / Gîte ⭐",
                "TVA (franchise en base)",
                "SSI obligatoire",
            ],
            "Seuil": [
                f"{b['micro_bic_non_classe_seuil']:,.0f} €",
                f"{b['micro_bic_classe_seuil']:,.0f} €",
                "91 900 €",
                "23 000 €",
            ],
            "Abattement": [
                f"{b['abattement_non_classe']*100:.0f}%",
                f"{b['abattement_classe']*100:.0f}%",
                "N/A", "N/A",
            ],
            "Votre CA": [f"{ca_total:,.0f} €"] * 4,
            "Statut": [
                "✅ OK" if ca_total < b["micro_bic_non_classe_seuil"] else "⛔ Dépassé",
                "✅ OK" if ca_total < b["micro_bic_classe_seuil"] else "⛔ Dépassé",
                "✅ OK" if ca_total < 91900 else "⚠️ Vérifier",
                "✅ OK" if ca_total < 23000 else "⚠️ Vérifier",
            ]
        }

        # Badge loi applicable
        loi_note = b.get("loi_note", "")
        if "nouveaux" in loi_note:
            st.warning(f"⚠️ **{loi_note}** — Abattements réduits : classé 50% (au lieu de 71%), non classé 30% (au lieu de 50%). Seuils également abaissés.")
        else:
            st.info(f"ℹ️ **{loi_note}** — Anciens taux en vigueur.")

        st.dataframe(pd.DataFrame(seuils_data), use_container_width=True, hide_index=True)

        # Note TVA
        st.info("""
**💡 TVA — Franchise en base :** Tant que vos recettes restent sous 91 900 €, vous n'êtes pas soumis à la TVA
(régime LMNP). Au-delà, TVA collectée à 10% sur les prestations para-hôtelières (ménage, petit-déjeuner...).

**💡 Seuil SSI :** Si vos recettes de location meublée dépassent 23 000 € ET représentent plus de 50%
de vos revenus du foyer, vous basculez en LMP (Loueur Meublé Professionnel) avec cotisations SSI.
        """)

    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader(f"💶 Estimation impôt {annee}")
        st.caption("Simulation indicative — consultez un expert-comptable pour votre situation réelle.")

        # ── Filtre propriété ──────────────────────────────────────────────
        props_opt_t2 = {0: "Toutes les propriétés"}
        props_opt_t2.update({p["id"]: p["nom"] for p in props.values()})
        prop_id_t2 = st.selectbox(
            "🏠 Propriété (foyer fiscal)",
            options=list(props_opt_t2.keys()),
            format_func=lambda x: props_opt_t2[x],
            key="prop_t2",
            help="Chaque bien est un foyer fiscal distinct"
        )
        df_t2 = df_an if prop_id_t2 == 0 else df_an[df_an["propriete_id"] == prop_id_t2]
        ca_t2 = float(df_t2["prix_brut"].fillna(0).sum()) if "prix_brut" in df_t2.columns else 0.0
        st.caption(f"CA {annee} — **{props_opt_t2[prop_id_t2]}** : **{ca_t2:,.0f} €**")
        st.divider()

        abattement, revenu_bic = _micro_bic(ca_t2, classe, b)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Calcul Micro-BIC**")
            st.markdown(f"""
| Étape | Montant |
|-------|---------|
| CA Brut (recettes) | **{ca_t2:,.0f} €** |
| Abattement {abatt_taux*100:.0f}% | — {abattement:,.0f} € |
| **Revenu BIC net** | **{revenu_bic:,.0f} €** |
| Autres revenus | + {autres_revenus:,.0f} € |
| **Revenu total imposable** | **{revenu_bic + autres_revenus:,.0f} €** |
""")

        revenu_total = revenu_bic + autres_revenus
        ir_brut = _impot_tranche(revenu_total, b)
        ir_par_part = _impot_tranche(revenu_total / nb_parts, b) * nb_parts
        csg = ca_t2 * b["csg_crds"]   # CSG/CRDS sur revenus patrimoine

        with col2:
            st.markdown("**Estimation fiscale**")
            st.markdown(f"""
| Poste | Montant estimé |
|-------|----------------|
| IR (1 part) | {ir_brut:,.0f} € |
| IR ({nb_parts:.1f} parts) | **{ir_par_part:,.0f} €** |
| CSG/CRDS (17,2%) | {csg:,.0f} € |
| **Total prélèvements** | **{ir_par_part + csg:,.0f} €** |
| Taux effectif | {((ir_par_part + csg)/ca_t2*100):.1f}% du CA |
""")

        st.divider()

        # Répartition visuelle
        if ca_t2 > 0:
            charges = ir_par_part + csg
            net_apres_impot = ca_t2 - charges
            labels = ["Net après impôt", "IR estimé", "CSG/CRDS"]
            values = [max(0, net_apres_impot), ir_par_part, csg]
            colors = ["#2E7D32", "#1565C0", "#E65100"]
            fig = go.Figure(go.Pie(
                labels=labels, values=values,
                hole=0.5,
                marker_colors=colors,
                textinfo="label+percent",
            ))
            fig.update_layout(height=280, margin=dict(t=10, b=10),
                              showlegend=True,
                              annotations=[{"text": f"{net_apres_impot:,.0f}€<br>net", "showarrow": False, "font_size": 13}])
            st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("⚖️ Comparaison Micro-BIC vs Régime Réel")

        # ── Filtre propriété ──────────────────────────────────────────────
        props_options = {0: "Toutes les propriétés"}
        props_options.update({p["id"]: p["nom"] for p in props.values()})
        prop_id_reel = st.selectbox(
            "🏠 Propriété (foyer fiscal)",
            options=list(props_options.keys()),
            format_func=lambda x: props_options[x],
            key="reel_prop",
            help="Chaque bien est un foyer fiscal distinct — sélectionnez la propriété à analyser"
        )
        if prop_id_reel == 0:
            df_reel_prop = df_an
            prop_label_reel = "Toutes les propriétés"
        else:
            df_reel_prop = df_an[df_an["propriete_id"] == prop_id_reel]
            prop_label_reel = props_options[prop_id_reel]

        ca_reel_prop = float(df_reel_prop["prix_brut"].fillna(0).sum()) if "prix_brut" in df_reel_prop.columns else 0.0
        st.caption(f"CA {annee} — **{prop_label_reel}** : **{ca_reel_prop:,.0f} €**")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Vos charges réelles estimées**")
            charges_amort    = st.number_input("Amortissements (€/an)", 0, 50000, 5000, 500, key="reel_amort")
            charges_travaux  = st.number_input("Travaux & entretien (€)",  0, 50000, 1000, 100, key="reel_trav")
            charges_gestion  = st.number_input("Frais gestion / compta (€)", 0, 10000, 500, 100, key="reel_gest")
            charges_assur    = st.number_input("Assurances (€)", 0, 5000, 300, 50, key="reel_assur")
            charges_copro    = st.number_input("Charges copropriété (€)", 0, 10000, 800, 100, key="reel_copro")
            charges_autres   = st.number_input("Autres charges (€)", 0, 20000, 0, 100, key="reel_autres")

        total_charges_reelles = charges_amort + charges_travaux + charges_gestion + charges_assur + charges_copro + charges_autres
        revenu_reel = max(0, ca_reel_prop - total_charges_reelles)
        ir_reel     = _impot_tranche(revenu_reel + autres_revenus, b) * nb_parts if nb_parts >= 1 else _impot_tranche(revenu_reel + autres_revenus, b)
        csg_reel    = revenu_reel * b["csg_crds"]

        abattement_micro, revenu_micro = _micro_bic(ca_reel_prop, classe, b)
        ir_micro = _impot_tranche((revenu_micro + autres_revenus) / nb_parts, b) * nb_parts
        csg_micro = ca_reel_prop * b["csg_crds"]

        with col2:
            total_reel  = ir_reel + csg_reel
            total_micro = ir_micro + csg_micro
            economie    = total_micro - total_reel
            st.markdown("**Comparaison**")
            st.markdown(f"""
|  | Micro-BIC | Réel simplifié |
|--|-----------|----------------|
| **Revenu brut (CA)** | **{ca_reel_prop:,.0f} €** | **{ca_reel_prop:,.0f} €** |
| Abattement / Charges déduites | {abattement_micro:,.0f} € ({abatt_taux*100:.0f}%) | {total_charges_reelles:,.0f} € |
| **Revenu imposable** | **{revenu_micro:,.0f} €** | **{revenu_reel:,.0f} €** |
| IR estimé | {ir_micro:,.0f} € | {ir_reel:,.0f} € |
| CSG/CRDS | {csg_micro:,.0f} € | {csg_reel:,.0f} € |
| **Total prélèvements** | **{total_micro:,.0f} €** | **{total_reel:,.0f} €** |
| **Net après impôt** | **{ca_reel_prop - total_micro:,.0f} €** | **{ca_reel_prop - total_reel:,.0f} €** |
""")
            if economie > 0:
                st.success(f"✅ Le **régime réel** vous ferait économiser **{economie:,.0f} €** cette année.")
            elif economie < 0:
                st.info(f"💡 Le **micro-BIC** est plus avantageux de **{abs(economie):,.0f} €** cette année.")
            else:
                st.info("Les deux régimes sont équivalents.")

            # Bar chart comparatif
            fig = go.Figure()
            for regime, ir, csg_v in [("Micro-BIC", ir_micro, csg_micro), ("Réel simplifié", ir_reel, csg_reel)]:
                fig.add_trace(go.Bar(name="IR", x=[regime], y=[ir], marker_color="#1565C0"))
                fig.add_trace(go.Bar(name="CSG/CRDS", x=[regime], y=[csg_v], marker_color="#E65100"))
            fig.update_layout(barmode="stack", height=250,
                              margin=dict(t=10,b=10), showlegend=True,
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════════════════════
    with tab4:
        st.subheader("🧾 Cotisations sociales & prélèvements")
        st.caption("Simulation selon votre statut LMNP/LMP et vos recettes.")

        # ── Filtre propriété ──────────────────────────────────────────────
        props_opt_t4 = {0: "Toutes les propriétés"}
        props_opt_t4.update({p["id"]: p["nom"] for p in props.values()})
        prop_id_t4 = st.selectbox(
            "🏠 Propriété (foyer fiscal)",
            options=list(props_opt_t4.keys()),
            format_func=lambda x: props_opt_t4[x],
            key="prop_t4",
            help="Chaque bien est un foyer fiscal distinct"
        )
        df_t4 = df_an if prop_id_t4 == 0 else df_an[df_an["propriete_id"] == prop_id_t4]
        ca_t4 = float(df_t4["prix_brut"].fillna(0).sum()) if "prix_brut" in df_t4.columns else 0.0
        st.caption(f"CA {annee} — **{props_opt_t4[prop_id_t4]}** : **{ca_t4:,.0f} €**")
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            statut = st.radio("Statut locatif",
                ["LMNP (Loueur Meublé Non Professionnel)",
                 "LMP (Loueur Meublé Professionnel)"],
                key="fisc_statut",
                help="LMP si recettes > 23 000€ ET > 50% revenus du foyer"
            )
            regime_social = st.radio("Régime social",
                ["Pas de cotisations SSI (LMNP pur)",
                 "Micro-entrepreneur (URSSAF)",
                 "TNS / Régime réel SSI"],
                key="fisc_regime_soc"
            )

        with col2:
            st.markdown("**Récapitulatif recettes**")
            st.metric("CA Brut total", f"{ca_t4:,.0f} €")
            abatt_m, rev_bic_m = _micro_bic(ca_t4, classe, b)
            st.metric(f"Revenu BIC net (abatt. {abatt_taux*100:.0f}%)", f"{rev_bic_m:,.0f} €")
            is_lmp = ca_t4 > b["seuil_cotisations"]
            if is_lmp:
                st.warning(f"⚠️ Recettes > {b['seuil_cotisations']:,} € → Vérifiez si LMP s'applique")
            else:
                st.success(f"✅ Recettes < {b['seuil_cotisations']:,} € → Pas de SSI obligatoire")

        st.divider()

        # ── Calcul cotisations selon régime ──────────────────────────────
        st.subheader("📋 Détail des cotisations")

        if "Pas de cotisations" in regime_social:
            # LMNP classique : CSG/CRDS sur revenus du patrimoine uniquement
            csg_patrim = rev_bic_m * 0.172
            rows_cot = [
                ("CSG (9,9%)",                   rev_bic_m * 0.099),
                ("CRDS (0,5%)",                  rev_bic_m * 0.005),
                ("Prélèvement solidarité (7,5%)", rev_bic_m * 0.075),
                ("Prélèvement libératoire",       0.0),
            ]
            total_cot = csg_patrim
            st.info("**LMNP — Prélèvements sociaux sur revenus du patrimoine (17,2%)** — Pas de cotisations SSI obligatoires.")

        elif "Micro-entrepreneur" in regime_social:
            # Taux micro-entrepreneur meublé tourisme classé : 6% (2024)
            taux_me = 0.06 if classe else 0.06
            cot_me  = ca_t4 * taux_me
            csg_me  = ca_t4 * 0.172
            rows_cot = [
                ("Cotisations sociales micro-entrepreneur (6%)", cot_me),
                ("CSG/CRDS (inclus dans taux)",                  0.0),
                ("CFE (Cotisation Foncière Entreprises)",         "Variable"),
            ]
            total_cot = cot_me
            st.info("**Micro-entrepreneur meublé de tourisme classé** Taux global : 6% sur CA — inclut retraite, maladie, famille.")

        else:
            # TNS / SSI régime réel
            taux_ssi = b["cotisations_ssi_taux"]
            base_ssi = rev_bic_m
            cot_maladie  = base_ssi * 0.013  # maladie
            cot_retraite = base_ssi * 0.178  # retraite base + compl
            cot_famille  = base_ssi * 0.031  # allocations familiales
            cot_invalid  = base_ssi * 0.013  # invalidité/décès
            cot_csg      = base_ssi * 0.097  # CSG déductible
            cot_crds     = base_ssi * 0.005  # CRDS
            total_cot    = base_ssi * taux_ssi
            rows_cot = [
                ("Maladie (1,3%)",              cot_maladie),
                ("Retraite de base + compl. (17,8%)", cot_retraite),
                ("Allocations familiales (3,1%)", cot_famille),
                ("Invalidité/Décès (1,3%)",     cot_invalid),
                ("CSG déductible (9,7%)",        cot_csg),
                ("CRDS (0,5%)",                  cot_crds),
            ]
            st.info(f"**Régime TNS/SSI — Base : revenu BIC net ({rev_bic_m:,.0f} €)**")

        # Tableau cotisations
        rows_display = []
        total_num = 0.0
        for poste, montant in rows_cot:
            if isinstance(montant, float):
                rows_display.append({"Poste": poste, "Montant": f"{montant:,.0f} €"})
                total_num += montant
            else:
                rows_display.append({"Poste": poste, "Montant": str(montant)})
        rows_display.append({"Poste": "**TOTAL COTISATIONS**", "Montant": f"**{total_num:,.0f} €**"})
        st.dataframe(pd.DataFrame(rows_display), use_container_width=True, hide_index=True)

        st.divider()

        # ── Synthèse globale prélèvements ─────────────────────────────────
        st.subheader("📊 Synthèse globale des prélèvements")

        abatt_m2, rev_bic_m2 = _micro_bic(ca_t4, classe, b)
        ir_final = _impot_tranche((rev_bic_m2 + autres_revenus) / nb_parts, b) * nb_parts
        csg_ir   = ca_total * b["csg_crds"] if "Pas de cotisations" in regime_social else 0

        total_prelevements = ir_final + csg_ir + total_num
        net_final = ca_t4 - total_prelevements

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💶 CA Brut",             f"{ca_t4:,.0f} €")
        c2.metric("🏛️ IR estimé",           f"{ir_final:,.0f} €")
        c3.metric("🧾 Cotisations sociales", f"{total_num:,.0f} €")
        c4.metric("💵 Net après tout",       f"{net_final:,.0f} €",
                  delta=f"{net_final/ca_t4*100:.1f}% du CA" if ca_t4 > 0 else "")

        if ca_t4 > 0:
            fig = go.Figure(go.Waterfall(
                name="", orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["CA Brut", f"Abattement {abatt_taux*100:.0f}%",
                   "IR estimé", "Cotisations", "Net final"],
                y=[ca_t4, -abatt_m2, -ir_final, -total_num, 0],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "#2E7D32"}},
                decreasing={"marker": {"color": "#C62828"}},
                totals={"marker": {"color": "#1565C0"}},
            ))
            fig.update_layout(height=320, margin=dict(t=10, b=10),
                              showlegend=False, yaxis_title="€")
            st.plotly_chart(fig, use_container_width=True)

    with tab5:
        st.subheader(f"📅 Projection annuelle {annee}")

        df_mois = df_an.copy()
        if not df_mois.empty and "date_arrivee" in df_mois.columns:
            df_mois["mois"] = pd.to_datetime(df_mois["date_arrivee"]).dt.month
            ca_par_mois = df_mois.groupby("mois")["prix_brut"].sum().reindex(range(1,13), fill_value=0)
            ca_cumul    = ca_par_mois.cumsum()

            MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=MOIS_FR, y=ca_par_mois.values,
                name="CA mensuel", marker_color="#90CAF9"
            ))
            fig.add_trace(go.Scatter(
                x=MOIS_FR, y=ca_cumul.values,
                name="Cumul annuel", mode="lines+markers",
                line=dict(color="#1565C0", width=2),
                yaxis="y2"
            ))
            # Lignes seuils
            for seuil_v, label_s, color_s in [
                (23000,  "Seuil SSI", "#FF9800"),
                (77700,  "Seuil non classé", "#F44336"),
                (188700, "Seuil classé", "#9C27B0"),
            ]:
                fig.add_hline(y=seuil_v, line_dash="dot", line_color=color_s,
                              annotation_text=label_s, annotation_position="right",
                              yref="y2")

            fig.update_layout(
                height=380,
                margin=dict(t=10, b=30),
                legend=dict(orientation="h", y=1.05),
                yaxis=dict(title="CA mensuel (€)"),
                yaxis2=dict(title="Cumul (€)", overlaying="y", side="right"),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Projection fin d'année
            mois_en_cours = date.today().month if annee == date.today().year else 12
            if mois_en_cours < 12 and ca_total > 0:
                ca_moyen_mensuel = ca_total / mois_en_cours
                ca_projete = ca_moyen_mensuel * 12
                st.info(
                    f"📈 **Projection fin {annee}** (base CA moyen mensuel {ca_moyen_mensuel:,.0f} €) : "
                    f"**{ca_projete:,.0f} €**  "
                    + ("⛔ Dépassement seuil prévu !" if ca_projete > seuil_applicable
                       else f"— reste {seuil_applicable - ca_projete:,.0f} € de marge.")
                )
        else:
            st.info("Données mensuelles insuffisantes pour la projection.")

    # ── Disclaimer ───────────────────────────────────────────────────────
    st.caption(
        "⚠️ Ce tableau de bord est un outil d'aide à la décision. "
        "Les calculs sont indicatifs et ne remplacent pas l'avis d'un expert-comptable. "
        f"Barèmes {annee} — sources DGFiP / BOFIP."
    )
