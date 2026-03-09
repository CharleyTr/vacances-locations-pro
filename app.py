import streamlit as st

st.set_page_config(
    page_title="Vacances-Locations PRO",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from components.sidebar import sidebar
from pages import dashboard, reservations, calendar, analytics, gaps

try:
    from pages import paiements
except ImportError:
    paiements = None
try:
    from pages import menage
except ImportError:
    menage = None
try:
    from pages import messages
except ImportError:
    messages = None
try:
    from pages import ical_sync
except ImportError:
    ical_sync = None
try:
    from pages import proprietes
except ImportError:
    proprietes = None

page = sidebar()

if page == "Dashboard":       dashboard.show()
elif page == "Réservations":  reservations.show()
elif page == "Calendrier":    calendar.show()
elif page == "Analyses":      analytics.show()
elif page == "Créneaux":      gaps.show()
elif page == "Paiements":     paiements.show() if paiements else st.error("Uploadez pages/paiements.py")
elif page == "Ménage":        menage.show()    if menage    else st.error("Uploadez pages/menage.py")
elif page == "Messages":      messages.show() if messages  else st.error("Uploadez pages/messages.py")
elif page == "iCal":          ical_sync.show() if ical_sync else st.error("Uploadez pages/ical_sync.py")
elif page == "Propriétés":    proprietes.show() if proprietes else st.error("Uploadez pages/proprietes.py")
