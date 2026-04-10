"""CRUD pour la table proprietes."""
import pandas as pd
from database.supabase_client import get_supabase
TABLE = "proprietes"
_cache: list | None = None

def fetch_all(force_refresh: bool = False) -> list[dict]:
    """Retourne toutes les propriétés actives depuis Supabase."""
    global _cache
    sb = get_supabase()
    if sb is None:
        return _fallback()
    try:
        result = sb.table(TABLE).select("*").eq("actif", True).order("id").execute()
        _cache = result.data or []
        return _cache
    except Exception:
        if _cache is not None:
            return _cache
        return _fallback()

def fetch_dict(force_refresh: bool = False) -> dict:
    """Retourne {id: nom} pour tous les sélecteurs."""
    props = fetch_all(force_refresh)
    return {p["id"]: p["nom"] for p in props}

def insert_propriete(data: dict) -> dict:
    sb = get_supabase()
    if sb is None:
        raise ConnectionError("Supabase non configuré")
    global _cache
    _cache = None
    result = sb.table(TABLE).insert(data).execute()
    return result.data[0] if result.data else {}

def update_propriete(prop_id: int, data: dict) -> dict:
    sb = get_supabase()
    if sb is None:
        raise ConnectionError("Supabase non configuré")
    global _cache
    _cache = None
    result = sb.table(TABLE).update(data).eq("id", prop_id).execute()
    return result.data[0] if result.data else {}

def delete_propriete(prop_id: int) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    global _cache
    _cache = None
    sb.table(TABLE).update({"actif": False}).eq("id", prop_id).execute()
    return True

def _fallback() -> list[dict]:
    """Données par défaut si Supabase non disponible."""
    return [
        {"id": 1, "nom": "Le Turenne - Bordeaux",  "adresse": "Bordeaux", "actif": True},
        {"id": 2, "nom": "Villa Tobias - Nice",     "adresse": "Nice",     "actif": True},
    ]
