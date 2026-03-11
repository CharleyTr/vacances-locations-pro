"""Repository livre d'or."""
from database.supabase_client import get_supabase, is_connected
import pandas as pd

TABLE = "avis"

def get_avis(propriete_id: int = None) -> list[dict]:
    if not is_connected(): return []
    try:
        q = get_supabase().table(TABLE).select("*").order("created_at", desc=True)
        if propriete_id:
            q = q.eq("propriete_id", propriete_id)
        return q.execute().data or []
    except Exception as e:
        print(f"[AvisRepo] get: {e}")
        return []

def save_avis(data: dict) -> bool:
    if not is_connected(): return False
    try:
        sb = get_supabase()
        if data.get("id"):
            sb.table(TABLE).update(data).eq("id", data["id"]).execute()
        else:
            sb.table(TABLE).insert(data).execute()
        return True
    except Exception as e:
        print(f"[AvisRepo] save: {e}")
        return False

def delete_avis(avis_id: int) -> bool:
    if not is_connected(): return False
    try:
        get_supabase().table(TABLE).delete().eq("id", avis_id).execute()
        return True
    except Exception as e:
        print(f"[AvisRepo] delete: {e}")
        return False
