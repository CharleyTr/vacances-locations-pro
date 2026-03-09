import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from services.reservation_service import load_reservations
from services.analytics_service import compute_kpis, compute_monthly
from services.finance_service import financial_summary


def show():
    st.title("📈 Analyses financières")

    df = load_reservations()
    if df.empty:
        st.info("Aucune donnée disponible.")
        return

    # Sélecteur d'année
    annees = sorted(df["annee"].dropna().unique().tolist(), reverse=True)
    annee = st.selectbox("Année", annees, index=0)
    df_an = df[df["annee"] == annee]

    kpis = compute_kpis(df_an)

    # ── KPIs annuels ──────────────────────────────────────────────────────
    st.subheader(f"Bilan {annee}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CA Brut",        f"{kpis['ca_brut']:,.0f} €")
    c2.metric("CA Net",         f"{kpis['ca_net']:,.0f} €")
    c3.metric("Commissions",    f"{kpis['commissions']:,.0f} €")
    c4.metric("Ménages",        f"{kpis['menage']:,.0f} €")

    # ── CA mensuel ────────────────────────────────────────────────────────
    st.subheader("CA mensuel")
    monthly = compute_monthly(df_an)
    if not monthly.empty:
        fig = px.bar(
            monthly, x="mois_str", y=["ca_brut", "ca_net"],
            barmode="group",
            labels={"value": "€", "mois_str": "Mois", "variable": ""},
            color_discrete_map={"ca_brut": "#90CAF9", "ca_net": "#1565C0"}
        )
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    # ── Revenus par plateforme ────────────────────────────────────────────
    with col1:
        st.subheader("Revenus par plateforme")
        if "plateforme" in df_an.columns:
            plat = df_an.groupby("plateforme").agg(
                ca_net=("prix_net", "sum"),
                nb=("id", "count")
            ).reset_index()
            fig2 = px.pie(plat, names="plateforme", values="ca_net",
                          color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig2, use_container_width=True)

    # ── Revenu moyen par nuit ─────────────────────────────────────────────
    with col2:
        st.subheader("Revenu moyen / nuit par mois")
        if not monthly.empty and "nuits" in monthly.columns:
            monthly["rev_par_nuit"] = (monthly["ca_net"] / monthly["nuits"]).round(2)
            fig3 = px.line(monthly, x="mois_str", y="rev_par_nuit",
                           markers=True,
                           labels={"rev_par_nuit": "€/nuit", "mois_str": "Mois"})
            st.plotly_chart(fig3, use_container_width=True)

    # ── Tableau détaillé ──────────────────────────────────────────────────
    st.subheader("Détail mensuel")
    if not monthly.empty:
        st.dataframe(monthly.drop(columns=["mois"], errors="ignore"),
                     use_container_width=True, hide_index=True)
