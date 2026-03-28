from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None
_error: str | None = None


def get_supabase() -> Client | None:
    global _client, _error

    if _client is not None:
        return _client

    # Relire config à chaque appel (st.secrets disponible seulement après démarrage)
    url = SUPABASE_URL
    key = SUPABASE_KEY

    # Si config.py a déjà chargé des valeurs vides, retenter via st.secrets directement
    if not url or not key:
        try:
            import streamlit as st
            url = st.secrets.get("SUPABASE_URL", "")
            key = st.secrets.get("SUPABASE_KEY", "")
        except Exception:
            pass

    if not url or not key:
        _error = "SUPABASE_URL ou SUPABASE_KEY manquant dans les secrets."
        return None

    try:
        _client = create_client(url, key)
        _error = None
        return _client
    except Exception as e:
        _error = str(e)
        return None


def _reset_client():
    """Force la recréation du client Supabase (utile si JWT expiré)."""
    global _client, _error
    _client = None
    _error = None


def is_connected() -> bool:
    return get_supabase() is not None


def get_connection_error() -> str | None:
    get_supabase()  # tenter la connexion
    return _error
