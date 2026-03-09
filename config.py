import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
EMAIL_FROM    = os.getenv("EMAIL_FROM", "")
