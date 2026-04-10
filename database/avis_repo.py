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




def get_or_create_lien_questionnaire(reservation: dict, app_url: str = "") -> str:
    """
    Retourne le lien questionnaire pour une réservation.
    Crée l'entrée dans la table avis si elle n'existe pas encore.
    """
    import hashlib, os, secrets as _sec
    from datetime import datetime, timezone, timedelta

    if not is_connected():
        return ""

    res_id  = str(reservation.get("id", "") or "")
    nom     = str(reservation.get("nom_client", "") or "")
    prop_id = reservation.get("propriete_id")
    if not res_id:
        return ""

    _app_url = app_url or os.environ.get("APP_URL", "")

    try:
        sb = get_supabase()
        # Chercher un avis existant pour cette réservation
        existing = sb.table(TABLE).select("token")                     .eq("reservation_id", res_id).execute().data
        if existing and existing[0].get("token"):
            token = existing[0]["token"]
        else:
            # Créer un nouveau token unique
            token = _sec.token_urlsafe(16)
            expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            sb.table(TABLE).insert({
                "reservation_id":  res_id,
                "nom_client":      nom,
                "propriete_id":    prop_id,
                "token":           token,
                "token_expires_at": expires,
                "token_used":      False,
                "date_sejour":     str(reservation.get("date_arrivee", ""))[:10],
                "plateforme":      reservation.get("plateforme", ""),
            }).execute()

        return f"{_app_url}/?token={token}" if _app_url else f"/?token={token}"

    except Exception as e:
        print(f"[AvisRepo] get_or_create_token: {e}")
        # Fallback : lien simple avec hash
        token_fb = hashlib.md5(f"{res_id}{_app_url}".encode()).hexdigest()[:16]
        return f"{_app_url}/?token={token_fb}" if _app_url else ""

def delete_avis(avis_id: int) -> bool:
    if not is_connected():
        return False
    try:
        get_supabase().table(TABLE).delete().eq("id", avis_id).execute()
        return True
    except Exception as e:
        print(f"[AvisRepo] delete: {e}")
        return False


def create_token_questionnaire(reservation: dict, propriete: dict,
                                jours_validite: int = 30) -> str | None:
    """
    Crée un avis avec token pour le questionnaire post-séjour.
    Retourne le token généré ou None en cas d'erreur.
    """
    import uuid
    from datetime import datetime, timezone, timedelta

    if not is_connected():
        return None
    try:
        token = str(uuid.uuid4()).replace("-", "")
        expires = datetime.now(timezone.utc) + timedelta(days=jours_validite)

        data = {
            "reservation_id":  reservation.get("id"),
            "propriete_id":    reservation.get("propriete_id"),
            "nom_client":      reservation.get("nom_client", ""),
            "plateforme":      reservation.get("plateforme", ""),
            "date_sejour":     str(reservation.get("date_arrivee", ""))[:10],
            "_prop_nom":       propriete.get("nom", ""),
            "token":           token,
            "token_used":      False,
            "token_expires_at": expires.isoformat(),
        }
        get_supabase().table(TABLE).insert(data).execute()
        return token
    except Exception as e:
        print(f"[AvisRepo] create_token: {e}")
        return None
