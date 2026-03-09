import streamlit as st
import pandas as pd
from services.reservation_service import load_reservations
from services.calendar_service import build_calendar_events


def show():
    st.title("📅 Calendrier des réservations")

    df = load_reservations()
    if df.empty:
        st.info("Aucune réservation à afficher.")
        return

    # Filtre propriété
    if "propriete_id" in df.columns:
        proprietes = sorted(df["propriete_id"].unique().tolist())
        labels = {1: "Villa Tobias", 2: "Propriété 2"}
        choix = st.selectbox(
            "Propriété",
            proprietes,
            format_func=lambda x: labels.get(x, f"Propriété {x}")
        )
        df = df[df["propriete_id"] == choix]

    events = build_calendar_events(df)

    # Vue tableau chronologique
    st.subheader("📋 Vue chronologique")

    cols_display = ["nom_client", "plateforme", "date_arrivee", "date_depart", "nuitees", "prix_net", "paye"]
    cols_avail = [c for c in cols_display if c in df.columns]

    df_sorted = df[cols_avail].sort_values("date_arrivee")
    st.dataframe(
        df_sorted,
        use_container_width=True,
        hide_index=True,
        column_config={
            "prix_net": st.column_config.NumberColumn("Prix net", format="%.2f €"),
            "paye":     st.column_config.CheckboxColumn("Payé"),
        }
    )

    # Légende plateformes
    st.divider()
    st.markdown("**Légende :** 🔵 Booking &nbsp;|&nbsp; 🔴 Airbnb &nbsp;|&nbsp; 🟢 Direct")
