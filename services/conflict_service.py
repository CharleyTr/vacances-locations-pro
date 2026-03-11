"""
Service de détection des conflits de réservations.
Un conflit = deux réservations qui se chevauchent sur la même propriété.
"""
import pandas as pd
from datetime import date


def detect_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retourne un DataFrame des paires en conflit.
    Colonnes : prop_id, res1_id, res1_client, res1_arrivee, res1_depart,
               res2_id, res2_client, res2_arrivee, res2_depart, overlap_days
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"])
    df["date_depart"]  = pd.to_datetime(df["date_depart"])
    df = df.dropna(subset=["date_arrivee", "date_depart"])

    conflicts = []

    for prop_id in df["propriete_id"].unique():
        df_p = df[df["propriete_id"] == prop_id].sort_values("date_arrivee").reset_index(drop=True)

        for i in range(len(df_p)):
            for j in range(i + 1, len(df_p)):
                a = df_p.iloc[i]
                b = df_p.iloc[j]

                # Chevauchement : arrivée B avant départ A (et B commence après A)
                overlap_start = max(a["date_arrivee"], b["date_arrivee"])
                overlap_end   = min(a["date_depart"],  b["date_depart"])

                if overlap_start < overlap_end:
                    overlap_days = (overlap_end - overlap_start).days
                    conflicts.append({
                        "propriete_id":  prop_id,
                        "res1_id":       a.get("id", ""),
                        "res1_client":   a.get("nom_client", "?"),
                        "res1_arrivee":  a["date_arrivee"].date(),
                        "res1_depart":   a["date_depart"].date(),
                        "res1_plat":     a.get("plateforme", "?"),
                        "res2_id":       b.get("id", ""),
                        "res2_client":   b.get("nom_client", "?"),
                        "res2_arrivee":  b["date_arrivee"].date(),
                        "res2_depart":   b["date_depart"].date(),
                        "res2_plat":     b.get("plateforme", "?"),
                        "overlap_days":  overlap_days,
                    })

    return pd.DataFrame(conflicts) if conflicts else pd.DataFrame()
