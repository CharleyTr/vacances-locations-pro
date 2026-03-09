import streamlit as st
from streamlit_calendar import calendar

def show_calendar(events):

    calendar_options = {
        "initialView": "dayGridMonth",
        "editable": True,
        "selectable": True
    }

    state = calendar(
        events=events,
        options=calendar_options
    )

    return state
