"""Repository livre d'or avec critères détaillés et tokens questionnaire."""
from database.supabase_client import get_supabase, is_connected

TABLE = "avis"

CRITERES = [
    ("note_proprete",     "🧹 Propreté"),
    ("note_emplacement",  "📍 Emplacement"),
    ("note_personnel",    "👤 Personnel"),
    ("note_confort",      "🛋️ Confort"),
    ("note_equipements",  "⚙️ Équipements"),
    ("note_qualite_prix", "💶 Rapport qualité/prix"),
]


def get_avis(propriete_id: int = None) -> list[dict]:
    if not is_connected():
        return []
    try:
        q = get_supabase().table(TABLE).select("*").order("created_at", desc=True)
        if propriete_id:
            q = q.eq("propriete_id", propriete_id)
        return q.execute().data or []
    except Exception as e:
        print(f"[AvisRepo] get: {e}")
        return []


def get_avis_by_token(token: str) -> dict | None:
    """Récupère un avis par son token (accès public questionnaire)."""
    if not is_connected():
        return None
    try:
        res = get_supabase().table(TABLE)\
            .select("*").eq("token", token).single().execute()
        return res.data
    except Exception:
        return None


def save_avis(data: dict) -> bool:
    if not is_connected():
        return False
    try:
        sb  = get_supabase()
        d   = {k: v for k, v in data.items() if k != "id"}
        if data.get("id"):
            sb.table(TABLE).update(d).eq("id", data["id"]).execute()
        else:
            sb.table(TABLE).insert(d).execute()
        return True
    except Exception as e:
        print(f"[AvisRepo] save: {e}")
        return False


def submit_questionnaire(token: str, reponses: dict) -> bool:
    """Le client soumet ses réponses via le token."""
    if not is_connected():
        return False
    try:
        reponses["token_used"] = True
        get_supabase().table(TABLE)\
            .update(reponses).eq("token", token).execute()
        return True
    except Exception as e:
        print(f"[AvisRepo] submit: {e}")
        return False


def delete_avis(avis_id: int) -> bool:
    if not is_connected():
        return False
    try:
        get_supabase().table(TABLE).delete().eq("id", avis_id).execute()
        return True
    except Exception as e:
        print(f"[AvisRepo] delete: {e}")
        return False
