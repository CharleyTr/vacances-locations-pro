import streamlit as st
from database.supabase_client import is_connected, get_connection_error
from services.proprietes_service import get_proprietes_dict

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

        if is_connected():
            st.success("🟢 Supabase connecté", icon="✅")
        else:
            err = get_connection_error()
            st.error("🔴 Supabase non connecté")
            if err:
                st.caption(f"⚠️ {err}")

        st.divider()

        # ── Sélecteur propriété global ────────────────────────────────────
        # La clé "propriete_selectionnee" est lue directement par toutes les pages
        # via st.session_state — pas besoin de rerun ni de setter
        st.markdown("**🏠 Propriété active**")

        props = get_proprietes_dict()
        options_ids    = [0] + list(props.keys())
        options_labels = ["🏠 Toutes"] + list(props.values())

        # Initialiser à 0 si absent
        if "propriete_selectionnee" not in st.session_state:
            st.session_state["propriete_selectionnee"] = 0

        current = st.session_state["propriete_selectionnee"]
        current_idx = options_ids.index(current) if current in options_ids else 0

        chosen_idx = st.selectbox(
            "prop_sidebar",
            options=range(len(options_labels)),
            format_func=lambda i: options_labels[i],
            index=current_idx,
            label_visibility="collapsed",
        )

        # Mettre à jour session_state directement sans rerun
        st.session_state["propriete_selectionnee"] = options_ids[chosen_idx]

        st.divider()

        choice = st.radio(
            "Navigation",
            list(PAGES.keys()),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("v3.0 — 2026")

    return PAGES[choice]
