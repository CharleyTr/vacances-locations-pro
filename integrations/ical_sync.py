"""
Synchronisation iCal — Import des réservations Booking/Airbnb via flux iCal.
"""
import requests
from icalendar import Calendar
from datetime import datetime, date
import pandas as pd


def load_ical(url: str) -> list[dict]:
    """
    Charge et parse un flux iCal depuis une URL.
    Retourne une liste de réservations sous forme de dicts.
    """
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ConnectionError(f"Impossible de charger le flux iCal : {e}")

    try:
        cal = Calendar.from_ical(response.content)
    except Exception as e:
        raise ValueError(f"Flux iCal invalide : {e}")

    reservations = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        summary = str(component.get("summary", ""))

        # Ignorer les blocages de maintenance
        if any(kw in summary.upper() for kw in ["BLOCKED", "NOT AVAILABLE", "MAINTENANCE"]):
            continue

        dtstart = component.get("dtstart")
        dtend   = component.get("dtend")

        if not dtstart or not dtend:
            continue

        start = dtstart.dt
        end   = dtend.dt

        # Convertir date → datetime si besoin
        if isinstance(start, date) and not isinstance(start, datetime):
            start = datetime.combine(start, datetime.min.time())
        if isinstance(end, date) and not isinstance(end, datetime):
            end = datetime.combine(end, datetime.min.time())

        nuits = (end.date() - start.date()).days

        ical_uid = str(component.get("uid", ""))
        description = str(component.get("description", ""))

        # Détecter plateforme depuis l'UID ou le résumé
        plateforme = _detect_platform(ical_uid, summary, url)

        reservations.append({
            "ical_uid":    ical_uid,
            "nom_client":  _clean_name(summary, plateforme),
            "date_arrivee": start.date().isoformat(),
            "date_depart":  end.date().isoformat(),
            "nuitees":      nuits,
            "plateforme":   plateforme,
            "description":  description[:500] if description else None,
        })

    return reservations


def _detect_platform(uid: str, summary: str, url: str) -> str:
    uid_lower = uid.lower()
    url_lower = url.lower()
    sum_lower = summary.lower()

    if "airbnb" in uid_lower or "airbnb" in url_lower:
        return "Airbnb"
    if "booking" in uid_lower or "booking" in url_lower:
        return "Booking"
    if "abritel" in uid_lower or "abritel" in url_lower or "homeaway" in url_lower:
        return "Abritel"
    if "vrbo" in url_lower:
        return "Abritel"
    return "Direct"


def _clean_name(summary: str, plateforme: str) -> str:
    """Nettoie le nom du client depuis le champ summary."""
    # Airbnb : "Reservation - Prénom Nom"
    for prefix in ["Reservation - ", "Réservation - ", "Reserved - ", "CLOSED - "]:
        if summary.startswith(prefix):
            return summary[len(prefix):].strip()
    # Booking : souvent juste le nom
    return summary.strip() or "Client iCal"


def ical_to_dataframe(reservations: list[dict]) -> pd.DataFrame:
    """Convertit la liste de réservations iCal en DataFrame."""
    if not reservations:
        return pd.DataFrame()
    df = pd.DataFrame(reservations)
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"])
    df["date_depart"]  = pd.to_datetime(df["date_depart"])
    return df
