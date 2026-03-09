"""
Service de chargement des réservations.
Priorité : Supabase → CSV local (fallback).
"""
import pandas as pd
from pathlib import Path
from database.supabase_client import is_connected
import database.reservations_repo as repo

CSV_PATH = Path(__file__).parent.parent / "data" / "reservations.csv"
COLONNES_BOOL = ["paye", "sms_envoye", "post_depart_envoye"]


def load_reservations(propriete_id: int | None = None) -> pd.DataFrame:
    """Charge les réservations depuis Supabase ou CSV local."""
    if is_connected():
        try:
            df = repo.fetch_all(propriete_id)
            return _enrich(df)
        except Exception as e:
            print(f"[ReservationService] Erreur Supabase, bascule CSV : {e}")

    return _load_from_csv(propriete_id)


def _load_from_csv(propriete_id: int | None = None) -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(CSV_PATH)
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"], errors="coerce")
    df["date_depart"]  = pd.to_datetime(df["date_depart"],  errors="coerce")

    for col in COLONNES_BOOL:
        if col in df.columns:
            df[col] = df[col].map(
                lambda x: str(x).lower() == "true" if pd.notna(x) else False
            )

    if propriete_id is not None:
        df = df[df["propriete_id"] == propriete_id]

    return _enrich(df)


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    if "nuitees" not in df.columns or df["nuitees"].isna().any():
        df["nuitees"] = (df["date_depart"] - df["date_arrivee"]).dt.days

    if "prix_net" in df.columns:
        df["revenu_par_nuit"] = df.apply(
            lambda r: round(r["prix_net"] / r["nuitees"], 2) if r["nuitees"] > 0 else 0,
            axis=1
        )

    if "paye" in df.columns:
        df["statut_paiement"] = df["paye"].map({True: "✅ Payé", False: "⏳ En attente"})

    df["mois"] = df["date_arrivee"].dt.to_period("M")
    df["annee"] = df["date_arrivee"].dt.year

    return df
