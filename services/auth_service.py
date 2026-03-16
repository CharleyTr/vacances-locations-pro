"""
Module d'authentification par propriété.
Mot de passe stocké hashé (SHA-256) dans la table proprietes.
"""
import hashlib
import streamlit as st
from database.proprietes_repo import fetch_all, update_propriete


def _hash(mdp: str) -> str:
    return hashlib.sha256(mdp.strip().encode()).hexdigest()


def check_password(prop_id: int, mdp_saisi: str, mdp_hash_stored: str) -> bool:
    """Vérifie si le mot de passe saisi correspond au hash stocké."""
    return _hash(mdp_saisi) == mdp_hash_stored


def set_password(prop_id: int, nouveau_mdp: str) -> bool:
    """Enregistre un nouveau mot de passe hashé pour la propriété."""
    try:
        update_propriete(prop_id, {"mot_de_passe": _hash(nouveau_mdp)})
        return True
    except Exception as e:
        print(f"set_password error: {e}")
        return False


def remove_password(prop_id: int) -> bool:
    """Supprime le mot de passe d'une propriété (accès libre)."""
    try:
        update_propriete(prop_id, {"mot_de_passe": None})
        return True
    except Exception as e:
        print(f"remove_password error: {e}")
        return False


def is_unlocked(prop_id: int) -> bool:
    """Retourne True si la propriété est déverrouillée en session."""
    if prop_id == 0:
        return True
    return st.session_state.get(f"unlocked_{prop_id}", False)


def unlock(prop_id: int):
    st.session_state[f"unlocked_{prop_id}"] = True


def lock(prop_id: int):
    st.session_state.pop(f"unlocked_{prop_id}", None)


def require_auth(prop_id: int, prop_nom: str, mdp_hash: str) -> bool:
    """
    Affiche le formulaire de connexion si nécessaire.
    Retourne True si l'accès est autorisé, False si le formulaire est affiché.
    """
    if not mdp_hash:          # Pas de mot de passe configuré
        return True
    if is_unlocked(prop_id):  # Déjà authentifié en session
        return True

    # Afficher le formulaire
    st.markdown("---")
    col = st.columns([1, 2, 1])[1]
    with col:
        st.markdown(
            f"<div style='text-align:center;padding:2rem 1rem'>"
            f"<div style='font-size:48px'>🔐</div>"
            f"<h3>{prop_nom}</h3>"
            f"<p style='color:#666'>Cette propriété est protégée par un mot de passe.</p>"
            f"</div>",
            unsafe_allow_html=True
        )
        with st.form(f"form_auth_{prop_id}"):
            mdp_input = st.text_input("Mot de passe", type="password",
                                       placeholder="Entrez le mot de passe...")
            submitted = st.form_submit_button("🔓 Accéder", type="primary",
                                               use_container_width=True)

        if submitted:
            if check_password(prop_id, mdp_input, mdp_hash):
                unlock(prop_id)
                st.success("✅ Accès autorisé !")
                st.rerun()
            else:
                st.error("❌ Mot de passe incorrect.")
    return False
