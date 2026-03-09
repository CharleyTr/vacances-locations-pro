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

        # ── Sélecteur propriété ───────────────────────────────────────────
        # Le key="propriete_selectionnee" stocke DIRECTEMENT l'ID (0, 1, 2...)
        # dans st.session_state["propriete_selectionnee"]
        st.markdown("**🏠 Propriété active**")

        props = get_proprietes_dict()  # {1: "Le Turenne...", 2: "Villa Tobias..."}
        options_ids    = [0] + list(props.keys())
        options_labels = {0: "🏠 Toutes"} | {k: v for k, v in props.items()}

        st.selectbox(
            "prop_sidebar",
            options=options_ids,
            format_func=lambda x: options_labels.get(x, f"Propriété {x}"),
            key="propriete_selectionnee",   # ← valeur = l'ID directement
            label_visibility="collapsed",
        )

        st.divider()

        choice = st.radio(
            "Navigation",
            list(PAGES.keys()),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("v3.0 — 2026")

    return PAGES[choice]
