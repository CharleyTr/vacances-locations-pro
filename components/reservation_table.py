import streamlit as st

def show_table(df):

    st.dataframe(df, use_container_width=True)
