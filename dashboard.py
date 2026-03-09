from services.alert_service import upcoming_arrivals

arrivals = upcoming_arrivals(df)

st.subheader("Arrivées prochaines")

st.dataframe(arrivals)
