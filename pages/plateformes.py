"""CRUD pour la table platforms."""
from database.supabase_client import get_supabase

TABLE = "platforms"
_cache: list | None = None


def fetch_all(force_refresh: bool = False) -> list[dict]:
    """Retourne toutes les plateformes (actives et inactives) depuis Supabase."""
    global _cache
    if _cache is not None and not force_refresh:
        return _cache
    sb = get_supabase()
    if sb is None:
        return _fallback()
    try:
        result = sb.table(TABLE).select("*").order("nom").execute()
        _cache = result.data or []
        return _cache
    except Exception:
        if _cache is not None:
            return _cache
        return _fallback()


def fetch_actives(force_refresh: bool = False) -> list[dict]:
    """Retourne uniquement les plateformes actives."""
    return [p for p in fetch_all(force_refresh) if p.get("actif", True)]


def fetch_noms_actifs(force_refresh: bool = False) -> list[str]:
    """Retourne juste la liste des noms actifs, pour alimenter les selectbox/multiselect."""
    return [p["nom"] for p in fetch_actives(force_refresh)]


def insert_platform(data: dict) -> dict:
    sb = get_supabase()
    if sb is None:
        raise ConnectionError("Supabase non configuré")
    global _cache
    _cache = None
    result = sb.table(TABLE).insert(data).execute()
    return result.data[0] if result.data else {}


def update_platform(platform_id: str, data: dict) -> dict:
    sb = get_supabase()
    if sb is None:
        raise ConnectionError("Supabase non configuré")
    global _cache
    _cache = None
    result = sb.table(TABLE).update(data).eq("id", platform_id).execute()
    return result.data[0] if result.data else {}


def _fallback() -> list[dict]:
    """Données par défaut si Supabase non disponible (garantit que l'app ne casse pas)."""
    return [
        {"id": None, "nom": "Airbnb", "couleur": "#FF5A5F", "commission_pct": 0, "actif": True},
        {"id": None, "nom": "Airbnb/Annule", "couleur": "#FF5A5F", "commission_pct": 0, "actif": True},
        {"id": None, "nom": "Booking", "couleur": "#003580", "commission_pct": 0, "actif": True},
        {"id": None, "nom": "Booking/Annule", "couleur": "#003580", "commission_pct": 0, "actif": True},
        {"id": None, "nom": "Abritel", "couleur": "#4CAF50", "commission_pct": 0, "actif": True},
        {"id": None, "nom": "PAP", "couleur": "#9C27B0", "commission_pct": 0, "actif": True},
        {"id": None, "nom": "Direct", "couleur": "#607D8B", "commission_pct": 0, "actif": True},
        {"id": None, "nom": "VRBO", "couleur": "#3D67FF", "commission_pct": 0, "actif": True},
    ]
