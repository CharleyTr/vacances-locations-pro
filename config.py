import os
from dotenv import load_dotenv

load_dotenv()

def _get(key: str, default: str = "") -> str:
    """Lit depuis st.secrets (Streamlit Cloud) ou os.getenv (local/.env)."""
    # 1. Variable d'environnement (local ou Streamlit Cloud injecté)
    val = os.getenv(key, "")
    if val:
        return val
    # 2. st.secrets (Streamlit Cloud)
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default

SUPABASE_URL  = _get("SUPABASE_URL")
SUPABASE_KEY  = _get("SUPABASE_KEY")
BREVO_API_KEY = _get("BREVO_API_KEY")
EMAIL_FROM    = _get("EMAIL_FROM")
