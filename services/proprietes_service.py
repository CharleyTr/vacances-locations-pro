"""
Service propriétés — source unique de vérité pour tous les fichiers.
Utilise st.session_state pour la propriété sélectionnée globalement.
"""
import streamlit as st
from database.proprietes_repo import fetch_dict, fetch_all

SESSION_KEY = "propriete_selectionnee"  # 0 = toutes


def get_proprietes_dict() -> dict:
    """Retourne {id: nom} depuis Supabase (avec cache)."""
    return fetch_dict()


def get_proprietes_list() -> list[dict]:
    """Retourne la liste complète des propriétés."""
    return fetch_all()


def get_propriete_selectionnee() -> int:
    """Retourne l'ID de la propriété sélectionnée globalement (0 = toutes)."""
    return st.session_state.get(SESSION_KEY, 0)


def set_propriete_selectionnee(prop_id: int):
    st.session_state[SESSION_KEY] = prop_id


def get_label(prop_id: int) -> str:
    """Retourne le nom d'une propriété par son ID."""
    if prop_id == 0:
        return "Toutes les propriétés"
    props = get_proprietes_dict()
    return props.get(prop_id, f"Propriété {prop_id}")


def filter_df(df, prop_id: int | None = None):
    """Filtre un DataFrame selon la propriété sélectionnée."""
    import pandas as pd
    if "propriete_id" in df.columns:
        df["propriete_id"] = df["propriete_id"].fillna(0).astype(int)

    pid = prop_id if prop_id is not None else get_propriete_selectionnee()
    if pid == 0:
        return df
    return df[df["propriete_id"] == pid]
