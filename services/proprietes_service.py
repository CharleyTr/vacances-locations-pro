"""
Service propriétés — source unique de vérité.
La propriété sélectionnée est stockée dans st.session_state["propriete_selectionnee"].
"""
import streamlit as st
from database.proprietes_repo import fetch_dict, fetch_all

SESSION_KEY = "propriete_selectionnee"


def get_proprietes_dict() -> dict:
    return fetch_dict()


def get_proprietes_list() -> list[dict]:
    return fetch_all()


def get_propriete_selectionnee() -> int:
    """Lit directement dans session_state — mis à jour par la sidebar."""
    return st.session_state.get(SESSION_KEY, 0)


def get_label(prop_id: int) -> str:
    if prop_id == 0:
        return "Toutes les propriétés"
    return get_proprietes_dict().get(prop_id, f"Propriété {prop_id}")


def filter_df(df, prop_id: int | None = None):
    """Filtre un DataFrame selon la propriété sélectionnée."""
    if "propriete_id" in df.columns:
        df = df.copy()
        df["propriete_id"] = df["propriete_id"].fillna(0).astype(int)

    pid = prop_id if prop_id is not None else get_propriete_selectionnee()
    if pid == 0:
        return df
    return df[df["propriete_id"] == pid]
