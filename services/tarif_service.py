"""
Service de gestion des tarifs par saison.
Calcul automatique du prix selon la période de réservation.
"""
import pandas as pd
from datetime import date, timedelta
from database.supabase_client import get_supabase, is_connected

TABLE = "tarifs_saison"

# Tarifs par défaut si aucune config en base
TARIFS_DEFAUT = [
    {"nom": "Basse saison",        "couleur": "#90CAF9", "prix_nuit": 80,  "prix_menage": 60},
    {"nom": "Moyenne saison",      "couleur": "#FFF176", "prix_nuit": 100, "prix_menage": 70},
    {"nom": "Haute saison",        "couleur": "#FFAB91", "prix_nuit": 140, "prix_menage": 80},
    {"nom": "Vacances scolaires",  "couleur": "#CE93D8", "prix_nuit": 120, "prix_menage": 75},
    {"nom": "Noël / Nouvel An",    "couleur": "#EF9A9A", "prix_nuit": 160, "prix_menage": 90},
]


def get_tarifs(propriete_id: int) -> list[dict]:
    """Récupère les tarifs Supabase ou retourne liste vide."""
    if not is_connected():
        return []
    try:
        sb = get_supabase()
        res = sb.table(TABLE).select("*").eq("propriete_id", propriete_id).order("date_debut").execute()
        return res.data or []
    except Exception as e:
        print(f"[TarifService] {e}")
        return []


def save_tarif(data: dict) -> bool:
    if not is_connected():
        return False
    try:
        sb = get_supabase()
        if data.get("id"):
            sb.table(TABLE).update(data).eq("id", data["id"]).execute()
        else:
            sb.table(TABLE).insert(data).execute()
        return True
    except Exception as e:
        print(f"[TarifService] save: {e}")
        return False


def delete_tarif(tarif_id: int) -> bool:
    if not is_connected():
        return False
    try:
        get_supabase().table(TABLE).delete().eq("id", tarif_id).execute()
        return True
    except Exception as e:
        print(f"[TarifService] delete: {e}")
        return False


def calcul_prix(
    date_arrivee: date,
    date_depart: date,
    propriete_id: int,
) -> dict:
    """
    Calcule le prix total d'un séjour selon les tarifs configurés.
    Retourne prix_nuit moyen pondéré, prix_total, frais_menage, détail par saison.
    """
    nuitees = (date_depart - date_arrivee).days
    if nuitees <= 0:
        return {"nuitees": 0, "prix_total": 0, "prix_nuit_moy": 0, "frais_menage": 0, "detail": []}

    tarifs = get_tarifs(propriete_id)
    if not tarifs:
        return {"nuitees": nuitees, "prix_total": 0, "prix_nuit_moy": 0,
                "frais_menage": 0, "detail": [], "erreur": "Aucun tarif configuré"}

    # Calculer nuit par nuit
    total_prix = 0.0
    frais_menage = 0.0
    detail = {}
    found_menage = False

    for n in range(nuitees):
        nuit = date_arrivee + timedelta(days=n)
        tarif_match = _find_tarif(nuit, tarifs)

        if tarif_match:
            nom = tarif_match["nom"]
            prix_n = float(tarif_match.get("prix_nuit", 0))
            total_prix += prix_n
            if not found_menage:
                frais_menage = float(tarif_match.get("prix_menage", 0))
                found_menage = True
            if nom not in detail:
                detail[nom] = {"nuits": 0, "prix_nuit": prix_n,
                                "couleur": tarif_match.get("couleur", "#90CAF9")}
            detail[nom]["nuits"] += 1
        else:
            total_prix += 0
            if "Non configuré" not in detail:
                detail["Non configuré"] = {"nuits": 0, "prix_nuit": 0, "couleur": "#BDBDBD"}
            detail["Non configuré"]["nuits"] += 1

    prix_nuit_moy = round(total_prix / nuitees, 2) if nuitees > 0 else 0

    return {
        "nuitees":       nuitees,
        "prix_total":    round(total_prix, 2),
        "prix_nuit_moy": prix_nuit_moy,
        "frais_menage":  frais_menage,
        "prix_ttc":      round(total_prix + frais_menage, 2),
        "detail":        [{"saison": k, **v} for k, v in detail.items()],
    }


def _find_tarif(d: date, tarifs: list[dict]):
    """Retourne le tarif correspondant à une date (premier match)."""
    for t in tarifs:
        try:
            debut = _to_date(t["date_debut"])
            fin   = _to_date(t["date_fin"])
            if debut <= d <= fin:
                return t
        except Exception:
            continue
    return None


def _to_date(val) -> date:
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        return date.fromisoformat(val[:10])
    return date.today()
