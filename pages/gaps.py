import streamlit as st
from database.proprietes_repo import fetch_all as _fa_gaps
from services.auth_service import is_unlocked
from services.reservation_service import load_reservations
from services.gap_service import detect_gaps
from services.opportunity_service import booking_opportunities
import pandas as pd


def show():
    st.title("🕳️ Créneaux libres & Opportunités")

    df = load_reservations()
    _auth_gaps = [p['id'] for p in _fa_gaps() if not p.get('mot_de_passe') or is_unlocked(p['id'])]
    df = df[df['propriete_id'].isin(_auth_gaps)] if 'propriete_id' in df.columns else df
    if df.empty:
        st.info("Aucune réservation disponible.")
        return

    # Par propriété
    proprietes = sorted(df["propriete_id"].unique()) if "propriete_id" in df.columns else [None]
    labels = {1: "Villa Tobias", 2: "Propriété 2"}

    for prop_id in proprietes:
        nom = labels.get(prop_id, f"Propriété {prop_id}")
        st.subheader(f"🏠 {nom}")

        gaps = detect_gaps(df, prop_id)

        if not gaps:
            st.success(f"Aucun créneau libre détecté.")
            continue

        opps = booking_opportunities(gaps)

        df_gaps = pd.DataFrame(gaps)
        df_gaps["start"] = pd.to_datetime(df_gaps["start"]).dt.strftime("%d/%m/%Y")
        df_gaps["end"]   = pd.to_datetime(df_gaps["end"]).dt.strftime("%d/%m/%Y")

        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.dataframe(
                df_gaps.rename(columns={
                    "start": "Début", "end": "Fin",
                    "nuits": "Nuits", "avant": "Départ précédent", "apres": "Arrivée suivante"
                }),
                use_container_width=True, hide_index=True
            )
        with col_b:
            st.metric("Créneaux", len(gaps))
            st.metric("Opportunités", len(opps))
            total_nuits_libres = sum(g["nuits"] for g in gaps)
            st.metric("Nuits libres", total_nuits_libres)

        if opps:
            st.info(f"💡 {len(opps)} opportunité(s) de réservation détectées")

        st.divider()
