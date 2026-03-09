import os
from dotenv import load_dotenv

load_dotenv()

def _get(key: str, default: str = "") -> str:
    val = os.getenv(key, "")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default

SUPABASE_URL          = _get("SUPABASE_URL")
SUPABASE_KEY          = _get("SUPABASE_KEY")
BREVO_API_KEY         = _get("BREVO_API_KEY")
EMAIL_FROM            = _get("EMAIL_FROM")
TWILIO_ACCOUNT_SID    = _get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN     = _get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM  = _get("TWILIO_WHATSAPP_FROM")
