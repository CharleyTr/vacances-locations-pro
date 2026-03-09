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

        st.markdown("**🏠 Propriété active**")

        props = get_proprietes_dict()
        options_ids    = [0] + list(props.keys())
        options_labels = ["🏠 Toutes"] + list(props.values())

        # On stocke l'ID directement — options contient les vrais IDs
        current_id = int(st.session_state.get("prop_id", 0))
        if current_id not in options_ids:
            current_id = 0
        current_idx = options_ids.index(current_id)

        chosen = st.selectbox(
            "prop_sidebar",
            options=options_ids,                          # ← les IDs réels (0, 1, 2…)
            format_func=lambda x: options_labels[options_ids.index(x)],
            index=current_idx,
            label_visibility="collapsed",
        )

        # Écriture directe dans session_state — pas de callback, pas de rerun
        st.session_state["prop_id"] = int(chosen)

        if chosen != 0:
            st.caption(f"📍 {props.get(chosen, '')}")

        st.divider()

        choice = st.radio(
            "Navigation",
            list(PAGES.keys()),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("v3.0 — 2026")

    return PAGES[choice]
