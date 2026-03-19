"""
Service d'authentification — gère les deux modes (PIN + Supabase Auth).
Point d'entrée unique pour toutes les vérifications d'accès.
"""
import hashlib


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.strip().encode()).hexdigest()


# ── Mode PIN (rétrocompatible) ─────────────────────────────────────────────────

def is_unlocked(prop_id: int) -> bool:
    """Vérifie si une propriété est déverrouillée dans la session."""
    import streamlit as st
    if st.session_state.get("is_admin", False):
        return True
    return bool(st.session_state.get(f"unlocked_{prop_id}", False))


def lock(prop_id: int) -> None:
    """Verrouille une propriété."""
    import streamlit as st
    st.session_state.pop(f"unlocked_{prop_id}", None)
    st.session_state["global_logged_in"] = False


def require_auth(prop_id: int, prop_nom: str = "", mdp_hash: str = "") -> bool:
    import streamlit as st
    """
    Vérifie si l'utilisateur a accès à la propriété.
    Retourne True si accès autorisé.
    """
    if not mdp_hash:
        return True
    if st.session_state.get("is_admin", False):
        return True
    if is_unlocked(prop_id):
        return True
    # Afficher le formulaire de déverrouillage
    st.warning(f"🔒 Cette propriété ({prop_nom}) est protégée.")
    with st.form(f"unlock_{prop_id}"):
        pin = st.text_input("Code d'accès", type="password", key=f"pin_input_{prop_id}")
        ok = st.form_submit_button("🔓 Déverrouiller")
    if ok:
        if _hash_pin(pin) == mdp_hash or pin == mdp_hash:
            st.session_state[f"unlocked_{prop_id}"] = True
            st.rerun()
        else:
            st.error("❌ Code incorrect.")
    return False


# ── Mode Supabase Auth ─────────────────────────────────────────────────────────

def get_auth_user() -> dict | None:
    import streamlit as st
    """Retourne les infos de l'utilisateur Auth connecté, ou None."""
    user_id = st.session_state.get("auth_user_id")
    if not user_id:
        return None
    return {
        "id":    user_id,
        "email": st.session_state.get("auth_user_email", ""),
        "role":  st.session_state.get("auth_user_role", "proprietaire"),
    }


def is_admin() -> bool:
    import streamlit as st
    return bool(st.session_state.get("is_admin", False))


def get_accessible_prop_ids() -> list[int] | None:
    import streamlit as st
    """
    Retourne la liste des prop_id accessibles, ou None = toutes (admin).
    """
    if is_admin():
        return None
    user = get_auth_user()
    if user:
        from database.auth_repo import get_proprietes_for_user
        props = get_proprietes_for_user(user["id"], user["role"])
        return [p["id"] for p in props]
    # Mode PIN — lire les propriétés déverrouillées
    unlocked = [
        int(k.replace("unlocked_", ""))
        for k in st.session_state
        if k.startswith("unlocked_") and st.session_state[k]
    ]
    return unlocked or None


def logout() -> None:
    import streamlit as st
    """Déconnexion complète — vide la session."""
    user = get_auth_user()
    if user:
        try:
            from database.auth_repo import sign_out
            sign_out()
        except Exception:
            pass
    for key in list(st.session_state.keys()):
        del st.session_state[key]
