"""Alertes : arrivées proches, paiements manquants."""
import pandas as pd
from datetime import datetime, timedelta


def upcoming_arrivals(df: pd.DataFrame, days: int = 3) -> pd.DataFrame:
    today = datetime.today()
    limit = today + timedelta(days=days)

    mask = (df["date_arrivee"] >= today) & (df["date_arrivee"] <= limit)
    return df[mask].sort_values("date_arrivee")


def unpaid_reservations(df: pd.DataFrame) -> pd.DataFrame:
    if "paye" not in df.columns:
        return pd.DataFrame()
    return df[df["paye"] == False].sort_values("date_arrivee")


def missing_contacts(df: pd.DataFrame) -> pd.DataFrame:
    """Réservations sans email ni téléphone."""
    mask = df["email"].isna() & df["telephone"].isna()
    return df[mask]
