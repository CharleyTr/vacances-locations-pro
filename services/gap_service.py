"""Détection des créneaux libres entre réservations."""
import pandas as pd
from datetime import date


def detect_gaps(df: pd.DataFrame, propriete_id: int | None = None) -> list[dict]:
    if df.empty:
        return []

    if propriete_id and "propriete_id" in df.columns:
        df = df[df["propriete_id"] == propriete_id]

    df = df.sort_values("date_arrivee").dropna(subset=["date_arrivee", "date_depart"])
    gaps = []

    for i in range(len(df) - 1):
        depart  = df.iloc[i]["date_depart"]
        arrivee = df.iloc[i + 1]["date_arrivee"]

        if hasattr(depart, "date"):
            depart = depart.date()
        if hasattr(arrivee, "date"):
            arrivee = arrivee.date()

        diff = (arrivee - depart).days

        if diff > 0:
            gaps.append({
                "start":  depart,
                "end":    arrivee,
                "nuits":  diff,
                "avant":  df.iloc[i].get("nom_client", ""),
                "apres":  df.iloc[i + 1].get("nom_client", ""),
            })

    return gaps
