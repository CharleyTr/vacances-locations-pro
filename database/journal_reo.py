"""Repository pour le journal des connexions."""
from database.supabase_client import get_supabase

TABLE = "journal_connexions"


def log_connexion(
    mode: str,
    statut: str,
    user_email: str = "",
    user_id: str = "",
    propriete_id: int = None,
    propriete_nom: str = "",
    detail: str = "",
) -> None:
    """Enregistre une tentative de connexion (succès ou échec)."""
    sb = get_supabase()
    if sb is None:
        return
    try:
        row = {
            "mode":         mode,
            "statut":       statut,
            "user_email":   user_email or None,
            "user_id":      str(user_id) if user_id else None,
            "propriete_id": propriete_id,
            "propriete_nom":propriete_nom or None,
            "detail":       detail or None,
        }
        sb.table(TABLE).insert(row).execute()
    except Exception as e:
        print(f"log_connexion error: {e}")


def get_journal(limit: int = 200) -> list:
    """Retourne les dernières connexions (admin uniquement)."""
    sb = get_supabase()
    if sb is None:
        return []
    try:
        return sb.table(TABLE).select("*")\
                 .order("created_at", desc=True)\
                 .limit(limit).execute().data or []
    except Exception as e:
        print(f"get_journal error: {e}")
        return []


def get_stats_connexions() -> dict:
    """Statistiques rapides pour le dashboard admin."""
    sb = get_supabase()
    if sb is None:
        return {}
    try:
        all_rows = sb.table(TABLE).select("statut, mode, created_at")\
                     .order("created_at", desc=True).limit(500).execute().data or []
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        today    = [r for r in all_rows if r["created_at"][:10] == now.strftime("%Y-%m-%d")]
        week     = [r for r in all_rows if (now - datetime.fromisoformat(r["created_at"].replace("Z","+00:00"))).days < 7]
        echecs   = [r for r in all_rows if r["statut"] == "echec"]
        return {
            "total":         len(all_rows),
            "today":         len(today),
            "week":          len(week),
            "echecs_today":  len([r for r in today if r["statut"] == "echec"]),
            "echecs_total":  len(echecs),
            "last":          all_rows[0]["created_at"][:16].replace("T"," ") if all_rows else "—",
        }
    except Exception:
        return {}
