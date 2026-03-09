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


def _on_prop_change():
    """Callback : copie l'index sélectionné vers prop_id réel."""
    idx = st.session_state["_prop_select_idx"]
    props = get_proprietes_dict()
    options_ids = [0] + list(props.keys())
    st.session_state["prop_id"] = options_ids[idx]


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

        st.markdown("**🏠 Propriété active**")

        props = get_proprietes_dict()
        options_ids    = [0] + list(props.keys())
        options_labels = ["🏠 Toutes"] + list(props.values())

        # Retrouver l'index courant depuis prop_id
        current_id  = st.session_state.get("prop_id", 0)
        current_idx = options_ids.index(current_id) if current_id in options_ids else 0

        # Stocker l'index dans une clé séparée, le callback traduit en ID réel
        if "_prop_select_idx" not in st.session_state:
            st.session_state["_prop_select_idx"] = current_idx

        st.selectbox(
            "prop_sidebar",
            options=range(len(options_labels)),
            format_func=lambda i: options_labels[i],
            index=current_idx,
            key="_prop_select_idx",
            on_change=_on_prop_change,
            label_visibility="collapsed",
        )

        if current_id != 0:
            st.caption(f"📍 {props.get(current_id, '')}")

        st.divider()

        choice = st.radio(
            "Navigation",
            list(PAGES.keys()),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("v3.0 — 2026")

    return PAGES[choice]
