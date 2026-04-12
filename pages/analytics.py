import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from services.reservation_service import load_reservations
from services.analytics_service import compute_kpis, compute_monthly
PLATEFORME_FERMETURE = "Fermeture"  # local fallback
from services.proprietes_service import get_proprietes_dict
import calendar

MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]
COULEURS = ["#1565C0","#E65100","#2E7D32","#6A1B9A","#00838F"]  # 1 couleur par année


# ─────────────────────────────────────────────────────────────────────────────
# Comparatif pluriannuel
# ─────────────────────────────────────────────────────────────────────────────

def _build_comparatif(df_all, annee_ref, nb_annees=4):
    """Construit un DataFrame mensuel pour annee_ref et les N années précédentes."""
    annees = list(range(annee_ref - nb_annees, annee_ref + 1))
    rows = []
    for an in annees:
        df_an = df_all[df_all["annee"] == an]
        if df_an.empty:
            continue
        monthly = compute_monthly(df_an)
        if monthly.empty:
            continue
        for _, r in monthly.iterrows():
            # mois est un Period pandas → utiliser .month
            try:
                m = r["mois"].month  # Period object
            except AttributeError:
                m = int(r["mois"])   # fallback int
            nuits = float(r.get("nuits", 0) or 0)
            jours = calendar.monthrange(int(an), m)[1]
            rows.append({
                "annee":    int(an),
                "mois":     m,
                "mois_str": MOIS_FR[m - 1],
                "nuitees":  round(nuits, 0),
                "ca_brut":  round(float(r.get("ca_brut", 0) or 0), 0),
                "ca_net":   round(float(r.get("ca_net", 0) or 0), 0),
                "taux_occ": round(nuits / jours * 100, 1),
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _pivot_table(df, col_key, fmt="{:.0f}", annees_dispo=None,
                 total=True, total_fn="sum"):
    """Construit un tableau croisé mois x années pour une métrique."""
    annees = annees_dispo or sorted(df["annee"].unique())
    base = pd.DataFrame({"mois": list(range(1, 13)), "Mois": MOIS_FR})
    for an in annees:
        col_name = str(int(an))
        df_an = df[df["annee"] == an][["mois", col_key]].copy()
        df_an = df_an.groupby("mois", as_index=False)[col_key].sum()
        df_an = df_an.rename(columns={col_key: col_name})
        base = base.merge(df_an, on="mois", how="left")
        base[col_name] = base[col_name].fillna(0).apply(lambda v: fmt.format(v))
    if total:
        total_row = {"mois": 0, "Mois": "TOTAL"}
        for an in annees:
            col_name = str(int(an))
            vals = df[df["annee"] == an][col_key]
            val = vals.mean() if total_fn == "mean" else vals.sum()
            total_row[col_name] = fmt.format(val)
        base = pd.concat([base, pd.DataFrame([total_row])], ignore_index=True)
    return base.drop(columns=["mois"])


def _show_comparatif(df_all, annee_ref):
    st.subheader(f"📅 Comparaison {annee_ref - 4} → {annee_ref}")

    df = _build_comparatif(df_all, annee_ref, nb_annees=4)
    if df.empty:
        st.info("Pas assez de données historiques pour la comparaison.")
        return

    annees_dispo = sorted(df["annee"].unique())

    # Calcul prix moyen/nuit (ca_brut / nuitees)
    df["prix_nuit"] = (df["ca_brut"] / df["nuitees"].replace(0, float("nan"))).round(2).fillna(0)

    metriques = [
        ("ca_brut",   "💶 Revenus Bruts (€)",         "{:,.0f}"),
        ("ca_net",    "💵 Revenus Nets (€)",           "{:,.0f}"),
        ("nuitees",   "🌙 Nuitées",                    "{:.0f}"),
        ("taux_occ",  "📊 Taux d'occupation (%)",     "{:.1f}"),
        ("prix_nuit", "💰 Prix moyen / nuit (€)",      "{:,.0f}"),
    ]

    for col_key, titre, fmt in metriques:
        st.markdown(f"#### {titre}")
        pivot = _pivot_table(df, col_key, fmt=fmt, annees_dispo=annees_dispo,
                             total=True,
                             total_fn="mean" if col_key in ("taux_occ","prix_nuit") else "sum")
        st.dataframe(pivot, use_container_width=True, hide_index=True)
        st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────────────────────────────────────

def _show_stats_pays(df):
    """Statistiques par pays d'origine des voyageurs."""
    import plotly.express as px

    # Filtrer les réservations réelles (pas fermetures)
    df_pays = df[
        (df["plateforme"] != "Fermeture") &
        df["pays"].notna() &
        (df["pays"].str.strip() != "")
    ].copy()

    if df_pays.empty:
        st.info("Aucune donnée pays disponible. Assurez-vous que le pays est renseigné dans les réservations.")
        st.caption("💡 Le pays est auto-détecté depuis l'indicatif téléphonique lors de l'enregistrement.")
        return

    # ── KPIs ─────────────────────────────────────────────────────────────
    nb_pays = df_pays["pays"].nunique()
    top_pays = df_pays["pays"].value_counts().index[0] if len(df_pays) > 0 else "—"
    pct_top  = df_pays["pays"].value_counts().iloc[0] / len(df_pays) * 100 if len(df_pays) > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌍 Pays représentés", nb_pays)
    c2.metric("🏆 1er marché",       top_pays)
    c3.metric("📊 Part du 1er",      f"{pct_top:.0f}%")
    c4.metric("📋 Réservations",     len(df_pays))

    st.divider()

    # ── Agrégation par pays ───────────────────────────────────────────────
    agg = df_pays.groupby("pays").agg(
        reservations  = ("id",         "count"),
        nuits         = ("nuitees",    "sum"),
        ca_net        = ("prix_net",   "sum"),
        ca_brut       = ("prix_brut",  "sum"),
    ).reset_index().sort_values("reservations", ascending=False)

    agg["ca_moyen"] = (agg["ca_net"] / agg["reservations"]).round(0)
    agg["nuits_moy"] = (agg["nuits"] / agg["reservations"]).round(1)

    col_g, col_t = st.columns([1, 1])

    with col_g:
        st.subheader("🥧 Répartition des séjours")
        fig_pie = px.pie(
            agg.head(10), values="reservations", names="pays",
            color_discrete_sequence=px.colors.qualitative.Set3,
            hole=0.4,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), height=320)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_t:
        st.subheader("💶 CA net par pays")
        fig_bar = px.bar(
            agg.head(10).sort_values("ca_net"),
            x="ca_net", y="pays", orientation="h",
            color="ca_net",
            color_continuous_scale="Blues",
            labels={"ca_net": "CA net (€)", "pays": ""},
        )
        fig_bar.update_layout(coloraxis_showscale=False,
                               margin=dict(t=0,b=0,l=0,r=0), height=320)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("📋 Détail par pays")
    agg_display = agg.copy()
    agg_display.columns = ["Pays", "Réservations", "Nuits", "CA net (€)", "CA brut (€)", "CA moyen (€)", "Nuits moy."]

    # Ajouter colonne drapeau depuis le code ISO
    from services.indicatifs_service import INDICATIFS as _IND
    _pays_to_iso = {v[0]: v[1].lower() for v in _IND.values()}
    agg_display.insert(1, "Drapeau",
        agg_display["Pays"].apply(
            lambda p: f"https://flagcdn.com/24x18/{_pays_to_iso.get(p,'').lower()}.png"
            if _pays_to_iso.get(p) else ""
        )
    )

    agg_display["CA net (€)"]   = agg_display["CA net (€)"].apply(lambda x: f"{x:,.0f} €")
    agg_display["CA brut (€)"]  = agg_display["CA brut (€)"].apply(lambda x: f"{x:,.0f} €")
    agg_display["CA moyen (€)"] = agg_display["CA moyen (€)"].apply(lambda x: f"{x:,.0f} €")

    st.dataframe(
        agg_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Drapeau": st.column_config.ImageColumn("🏳️", width="small"),
        }
    )

    # Export
    csv = agg_display.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exporter CSV", csv, "stats_pays.csv", "text/csv")



