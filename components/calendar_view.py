import plotly.express as px
import streamlit as st

def show_calendar(df):

    fig = px.timeline(
        df,
        x_start="start",
        x_end="end",
        y="appartement",
        color="client"
    )

    fig.update_yaxes(autorange="reversed")

    st.plotly_chart(fig, use_container_width=True)
