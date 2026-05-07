"""
Service de synchronisation des canaux iCal vers Supabase.
"""
from integrations.ical_sync import load_ical
from database.supabase_client import is_connected
import database.reservations_repo as repo

ICAL_SOURCES = {}

# Champs autorisés dans la table reservations
CHAMPS_AUTORISES = {
    "ical_uid", "nom_client", "date_arrivee", "date_depart",
    "nuitees", "plateforme", "propriete_id", "email",
    "telephone", "pays", "prix_brut", "prix_net",
    "numero_reservation",
}

def sync_ical(propriete_id: int, plateforme: str, url: str) -> dict:
    if not is_connected():
        return {"erreur": "Supabase non configuré"}
    try:
        reservations = load_ical(url)
    except Exception as e:
        return {"erreur": str(e)}

    count   = 0
    erreurs = []

    for res in reservations:
        res["propriete_id"] = propriete_id
        res["plateforme"]   = plateforme

        # Filtrer uniquement les champs autorisés
        res_clean = {k: v for k, v in res.items() if k in CHAMPS_AUTORISES}

        # Ignorer si ical_uid vide
        if not res_clean.get("ical_uid"):
            erreurs.append("ical_uid manquant")
            continue

        try:
            existing = repo.get_supabase().table("reservations") \
                .select("id") \
                .eq("ical_uid", res_clean["ical_uid"]) \
                .eq("propriete_id", propriete_id) \
                .execute()

            if existing.data:
                res_id = existing.data[0]["id"]
                repo.update_reservation(res_id, res_clean)
            else:
                repo.insert_reservation(res_clean)
            count += 1
        except Exception as e:
            erreurs.append(str(e) or "Erreur inconnue")

    return {
        "synchronisées": count,
        "total_ical":    len(reservations),
        "erreurs":       len(erreurs),
        "detail_erreurs": erreurs[:3],
    }
