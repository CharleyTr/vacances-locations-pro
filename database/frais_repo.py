"""Repository pour les frais déductibles (régime réel LMNP)."""
from database.supabase_client import get_supabase

TABLE = "frais_deductibles"

CATEGORIES = [
    "Amortissements",
    "Travaux & réparations",
    "Frais de gestion / Compta",
    "Assurances",
    "Charges de copropriété",
    "Intérêts d'emprunt",
    "Taxe foncière",
    "Frais de ménage",
    "Frais de plateforme",
    "Abonnements & services",
    "Équipements & mobilier",
    "Frais divers",
]

def get_frais(propriete_id: int, annee: int) -> list:
    sb = get_supabase()
    if sb is None:
        return []
    try:
        return sb.table(TABLE).select("*")\
            .eq("propriete_id", propriete_id)\
            .eq("annee", annee)\
            .order("categorie")\
            .execute().data or []
    except Exception:
        return []

def save_frais(data: dict) -> bool:
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
        print(f"save_frais error: {e}")
        return False

def delete_frais(frais_id: int) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    try:
        sb.table(TABLE).delete().eq("id", frais_id).execute()
        return True
    except Exception:
        return False

def upsert_frais_batch(rows: list) -> bool:
    """Sauvegarde une liste de frais (update si id présent, insert sinon)."""
    sb = get_supabase()
    if sb is None:
        return False
    try:
        for row in rows:
            save_frais(row)
        return True
    except Exception:
        return False
