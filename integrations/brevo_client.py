"""Client Brevo (ex-Sendinblue) pour envoi d'emails et SMS."""
import requests
from config import BREVO_API_KEY, EMAIL_FROM

BREVO_EMAIL_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_SMS_URL   = "https://api.brevo.com/v3/transactionalSMS/sms"


def send_email(to_email: str, to_name: str, subject: str, html: str) -> dict:
    """Envoie un email via Brevo. Retourne {'ok': bool, 'error': str|None}."""
    if not BREVO_API_KEY:
        return {"ok": False, "error": "BREVO_API_KEY non configurée"}
    if not to_email:
        return {"ok": False, "error": "Email destinataire manquant"}

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "sender":      {"email": EMAIL_FROM or "noreply@example.com", "name": "Vacances-Locations"},
        "to":          [{"email": to_email, "name": to_name}],
        "subject":     subject,
        "htmlContent": html,
    }
    try:
        r = requests.post(BREVO_EMAIL_URL, json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 201):
            return {"ok": True, "error": None}
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_sms(to_phone: str, message: str, sender: str = "VacLoc") -> dict:
    """Envoie un SMS via Brevo."""
    if not BREVO_API_KEY:
        return {"ok": False, "error": "BREVO_API_KEY non configurée"}
    if not to_phone:
        return {"ok": False, "error": "Numéro de téléphone manquant"}

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json"
    }
    # Nettoyage numéro : garder uniquement chiffres et +
    phone = "".join(c for c in to_phone if c.isdigit() or c == "+")
    if not phone.startswith("+"):
        phone = "+" + phone

    payload = {
        "sender":    sender[:11],
        "recipient": phone,
        "content":   message[:160],
        "type":      "transactional",
    }
    try:
        r = requests.post(BREVO_SMS_URL, json=payload, headers=headers, timeout=10)
        if r.status_code in (200, 201):
            return {"ok": True, "error": None}
        return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:200]}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
