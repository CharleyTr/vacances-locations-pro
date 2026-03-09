import streamlit as st
import pandas as pd
from services.reservation_service import load_reservations
from services.import_service import import_csv_file, preview_csv
from database.supabase_client import is_connected


COLONNES_AFFICHAGE = [
    "id", "nom_client", "plateforme", "date_arrivee", "date_depart",
    "nuitees", "prix_brut", "commissions", "prix_net", "paye", "statut_paiement", "pays"
]


def show():
    st.title("📋 Réservations")

    # ── Filtres ───────────────────────────────────────────────────────────
    with st.expander("🔍 Filtres", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            plateforme = st.multiselect("Plateforme", ["Booking", "Airbnb", "Direct"])
        with col2:
            annee = st.selectbox("Année", [2025, 2026, 2024], index=0)
        with col3:
            statut_paye = st.selectbox("Paiement", ["Tous", "Payés", "En attente"])

    df = load_reservations()

    if df.empty:
        st.warning("Aucune réservation disponible.")
        return

    # Appliquer filtres
    if plateforme:
        df = df[df["plateforme"].isin(plateforme)]
    if annee:
        df = df[df["annee"] == annee]
    if statut_paye == "Payés":
        df = df[df["paye"] == True]
    elif statut_paye == "En attente":
        df = df[df["paye"] == False]

    # Colonnes disponibles
    cols = [c for c in COLONNES_AFFICHAGE if c in df.columns]

    st.markdown(f"**{len(df)} réservations**")
    st.dataframe(
        df[cols].sort_values("date_arrivee", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "prix_brut":   st.column_config.NumberColumn("Prix brut", format="%.2f €"),
            "prix_net":    st.column_config.NumberColumn("Prix net", format="%.2f €"),
            "commissions": st.column_config.NumberColumn("Commissions", format="%.2f €"),
            "paye":        st.column_config.CheckboxColumn("Payé"),
        }
    )

    # ── Export CSV ────────────────────────────────────────────────────────
    csv_data = df[cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exporter CSV", csv_data,
        file_name="reservations_export.csv", mime="text/csv"
    )

    st.divider()

    # ── Import CSV ────────────────────────────────────────────────────────
    st.subheader("📤 Importer un CSV")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise pour l'import. Configurez .env")
        return

    uploaded = st.file_uploader("Choisir un fichier CSV", type=["csv"])
    if uploaded:
        preview = preview_csv(uploaded)
        st.write(f"**{len(preview)} lignes détectées**")
        st.dataframe(preview.head(5), use_container_width=True, hide_index=True)

        if st.button("✅ Importer dans Supabase", type="primary"):
            uploaded.seek(0)
            with st.spinner("Import en cours..."):
                result = import_csv_file(uploaded)
            st.success(
                f"✅ {result['importées']} réservations importées "
                f"({result['total_csv']} lignes dans le CSV)"
            )
            st.rerun()
