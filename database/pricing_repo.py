"""Repository pour événements locaux et prix concurrents."""
from database.supabase_client import get_supabase

def get_evenements(propriete_id=None):
    sb = get_supabase()
    if sb is None: return []
    try:
        q = sb.table("evenements_locaux").select("*").order("date_debut")
        if propriete_id:
            q = q.or_(f"propriete_id.eq.{propriete_id},propriete_id.is.null")
        return q.execute().data or []
    except: return []

def save_evenement(data):
    sb = get_supabase()
    if sb is None: return False
    try:
        d = {k: v for k, v in data.items() if k != "id"}
        if data.get("id"):
            sb.table("evenements_locaux").update(d).eq("id", data["id"]).execute()
        else:
            sb.table("evenements_locaux").insert(d).execute()
        return True
    except Exception as e:
        print(f"save_evenement: {e}"); return False

def delete_evenement(eid):
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.table("evenements_locaux").delete().eq("id", eid).execute()
        return True
    except: return False

def get_concurrents(propriete_id):
    sb = get_supabase()
    if sb is None: return []
    try:
        return sb.table("prix_concurrents").select("*")\
            .eq("propriete_id", propriete_id)\
            .order("date_releve", desc=True).execute().data or []
    except: return []

def save_concurrent(data):
    sb = get_supabase()
    if sb is None: return False
    try:
        d = {k: v for k, v in data.items() if k != "id"}
        # Auto-remplir mois/annee depuis date_releve
        if "date_releve" in d and d["date_releve"]:
            from datetime import datetime
            try:
                dt = datetime.strptime(str(d["date_releve"])[:10], "%Y-%m-%d")
                d["mois"]  = dt.month
                d["annee"] = dt.year
            except Exception:
                pass
        if data.get("id"):
            sb.table("prix_concurrents").update(d).eq("id", data["id"]).execute()
        else:
            sb.table("prix_concurrents").insert(d).execute()
        return True
    except Exception as e:
        print(f"save_concurrent: {e}"); return False

def delete_concurrent(cid):
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.table("prix_concurrents").delete().eq("id", cid).execute()
        return True
    except: return False


# ── Nouvelle table prix_concurrents_mois (1 ligne par concurrent/année) ────

COLS_MOIS = ["m01","m02","m03","m04","m05","m06",
             "m07","m08","m09","m10","m11","m12"]

def get_concurrents_mois(propriete_id: int, annee: int) -> list[dict]:
    sb = get_supabase()
    if sb is None: return []
    try:
        return sb.table("prix_concurrents_mois").select("*")\
            .eq("propriete_id", propriete_id)\
            .eq("annee", annee)\
            .order("concurrent").execute().data or []
    except Exception as e:
        print(f"get_concurrents_mois: {e}"); return []

def save_concurrent_mois(data: dict) -> bool:
    """Upsert une ligne concurrent/année avec les 12 mois."""
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.table("prix_concurrents_mois").upsert(
            data, on_conflict="propriete_id,concurrent,annee"
        ).execute()
        return True
    except Exception as e:
        print(f"save_concurrent_mois: {e}"); return False

def delete_concurrent_mois(cid: int) -> bool:
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.table("prix_concurrents_mois").delete().eq("id", cid).execute()
        return True
    except Exception as e:
        print(f"delete_concurrent_mois: {e}"); return False
