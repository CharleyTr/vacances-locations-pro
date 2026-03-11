"""Repository checklist items & done."""
from database.supabase_client import get_supabase, is_connected

TABLE_ITEMS = "checklist_items"
TABLE_DONE  = "checklist_done"

# ── Items (modèle) ─────────────────────────────────────────────────────────────

def get_items(propriete_id: int) -> list[dict]:
    if not is_connected(): return []
    try:
        res = get_supabase().table(TABLE_ITEMS).select("*")\
            .eq("propriete_id", propriete_id).order("ordre").execute()
        return res.data or []
    except Exception as e:
        print(f"[ChecklistRepo] get_items: {e}")
        return []

def save_item(data: dict) -> dict | None:
    if not is_connected(): return None
    try:
        sb = get_supabase()
        if data.get("id"):
            return sb.table(TABLE_ITEMS).update(data).eq("id", data["id"]).execute().data
        return sb.table(TABLE_ITEMS).insert(data).execute().data
    except Exception as e:
        print(f"[ChecklistRepo] save_item: {e}")
        return None

def delete_item(item_id: int) -> bool:
    if not is_connected(): return False
    try:
        get_supabase().table(TABLE_ITEMS).delete().eq("id", item_id).execute()
        return True
    except Exception as e:
        print(f"[ChecklistRepo] delete_item: {e}")
        return False

# ── Done (état coché par date) ─────────────────────────────────────────────────

def get_done(propriete_id: int, date_menage: str) -> dict[int, bool]:
    """Retourne {item_id: fait} pour une date donnée."""
    if not is_connected(): return {}
    try:
        res = get_supabase().table(TABLE_DONE).select("item_id, fait")\
            .eq("propriete_id", propriete_id).eq("date_menage", date_menage).execute()
        return {r["item_id"]: r["fait"] for r in (res.data or [])}
    except Exception as e:
        print(f"[ChecklistRepo] get_done: {e}")
        return {}

def set_done(propriete_id: int, date_menage: str, item_id: int, fait: bool) -> bool:
    if not is_connected(): return False
    try:
        get_supabase().table(TABLE_DONE).upsert({
            "propriete_id": propriete_id,
            "date_menage":  date_menage,
            "item_id":      item_id,
            "fait":         fait,
        }, on_conflict="propriete_id,date_menage,item_id").execute()
        return True
    except Exception as e:
        print(f"[ChecklistRepo] set_done: {e}")
        return False
