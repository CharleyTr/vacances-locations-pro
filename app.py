import streamlit as st
from components.sidebar import sidebar
from pages import dashboard, reservations, calendar, analytics, gaps

try:
    from pages import paiements
    HAS_PAIEMENTS = True
except ImportError:
    HAS_PAIEMENTS = False

try:
    from pages import menage
    HAS_MENAGE = True
except ImportError:
    HAS_MENAGE = False

try:
    from pages import messages
    HAS_MESSAGES = True
except ImportError:
    HAS_MESSAGES = False

try:
    from pages import ical_sync
    HAS_ICAL = True
except ImportError:
    HAS_ICAL = False

try:
    from pages import proprietes
    HAS_PROPRIETES = True
except ImportError:
    HAS_PROPRIETES = False

st.set_page_config(
    page_title="Vacances-Locations PRO",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

page = sidebar()

if page == "Dashboard":
    dashboard.show()
elif page == "Réservations":
    reservations.show()
elif page == "Calendrier":
    calendar.show()
elif page == "Analyses":
    analytics.show()
elif page == "Créneaux":
    gaps.show()
elif page == "Paiements":
    paiements.show() if HAS_PAIEMENTS else st.error("Uploadez `pages/paiements.py`")
elif page == "Ménage":
    menage.show() if HAS_MENAGE else st.error("Uploadez `pages/menage.py`")
elif page == "Messages":
    messages.show() if HAS_MESSAGES else st.error("Uploadez `pages/messages.py`")
elif page == "iCal":
    ical_sync.show() if HAS_ICAL else st.error("Uploadez `pages/ical_sync.py`")
elif page == "Propriétés":
    proprietes.show() if HAS_PROPRIETES else st.error("Uploadez `pages/proprietes.py`")
