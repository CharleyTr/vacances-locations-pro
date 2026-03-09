"""
Export des réservations au format iCal (.ics) pour import dans Google Calendar.
Génère un fichier .ics par propriété, téléchargeable et importable dans n'importe quel
calendrier (Google Calendar, Apple Calendar, Outlook...).
"""
import uuid
from datetime import datetime, timezone
from io import BytesIO


COULEURS_GCAL = {
    # Valeurs COLOR acceptées par Google Calendar (via X-APPLE-CALENDAR-COLOR et CATEGORIES)
    "Booking":   "TOMATO",
    "Airbnb":    "FLAMINGO",
    "Direct":    "SAGE",
    "Abritel":   "BANANA",
    "Fermeture": "GRAPHITE",
}


def reservations_to_ics(reservations: list[dict], nom_calendrier: str = "Vacances-Locations") -> bytes:
    """
    Convertit une liste de réservations en fichier .ics (bytes).

    Chaque réservation doit avoir :
      - nom_client, date_arrivee, date_depart, plateforme
      - prix_net (optionnel), nuitees (optionnel), paye (optionnel)
      - email, telephone (optionnels)
    """
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Vacances-Locations PRO//FR",
        f"X-WR-CALNAME:{nom_calendrier}",
        "X-WR-TIMEZONE:Europe/Paris",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    for res in reservations:
        # Dates
        arrivee = _to_date_str(res.get("date_arrivee"))
        depart  = _to_date_str(res.get("date_depart"))
        if not arrivee or not depart:
            continue

        client     = _escape(str(res.get("nom_client", "Client")))
        plateforme = str(res.get("plateforme", "Direct"))
        nuits      = res.get("nuitees", "")
        prix       = res.get("prix_net", 0)
        paye       = res.get("paye", False)
        email      = res.get("email", "")
        tel        = res.get("telephone", "")
        num_res    = res.get("numero_reservation", "")

        # Titre de l'événement
        summary = f"{client} — {plateforme} ({nuits}n)" if nuits else f"{client} — {plateforme}"

        # Description détaillée
        desc_parts = [
            f"Client : {client}",
            f"Plateforme : {plateforme}",
            f"Durée : {nuits} nuits" if nuits else "",
            f"Prix net : {float(prix):.2f} €" if prix else "",
            f"Paiement : {'✅ Payé' if paye else '⏳ En attente'}",
            f"N° réservation : {num_res}" if num_res else "",
            f"Email : {email}" if email else "",
            f"Tél : {tel}" if tel else "",
        ]
        description = _escape("\\n".join(p for p in desc_parts if p))

        # UID unique basé sur les données (stable = pas de doublons si réimporté)
        uid_base  = f"{res.get('id', '')}-{arrivee}-{client}"
        event_uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, uid_base))

        lines += [
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{now}",
            f"DTSTART;VALUE=DATE:{arrivee}",
            f"DTEND;VALUE=DATE:{depart}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            f"CATEGORIES:{plateforme}",
            f"STATUS:CONFIRMED",
            "END:VEVENT",
        ]

    lines.append("END:VCALENDAR")

    content = "\r\n".join(lines)
    return content.encode("utf-8")


def _to_date_str(val) -> str | None:
    """Convertit une date en string YYYYMMDD pour iCal."""
    if val is None:
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y%m%d")
    s = str(val)[:10].replace("-", "")
    return s if len(s) == 8 else None


def _escape(text: str) -> str:
    """Échappe les caractères spéciaux iCal."""
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
