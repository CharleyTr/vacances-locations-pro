"""
Service d'import CSV vers Supabase.
Gère le format exact du fichier reservations.csv exporté.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from database.supabase_client import is_connected
import database.reservations_repo as repo

COLONNES_NUMERIQUES = [
    "prix_brut", "commissions", "frais_cb", "prix_net",
    "menage", "taxes_sejour", "base", "charges",
    "pct_commission", "commissions_hote", "frais_menage"
]
COLONNES_BOOL = ["paye", "sms_envoye", "post_depart_envoye"]


def import_csv_file(file) -> dict:
    """
    Importe un CSV dans Supabase.
    Retourne un résumé {importées, doublons, erreurs}.
    """
    df = _parse_csv(file)

    if not is_connected():
        raise ConnectionError(
            "Supabase non configuré. Ajoutez SUPABASE_URL et SUPABASE_KEY dans .env"
        )

    rows = df.to_dict(orient="records")
    count = repo.upsert_reservations(rows)

    return {
        "importées": count,
        "total_csv": len(df),
        "erreurs": len(df) - count,
    }


def preview_csv(file) -> pd.DataFrame:
    """Prévisualise le CSV sans importer."""
    return _parse_csv(file)


def _parse_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)

    # Dates
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"], errors="coerce")
    df["date_depart"]  = pd.to_datetime(df["date_depart"],  errors="coerce")

    # Numériques
    for col in COLONNES_NUMERIQUES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Booléens
    for col in COLONNES_BOOL:
        if col in df.columns:
            df[col] = df[col].map(
                lambda x: str(x).lower() == "true" if pd.notna(x) else False
            )

    # Nettoyage champs texte
    for col in ["nom_client", "email", "telephone", "pays", "plateforme", "numero_reservation"]:
        if col in df.columns:
            df[col] = df[col].where(df[col].notna(), None)

    # Suppression colonne nuitees (calculée côté DB)
    df.drop(columns=["nuitees"], errors="ignore", inplace=True)

    # Supprimer les lignes sans dates
    df.dropna(subset=["date_arrivee", "date_depart"], inplace=True)

    return df
