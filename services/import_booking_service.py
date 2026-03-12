"""
Import des réservations depuis le fichier XLS Booking.com
(reservation_statements_overview_YYYY-MM.xls)
"""
import pandas as pd
import io
from datetime import date

# Mapping propriétés Booking → IDs Supabase
# Hotel id Booking → propriete_id local
HOTEL_MAP = {
    1844114: 1,   # Le Turenne - Bordeaux
    # Ajouter ici l'ID Booking de Villa Tobias quand disponible
}

# Nom propriété → propriete_id (fallback si Hotel id absent)
NAME_MAP = {
    "le turenne": 1,
    "villa tobias": 2,
}


def parse_booking_xls(file_bytes: bytes) -> pd.DataFrame:
    """
    Lit un fichier XLS Booking et retourne un DataFrame normalisé
    prêt pour l'insertion dans Supabase.
    """
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception:
        df = pd.read_excel(io.BytesIO(file_bytes))

    # Garder uniquement les réservations OK (pas annulées)
    if "Status" in df.columns:
        df = df[df["Status"].str.upper() == "OK"]

    if df.empty:
        return pd.DataFrame()

    rows = []
    for _, r in df.iterrows():
        # Résoudre propriete_id
        prop_id = None
        hotel_id = r.get("Hotel id")
        if hotel_id and int(hotel_id) in HOTEL_MAP:
            prop_id = HOTEL_MAP[int(hotel_id)]
        else:
            prop_name = str(r.get("Property name", "")).lower().strip()
            for k, v in NAME_MAP.items():
                if k in prop_name:
                    prop_id = v
                    break

        if not prop_id:
            prop_id = 0  # "Toutes" - à corriger manuellement si besoin

        # Calculs financiers
        prix_brut   = float(r.get("Original amount", 0) or 0)
        commission  = float(r.get("Commission amount", 0) or 0)
        pct_comm    = float(r.get("Commission %", 0) or 0)
        prix_net    = round(prix_brut - commission, 2)
        nuitees     = int(r.get("Room nights", 0) or 0)
        rev_nuit    = round(prix_net / nuitees, 2) if nuitees > 0 else 0

        rows.append({
            "numero_reservation": str(int(r.get("Reservation number", 0))),
            "propriete_id":       prop_id,
            "plateforme":         "Booking",
            "nom_client":         str(r.get("Guest name", "") or "").strip(),
            "pays":               str(r.get("Country", "") or "").strip(),
            "date_arrivee":       str(r.get("Arrival", ""))[:10],
            "date_depart":        str(r.get("Departure", ""))[:10],
            "nuitees":            nuitees,
            "prix_brut":          prix_brut,
            "commissions":        commission,
            "commissions_hote":   commission,
            "pct_commission":     round(pct_comm, 2),
            "prix_net":           prix_net,
            "frais_menage":       0.0,
            "menage":             0.0,
            "taxes_sejour":       0.0,
            "base":               prix_net,
            "charges":            0.0,
            "frais_cb":           0.0,
            "paye":               True,   # Booking = déjà encaissé
            "sms_envoye":         False,
            "post_depart_envoye": False,
        })

    return pd.DataFrame(rows)


def preview_booking_xls(file_bytes: bytes) -> pd.DataFrame:
    """Retourne un aperçu lisible pour affichage avant import."""
    df = parse_booking_xls(file_bytes)
    if df.empty:
        return df
    return df[[
        "numero_reservation", "nom_client", "pays",
        "date_arrivee", "date_depart", "nuitees",
        "prix_brut", "commissions", "prix_net", "paye"
    ]]