def _show_performances(df_filtered: "pd.DataFrame", props: dict, annee: int):
    """Comparaison N vs N-1 par propriété."""
    import plotly.graph_objects as go
    st.subheader(f"🏆 Performances {annee} vs {annee - 1}")

    df_reel = df_filtered[df_filtered["plateforme"] != "Fermeture"].copy()
    annee_prec = annee - 1

    # Données uniquement pour cette propriété (df_reel déjà filtré)
    df_n  = df_reel[df_reel["annee"] == annee]
    df_n1 = df_reel[df_reel["annee"] == annee_prec]

    ca_n      = float(df_n["prix_net"].fillna(0).sum())
    ca_n1     = float(df_n1["prix_net"].fillna(0).sum())
    nuits_n   = float(df_n["nuitees"].fillna(0).sum())
    nuits_n1  = float(df_n1["nuitees"].fillna(0).sum())
    res_n     = len(df_n)
    res_n1    = len(df_n1)

    delta_ca    = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else 0
    delta_nuits = ((nuits_n - nuits_n1) / nuits_n1 * 100) if nuits_n1 > 0 else 0

    # KPIs
    k1, k2, k3 = st.columns(3)
    k1.metric(f"💶 CA Net {annee}", f"{ca_n:,.0f} €",
              f"{delta_ca:+.1f}% vs {annee_prec}", delta_color="normal")
    k2.metric(f"🌙 Nuits {annee}", f"{int(nuits_n)}",
              f"{delta_nuits:+.1f}% vs {annee_prec}", delta_color="normal")
    k3.metric(f"📅 Réservations {annee}", res_n,
              f"{res_n - res_n1:+d} vs {annee_prec}", delta_color="normal")

    st.divider()

    # Graphique mensuel N vs N-1
    MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]
    df_n["mois"]  = df_n["date_arrivee"].dt.month
    df_n1["mois"] = df_n1["date_arrivee"].dt.month
    m_n  = df_n.groupby("mois")["prix_net"].sum().reindex(range(1,13), fill_value=0)
    m_n1 = df_n1.groupby("mois")["prix_net"].sum().reindex(range(1,13), fill_value=0)

    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Bar(name=str(annee_prec), x=MOIS_FR, y=m_n1.values, marker_color="#90CAF9"))
    fig.add_trace(go.Bar(name=str(annee), x=MOIS_FR, y=m_n.values, marker_color="#1565C0"))
    fig.update_layout(barmode="group", title=f"CA Net mensuel {annee_prec} vs {annee}",
                       height=350, margin=dict(t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # Tableau mensuel
    st.markdown("#### 📋 Détail mensuel")
    rows_detail = []
    for m in range(1, 13):
        rows_detail.append({
            "Mois": MOIS_FR[m-1],
            f"CA {annee_prec}": f"{m_n1[m]:,.0f} €",
            f"CA {annee}": f"{m_n[m]:,.0f} €",
            "Évolution": f"{((m_n[m]-m_n1[m])/m_n1[m]*100):+.1f}%" if m_n1[m] > 0 else "—",
        })
    st.dataframe(pd.DataFrame(rows_detail), use_container_width=True, hide_index=True)


def _show_previsions(df_filtered: "pd.DataFrame", props: dict, annee: int):
    """Prévisions de revenus basées sur les réservations futures."""
    st.subheader("🔮 Prévisions de revenus")

    from datetime import date
    aujourd_hui = pd.Timestamp(date.today())

    df_reel = df_filtered[df_filtered["plateforme"] != "Fermeture"].copy()
    df_futur = df_reel[df_reel["date_arrivee"] >= aujourd_hui].copy()
    df_passe = df_reel[df_reel["date_arrivee"] < aujourd_hui].copy()

    if df_futur.empty:
        st.info("Aucune réservation future enregistrée.")
        return

    # KPIs futurs
    ca_futur   = float(df_futur["prix_net"].fillna(0).sum())
    nuits_futur = float(df_futur["nuitees"].fillna(0).sum())
    ca_realise = float(df_passe[df_passe["annee"] == annee]["prix_net"].fillna(0).sum())

    k1, k2, k3 = st.columns(3)
    k1.metric("💶 CA déjà réalisé", f"{ca_realise:,.0f} €", f"en {annee}")
    k2.metric("🔮 CA réservations futures", f"{ca_futur:,.0f} €")
    k3.metric("📊 CA total projeté", f"{ca_realise + ca_futur:,.0f} €",
               help="CA réalisé + CA des réservations futures confirmées")

    st.divider()

    # Timeline des revenus futurs par mois
    df_futur["mois"] = df_futur["date_arrivee"].dt.to_period("M")
    monthly = df_futur.groupby("mois").agg(
        ca_net=("prix_net", "sum"),
        nuitees=("nuitees", "sum"),
        nb_res=("id", "count")
    ).reset_index()
    monthly["mois_str"] = monthly["mois"].astype(str)

    fig = px.bar(monthly, x="mois_str", y="ca_net",
                  title="📅 CA Net prévu par mois",
                  labels={"mois_str": "Mois", "ca_net": "CA Net (€)"},
                  color="ca_net",
                  color_continuous_scale="Blues",
                  text="nb_res")
    fig.update_traces(texttemplate="%{text} rés.", textposition="outside")
    fig.update_layout(height=350, showlegend=False, margin=dict(t=40, b=20),
                       coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    # Tableau détaillé
    st.markdown("#### 📋 Réservations futures")
    df_futur_display = df_futur.sort_values("date_arrivee")[
        ["nom_client", "date_arrivee", "date_depart", "nuitees",
         "plateforme", "prix_net", "paye"]
    ].copy()
    df_futur_display["date_arrivee"] = df_futur_display["date_arrivee"].dt.strftime("%d/%m/%Y")
    df_futur_display["date_depart"]  = df_futur_display["date_depart"].apply(
        lambda x: str(x)[:10] if pd.notna(x) else "")
    df_futur_display["prix_net"] = df_futur_display["prix_net"].apply(
        lambda x: f"{float(x):,.0f} €" if pd.notna(x) else "—")
    df_futur_display["paye"] = df_futur_display["paye"].apply(lambda x: "✅" if x else "⏳")
    st.dataframe(df_futur_display, use_container_width=True, hide_index=True,
                  column_config={
                      "nom_client": "Client", "date_arrivee": "Arrivée",
                      "date_depart": "Départ", "nuitees": "Nuits",
                      "plateforme": "Plateforme", "prix_net": "CA Net", "paye": "Payé"
                  })


def _show_saisonnalite(df_filtered: "pd.DataFrame", props: dict, annee: int):
    """Analyse de saisonnalité et recommandations tarifaires."""
    import plotly.graph_objects as go
    st.subheader("🌡️ Analyse de saisonnalité")

    MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun",
               "Jul","Aoû","Sep","Oct","Nov","Déc"]

    df_reel = df_filtered[df_filtered["plateforme"] != "Fermeture"].copy()
    df_reel["mois_num"] = df_reel["date_arrivee"].dt.month
    df_reel["mois_nom"] = df_reel["mois_num"].apply(lambda x: MOIS_FR[x-1] if pd.notna(x) else "")

    # Analyse par mois (toutes années)
    monthly = df_reel.groupby("mois_num").agg(
        ca_net=("prix_net", "mean"),
        nuitees=("nuitees", "sum"),
        nb_res=("id", "count"),
        rev_nuit=("prix_net", lambda x: x.sum() / df_reel.loc[x.index, "nuitees"].sum()
                  if df_reel.loc[x.index, "nuitees"].sum() > 0 else 0)
    ).reset_index()
    monthly["mois_nom"] = monthly["mois_num"].apply(lambda x: MOIS_FR[x-1])

    # Heatmap saisonnalité
    fig_heat = go.Figure(go.Bar(
        x=monthly["mois_nom"],
        y=monthly["nuitees"],
        marker_color=monthly["nuitees"],
        marker_colorscale="RdYlGn",
        text=monthly["nb_res"].apply(lambda x: f"{x} rés."),
        textposition="outside",
    ))
    fig_heat.update_layout(title="🌙 Nuits louées par mois (toutes années)",
                            height=320, margin=dict(t=40, b=20))
    st.plotly_chart(fig_heat, use_container_width=True)

    # Revenu moyen par nuit par mois
    fig_rev = px.line(monthly, x="mois_nom", y="rev_nuit",
                       title="💶 Revenu moyen / nuit par mois",
                       labels={"mois_nom": "Mois", "rev_nuit": "€/nuit"},
                       markers=True)
    fig_rev.update_layout(height=300, margin=dict(t=40, b=20))
    st.plotly_chart(fig_rev, use_container_width=True)

    st.divider()

    # Recommandations tarifaires
    st.markdown("### 💡 Recommandations tarifaires")
    st.caption("Basées sur vos données historiques et les événements locaux.")

    if monthly.empty:
        st.info("Pas assez de données pour les recommandations.")
        return

    rev_moyen_global = float(monthly["rev_nuit"].mean())
    for _, row in monthly.iterrows():
        mois = int(row["mois_num"])
        nom  = row["mois_nom"]
        rev  = float(row["rev_nuit"])
        nuits = float(row["nuitees"])

        if rev == 0:
            continue

        ratio = rev / rev_moyen_global if rev_moyen_global > 0 else 1

        if ratio >= 1.3:
            icon, conseil, couleur = "🔴", "Haute saison — augmentez vos tarifs de 20-30%", "#C62828"
        elif ratio >= 1.1:
            icon, conseil, couleur = "🟠", "Bonne période — tarifs légèrement au-dessus de la moyenne", "#E65100"
        elif ratio >= 0.9:
            icon, conseil, couleur = "🟡", "Saison moyenne — maintenez vos tarifs habituels", "#F9A825"
        else:
            icon, conseil, couleur = "🟢", "Basse saison — proposez des promotions ou séjours minimums réduits", "#2E7D32"

        st.markdown(
            f"<div style='border-left:4px solid {couleur};padding:6px 12px;margin:4px 0;"
            f"border-radius:0 6px 6px 0'>"
            f"<b>{icon} {nom}</b> — {rev:.0f} €/nuit moy. — {conseil}</div>",
            unsafe_allow_html=True
        )

    # Événements locaux si disponibles
    try:
        from database.evenements_repo import get_evenements
        # Récupérer les propriétés uniques dans df_filtered
        prop_ids = df_filtered["propriete_id"].dropna().unique().tolist()
        prop_id_evt = int(prop_ids[0]) if len(prop_ids) == 1 else None
        evts = get_evenements(propriete_id=prop_id_evt)
        if evts:
            st.divider()
            st.markdown("### 🎪 Événements à prendre en compte")
            for e in evts[:10]:
                impact = e.get("impact_tarif","moyen")
                icon = {"fort":"🔴","moyen":"🟠","faible":"🟡"}.get(impact,"🟡")
                st.markdown(f"**{icon} {e['nom']}** — {e['date_debut']} → {e['date_fin']} — "
                             f"Impact **{impact}** sur les tarifs")
    except Exception:
        pass


def show():
    st.title("📈 Analyses financières")

    raw = st.session_state.get("prop_id", None)
    try:
        prop_id = int(raw) if raw is not None else 0
    except (ValueError, TypeError):
        prop_id = 0

    df_all = load_reservations()
    if df_all.empty:
        st.info("Aucune donnée disponible.")
        return

    df_all = df_all.copy()
    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)

    if prop_id != 0:
        df = df_all[df_all["propriete_id"] == prop_id]
    else:
        df = df_all

    props = get_proprietes_dict()
    label = props.get(prop_id, "Toutes les propriétés") if prop_id != 0 else "Toutes les propriétés"
    st.info(f"🏠 **{label}** — {len(df)} réservation(s)")

    annees = sorted(df["annee"].dropna().unique().tolist(), reverse=True)
    if not annees:
        st.warning("Aucune donnée pour cette propriété.")
        return

    annee = st.selectbox("Année de référence", annees, index=0, key="analytics_annee")

    # ── Filtre plateforme global ──────────────────────────────────────────────
    plateformes_dispo = sorted(
        df[df["plateforme"] != "Fermeture"]["plateforme"].dropna().unique()
    )
    plat_global = st.multiselect(
        "🔀 Filtrer par plateforme", plateformes_dispo,
        default=[], key="analytics_plat",
        placeholder="Toutes les plateformes"
    )
    if plat_global:
        df = df[
            (df["plateforme"].isin(plat_global)) |
            (df["plateforme"] == "Fermeture")
        ]

    # ── Onglets ───────────────────────────────────────────────────────────────
    tab_bilan, tab_compar, tab_pays, tab_perf, tab_prev, tab_saison,     tab_heat, tab_funnel, tab_scatter, tab_obj, tab_comm, tab_sim, tab_score, tab_top, tab_duree = st.tabs([
        "📊 Bilan annuel", "📅 Comparaison pluriannuelle", "🌍 Par pays",
        "🏆 Performances N vs N-1", "🔮 Prévisions", "🌡️ Saisonnalité",
        "🔥 Heatmap", "📐 Entonnoir", "🔵 Durée vs Prix",
        "🎯 Objectif", "💸 Commissions", "🎲 Simulation",
        "🏅 Score", "🥇 Top mois", "📏 Durées"
    ])

    with tab_compar:
        _show_comparatif(df, int(annee))

    with tab_pays:
        annee_pays = st.selectbox("Année", ["Toutes"] + [str(int(a)) for a in annees],
                                   key="pays_annee")
        df_pays_filtre = df if annee_pays == "Toutes" else df[df["annee"] == int(annee_pays)]
        _show_stats_pays(df_pays_filtre)

    with tab_perf:
        _show_performances(df, props, int(annee))

    with tab_prev:
        _show_previsions(df, props, int(annee))

    with tab_saison:
        _show_saisonnalite(df, props, int(annee))

    with tab_heat:
        _show_heatmap(df[df["annee"] == annee])

    with tab_funnel:
        _show_entonnoir(df[df["annee"] == annee])

    with tab_scatter:
        _show_scatter(df[df["annee"] == annee])

    with tab_obj:
        _show_objectif(df, int(annee))

    with tab_comm:
        _show_commissions(df[df["annee"] == annee])

    with tab_sim:
        _show_simulation(df[df["annee"] == annee])

    with tab_score:
        _show_score(df, int(annee))

    with tab_top:
        _show_top_mois(df_all[df_all['propriete_id'] == prop_id] if prop_id != 0 else df_all)

    with tab_duree:
        _show_duree_plateforme(df[df["annee"] == annee])

    with tab_bilan:
        df_an = df[df["annee"] == annee]
        if df_an.empty:
            st.warning("Aucune réservation pour cette sélection.")
            return

        kpis = compute_kpis(df_an)
        st.subheader(f"Bilan {annee} — {label}")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("💰 CA Brut",    f"{kpis['ca_brut']:,.0f} €")
        c2.metric("💵 CA Net",     f"{kpis['ca_net']:,.0f} €")
        c3.metric("🔖 Commissions",f"{kpis['commissions']:,.0f} €")
        c4.metric("🧹 Ménages",    f"{kpis['menage']:,.0f} €")
        c5.metric("📈 Rev/nuit",   f"{kpis['revenu_nuit']:,.0f} €")

        c6, c7, c8 = st.columns(3)
        c6.metric("🌙 Nuits louées",    kpis.get("nuits_louees", 0))
        c7.metric("📊 Taux occupation", f"{kpis.get('taux_occupation', 0):.1f} %")
        c8.metric("📋 Réservations",    kpis.get("nb_reservations", 0))

        monthly = compute_monthly(df_an)

        # CA mensuel
        st.subheader("📊 CA mensuel")
        if not monthly.empty:
            fig = px.bar(monthly, x="mois_str", y=["ca_brut", "ca_net"],
                         barmode="group",
                         labels={"value": "€", "mois_str": "Mois", "variable": ""},
                         color_discrete_map={"ca_brut": "#90CAF9", "ca_net": "#1565C0"})
            fig.update_layout(height=320, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔀 Répartition plateformes")
            plat = df_an.groupby("plateforme").agg(
                ca_net=("prix_net","sum"), nb=("id","count")
            ).reset_index()
            fig2 = px.pie(plat, names="plateforme", values="ca_net",
                          color_discrete_sequence=px.colors.qualitative.Set2)
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.subheader("📈 Revenu moyen / nuit")
            if not monthly.empty and "nuits" in monthly.columns:
                monthly["rev_par_nuit"] = (monthly["ca_net"] / monthly["nuits"].replace(0,1)).round(2)
                fig3 = px.line(monthly, x="mois_str", y="rev_par_nuit", markers=True,
                               labels={"rev_par_nuit": "€/nuit", "mois_str": "Mois"})
                fig3.update_layout(height=300)
                st.plotly_chart(fig3, use_container_width=True)

        st.subheader("📋 Détail mensuel")
        if not monthly.empty:
            st.dataframe(monthly.drop(columns=["mois"], errors="ignore"),
                         use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# NOUVELLES FONCTIONS ANALYTIQUES
# ─────────────────────────────────────────────────────────────────────────────

def _show_heatmap(df):
    """Heatmap occupation par jour de semaine x mois."""
    st.subheader("🌡️ Heatmap — Nuits louées par jour de semaine et mois")
    if df.empty:
        st.info("Pas de données."); return
    try:
        df2 = df[df["plateforme"] != "Fermeture"].copy()
        df2["date_arrivee"] = pd.to_datetime(df2["date_arrivee"], errors="coerce")
        df2["mois"]     = df2["date_arrivee"].dt.month
        df2["jour_sem"] = df2["date_arrivee"].dt.dayofweek
        jours = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
        heat  = df2.groupby(["mois","jour_sem"])["nuitees"].sum().reset_index()
        pivot = heat.pivot(index="jour_sem", columns="mois", values="nuitees").fillna(0)
        pivot.index = [jours[i] for i in pivot.index]
        pivot.columns = [MOIS_FR[m-1] for m in pivot.columns]
        fig = px.imshow(pivot, color_continuous_scale="Blues",
                        labels={"color":"Nuits","x":"Mois","y":"Jour"},
                        text_auto=True, aspect="auto")
        fig.update_layout(height=320, margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur heatmap : {e}")


def _show_entonnoir(df):
    """Graphique entonnoir : réservations → payées → avis reçus."""
    st.subheader("📊 Entonnoir de conversion")
    if df.empty:
        st.info("Pas de données."); return
    try:
        df2 = df[df["plateforme"] != "Fermeture"]
        nb_resas   = len(df2)
        nb_payees  = int(df2.get("paye", pd.Series([False]*len(df2))).sum())
        # Compter les avis depuis Supabase
        try:
            from database.supabase_client import get_supabase
            sb = get_supabase()
            prop_id = df2["propriete_id"].iloc[0] if not df2.empty else None
            if sb and prop_id:
                res = sb.table("avis").select("id", count="exact").eq("propriete_id", int(prop_id)).eq("token_used", True).execute()
                nb_avis = res.count or 0
            else:
                nb_avis = 0
        except:
            nb_avis = 0

        fig = go.Figure(go.Funnel(
            y=["Réservations", "Payées", "Avis reçus"],
            x=[nb_resas, nb_payees, nb_avis],
            textinfo="value+percent initial",
            marker_color=["#1565C0","#F0B429","#2E7D32"]
        ))
        fig.update_layout(height=300, margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur entonnoir : {e}")


def _show_scatter(df):
    """Scatter : durée séjour vs prix/nuit."""
    st.subheader("🔵 Durée séjour vs Revenu/nuit")
    if df.empty:
        st.info("Pas de données."); return
    try:
        df2 = df[df["plateforme"] != "Fermeture"].copy()
        df2["nuitees"]  = pd.to_numeric(df2["nuitees"], errors="coerce").fillna(0)
        df2["prix_net"] = pd.to_numeric(df2["prix_net"], errors="coerce").fillna(0)
        df2 = df2[df2["nuitees"] > 0]
        df2["rev_nuit"] = (df2["prix_net"] / df2["nuitees"]).round(2)
        fig = px.scatter(df2, x="nuitees", y="rev_nuit",
                         color="plateforme", hover_data=["nom_client"],
                         labels={"nuitees":"Nuits","rev_nuit":"€/nuit","plateforme":"Plateforme"},
                         size_max=12)
        fig.update_layout(height=350, margin=dict(t=10,b=10))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur scatter : {e}")


def _show_objectif(df, annee):
    """Jauge CA réel vs objectif annuel."""
    st.subheader("🎯 Progression vers l'objectif annuel")
    objectif = st.number_input("Objectif CA Net annuel (€)", min_value=0,
                                value=50000, step=1000, key="obj_ca")
    df_an = df[(df["annee"] == annee) & (df["plateforme"] != "Fermeture")]
    ca_net = float(df_an["prix_net"].sum()) if not df_an.empty else 0
    pct    = min(100, ca_net / objectif * 100) if objectif > 0 else 0

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=ca_net,
        delta={"reference": objectif, "valueformat": ",.0f"},
        number={"suffix": " €", "valueformat": ",.0f"},
        gauge={
            "axis": {"range": [0, objectif]},
            "bar":  {"color": "#1565C0"},
            "steps": [
                {"range": [0, objectif*0.5], "color": "#FFEBEE"},
                {"range": [objectif*0.5, objectif*0.8], "color": "#FFF8E1"},
                {"range": [objectif*0.8, objectif], "color": "#E8F5E9"},
            ],
            "threshold": {"line": {"color": "#F0B429", "width": 4},
                          "thickness": 0.75, "value": objectif}
        },
        title={"text": f"CA Net {annee} — Objectif : {objectif:,.0f} €"}
    ))
    fig.update_layout(height=300, margin=dict(t=40,b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.progress(pct/100, text=f"{pct:.1f}% de l'objectif atteint")


def _show_commissions(df):
    """Analyse commissions par plateforme."""
    st.subheader("💸 Commissions par plateforme")
    if df.empty:
        st.info("Pas de données."); return
    try:
        df2 = df[df["plateforme"] != "Fermeture"].copy()
        df2["commissions"] = pd.to_numeric(df2.get("commissions", 0), errors="coerce").fillna(0)
        df2["prix_brut"]   = pd.to_numeric(df2.get("prix_brut", 0),   errors="coerce").fillna(0)
        grp = df2.groupby("plateforme").agg(
            commissions=("commissions","sum"),
            ca_brut=("prix_brut","sum"),
            nb=("id","count")
        ).reset_index()
        grp["pct"] = (grp["commissions"] / grp["ca_brut"].replace(0,1) * 100).round(1)
        grp["commissions_fmt"] = grp["commissions"].apply(lambda x: f"{x:,.0f} €")
        grp["pct_fmt"] = grp["pct"].apply(lambda x: f"{x:.1f}%")

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(grp, x="plateforme", y="commissions",
                         color="plateforme", text="commissions_fmt",
                         labels={"commissions":"€","plateforme":"Plateforme"})
            fig.update_layout(height=280, margin=dict(t=10,b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.bar(grp, x="plateforme", y="pct",
                          color="plateforme", text="pct_fmt",
                          labels={"pct":"% commission","plateforme":"Plateforme"})
            fig2.update_layout(height=280, margin=dict(t=10,b=10), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        st.dataframe(grp[["plateforme","nb","ca_brut","commissions","pct"]].rename(columns={
            "plateforme":"Plateforme","nb":"Nb rés.","ca_brut":"CA Brut (€)",
            "commissions":"Commissions (€)","pct":"% comm."
        }), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Erreur commissions : {e}")


def _show_simulation(df):
    """Simulation 'et si' — impact d'une variation de prix."""
    st.subheader("🎲 Simulation — Et si je modifiais mes prix ?")
    if df.empty:
        st.info("Pas de données."); return

    df2 = df[df["plateforme"] != "Fermeture"].copy()
    df2["prix_net"] = pd.to_numeric(df2["prix_net"], errors="coerce").fillna(0)
    df2["nuitees"]  = pd.to_numeric(df2["nuitees"],  errors="coerce").fillna(0)

    ca_actuel   = float(df2["prix_net"].sum())
    nuits_tot   = float(df2["nuitees"].sum())
    rev_nuit_act = ca_actuel / nuits_tot if nuits_tot > 0 else 0

    c1, c2 = st.columns(2)
    with c1:
        variation_prix = st.slider("Variation du prix/nuit (%)", -30, 50, 0, key="sim_prix")
    with c2:
        variation_occ  = st.slider("Variation du taux d'occupation (%)", -30, 30, 0, key="sim_occ")

    ca_simule   = ca_actuel * (1 + variation_prix/100) * (1 + variation_occ/100)
    delta_ca    = ca_simule - ca_actuel
    rev_nuit_new = rev_nuit_act * (1 + variation_prix/100)

    col1, col2, col3 = st.columns(3)
    col1.metric("CA Actuel",  f"{ca_actuel:,.0f} €")
    col2.metric("CA Simulé",  f"{ca_simule:,.0f} €",
                delta=f"{delta_ca:+,.0f} €",
                delta_color="normal")
    col3.metric("Rev/nuit simulé", f"{rev_nuit_new:,.0f} €",
                delta=f"{rev_nuit_new-rev_nuit_act:+,.0f} €")

    if variation_prix > 0 and variation_occ < 0:
        st.warning("⚠️ Une hausse des prix réduit souvent le taux d'occupation — vérifiez vos concurrents.")
    elif variation_prix < 0 and variation_occ > 0:
        st.info("💡 Baisser les prix peut attirer plus de réservations — mais surveillez votre rentabilité.")
    elif ca_simule > ca_actuel:
        st.success(f"✅ Cette combinaison génère **{delta_ca:+,.0f} €** supplémentaires.")


def _show_score(df, annee):
    """Score de performance global."""
    st.subheader("🏆 Score de performance global")
    df_an = df[(df["annee"] == annee) & (df["plateforme"] != "Fermeture")]
    if df_an.empty:
        st.info("Pas de données."); return

    df_an = df_an.copy()
    df_an["prix_net"] = pd.to_numeric(df_an["prix_net"], errors="coerce").fillna(0)
    df_an["nuitees"]  = pd.to_numeric(df_an["nuitees"],  errors="coerce").fillna(0)

    nuits     = float(df_an["nuitees"].sum())
    taux_occ  = min(100, nuits / 365 * 100)
    rev_nuit  = float(df_an["prix_net"].sum()) / nuits if nuits > 0 else 0
    pct_paye  = float(df_an.get("paye", pd.Series([False]*len(df_an))).sum()) / len(df_an) * 100 if len(df_an) > 0 else 0

    # Scores sur 10
    s_occ  = min(10, taux_occ / 10)
    s_rev  = min(10, rev_nuit / 20)
    s_pay  = pct_paye / 10
    score  = round((s_occ + s_rev + s_pay) / 3, 1)

    fig = go.Figure()
    categories = ["Taux d'occupation","Revenu/nuit","Taux de paiement"]
    values     = [s_occ, s_rev, s_pay]
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself", name="Performance",
        line_color="#1565C0", fillcolor="rgba(21,101,192,0.2)"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,10])),
        height=320, margin=dict(t=20,b=20)
    )
    st.plotly_chart(fig, use_container_width=True)

    emoji = "🏆" if score >= 7 else "👍" if score >= 5 else "⚠️"
    st.markdown(f"### {emoji} Score global : **{score}/10**")
    c1, c2, c3 = st.columns(3)
    c1.metric("Taux occupation", f"{taux_occ:.1f}%", f"Score: {s_occ:.1f}/10")
    c2.metric("Revenu/nuit",     f"{rev_nuit:.0f} €", f"Score: {s_rev:.1f}/10")
    c3.metric("Taux paiement",   f"{pct_paye:.0f}%",  f"Score: {s_pay:.1f}/10")


def _show_top_mois(df):
    """Classement des meilleurs mois historiques."""
    st.subheader("🥇 Classement des meilleurs mois (historique)")
    if df.empty:
        st.info("Pas de données."); return
    try:
        df2 = df[df["plateforme"] != "Fermeture"].copy()
        df2["prix_net"] = pd.to_numeric(df2["prix_net"], errors="coerce").fillna(0)
        df2["annee"]    = pd.to_numeric(df2["annee"],    errors="coerce").astype("Int64")
        df2["mois"]     = pd.to_numeric(df2["mois"],     errors="coerce").astype("Int64")
        df2 = df2.dropna(subset=["annee","mois"])

        rows = []
        for (annee, mois), grp in df2.groupby(["annee","mois"]):
            rows.append({
                "periode": f"{MOIS_FR[int(mois)-1]} {int(annee)}" if 1 <= int(mois) <= 12 else "?",
                "ca_net":  grp["prix_net"].sum(),
                "nb":      len(grp),
            })
        if not rows:
            st.info("Pas de données."); return

        result = pd.DataFrame(rows).sort_values("ca_net", ascending=False).head(12)
        result["ca_label"] = result["ca_net"].apply(lambda x: f"{x:,.0f} €")

        fig = px.bar(result, x="periode", y="ca_net", color="ca_net",
                     color_continuous_scale="Blues", text="ca_label",
                     labels={"ca_net":"CA Net (€)","periode":"Mois"})
        fig.update_traces(textposition="outside")
        fig.update_layout(height=350, margin=dict(t=10,b=30),
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur classement : {e}")


def _show_duree_plateforme(df):
    """Durée moyenne des séjours par plateforme et mois."""
    st.subheader("📏 Durée moyenne des séjours")
    if df.empty:
        st.info("Pas de données."); return
    try:
        df2 = df[df["plateforme"] != "Fermeture"].copy()
        df2["nuitees"] = pd.to_numeric(df2["nuitees"], errors="coerce").fillna(0)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Par plateforme**")
            grp_plat = df2.groupby("plateforme")["nuitees"].mean().round(1).reset_index()
            grp_plat.columns = ["Plateforme","Durée moy. (nuits)"]
            fig = px.bar(grp_plat, x="Plateforme", y="Durée moy. (nuits)",
                         color="Plateforme", text="Durée moy. (nuits)")
            fig.update_layout(height=280, showlegend=False, margin=dict(t=10,b=10))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.markdown("**Par mois**")
            df2["mois"] = pd.to_numeric(df2["mois"], errors="coerce")
            grp_mois = df2.groupby("mois")["nuitees"].mean().round(1).reset_index()
            grp_mois["mois_str"] = grp_mois["mois"].apply(
                lambda m: MOIS_FR[int(m)-1] if 1 <= int(m) <= 12 else "?"
            )
            fig2 = px.line(grp_mois, x="mois_str", y="nuitees", markers=True,
                           labels={"nuitees":"Nuits moy.","mois_str":"Mois"})
            fig2.update_layout(height=280, margin=dict(t=10,b=10))
            st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.error(f"Erreur durée : {e}")
