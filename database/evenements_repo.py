"""Repository pour les événements de la ville."""
from database.supabase_client import get_supabase

TABLE = "evenements"

TYPE_LABELS = {
    "evenement":  "📅 Événement",
    "festival":   "🎪 Festival",
    "salon":      "🏢 Salon / Congrès",
    "concert":    "🎵 Concert",
    "sport":      "🏆 Événement sportif",
    "ferie":      "🎌 Jour férié",
}

IMPACT_LABELS = {
    "fort":   "🔴 Fort",
    "moyen":  "🟠 Moyen",
    "faible": "🟡 Faible",
}

COULEURS_TYPE = {
    "festival": "#E91E63",
    "salon":    "#1565C0",
    "concert":  "#7B1FA2",
    "sport":    "#E53935",
    "ferie":    "#00897B",
    "evenement":"#FF6B35",
}


def get_evenements(propriete_id: int = None, annee: int = None) -> list[dict]:
    sb = get_supabase()
    if sb is None:
        return []
    try:
        q = sb.table(TABLE).select("*").eq("actif", True)
        if propriete_id:
            q = q.eq("propriete_id", propriete_id)
        if annee:
            q = q.gte("date_debut", f"{annee}-01-01").lte("date_fin", f"{annee}-12-31")
        return q.order("date_debut").execute().data or []
    except Exception as e:
        print(f"[Evenements] get: {e}")
        return []


def get_evenements_mois(annee: int, mois: int, propriete_id: int = None) -> list[dict]:
    """Retourne les événements qui chevauchent un mois donné."""
    from datetime import date
    import calendar
    debut_mois = date(annee, mois, 1).isoformat()
    fin_mois   = date(annee, mois, calendar.monthrange(annee, mois)[1]).isoformat()
    sb = get_supabase()
    if sb is None:
        return []
    try:
        q = sb.table(TABLE).select("*").eq("actif", True)\
               .lte("date_debut", fin_mois)\
               .gte("date_fin",   debut_mois)
        if propriete_id:
            q = q.eq("propriete_id", propriete_id)
        return q.order("date_debut").execute().data or []
    except Exception as e:
        print(f"[Evenements] get_mois: {e}")
        return []


def save_evenement(data: dict) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    try:
        d = {k: v for k, v in data.items() if k != "id"}
        if data.get("id"):
            sb.table(TABLE).update(d).eq("id", data["id"]).execute()
        else:
            sb.table(TABLE).insert(d).execute()
        return True
    except Exception as e:
        print(f"[Evenements] save: {e}")
        return False


def delete_evenement(evt_id: int) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    try:
        sb.table(TABLE).delete().eq("id", evt_id).execute()
        return True
    except Exception as e:
        print(f"[Evenements] delete: {e}")
        return False
