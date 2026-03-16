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

# Correspondance catégorie → rubrique déclaration LMNP réel simplifié
# Formulaire 2031 + annexe 2033-B (Compte de résultat simplifié)
IR_RUBRIQUES = {
    "Amortissements":          "2033-B Ligne 250 — Dotations aux amortissements",
    "Travaux & réparations":   "2033-B Ligne 236 — Autres achats et charges externes",
    "Frais de gestion / Compta": "2033-B Ligne 236 — Autres achats et charges externes",
    "Assurances":              "2033-B Ligne 236 — Autres achats et charges externes",
    "Charges de copropriété":  "2033-B Ligne 236 — Autres achats et charges externes",
    "Intérêts d'emprunt":      "2033-B Ligne 256 — Charges financières",
    "Taxe foncière":           "2033-B Ligne 240 — Impôts et taxes",
    "Frais de ménage":         "2033-B Ligne 236 — Autres achats et charges externes",
    "Frais de plateforme":     "2033-B Ligne 236 — Autres achats et charges externes",
    "Abonnements & services":  "2033-B Ligne 236 — Autres achats et charges externes",
    "Équipements & mobilier":  "2033-B Ligne 250 — Dotations amort. (si >500€) / Ligne 236 si <500€",
    "Frais divers":            "2033-B Ligne 258 — Autres charges",
}

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
