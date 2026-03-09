import streamlit as st
import plotly.express as px
from services.reservation_service import load_reservations
from services.analytics_service import compute_kpis, compute_monthly
from services.proprietes_service import get_proprietes_dict


def show():
    st.title("📈 Analyses financières")

    # ── Lecture DIRECTE de session_state ─────────────────────────────────
    raw = st.session_state.get("prop_id", None)
    st.caption(f"🔍 session_state prop_id = `{raw}` (type: {type(raw).__name__})")

    try:
        prop_id = int(raw) if raw is not None else 0
    except (ValueError, TypeError):
        prop_id = 0

    df_all = load_reservations()
    if df_all.empty:
        st.info("Aucune donnée disponible.")
        return

    # Forcer int sur propriete_id
    df_all = df_all.copy()
    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)

    st.caption(f"🔍 propriete_id uniques dans les données : {sorted(df_all['propriete_id'].unique().tolist())}")

    # Filtre
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

    annee = st.selectbox("Année", annees, index=0)
    df_an = df[df["annee"] == annee]
    if df_an.empty:
        st.warning("Aucune réservation pour cette sélection.")
        return

    kpis = compute_kpis(df_an)
    st.subheader(f"Bilan {annee} — {label}")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 CA Brut",    f"{kpis['ca_brut']:,.0f} €")
    c2.metric("💵 CA Net",      f"{kpis['ca_net']:,.0f} €")
    c3.metric("🔖 Commissions", f"{kpis['commissions']:,.0f} €")
    c4.metric("🧹 Ménages",     f"{kpis['menage']:,.0f} €")
    c5.metric("📈 Rev/nuit",    f"{kpis['revenu_nuit']:,.0f} €")

    st.divider()

    monthly = compute_monthly(df_an)
    if not monthly.empty:
        st.subheader("CA mensuel")
        fig = px.bar(monthly, x="mois_str", y=["ca_brut", "ca_net"],
                     barmode="group",
                     labels={"value": "€", "mois_str": "Mois", "variable": ""},
                     color_discrete_map={"ca_brut": "#90CAF9", "ca_net": "#1565C0"})
        fig.update_layout(height=320, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Répartition plateformes")
        plat = df_an.groupby("plateforme").agg(
            ca_net=("prix_net","sum"), nb=("id","count")
        ).reset_index()
        fig2 = px.pie(plat, names="plateforme", values="ca_net",
                      color_discrete_sequence=px.colors.qualitative.Set2)
        fig2.update_layout(height=300)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("Revenu moyen / nuit")
        if not monthly.empty and "nuits" in monthly.columns:
            monthly["rev_par_nuit"] = (monthly["ca_net"] / monthly["nuits"].replace(0,1)).round(2)
            fig3 = px.line(monthly, x="mois_str", y="rev_par_nuit", markers=True,
                           labels={"rev_par_nuit": "€/nuit", "mois_str": "Mois"})
            fig3.update_layout(height=300)
            st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Détail mensuel")
    if not monthly.empty:
        st.dataframe(monthly.drop(columns=["mois"], errors="ignore"),
                     use_container_width=True, hide_index=True)
