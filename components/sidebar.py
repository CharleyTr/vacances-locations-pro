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
    "📊 Rapports":       "Rapports",
    "💶 Tarifs":         "Tarifs",
    "⭐ Livre d'or":     "Livre d'or",
    "📥 Import Booking": "Import Booking",
    "📥 Import Airbnb":  "Import Airbnb",
    "📝 Modèles msgs":   "Modèles msgs",
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
        st.markdown("**🏠 Propriété active**")

        props = get_proprietes_dict()  # {1: "Le Turenne...", 2: "Villa Tobias..."}
        options_ids    = [0] + list(props.keys())
        options_labels = ["🏠 Toutes"] + list(props.values())

        # key="prop_id" → Streamlit écrit DIRECTEMENT la valeur sélectionnée
        # (l'un des options_ids) dans st.session_state["prop_id"]
        # Pas de index=, pas de callback, pas de rerun — Streamlit gère tout seul
        st.selectbox(
            "prop_sidebar",
            options=options_ids,
            format_func=lambda x: options_labels[options_ids.index(x)],
            key="prop_id",
            label_visibility="collapsed",
        )

        current = st.session_state.get("prop_id", 0)
        if current and current != 0:
            st.caption(f"📍 {props.get(current, '')}")

        st.divider()

        choice = st.radio(
            "Navigation",
            list(PAGES.keys()),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("v3.0 — 2026")

    return PAGES[choice]
