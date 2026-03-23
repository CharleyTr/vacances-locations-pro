"""
Service pour appliquer les variables dans les templates de messages.
"""
from datetime import datetime

VARIABLES = {
    "{prenom}":             "Prénom du client (1er mot du nom)",
    "{nom}":                "Nom complet du client",
    "{email}":              "Email du client",
    "{telephone}":          "Téléphone du client",
    "{pays}":               "Pays du client (ex: France)",
    "{drapeau}":            "Drapeau du pays du client (ex: 🇫🇷)",
    "{date_arrivee}":       "Date d'arrivée (jj/mm/aaaa)",
    "{date_depart}":        "Date de départ (jj/mm/aaaa)",
    "{nuitees}":            "Nombre de nuits",
    "{plateforme}":         "Plateforme (Airbnb, Booking...)",
    "{numero_reservation}": "Numéro de réservation",
    "{prix_brut}":          "Montant total (€)",
    "{prix_net}":           "Montant net hôte (€)",
    "{propriete}":          "Nom du logement",
    "{ville}":              "Ville du logement",
    "{lien_questionnaire}": "Lien vers le questionnaire satisfaction",
    "{signataire}":         "Signataire (défini dans la fiche propriété)",
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


def _get_iso(pays: str) -> str:
    """Retourne le code ISO 2 lettres depuis le nom du pays."""
    if not pays:
        return ""
    try:
        from services.indicatifs_service import INDICATIFS
        pays_to_iso = {v[0]: v[1].upper() for v in INDICATIFS.values()}
        return pays_to_iso.get(pays.strip(), "")
    except Exception:
        return ""


def _get_drapeau(pays: str) -> str:
    """Retourne un drapeau compatible Windows : image HTML + fallback texte.
    Dans WhatsApp (texte pur) : affiche ex. [🇳🇱 NL]
    Dans l'aperçu Streamlit : affiche l'image du drapeau via flagcdn.com
    """
    if not pays:
        return ""
    iso = _get_iso(pays)
    if not iso or len(iso) != 2:
        return pays
    iso_lower = iso.lower()
    # Pour l'aperçu HTML dans Streamlit
    img_html = (f'<img src="https://flagcdn.com/20x15/{iso_lower}.png" '
                f'width="20" height="15" style="vertical-align:middle;'
                f'border-radius:2px;margin-right:3px"> {iso}')
    return img_html


def _get_drapeau_texte(pays: str) -> str:
    """Version texte pur pour WhatsApp/SMS — affiche le code pays."""
    if not pays:
        return ""
    iso = _get_iso(pays)
    return f"[{iso}]" if iso else ""


def apply_template_texte(contenu: str, reservation: dict, propriete_nom: str = "",
                         ville: str = "", lien_questionnaire: str = "",
                         signataire: str = "") -> str:
    """Version texte pur pour WhatsApp/SMS — drapeaux en code ISO [NL]."""
    pays = str(reservation.get("pays", "") or "")
    result = apply_template(contenu, reservation, propriete_nom=propriete_nom,
                             ville=ville, lien_questionnaire=lien_questionnaire,
                             signataire=signataire)
    # Remplacer l'HTML du drapeau par le code texte
    import re as _re2
    result = _re2.sub(r'<img[^>]+>\s*([A-Z]{2})', r'[]', result)
    return result


def apply_template(contenu: str, reservation: dict, propriete_nom: str = "",
                   ville: str = "", lien_questionnaire: str = "",
                   signataire: str = "") -> str:
    """Remplace toutes les variables dans le contenu du template."""

    # Auto-générer le lien questionnaire si absent
    if "{lien_questionnaire}" in contenu and not lien_questionnaire:
        try:
            import os as _os
            from database.avis_repo import get_or_create_lien_questionnaire
            _app_url = __import__("streamlit").secrets.get(
                "APP_URL", _os.environ.get("APP_URL", ""))
            lien_questionnaire = get_or_create_lien_questionnaire(reservation, _app_url)
        except Exception as _e:
            print(f"Auto-lien questionnaire: {_e}")

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
    pays   = str(reservation.get("pays", "") or "")

    # Ordre important : traiter {propriete} avant {pays} pour éviter les conflits
    replacements = [
        ("{prenom}",             prenom),
        ("{nom}",                nom_complet),
        ("{email}",              str(reservation.get("email", "") or "")),
        ("{telephone}",          str(reservation.get("telephone", "") or "")),
        ("{pays}",               pays),
        ("{drapeau}",            _get_drapeau(pays)),  # HTML image pour aperçu
        ("{date_arrivee}",       _fmt_date(reservation.get("date_arrivee"))),
        ("{date_depart}",        _fmt_date(reservation.get("date_depart"))),
        ("{nuitees}",            str(int(reservation.get("nuitees", 0) or 0))),
        ("{plateforme}",         str(reservation.get("plateforme", "") or "")),
        ("{numero_reservation}", str(reservation.get("numero_reservation", "") or "")),
        ("{prix_brut}",          f"{float(reservation.get('prix_brut', 0) or 0):,.0f}"),
        ("{prix_net}",           f"{float(reservation.get('prix_net', 0) or 0):,.0f}"),
        ("{propriete}",          propriete_nom),
        ("{ville}",              ville),
        ("{lien_questionnaire}", lien_questionnaire),
        ("{signataire}",         signataire),
    ]

    result = contenu
    for var, val in replacements:
        result = result.replace(var, str(val) if val is not None else "")
    return result
