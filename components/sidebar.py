import streamlit as st
from database.supabase_client import is_connected


PAGES = {
    "📊 Dashboard":      "Dashboard",
    "📋 Réservations":   "Réservations",
    "📅 Calendrier":     "Calendrier",
    "📈 Analyses":       "Analyses",
    "🕳️ Créneaux":      "Créneaux",
}


def sidebar() -> str:
    with st.sidebar:
        st.title("🏖️ Vacances-Locations")
        st.caption("PRO — Gestion locative")

        if is_connected():
            st.success("🟢 Supabase", icon="✅")
        else:
            st.warning("🟡 Mode CSV")

        st.divider()
        choice = st.radio("Navigation", list(PAGES.keys()), label_visibility="collapsed")
        st.divider()
        st.caption("v2.0 — 2026")

    return PAGES[choice]
