import streamlit as st

def show_kpis(kpis):

    col1, col2, col3 = st.columns(3)

    col1.metric("CA total", f"{kpis['ca_total']:.0f} €")
    col2.metric("Réservations", kpis["nb_resa"])
    col3.metric("Revenu / nuit", f"{kpis['revenu_nuit']:.0f} €")
