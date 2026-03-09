"""
Page Calendrier — Vue Gantt interactive par propriété + Vue mensuelle.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta
from services.reservation_service import load_reservations

PROPRIETES = {1: "Villa Tobias", 2: "Propriété 2"}

COULEURS = {
    "Booking":   "#1565C0",
    "Airbnb":    "#E53935",
    "Direct":    "#2E7D32",
    "Abritel":   "#F57C00",
    "Fermeture": "#757575",
}


def show():
    st.title("📅 Calendrier des réservations")

    df = load_reservations()
    if df.empty:
        st.info("Aucune réservation à afficher.")
        return

    # ── Contrôles ─────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        proprietes_dispo = sorted(df["propriete_id"].dropna().unique().tolist())
        choix_prop = st.multiselect(
            "Propriété(s)",
            options=proprietes_dispo,
            default=proprietes_dispo,
            format_func=lambda x: PROPRIETES.get(int(x), f"Propriété {x}")
        )

    with col2:
        annees = sorted(df["annee"].dropna().unique().tolist())
        annee = st.selectbox("Année", annees, index=len(annees) - 1)

    with col3:
        plateformes_dispo = sorted(df["plateforme"].dropna().unique().tolist())
        choix_plat = st.multiselect(
            "Plateforme(s)", plateformes_dispo, default=plateformes_dispo
        )

    # ── Filtrage ──────────────────────────────────────────────────────────
    df_f = df.copy()
    if choix_prop:
        df_f = df_f[df_f["propriete_id"].isin(choix_prop)]
    if choix_plat:
        df_f = df_f[df_f["plateforme"].isin(choix_plat)]
    df_f = df_f[df_f["annee"] == annee]

    if df_f.empty:
        st.warning("Aucune réservation pour ces filtres.")
        return

    # ── Vue Gantt ─────────────────────────────────────────────────────────
    st.subheader("🗓️ Planning visuel")

    df_gantt = df_f.copy()
    df_gantt["date_arrivee"] = pd.to_datetime(df_gantt["date_arrivee"])
    df_gantt["date_depart"]  = pd.to_datetime(df_gantt["date_depart"])

    df_gantt["Propriété"] = df_gantt["propriete_id"].map(
        lambda x: PROPRIETES.get(int(x), f"Propriété {x}")
    )
    df_gantt["Label"] = df_gantt.apply(
        lambda r: f"{r['nom_client']}  ({int(r['nuitees'])}n — {r['plateforme']})", axis=1
    )
    df_gantt["Couleur"] = df_gantt["plateforme"].map(
        lambda p: COULEURS.get(p, "#607D8B")
    )
    df_gantt["Info"] = df_gantt.apply(
        lambda r: (
            f"<b>{r['nom_client']}</b><br>"
            f"📅 {r['date_arrivee'].strftime('%d/%m')} → {r['date_depart'].strftime('%d/%m/%Y')}<br>"
            f"🌙 {int(r['nuitees'])} nuits<br>"
            f"🏷️ {r['plateforme']}<br>"
            f"💶 {r['prix_net']:.0f} € net<br>"
            f"{'✅ Payé' if r['paye'] else '⏳ En attente'}"
        ), axis=1
    )

    fig = px.timeline(
        df_gantt,
        x_start="date_arrivee",
        x_end="date_depart",
        y="Propriété",
        color="plateforme",
        color_discrete_map=COULEURS,
        text="Label",
        custom_data=["Info"],
        labels={"plateforme": "Plateforme"},
    )

    fig.update_traces(
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(size=11, color="white"),
        hovertemplate="%{customdata[0]}<extra></extra>",
    )

    fig.update_layout(
        height=max(250, len(choix_prop) * 120 + 100),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="",
        yaxis_title="",
        legend_title="Plateforme",
        xaxis=dict(
            tickformat="%d %b",
            dtick="M1",
            ticklabelmode="period",
            showgrid=True,
            gridcolor="#EEEEEE",
        ),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Légende couleurs
    legende = " &nbsp;|&nbsp; ".join(
        [f"<span style='color:{c}'>■</span> {p}" for p, c in COULEURS.items()
         if p in df_f["plateforme"].values]
    )
    st.markdown(f"<small>{legende}</small>", unsafe_allow_html=True)

    st.divider()

    # ── Vue mensuelle condensée ───────────────────────────────────────────
    st.subheader("📆 Synthèse mensuelle")

    monthly = df_f.groupby(df_f["date_arrivee"].dt.to_period("M")).agg(
        reservations=("id", "count"),
        nuits=("nuitees", "sum"),
        ca_net=("prix_net", "sum"),
    ).reset_index()
    monthly["mois"] = monthly["date_arrivee"].dt.strftime("%B %Y")
    monthly["ca_net"] = monthly["ca_net"].round(0).astype(int)

    st.dataframe(
        monthly[["mois", "reservations", "nuits", "ca_net"]].rename(columns={
            "mois": "Mois", "reservations": "Réservations",
            "nuits": "Nuits", "ca_net": "CA Net (€)"
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # ── Liste détaillée ───────────────────────────────────────────────────
    with st.expander("📋 Liste complète"):
        cols = ["nom_client", "plateforme", "date_arrivee", "date_depart",
                "nuitees", "prix_net", "paye"]
        cols_ok = [c for c in cols if c in df_f.columns]
        st.dataframe(
            df_f[cols_ok].sort_values("date_arrivee"),
            use_container_width=True,
            hide_index=True,
            column_config={
                "prix_net": st.column_config.NumberColumn("Prix net", format="%.0f €"),
                "paye":     st.column_config.CheckboxColumn("Payé"),
            }
        )
