import plotly.express as px
import streamlit as st

def revenue_chart(data):

    fig = px.line(
        data,
        x=data.index,
        y=data.values,
        title="Revenus mensuels"
    )

    st.plotly_chart(fig, use_container_width=True)
