import streamlit as st
from components.sidebar import sidebar
from pages import dashboard, reservations, calendar, analytics, gaps

# Pages optionnelles (chargées si disponibles)
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
    if HAS_PAIEMENTS:
        paiements.show()
    else:
        st.error("Page Paiements non disponible — uploadez `pages/paiements.py` sur GitHub.")
elif page == "Ménage":
    if HAS_MENAGE:
        menage.show()
    else:
        st.error("Page Ménage non disponible — uploadez `pages/menage.py` sur GitHub.")
elif page == "Messages":
    if HAS_MESSAGES:
        messages.show()
    else:
        st.error("Page Messages non disponible — uploadez `pages/messages.py` sur GitHub.")
elif page == "iCal":
    if HAS_ICAL:
        ical_sync.show()
    else:
        st.error("Page iCal non disponible — uploadez `pages/ical_sync.py` sur GitHub.")
