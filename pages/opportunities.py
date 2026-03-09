import streamlit as st
from services.gap_service import detect_gaps
from services.opportunity_service import booking_opportunities
from services.reservation_service import load_reservations

def show():

    st.title("Opportunités de réservation")

    df = load_reservations()

    gaps = detect_gaps(df)

    opportunities = booking_opportunities(gaps)

    st.write(opportunities)
