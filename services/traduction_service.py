"""
Service de traduction automatique des messages selon le pays du client.
Utilise l'API Claude (Anthropic) pour traduire.
"""
import re as _re

# Mapping pays → (code langue, nom langue)
PAYS_VERS_LANGUE = {
    "France": ("fr", "français"), "Belgique": ("fr", "français"),
    "Suisse": ("fr", "français"), "Luxembourg": ("fr", "français"),
    "Monaco": ("fr", "français"), "Martinique": ("fr", "français"),
    "Guadeloupe": ("fr", "français"), "La Réunion": ("fr", "français"),
    "Polynésie française": ("fr", "français"), "Nouvelle-Calédonie": ("fr", "français"),
    "Royaume-Uni": ("en", "anglais"), "Irlande": ("en", "anglais"),
    "États-Unis / Canada": ("en", "anglais"), "Australie": ("en", "anglais"),
    "Nouvelle-Zélande": ("en", "anglais"), "Canada": ("en", "anglais"),
    "Singapour": ("en", "anglais"),
    "Allemagne": ("de", "allemand"), "Autriche": ("de", "allemand"),
    "Liechtenstein": ("de", "allemand"),
    "Espagne": ("es", "espagnol"), "Mexique": ("es", "espagnol"),
    "Argentine": ("es", "espagnol"), "Colombie": ("es", "espagnol"),
    "Chili": ("es", "espagnol"), "Pérou": ("es", "espagnol"),
    "Venezuela": ("es", "espagnol"), "Équateur": ("es", "espagnol"),
    "Cuba": ("es", "espagnol"), "République dominicaine": ("es", "espagnol"),
    "Uruguay": ("es", "espagnol"), "Paraguay": ("es", "espagnol"),
    "Bolivie": ("es", "espagnol"), "Panama": ("es", "espagnol"),
    "Costa Rica": ("es", "espagnol"),
    "Italie": ("it", "italien"),
    "Portugal": ("pt", "portugais"), "Brésil": ("pt", "portugais"),
    "Pays-Bas": ("nl", "néerlandais"),
    "Russie": ("ru", "russe"), "Ukraine": ("uk", "ukrainien"),
    "Biélorussie": ("ru", "russe"),
    "Maroc": ("ar", "arabe"), "Algérie": ("ar", "arabe"),
    "Tunisie": ("ar", "arabe"), "Arabie saoudite": ("ar", "arabe"),
    "Émirats arabes unis": ("ar", "arabe"), "Qatar": ("ar", "arabe"),
    "Koweït": ("ar", "arabe"), "Bahreïn": ("ar", "arabe"),
    "Oman": ("ar", "arabe"), "Jordanie": ("ar", "arabe"),
    "Liban": ("ar", "arabe"), "Égypte": ("ar", "arabe"),
    "Chine": ("zh", "chinois"), "Japon": ("ja", "japonais"),
    "Corée du Sud": ("ko", "coréen"), "Inde": ("hi", "hindi"),
    "Thaïlande": ("th", "thaï"), "Vietnam": ("vi", "vietnamien"),
    "Israël": ("he", "hébreu"), "Turquie": ("tr", "turc"),
    "Suède": ("sv", "suédois"), "Norvège": ("no", "norvégien"),
    "Danemark": ("da", "danois"), "Finlande": ("fi", "finnois"),
    "Pologne": ("pl", "polonais"), "Hongrie": ("hu", "hongrois"),
    "République tchèque": ("cs", "tchèque"), "Roumanie": ("ro", "roumain"),
    "Grèce": ("el", "grec"),
}

# Pattern regex pour emojis drapeaux (Regional Indicator Symbols)
# Utilise les codepoints unicode pour éviter les problèmes d'encodage
_FLAG_PATTERN = "[\U0001F1E0-\U0001F1FF]{2}"


def get_langue_from_pays(pays: str):
    """Retourne (code_langue, nom_langue) ou None si français/inconnu."""
    if not pays:
        return None
    result = PAYS_VERS_LANGUE.get(pays.strip())
    if not result or result[0] == "fr":
        return None
    return result


def traduire_message(message: str, pays: str, bilingue: bool = True) -> dict:
    """Traduit un message dans la langue du pays du client via Claude API."""
    langue_info = get_langue_from_pays(pays)
    if not langue_info:
        return {
            "traduit": False, "langue": "français",
            "message_traduit": message, "message_final": message,
        }

    code_langue, nom_langue = langue_info

    try:
        import requests, os
        try:
            import streamlit as st
            api_key = st.secrets.get("ANTHROPIC_API_KEY",
                       os.environ.get("ANTHROPIC_API_KEY", ""))
        except Exception:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")

        if not api_key:
            return {
                "traduit": False, "langue": nom_langue,
                "message_traduit": message, "message_final": message,
                "erreur": "ANTHROPIC_API_KEY manquante dans les Secrets"
            }

        # Protéger les emojis drapeaux avec des placeholders
        flags_found = _re.findall(_FLAG_PATTERN, message)
        msg_to_translate = message
        for i, flag in enumerate(flags_found):
            msg_to_translate = msg_to_translate.replace(flag, f"__FLAG{i}__", 1)

        prompt = f"""Traduis ce message de location de vacances en {nom_langue}.
Règles importantes :
- Garde exactement la même mise en forme (sauts de ligne, emojis, ponctuation)
- Ne traduis PAS les variables entre accolades : {{prenom}}, {{date_arrivee}}, {{lien_questionnaire}}, {{drapeau}}, etc.
- Ne traduis PAS les tokens __FLAG0__, __FLAG1__, etc. — laisse-les tels quels
- Ne traduis PAS les URLs, numéros de téléphone, adresses email
- Adapte le ton à la culture locale (ex: plus formel en allemand/japonais)
- Réponds UNIQUEMENT avec le message traduit, sans aucune explication ni commentaire

Message à traduire :
{msg_to_translate}"""

        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )

        if r.status_code == 200:
            traduit = r.json()["content"][0]["text"].strip()
            # Restaurer les emojis drapeaux
            for i, flag in enumerate(flags_found):
                traduit = traduit.replace(f"__FLAG{i}__", flag)
            message_final = f"{message}\n\n---\n\n{traduit}" if bilingue else traduit
            return {
                "traduit": True, "langue": nom_langue,
                "message_traduit": traduit, "message_final": message_final,
            }
        else:
            return {
                "traduit": False, "langue": nom_langue,
                "message_traduit": message, "message_final": message,
                "erreur": f"Erreur API {r.status_code}"
            }

    except Exception as e:
        return {
            "traduit": False, "langue": nom_langue,
            "message_traduit": message, "message_final": message,
            "erreur": str(e)
        }
