from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

_client: Client | None = None

def get_supabase() -> Client | None:
    """Retourne le client Supabase, ou None si non configuré."""
    global _client
    if _client is None:
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                _client = create_client(SUPABASE_URL, SUPABASE_KEY)
            except Exception as e:
                print(f"[Supabase] Connexion impossible : {e}")
                return None
    return _client

def is_connected() -> bool:
    return get_supabase() is not None
