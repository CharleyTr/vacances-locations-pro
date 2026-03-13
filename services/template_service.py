"""
Service pour appliquer les variables dans les templates de messages.
"""
from datetime import datetime

# Toutes les zones variables disponibles avec leur description
VARIABLES = {
    "{prenom}":              "Prénom du client (1er mot du nom)",
    "{nom}":                 "Nom complet du client",
    "{email}":               "Email du client",
    "{telephone}":           "Téléphone du client",
    "{pays}":                "Pays d'origine",
    "{date_arrivee}":        "Date d'arrivée (jj/mm/aaaa)",
    "{date_depart}":         "Date de départ (jj/mm/aaaa)",
    "{nuitees}":             "Nombre de nuits",
    "{plateforme}":          "Plateforme (Airbnb, Booking...)",
    "{numero_reservation}":  "Numéro de réservation",
    "{prix_brut}":           "Montant total (€)",
    "{prix_net}":            "Montant net hôte (€)",
    "{propriete}":           "Nom du logement",
    "{ville}":               "Ville du logement",
    "{lien_questionnaire}":  "Lien vers le questionnaire satisfaction",
    "{signataire}":          "Signataire (défini dans la fiche propriété)",
}

MOMENTS = {
    "confirmation": "✅ Confirmation réservation",
    "j-3":          "📅 Rappel arrivée J-3",
    "arrivee":      "🏠 Jour d'arrivée",
    "depart":       "🧳 Veille départ",
    "post_depart":  "⭐ Post-départ & avis",
    "paiement":     "💳 Rappel paiement",
    "fidelite":     "🎁 Offre fidélité",
    "autre":        "📝 Autre",
}


def apply_template(contenu: str, reservation: dict, propriete_nom: str = "",
                   ville: str = "", lien_questionnaire: str = "",
                   signataire: str = "") -> str:
    """Remplace toutes les variables dans le contenu du template."""

    def _fmt_date(val):
        if not val:
            return ""
        try:
            if hasattr(val, "strftime"):
                return val.strftime("%d/%m/%Y")
            return datetime.strptime(str(val)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return str(val)[:10]

    nom_complet = str(reservation.get("nom_client", "") or "")
    prenom = nom_complet.split()[0] if nom_complet else ""

    replacements = {
        "{prenom}":             prenom,
        "{nom}":                nom_complet,
        "{email}":              str(reservation.get("email", "") or ""),
        "{telephone}":          str(reservation.get("telephone", "") or ""),
        "{pays}":               str(reservation.get("pays", "") or ""),
        "{date_arrivee}":       _fmt_date(reservation.get("date_arrivee")),
        "{date_depart}":        _fmt_date(reservation.get("date_depart")),
        "{nuitees}":            str(int(reservation.get("nuitees", 0) or 0)),
        "{plateforme}":         str(reservation.get("plateforme", "") or ""),
        "{numero_reservation}": str(reservation.get("numero_reservation", "") or ""),
        "{prix_brut}":          f"{float(reservation.get('prix_brut', 0) or 0):,.0f}",
        "{prix_net}":           f"{float(reservation.get('prix_net', 0) or 0):,.0f}",
        "{propriete}":          propriete_nom,
        "{ville}":              ville,
        "{lien_questionnaire}": lien_questionnaire,
        "{signataire}":          signataire,
    }

    result = contenu
    for var, val in replacements.items():
        result = result.replace(var, val)
    return result
