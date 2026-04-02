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

    props_list = [{"id": 0, "nom": "Toutes"}] + [{"id": pid, "nom": nom} for pid, nom in props.items()]

    rows = []
    for p in props_list:
        pid = p["id"]
        df_n   = df_reel[df_reel["annee"] == annee]   if pid == 0 else df_reel[(df_reel["annee"] == annee)   & (df_reel["propriete_id"] == pid)]
        df_n1  = df_reel[df_reel["annee"] == annee_prec] if pid == 0 else df_reel[(df_reel["annee"] == annee_prec) & (df_reel["propriete_id"] == pid)]

        ca_n   = float(df_n["prix_net"].fillna(0).sum())
        ca_n1  = float(df_n1["prix_net"].fillna(0).sum())
        nuits_n  = float(df_n["nuitees"].fillna(0).sum())
        nuits_n1 = float(df_n1["nuitees"].fillna(0).sum())
        res_n  = len(df_n)
        res_n1 = len(df_n1)

        delta_ca    = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else 0
        delta_nuits = ((nuits_n - nuits_n1) / nuits_n1 * 100) if nuits_n1 > 0 else 0

        rows.append({
            "Propriété": p["nom"],
            f"CA Net {annee}": ca_n,
            f"CA Net {annee_prec}": ca_n1,
            "Évol. CA %": delta_ca,
            f"Nuits {annee}": int(nuits_n),
            f"Nuits {annee_prec}": int(nuits_n1),
            "Évol. Nuits %": delta_nuits,
            f"Résas {annee}": res_n,
            f"Résas {annee_prec}": res_n1,
        })

    df_perf = pd.DataFrame(rows)

    # KPIs globaux
    row_all = df_perf[df_perf["Propriété"] == "Toutes"].iloc[0]
    k1, k2, k3 = st.columns(3)
    k1.metric(f"💶 CA Net {annee}",
              f"{row_all[f'CA Net {annee}']:,.0f} €",
              f"{row_all['Évol. CA %']:+.1f}% vs {annee_prec}",
              delta_color="normal")
    k2.metric(f"🌙 Nuits {annee}",
              f"{int(row_all[f'Nuits {annee}'])}",
              f"{row_all['Évol. Nuits %']:+.1f}% vs {annee_prec}",
              delta_color="normal")
    k3.metric(f"📅 Résas {annee}",
              row_all[f"Résas {annee}"],
              f"{row_all[f'Résas {annee}'] - row_all[f'Résas {annee_prec}']:+d} vs {annee_prec}",
              delta_color="normal")

    st.divider()

    # Graphique barres comparatif par propriété
    df_props = df_perf[df_perf["Propriété"] != "Toutes"]
    if not df_props.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(name=str(annee_prec), x=df_props["Propriété"],
                              y=df_props[f"CA Net {annee_prec}"],
                              marker_color="#90CAF9"))
        fig.add_trace(go.Bar(name=str(annee), x=df_props["Propriété"],
                              y=df_props[f"CA Net {annee}"],
                              marker_color="#1565C0"))
        fig.update_layout(barmode="group", title=f"CA Net {annee_prec} vs {annee}",
                           height=350, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # Tableau détaillé
    st.markdown("#### 📋 Détail par propriété")
    for _, row in df_props.iterrows():
        col = "normal" if row["Évol. CA %"] >= 0 else "inverse"
        with st.expander(f"🏠 {row['Propriété']}", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("💶 CA Net", f"{row[f'CA Net {annee}']:,.0f} €",
                       f"{row['Évol. CA %']:+.1f}%", delta_color=col)
            c2.metric("🌙 Nuits", str(row[f"Nuits {annee}"]),
                       f"{row['Évol. Nuits %']:+.1f}%", delta_color=col)
            c3.metric("📅 Réservations", str(row[f"Résas {annee}"]),
                       f"{row[f'Résas {annee}'] - row[f'Résas {annee_prec}']:+d}", delta_color=col)


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
        evts = get_evenements()
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
    tab_bilan, tab_compar, tab_pays, tab_perf, tab_prev, tab_saison = st.tabs([
        "📊 Bilan annuel", "📅 Comparaison pluriannuelle", "🌍 Par pays",
        "🏆 Performances N vs N-1", "🔮 Prévisions", "🌡️ Saisonnalité"
    ])

    # ── TAB 2 : Comparaison pluriannuelle ─────────────────────────────────────
    with tab_compar:
        _show_comparatif(df, int(annee))

    # ── TAB 1 : Bilan annuel ──────────────────────────────────────────────────
    # ── TAB PAYS ─────────────────────────────────────────────────────────
    with tab_pays:
        # Filtre année pour les stats pays
        annee_pays = st.selectbox("Année", ["Toutes"] + [str(int(a)) for a in annees],
                                   key="pays_annee")
        df_pays_filtre = df if annee_pays == "Toutes" else df[df["annee"] == int(annee_pays)]
        _show_stats_pays(df_pays_filtre)

    with tab_perf:
        # df est déjà filtré par propriété — pas d'accès aux autres propriétés
        _show_performances(df, props, int(annee))

    with tab_prev:
        _show_previsions(df, props, int(annee))

    with tab_saison:
        _show_saisonnalite(df, props, int(annee))

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
