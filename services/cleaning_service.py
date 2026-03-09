"""Génère le planning de ménage."""
import pandas as pd
from datetime import date


def generate_cleaning_schedule(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    cols = ["propriete_id", "date_depart", "nom_client", "nuitees"]
    available = [c for c in cols if c in df.columns]
    cleanings = df[available].copy()

    cleanings = cleanings.rename(columns={"date_depart": "date_menage"})
    cleanings = cleanings.sort_values("date_menage")

    # Marquer les ménages à venir
    today = pd.Timestamp(date.today())
    cleanings["statut"] = cleanings["date_menage"].apply(
        lambda d: "🔜 À venir" if d >= today else "✅ Passé"
    )

    return cleanings
