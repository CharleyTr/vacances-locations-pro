"""
Client WhatsApp — deux modes :
  1. wa.me link  : ouvre WhatsApp avec message pré-rempli (aucune API, fonctionne immédiatement)
  2. Twilio API  : envoi automatique via WhatsApp Business (nécessite compte Twilio)
"""
import re
import requests
from urllib.parse import quote
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM


# ── Mode 1 : lien wa.me (pas d'API) ──────────────────────────────────────────

def build_wa_link(telephone: str, message: str) -> str:
    """
    Génère un lien wa.me qui ouvre WhatsApp avec le message pré-rempli.
    Fonctionne sans aucune API — s'ouvre dans WhatsApp Web ou l'app mobile.
    """
    phone = _clean_phone(telephone)
    if not phone:
        return ""
    return f"https://wa.me/{phone}?text={quote(message)}"


# ── Mode 2 : Twilio API (envoi automatique) ───────────────────────────────────

def send_whatsapp(telephone: str, message: str) -> dict:
    """
    Envoie un message WhatsApp via Twilio.
    Retourne {"ok": bool, "error": str|None, "sid": str|None}
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return {"ok": False, "error": "Twilio non configuré (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN manquants)"}

    phone = _clean_phone(telephone)
    if not phone:
        return {"ok": False, "error": f"Numéro invalide : {telephone}"}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
    from_wa = TWILIO_WHATSAPP_FROM or "whatsapp:+14155238886"  # sandbox Twilio par défaut

    payload = {
        "From": from_wa if from_wa.startswith("whatsapp:") else f"whatsapp:{from_wa}",
        "To":   f"whatsapp:{phone}",
        "Body": message[:1600],
    }

    try:
        r = requests.post(url, data=payload,
                          auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN), timeout=10)
        data = r.json()
        if r.status_code in (200, 201):
            return {"ok": True, "error": None, "sid": data.get("sid")}
        return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}"), "sid": None}
    except Exception as e:
        return {"ok": False, "error": str(e), "sid": None}


def _clean_phone(telephone: str) -> str:
    """Normalise un numéro : supprime espaces/tirets, ajoute + si absent."""
    if not telephone:
        return ""
    phone = re.sub(r"[\s\-\.\(\)]", "", str(telephone))
    if not phone.startswith("+"):
        # Numéro français sans indicatif
        if phone.startswith("0") and len(phone) == 10:
            phone = "+33" + phone[1:]
        else:
            phone = "+" + phone
    return phone
