"""
Service de synchronisation des canaux iCal vers Supabase.
"""
from integrations.ical_sync import load_ical
from database.supabase_client import is_connected
import database.reservations_repo as repo

# Configurer les URLs iCal de tes propriétés ici ou via Supabase
ICAL_SOURCES = {
    # propriete_id: {"plateforme": url, ...}
    # Exemple :
    # 1: {
    #     "Booking": "https://admin.booking.com/ical/...",
    #     "Airbnb":  "https://www.airbnb.fr/calendar/ical/...",
    # },
}


def sync_ical(propriete_id: int, plateforme: str, url: str) -> dict:
    """
    Synchronise un flux iCal et insère/met à jour les réservations dans Supabase.
    Retourne un résumé {nouvelles, mises_a_jour, erreurs}.
    """
    if not is_connected():
        return {"erreur": "Supabase non configuré"}

    try:
        reservations = load_ical(url)
    except Exception as e:
        return {"erreur": str(e)}

    count = 0
    erreurs = []

    for res in reservations:
        res["propriete_id"] = propriete_id
        res["plateforme"]   = plateforme

        try:
            # Upsert sur ical_uid pour éviter les doublons
            existing = repo.get_supabase().table("reservations") \
                .select("id") \
                .eq("ical_uid", res["ical_uid"]) \
                .execute()

            if existing.data:
                res_id = existing.data[0]["id"]
                repo.update_reservation(res_id, res)
            else:
                repo.insert_reservation(res)
            count += 1
        except Exception as e:
            erreurs.append(str(e))

    return {
        "synchronisées": count,
        "total_ical":    len(reservations),
        "erreurs":       len(erreurs),
    }
