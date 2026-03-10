"""Service de calcul des KPIs."""
import pandas as pd
from datetime import datetime, date


def compute_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return _empty_kpis()

    ca_brut     = df["prix_brut"].sum()    if "prix_brut"    in df.columns else 0
    ca_net      = df["prix_net"].sum()     if "prix_net"     in df.columns else 0
    commissions = df["commissions"].sum()  if "commissions"  in df.columns else 0
    menage      = df["menage"].sum()       if "menage"       in df.columns else 0
    taxes       = df["taxes_sejour"].sum() if "taxes_sejour" in df.columns else 0

    nb_reservations = len(df)
    # Nuits totales : toutes plateformes incluant Fermeture (pour le taux d'occupation)
    nuits_total     = int(df["nuitees"].sum()) if "nuitees" in df.columns else 0
    # Revenu/nuit : exclure Fermeture (pas de CA, fausserait la moyenne)
    df_payant = df[df["plateforme"] != "Fermeture"] if "plateforme" in df.columns else df
    nuits_payantes  = int(df_payant["nuitees"].sum()) if "nuitees" in df_payant.columns else 0
    revenu_nuit     = round(ca_net / nuits_payantes, 2) if nuits_payantes > 0 else 0

    non_payes = df[df["paye"] == False] if "paye" in df.columns else pd.DataFrame()
    montant_en_attente = non_payes["prix_net"].sum() if not non_payes.empty else 0

    annee = datetime.now().year
    df_annee = df[df["annee"] == annee] if "annee" in df.columns else df
    nuits_annee = int(df_annee["nuitees"].sum()) if not df_annee.empty else 0
    taux_occupation = round(nuits_annee / 365 * 100, 1)

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
    """
    Calcule les stats par mois en ventilant les nuits réellement passées
    dans chaque mois (une réservation du 26/02 au 01/03 = 3 nuits en fév, 0 en mars).

    Pour le CA : rattaché au mois d'arrivée (pas de prorata, c'est la convention comptable).
    Pour les nuits : ventilées jour par jour dans le bon mois.
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"])
    df["date_depart"]  = pd.to_datetime(df["date_depart"])

    # ── CA et réservations groupés par mois d'arrivée ────────────────────
    df["mois"] = df["date_arrivee"].dt.to_period("M")
    ca_monthly = df.groupby("mois").agg(
        ca_brut=(("prix_brut", "sum") if "prix_brut" in df.columns else ("prix_net", "sum")),
        ca_net=("prix_net", "sum"),
        nb_reservations=("id", "count"),
    ).reset_index()

    # ── Nuits ventilées par mois réel ─────────────────────────────────────
    # Pour chaque réservation, on calcule les nuits dans chaque mois qu'elle chevauche
    all_months = df["mois"].unique()
    nuits_par_mois = {}

    for period in all_months:
        ms_p       = period.to_timestamp()                      # 1er jour du mois
        me_exclu_p = (period + 1).to_timestamp()               # 1er jour du mois suivant

        def _nuits(row, ms=ms_p, me=me_exclu_p):
            debut = max(row["date_arrivee"], ms)
            fin   = min(row["date_depart"],  me)
            return max(0, (fin - debut).days)

        nuits_par_mois[period] = int(df.apply(_nuits, axis=1).sum())

    # Inclure aussi les mois touchés par des réservations qui dépassent (ex: arrivée en déc, départ en jan)
    for _, row in df.iterrows():
        arr, dep = row["date_arrivee"], row["date_depart"]
        if pd.isna(arr) or pd.isna(dep):
            continue
        p = arr.to_period("M")
        while p.to_timestamp() < dep:
            if p not in nuits_par_mois:
                ms_p       = p.to_timestamp()
                me_exclu_p = (p + 1).to_timestamp()
                def _n(row, ms=ms_p, me=me_exclu_p):
                    return max(0, (min(row["date_depart"], me) - max(row["date_arrivee"], ms)).days)
                nuits_par_mois[p] = int(df.apply(_n, axis=1).sum())
            p += 1

    df_nuits = pd.DataFrame([
        {"mois": k, "nuits": v} for k, v in nuits_par_mois.items()
    ])
    monthly = ca_monthly.merge(df_nuits, on="mois", how="left")

    monthly["nuits"]   = monthly["nuits"].fillna(0).astype(int)
    monthly["mois_str"] = monthly["mois"].dt.strftime("%b %Y")
    monthly = monthly.sort_values("mois")

    return monthly


def _empty_kpis() -> dict:
    return {
        "ca_brut": 0, "ca_net": 0, "commissions": 0,
        "menage": 0, "taxes": 0, "nb_reservations": 0,
        "nuits_total": 0, "revenu_nuit": 0,
        "montant_en_attente": 0, "taux_occupation": 0,
        "repartition_plateformes": {},
    }
