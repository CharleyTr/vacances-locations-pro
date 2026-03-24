"""
Repository pour tracker les sessions actives (mouchard connexions).
"""
from database.supabase_client import get_supabase

TABLE = "sessions_actives"


def ping_session(session_id: str, user_email: str = "", user_role: str = "",
                 prop_id: int = 0, page: str = "") -> None:
    """Met à jour ou crée la session active. Appelé toutes les 30s."""
    sb = get_supabase()
    if sb is None:
        return
    try:
        sb.table(TABLE).upsert({
            "session_id":          session_id,
            "user_email":          user_email or "anonyme",
            "user_role":           user_role or "inconnu",
            "prop_id":             prop_id or 0,
            "page_courante":       page or "",
            "derniere_activite":   "now()",
        }, on_conflict="session_id").execute()
        # Nettoyer les sessions mortes (> 2 min d'inactivité)
        from datetime import datetime, timezone, timedelta
        seuil = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        sb.table(TABLE).delete().lt("derniere_activite", seuil).execute()
    except Exception as e:
        print(f"[Sessions] ping error: {e}")


def get_sessions_actives() -> list[dict]:
    """Retourne la liste des sessions actives (< 2 min d'inactivité)."""
    sb = get_supabase()
    if sb is None:
        return []
    try:
        from datetime import datetime, timezone, timedelta
        seuil = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        return sb.table(TABLE).select("*")\
                 .gt("derniere_activite", seuil)\
                 .order("derniere_activite", desc=True)\
                 .execute().data or []
    except Exception as e:
        print(f"[Sessions] get error: {e}")
        return []


def count_sessions_actives() -> int:
    """Retourne le nombre de sessions actives."""
    return len(get_sessions_actives())


def remove_session(session_id: str) -> None:
    """Supprime la session à la déconnexion."""
    sb = get_supabase()
    if sb is None:
        return
    try:
        sb.table(TABLE).delete().eq("session_id", session_id).execute()
    except Exception as e:
        print(f"[Sessions] remove error: {e}")
