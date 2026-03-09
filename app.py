import streamlit as st
from components.sidebar import sidebar
from pages import dashboard, reservations, calendar, analytics, gaps

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
