"""Service financier : récapitulatifs et rapports."""
import pandas as pd


def financial_summary(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}

    total_brut   = df["prix_brut"].sum()   if "prix_brut"   in df.columns else 0
    total_net    = df["prix_net"].sum()    if "prix_net"    in df.columns else 0
    total_comm   = df["commissions"].sum() if "commissions" in df.columns else 0
    total_menage = df["menage"].sum()      if "menage"      in df.columns else 0
    total_taxes  = df["taxes_sejour"].sum() if "taxes_sejour" in df.columns else 0
    avg_stay     = df["nuitees"].mean()    if "nuitees"     in df.columns else 0

    monthly = None
    if "mois" in df.columns:
        monthly = df.groupby("mois").agg(
            ca_net=("prix_net", "sum"),
            ca_brut=("prix_brut", "sum"),
        ).round(2)

    by_platform = None
    if "plateforme" in df.columns:
        by_platform = df.groupby("plateforme").agg(
            ca_net=("prix_net", "sum"),
            nb=("id", "count"),
        ).round(2)

    return {
        "total_brut":   round(total_brut, 2),
        "total_net":    round(total_net, 2),
        "total_comm":   round(total_comm, 2),
        "total_menage": round(total_menage, 2),
        "total_taxes":  round(total_taxes, 2),
        "avg_stay":     round(avg_stay, 1),
        "monthly":      monthly,
        "by_platform":  by_platform,
    }
