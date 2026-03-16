"""
Service propriétés.
La propriété active est dans st.session_state["prop_id"] (0 = toutes).
"""
import streamlit as st
from database.proprietes_repo import fetch_dict, fetch_all


def get_proprietes_dict() -> dict:
    return fetch_dict()


def get_proprietes_list() -> list[dict]:
    return fetch_all()


def get_propriete_selectionnee() -> int:
    """Retourne l'ID actif. Toujours un int, jamais None."""
    val = st.session_state.get("prop_id", 0)
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def get_label(prop_id: int = None) -> str:
    if prop_id is None:
        prop_id = get_propriete_selectionnee()
    if prop_id == 0:
        return "Toutes les propriétés"
    return get_proprietes_dict().get(prop_id, f"Propriété {prop_id}")


def filter_df(df, prop_id: int = None):
    """Filtre le DataFrame par propriété. prop_id=None → lit session_state."""
    if df.empty:
        return df

    df = df.copy()
    if "propriete_id" in df.columns:
        df["propriete_id"] = df["propriete_id"].fillna(0).astype(int)

    if prop_id is None:
        prop_id = get_propriete_selectionnee()

    if prop_id == 0:
        return df

    return df[df["propriete_id"] == prop_id]


def get_proprietes_autorises() -> dict:
    """
    Retourne les propriétés accessibles :
    - Admin (Villa Tobias) : toutes les propriétés
    - Autre : uniquement la propriété déverrouillée au login
    """
    import streamlit as st
    from database.proprietes_repo import fetch_all
    from services.auth_service import is_unlocked

    all_props = fetch_all()
    if st.session_state.get("is_admin", False):
        return {p["id"]: p["nom"] for p in all_props}
    return {
        p["id"]: p["nom"] for p in all_props
        if not p.get("mot_de_passe") or is_unlocked(p["id"])
    }
