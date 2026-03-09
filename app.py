import streamlit as st
from components.sidebar import sidebar
from pages import dashboard, reservations, calendar, analytics, gaps
from pages import paiements, menage, messages, ical_sync

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
elif page == "Paiements":
    paiements.show()
elif page == "Ménage":
    menage.show()
elif page == "Messages":
    messages.show()
elif page == "iCal":
    ical_sync.show()
elif page == "Créneaux":
    gaps.show()
