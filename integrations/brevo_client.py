import requests
from config import BREVO_API_KEY, EMAIL_FROM

def send_email(to, subject, html):

    url = "https://api.brevo.com/v3/smtp/email"

    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "sender": {"email": EMAIL_FROM},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html
    }

    requests.post(url, json=payload, headers=headers)
