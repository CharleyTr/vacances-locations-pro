"""
Dépôt de données pour les réservations.
Lit depuis Supabase si connecté, sinon depuis le CSV local.
"""
import pandas as pd
from typing import Optional
from database.supabase_client import get_supabase

TABLE = "reservations"

# Colonnes attendues dans le CSV / Supabase
COLONNES_DATES = ["date_arrivee", "date_depart", "created_at", "updated_at"]
COLONNES_BOOL  = ["paye", "sms_envoye", "post_depart_envoye"]


# ──────────────────────────────────────────────
# LECTURE
# ──────────────────────────────────────────────

def fetch_all(propriete_id: Optional[int] = None) -> pd.DataFrame:
    """Récupère toutes les réservations depuis Supabase."""
    sb = get_supabase()
    if sb is None:
        raise ConnectionError("Supabase non configuré")

    query = sb.table(TABLE).select("*").order("date_arrivee")
    if propriete_id:
        query = query.eq("propriete_id", propriete_id)

    result = query.execute()
    df = pd.DataFrame(result.data)
    return _clean_df(df)


def fetch_by_id(reservation_id: int) -> Optional[dict]:
    sb = get_supabase()
    if sb is None:
        return None
    result = sb.table(TABLE).select("*").eq("id", reservation_id).single().execute()
    return result.data


# ──────────────────────────────────────────────
# ÉCRITURE
# ──────────────────────────────────────────────

def insert_reservation(data: dict) -> dict:
    """Insère une réservation dans Supabase."""
    sb = get_supabase()
    if sb is None:
        raise ConnectionError("Supabase non configuré")
    result = sb.table(TABLE).insert(_prepare(data)).execute()
    return result.data[0] if result.data else {}


def update_reservation(reservation_id: int, data: dict) -> dict:
    sb = get_supabase()
    if sb is None:
        raise ConnectionError("Supabase non configuré")
    result = (
        sb.table(TABLE)
        .update(_prepare(data))
        .eq("id", reservation_id)
        .execute()
    )
    return result.data[0] if result.data else {}


def delete_reservation(reservation_id: int) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    sb.table(TABLE).delete().eq("id", reservation_id).execute()
    return True


def upsert_reservations(rows: list[dict]) -> int:
    """Insère ou met à jour en masse (import CSV)."""
    sb = get_supabase()
    if sb is None:
        raise ConnectionError("Supabase non configuré")

    prepared = [_prepare(r) for r in rows]
    result = sb.table(TABLE).upsert(prepared, on_conflict="id").execute()
    return len(result.data)


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _prepare(data: dict) -> dict:
    """Nettoie un dict avant envoi à Supabase."""
    clean = {}
    for k, v in data.items():
        if pd.isna(v) if not isinstance(v, (list, dict, bool)) else False:
            clean[k] = None
        elif isinstance(v, pd.Timestamp):
            clean[k] = v.isoformat()
        else:
            clean[k] = v
    # Supprimer les colonnes calculées côté DB (aucune ici - nuitees doit être fourni)
    return clean


def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    for col in COLONNES_DATES:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in COLONNES_BOOL:
        if col in df.columns:
            df[col] = df[col].astype(bool)
    return df
