"""Génère les événements pour la vue calendrier."""
import pandas as pd

COULEURS_PLATEFORME = {
    "Booking":  "#003580",
    "Airbnb":   "#FF5A5F",
    "Direct":   "#2E7D32",
}


def build_calendar_events(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    events = []
    for _, row in df.iterrows():
        plateforme = row.get("plateforme", "Direct")
        couleur = COULEURS_PLATEFORME.get(plateforme, "#607D8B")

        events.append({
            "title":       row.get("nom_client", "—"),
            "start":       str(row["date_arrivee"])[:10],
            "end":         str(row["date_depart"])[:10],
            "plateforme":  plateforme,
            "color":       couleur,
            "nuits":       int(row.get("nuitees", 0)),
            "prix_net":    float(row.get("prix_net", 0)),
            "paye":        bool(row.get("paye", False)),
            "propriete_id": int(row.get("propriete_id", 1)),
        })

    return events
