"""
Repository pour les modèles de messages (templates).
Table Supabase : message_templates
"""
from database.supabase_client import get_supabase

TABLE = "message_templates"

def get_templates(canal: str = None) -> list:
    sb = get_supabase()
    if sb is None:
        return []
    try:
        q = sb.table(TABLE).select("*").order("nom")
        if canal:
            q = q.eq("canal", canal)
        return q.execute().data or []
    except Exception:
        return []

def save_template(data: dict) -> bool:
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
        print(f"save_template error: {e}")
        return False

def delete_template(template_id: int) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    try:
        sb.table(TABLE).delete().eq("id", template_id).execute()
        return True
    except Exception:
        return False
