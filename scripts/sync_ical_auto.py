"""
Script de synchronisation iCal automatique — GitHub Actions
Récupère les URLs iCal depuis Supabase et synchronise toutes les propriétés.
"""
import os
import requests
from icalendar import Calendar
from datetime import datetime, date
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

CHAMPS_AUTORISES = {
    "ical_uid", "nom_client", "date_arrivee", "date_depart",
    "nuitees", "plateforme", "propriete_id",
}

def load_ical(url):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  ❌ Erreur chargement URL : {e}")
        return []

    try:
        cal = Calendar.from_ical(r.content)
    except Exception as e:
        print(f"  ❌ Erreur parsing iCal : {e}")
        return []

    reservations = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("summary", ""))
        if any(kw in summary.upper() for kw in
               ["BLOCKED","NOT AVAILABLE","MAINTENANCE","UNAVAILABLE"]):
            continue

        dtstart = component.get("dtstart")
        dtend   = component.get("dtend")
        if not dtstart or not dtend:
            continue

        start = dtstart.dt
        end   = dtend.dt
        if isinstance(start, date) and not isinstance(start, datetime):
            start = datetime.combine(start, datetime.min.time())
        if isinstance(end, date) and not isinstance(end, datetime):
            end = datetime.combine(end, datetime.min.time())

        ical_uid = str(component.get("uid", ""))
        if not ical_uid:
            continue

        nom = summary.strip()
        for prefix in ["Reservation - ","Réservation - ","Reserved - ","CLOSED - "]:
            if nom.startswith(prefix):
                nom = nom[len(prefix):].strip()
                break
        if nom.upper() in ("RESERVED","NOT AVAILABLE","CLOSED",""):
            nom = "Client iCal"

        reservations.append({
            "ical_uid":     ical_uid,
            "nom_client":   nom,
            "date_arrivee": start.date().isoformat(),
            "date_depart":  end.date().isoformat(),
            "nuitees":      (end.date() - start.date()).days,
        })
    return reservations


def sync_propriete(prop_id, plateforme, url):
    print(f"  🔄 {plateforme} — prop {prop_id}")
    reservations = load_ical(url)
    if not reservations:
        print(f"  ⚠️ Aucune réservation dans le flux")
        return 0, 0

    count = 0
    erreurs = 0
    for res in reservations:
        res["propriete_id"] = prop_id
        res["plateforme"]   = plateforme
        res_clean = {k: v for k, v in res.items() if k in CHAMPS_AUTORISES}

        try:
            existing = sb.table("reservations")\
                .select("id")\
                .eq("ical_uid", res_clean["ical_uid"])\
                .eq("propriete_id", prop_id)\
                .execute()

            if existing.data:
                sb.table("reservations")\
                    .update({k: v for k, v in res_clean.items()
                             if k not in ("ical_uid","propriete_id")})\
                    .eq("id", existing.data[0]["id"])\
                    .execute()
            else:
                sb.table("reservations").insert(res_clean).execute()
            count += 1
        except Exception as e:
            erreurs += 1
            print(f"    ❌ {e}")

    print(f"  ✅ {count} sync, {erreurs} erreurs")
    return count, erreurs


def main():
    print("🔄 Démarrage sync iCal automatique")

    # Récupérer toutes les propriétés avec URLs iCal
    props = sb.table("proprietes")\
        .select("id, nom, ical_booking, ical_airbnb, ical_abritel")\
        .eq("actif", True)\
        .execute().data or []

    total_sync = 0
    total_err  = 0

    for prop in props:
        prop_id = prop["id"]
        prop_nom = prop.get("nom", "")

        sources = []
        if prop.get("ical_booking"):
            sources.append(("Booking", prop["ical_booking"]))
        if prop.get("ical_airbnb"):
            sources.append(("Airbnb", prop["ical_airbnb"]))
        if prop.get("ical_abritel"):
            sources.append(("Abritel", prop["ical_abritel"]))

        if not sources:
            continue

        print(f"\n📍 {prop_nom} (ID {prop_id})")
        for plateforme, url in sources:
            c, e = sync_propriete(prop_id, plateforme, url)
            total_sync += c
            total_err  += e

    print(f"\n✅ Sync terminée — {total_sync} réservations synchronisées, {total_err} erreurs")


if __name__ == "__main__":
    main()
