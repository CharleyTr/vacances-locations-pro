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
                             total=(col_key != "taux_occ" and col_key != "prix_nuit"),
                             total_fn="mean" if col_key in ("taux_occ","prix_nuit") else "sum")
        st.dataframe(pivot, use_container_width=True, hide_index=True)
        st.divider()


# ─────────────────────────────────────────────────────────────────────────────
# Page principale
# ─────────────────────────────────────────────────────────────────────────────

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
    tab_bilan, tab_compar = st.tabs(["📊 Bilan annuel", "📅 Comparaison pluriannuelle"])

    # ── TAB 2 : Comparaison pluriannuelle ─────────────────────────────────────
    with tab_compar:
        _show_comparatif(df, int(annee))

    # ── TAB 1 : Bilan annuel ──────────────────────────────────────────────────
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
