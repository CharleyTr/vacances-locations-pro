"""Service de calcul des KPIs."""
import pandas as pd
from datetime import datetime


def compute_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return _empty_kpis()

    ca_brut      = df["prix_brut"].sum() if "prix_brut" in df.columns else 0
    ca_net       = df["prix_net"].sum()  if "prix_net"  in df.columns else 0
    commissions  = df["commissions"].sum() if "commissions" in df.columns else 0
    menage       = df["menage"].sum()    if "menage"    in df.columns else 0
    taxes        = df["taxes_sejour"].sum() if "taxes_sejour" in df.columns else 0

    nb_reservations = len(df)
    nuits_total     = int(df["nuitees"].sum()) if "nuitees" in df.columns else 0
    revenu_nuit     = round(ca_net / nuits_total, 2) if nuits_total > 0 else 0

    non_payes = df[df["paye"] == False] if "paye" in df.columns else pd.DataFrame()
    montant_en_attente = non_payes["prix_net"].sum() if not non_payes.empty else 0

    # Taux occupation (approx. sur l'année en cours)
    annee = datetime.now().year
    df_annee = df[df["annee"] == annee] if "annee" in df.columns else df
    nuits_annee = int(df_annee["nuitees"].sum()) if not df_annee.empty else 0
    taux_occupation = round(nuits_annee / 365 * 100, 1)

    # Répartition plateformes
    repartition = {}
    if "plateforme" in df.columns:
        repartition = df.groupby("plateforme")["prix_net"].sum().round(2).to_dict()

    return {
        "ca_brut": round(ca_brut, 2),
        "ca_net": round(ca_net, 2),
        "commissions": round(commissions, 2),
        "menage": round(menage, 2),
        "taxes": round(taxes, 2),
        "nb_reservations": nb_reservations,
        "nuits_total": nuits_total,
        "revenu_nuit": revenu_nuit,
        "montant_en_attente": round(montant_en_attente, 2),
        "taux_occupation": taux_occupation,
        "repartition_plateformes": repartition,
    }


def compute_monthly(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "mois" not in df.columns:
        return pd.DataFrame()

    monthly = df.groupby("mois").agg(
        ca_brut=("prix_brut", "sum"),
        ca_net=("prix_net", "sum"),
        nb_reservations=("id", "count"),
        nuits=("nuitees", "sum"),
    ).reset_index()

    monthly["mois_str"] = monthly["mois"].dt.strftime("%b %Y")
    return monthly


def _empty_kpis() -> dict:
    return {
        "ca_brut": 0, "ca_net": 0, "commissions": 0,
        "menage": 0, "taxes": 0, "nb_reservations": 0,
        "nuits_total": 0, "revenu_nuit": 0,
        "montant_en_attente": 0, "taux_occupation": 0,
        "repartition_plateformes": {},
    }
