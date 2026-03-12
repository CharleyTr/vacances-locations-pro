"""
Import des réservations depuis les CSV Airbnb.
"""
import pandas as pd
import io

LOGEMENT_MAP = {
    "studio climatise avec garage privé": 2,
    "studio et garage au port de nice":   2,
    "le turenne":                          1,
}

def _resolve_prop(logement: str) -> int:
    key = str(logement or "").lower().strip()
    for pattern, pid in LOGEMENT_MAP.items():
        if pattern in key:
            return pid
    return 0

def _fval(row, col):
    v = row.get(col, 0)
    return 0.0 if (v is None or str(v) == 'nan') else float(v)

def _fmt_date(val) -> str:
    s = str(val or "").strip()
    if not s or s == "nan":
        return ""
    if "/" in s:
        parts = s.split("/")
        if len(parts) == 3:
            m, d, y = parts
            return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    return s[:10]

def parse_airbnb_csv(file_bytes: bytes, pending: bool = False) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')
    df.columns = [c.lstrip('\ufeff') for c in df.columns]
    df = df[df["Type"] == "Réservation"].copy()
    if df.empty:
        return pd.DataFrame()

    rows = []
    for _, r in df.iterrows():
        revenus_bruts = _fval(r, "Revenus bruts")
        montant       = _fval(r, "Montant")
        frais_service = _fval(r, "Frais de service")
        frais_menage  = _fval(r, "Frais de ménage")
        taxes_sejour  = _fval(r, "Taxes de séjour")
        frais_cb      = _fval(r, "Frais de Versement sur carte bancaire")
        nuitees       = int(_fval(r, "Nuits"))

        prix_brut  = round(revenus_bruts - frais_menage - taxes_sejour, 2)
        prix_net   = round(montant - frais_menage - frais_cb, 2)
        base_comm  = prix_brut + frais_menage
        pct_comm   = round(frais_service / base_comm * 100, 2) if base_comm > 0 else 0

        rows.append({
            "numero_reservation":  str(r.get("Code de confirmation", "") or "").strip(),
            "propriete_id":        _resolve_prop(str(r.get("Logement", "") or "")),
            "plateforme":          "Airbnb",
            "nom_client":          str(r.get("Voyageur", "") or "").strip(),
            "pays":                "",
            "date_arrivee":        _fmt_date(r.get("Date de début")),
            "date_depart":         _fmt_date(r.get("Date de fin")),
            "nuitees":             nuitees,
            "prix_brut":           prix_brut,
            "commissions":         frais_service,
            "commissions_hote":    frais_service,
            "pct_commission":      pct_comm,
            "frais_menage":        frais_menage,
            "menage":              frais_menage,
            "taxes_sejour":        taxes_sejour,
            "frais_cb":            frais_cb,
            "prix_net":            prix_net,
            "base":                prix_net,
            "charges":             0.0,
            "paye":                not pending,
            "sms_envoye":          False,
            "post_depart_envoye":  False,
        })

    return pd.DataFrame(rows)

def preview_airbnb_csv(file_bytes: bytes, pending: bool = False) -> pd.DataFrame:
    df = parse_airbnb_csv(file_bytes, pending)
    if df.empty:
        return df
    return df[["numero_reservation","nom_client","propriete_id",
               "date_arrivee","date_depart","nuitees",
               "prix_brut","commissions","frais_menage","prix_net","paye"]]
