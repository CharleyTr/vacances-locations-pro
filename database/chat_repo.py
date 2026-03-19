"""Repository pour la messagerie interne."""
from database.supabase_client import get_supabase

TABLE = "chat_messages"


def get_messages(limit: int = 100, propriete_id: int = None) -> list:
    """Retourne les derniers messages (globaux ou par propriété)."""
    sb = get_supabase()
    if sb is None:
        return []
    try:
        q = sb.table(TABLE).select("*").order("created_at", desc=False).limit(limit)
        if propriete_id:
            q = q.eq("propriete_id", propriete_id)
        return q.execute().data or []
    except Exception as e:
        print(f"get_messages error: {e}")
        return []


def send_message(contenu: str, user_email: str, user_nom: str = "",
                 propriete_id: int = None) -> dict | None:
    """Envoie un message."""
    sb = get_supabase()
    if sb is None:
        return None
    try:
        r = sb.table(TABLE).insert({
            "contenu":      contenu.strip(),
            "user_email":   user_email,
            "user_nom":     user_nom or user_email.split("@")[0],
            "propriete_id": propriete_id,
        }).execute()
        return r.data[0] if r.data else None
    except Exception as e:
        print(f"send_message error: {e}")
        return None


def count_unread(user_email: str) -> int:
    """Nombre de messages non lus pour cet utilisateur."""
    sb = get_supabase()
    if sb is None:
        return 0
    try:
        rows = sb.table(TABLE).select("lu_par").execute().data or []
        return sum(1 for r in rows if user_email not in (r.get("lu_par") or []))
    except:
        return 0


def mark_read(user_email: str) -> None:
    """Marque tous les messages comme lus pour cet utilisateur."""
    sb = get_supabase()
    if sb is None:
        return
    try:
        rows = sb.table(TABLE).select("id,lu_par").execute().data or []
        for r in rows:
            lu_par = r.get("lu_par") or []
            if user_email not in lu_par:
                sb.table(TABLE).update({"lu_par": lu_par + [user_email]})\
                  .eq("id", r["id"]).execute()
    except Exception as e:
        print(f"mark_read error: {e}")


def delete_message(msg_id: int) -> bool:
    """Supprime un message (admin uniquement)."""
    sb = get_supabase()
    if sb is None:
        return False
    try:
        sb.table(TABLE).delete().eq("id", msg_id).execute()
        return True
    except:
        return False
