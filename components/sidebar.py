import streamlit as st
from database.supabase_client import is_connected, get_connection_error
from services.proprietes_service import (
    get_proprietes_dict, get_propriete_selectionnee,
    set_propriete_selectionnee
)

PAGES = {
    "📊 Dashboard":      "Dashboard",
    "📋 Réservations":   "Réservations",
    "📅 Calendrier":     "Calendrier",
    "📈 Analyses":       "Analyses",
    "💳 Paiements":      "Paiements",
    "🧹 Ménage":         "Ménage",
    "📧 Messages":       "Messages",
    "🔄 Sync iCal":      "iCal",
    "🕳️ Créneaux":      "Créneaux",
    "🏠 Propriétés":     "Propriétés",
}


def sidebar() -> str:
    with st.sidebar:
        st.title("🏖️ Vacances-Locations")
        st.caption("PRO — Gestion locative")

        # ── Statut connexion ──────────────────────────────────────────────
        if is_connected():
            st.success("🟢 Supabase connecté", icon="✅")
        else:
            err = get_connection_error()
            st.error("🔴 Supabase non connecté")
            if err:
                st.caption(f"⚠️ {err}")

        st.divider()

        # ── Sélecteur propriété global ────────────────────────────────────
        st.markdown("**🏠 Propriété active**")

        props = get_proprietes_dict()
        options_ids    = [0] + list(props.keys())
        options_labels = ["Toutes"] + list(props.values())

        current = get_propriete_selectionnee()
        current_idx = options_ids.index(current) if current in options_ids else 0

        selected_idx = st.selectbox(
            "prop_global",
            range(len(options_labels)),
            format_func=lambda i: options_labels[i],
            index=current_idx,
            label_visibility="collapsed",
            key="sidebar_prop_select"
        )
        selected_id = options_ids[selected_idx]

        if selected_id != current:
            set_propriete_selectionnee(selected_id)
            st.rerun()

        if selected_id != 0:
            st.caption(f"📍 {options_labels[selected_idx]}")

        st.divider()

        # ── Navigation ────────────────────────────────────────────────────
        choice = st.radio(
            "Navigation",
            list(PAGES.keys()),
            label_visibility="collapsed"
        )
        st.divider()
        st.caption("v3.0 — 2026")

    return PAGES[choice]
