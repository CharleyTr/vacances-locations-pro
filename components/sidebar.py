import streamlit as st
from database.supabase_client import is_connected, get_connection_error
from services.proprietes_service import get_proprietes_dict
from database.proprietes_repo import fetch_all
from services.auth_service import is_unlocked, lock

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
    "📊 Export comptable": "Export comptable",
    "🏛️ Fiscal LMNP":      "Fiscal LMNP",
    "📈 Revenus & Pricing": "Revenus & Pricing",
    "📐 Barèmes fiscaux":    "Barèmes fiscaux",
    "🧾 Factures":           "Factures",
    "📖 Documentation":      "Documentation",
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
        # Non-admin : forcer la propriété déverrouillée, désactiver la sélection
        _forced = st.session_state.get("_forced_prop_id")
        _is_admin_sidebar = st.session_state.get("is_admin", False)

        if _forced and not _is_admin_sidebar and _forced in options_ids:
            # Afficher juste le nom sans selectbox
            idx_forced = options_ids.index(_forced)
            st.markdown(f"**{options_labels[idx_forced]}**")
            # Synchroniser sans toucher au widget
            if st.session_state.get("prop_id") != _forced:
                st.session_state["prop_id"] = _forced
        else:
            st.selectbox(
                "prop_sidebar",
                options=options_ids if _is_admin_sidebar else
                        [i for i in options_ids if i == 0 or
                         st.session_state.get(f"unlocked_{i}", False)],
                format_func=lambda x: options_labels[options_ids.index(x)],
                key="prop_id",
                label_visibility="collapsed",
            )

        current = st.session_state.get("prop_id", 0)
        if current and current != 0:
            # Vérifier si mot de passe configuré
            props_full = {p["id"]: p for p in fetch_all()}
            mdp_hash = props_full.get(current, {}).get("mot_de_passe")
            if mdp_hash:
                if is_unlocked(current):
                    col_cap, col_lock = st.columns([3,1])
                    col_cap.caption(f"📍 {props.get(current, '')}")
                    if col_lock.button("🔒", key="btn_lock", help="Verrouiller"):
                        lock(current)
                        st.rerun()
                else:
                    st.caption(f"🔐 {props.get(current, '')} — *verrouillé*")
            else:
                st.caption(f"📍 {props.get(current, '')}")

        st.divider()

        # Pages admin uniquement (Villa Tobias)
        PAGES_ADMIN_ONLY = {"🏠 Propriétés", "📐 Barèmes fiscaux"}
        is_admin = st.session_state.get("is_admin", False)

        pages_visibles = {
            k: v for k, v in PAGES.items()
            if k not in PAGES_ADMIN_ONLY or is_admin
        }

        choice = st.radio(
            "Navigation",
            list(pages_visibles.keys()),
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("v3.0 — 2026")

    return pages_visibles[choice]
