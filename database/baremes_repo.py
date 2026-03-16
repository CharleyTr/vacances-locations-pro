"""Repository pour les barèmes fiscaux éditables."""
import json
from database.supabase_client import get_supabase

TABLE = "baremes_fiscaux"

def get_bareme(annee: int) -> dict | None:
    sb = get_supabase()
    if sb is None:
        return None
    try:
        r = sb.table(TABLE).select("*").eq("annee", annee).execute()
        if r.data:
            return r.data[0]
    except:
        pass
    return None

def get_all_baremes() -> list:
    sb = get_supabase()
    if sb is None:
        return []
    try:
        return sb.table(TABLE).select("*").order("annee", desc=True).execute().data or []
    except:
        return []

def save_bareme(data: dict) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    try:
        # tranches_ir doit être une string JSON si c'est une liste
        if isinstance(data.get("tranches_ir"), list):
            data = dict(data)
            data["tranches_ir"] = json.dumps(data["tranches_ir"])
        if data.get("id"):
            d = {k: v for k, v in data.items() if k != "id"}
            sb.table(TABLE).update(d).eq("id", data["id"]).execute()
        else:
            sb.table(TABLE).upsert(data, on_conflict="annee").execute()
        return True
    except Exception as e:
        print(f"save_bareme error: {e}")
        return False


def bareme_to_dict(row: dict) -> dict:
    """Convertit une ligne DB en dict compatible avec le code fiscal existant."""
    if not row:
        return {}
    tranches = row.get("tranches_ir", [])
    if isinstance(tranches, str):
        import json
        tranches = json.loads(tranches)
    return {
        "micro_bic_classe_seuil":      int(row.get("seuil_classe", 188700)),
        "micro_bic_non_classe_seuil":  int(row.get("seuil_non_classe", 77700)),
        "abattement_classe":           float(row.get("abattement_classe", 0.71)),
        "abattement_non_classe":       float(row.get("abattement_non_classe", 0.50)),
        "abattement_min_classe":       float(row.get("abattement_min", 305)),
        "csg_crds":                    float(row.get("csg_crds", 0.172)),
        "cotisations_ssi_taux":        float(row.get("cotisations_ssi", 0.231)),
        "cotisations_urssaf_taux":     0.172,
        "seuil_cotisations":           int(row.get("seuil_cotisations", 23000)),
        "loi_note":                    row.get("loi_note", ""),
        "tranches_ir": [
            (t["bas"], t.get("haut"), t["taux"])
            for t in tranches
        ],
    }
