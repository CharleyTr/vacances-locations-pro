"""Service de calcul des KPIs."""
import pandas as pd
from datetime import datetime, date

PLATEFORME_FERMETURE = "Fermeture"


def compute_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return _empty_kpis()

    # Séparer réservations réelles et fermetures
    if "plateforme" in df.columns:
        df_reel    = df[df["plateforme"] != PLATEFORME_FERMETURE]
        df_fermetu = df[df["plateforme"] == PLATEFORME_FERMETURE]
    else:
        df_reel    = df
        df_fermetu = pd.DataFrame()

    # CA calculé uniquement sur les réservations réelles
    ca_brut     = df_reel["prix_brut"].sum()    if "prix_brut"    in df_reel.columns else 0
    ca_net      = df_reel["prix_net"].sum()     if "prix_net"     in df_reel.columns else 0
    commissions = df_reel["commissions"].sum()  if "commissions"  in df_reel.columns else 0
    menage      = df_reel["menage"].sum()       if "menage"       in df_reel.columns else 0
    taxes       = df_reel["taxes_sejour"].sum() if "taxes_sejour" in df_reel.columns else 0

    # Réservations : uniquement les vraies (pas les fermetures)
    nb_reservations = len(df_reel)

    # Calculer les nuits depuis les dates si nuitees est NULL/0
    def _calc_nuits(d: pd.DataFrame) -> int:
        if d.empty:
            return 0
        if "nuitees" in d.columns:
            # Utiliser nuitees si disponible, sinon calculer depuis les dates
            n = d["nuitees"].copy()
            if "date_arrivee" in d.columns and "date_depart" in d.columns:
                mask_null = n.isna() | (n == 0)
                if mask_null.any():
                    arr = pd.to_datetime(d.loc[mask_null, "date_arrivee"])
                    dep = pd.to_datetime(d.loc[mask_null, "date_depart"])
                    n.loc[mask_null] = (dep - arr).dt.days
            return int(n.fillna(0).sum())
        elif "date_arrivee" in d.columns and "date_depart" in d.columns:
            arr = pd.to_datetime(d["date_arrivee"])
            dep = pd.to_datetime(d["date_depart"])
            return int((dep - arr).dt.days.fillna(0).sum())
        return 0

    # Nuits louées (sans fermetures) → pour revenu/nuit
    nuits_louees    = _calc_nuits(df_reel)
    nuits_fermeture = _calc_nuits(df_fermetu)
    nuits_total     = nuits_louees + nuits_fermeture
    revenu_nuit     = round(ca_net / nuits_louees, 2) if nuits_louees > 0 else 0

    # Taux d'occupation = (nuits louées + fermetures) / jours de l'année filtrée
    # On calcule sur l'année sélectionnée dans le df (pas forcément l'année courante)
    if "annee" in df.columns:
        annees = df["annee"].dropna().unique()
        if len(annees) == 1:
            nb_jours = 366 if int(annees[0]) % 4 == 0 else 365
        else:
            nb_jours = 365
    else:
        nb_jours = 365
    taux_occupation = round(nuits_total / nb_jours * 100, 1)

    # Montant en attente : uniquement réservations réelles non payées
    non_payes = df_reel[df_reel["paye"] == False] if "paye" in df_reel.columns else pd.DataFrame()
    montant_en_attente = non_payes["prix_net"].sum() if not non_payes.empty else 0

    repartition = {}
    if "plateforme" in df.columns:
        repartition = df_reel.groupby("plateforme")["prix_net"].sum().round(2).to_dict()

    return {
        "ca_brut":              round(ca_brut, 2),
        "ca_net":               round(ca_net, 2),
        "commissions":          round(commissions, 2),
        "menage":               round(menage, 2),
        "taxes":                round(taxes, 2),
        "nb_reservations":      nb_reservations,
        "nuits_total":          nuits_total,
        "nuits_louees":         nuits_louees,
        "nuits_fermeture":      nuits_fermeture,
        "revenu_nuit":          revenu_nuit,
        "montant_en_attente":   round(montant_en_attente, 2),
        "taux_occupation":      taux_occupation,
        "repartition_plateformes": repartition,
    }


def compute_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Stats par mois — nuits ventilées jour par jour dans le bon mois.
    Fermetures exclues du CA et du compte de réservations.
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"])
    df["date_depart"]  = pd.to_datetime(df["date_depart"])
    df["mois"]         = df["date_arrivee"].dt.to_period("M")

    # CA et réservations : exclure Fermeture
    if "plateforme" in df.columns:
        df_ca = df[df["plateforme"] != PLATEFORME_FERMETURE]
    else:
        df_ca = df

    ca_monthly = df_ca.groupby("mois").agg(
        ca_brut=("prix_brut", "sum") if "prix_brut" in df_ca.columns else ("prix_net", "sum"),
        ca_net=("prix_net", "sum"),
        nb_reservations=("id", "count"),
    ).reset_index()

    # Nuits ventilées par mois réel (toutes réservations y compris Fermeture)
    all_periods = set(df["mois"].unique())
    for _, row in df.iterrows():
        arr, dep = row["date_arrivee"], row["date_depart"]
        if pd.isna(arr) or pd.isna(dep):
            continue
        p = arr.to_period("M")
        while p.to_timestamp() < dep:
            all_periods.add(p)
            p += 1

    nuits_par_mois = {}
    for period in all_periods:
        ms = period.to_timestamp()
        me = (period + 1).to_timestamp()
        def _nuits(row, ms=ms, me=me):
            debut = max(row["date_arrivee"], ms)
            fin   = min(row["date_depart"],  me)
            return max(0, (fin - debut).days)
        nuits_par_mois[period] = int(df.apply(_nuits, axis=1).sum())

    df_nuits = pd.DataFrame([{"mois": k, "nuits": v} for k, v in nuits_par_mois.items()])

    monthly = ca_monthly.merge(df_nuits, on="mois", how="left")
    monthly["nuits"]    = monthly["nuits"].fillna(0).astype(int)
    monthly["mois_str"] = monthly["mois"].dt.strftime("%b %Y")
    monthly = monthly.sort_values("mois")

    return monthly


def _empty_kpis() -> dict:
    return {
        "ca_brut": 0, "ca_net": 0, "commissions": 0,
        "menage": 0, "taxes": 0, "nb_reservations": 0,
        "nuits_total": 0, "nuits_louees": 0, "nuits_fermeture": 0,
        "revenu_nuit": 0, "montant_en_attente": 0,
        "taux_occupation": 0, "repartition_plateformes": {},
    }
