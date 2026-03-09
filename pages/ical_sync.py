"""
Page Synchronisation iCal — Import depuis Booking, Airbnb, Abritel.
"""
import streamlit as st
from services.channel_sync_service import sync_ical
from integrations.ical_sync import load_ical, ical_to_dataframe
from database.supabase_client import is_connected


def show():
    st.title("🔄 Synchronisation iCal")
    st.caption("Importez vos réservations depuis Booking, Airbnb, Abritel via leurs flux iCal.")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise pour synchroniser.")
        return

    PROPRIETES = {1: "Villa Tobias", 2: "Propriété 2"}
    PLATEFORMES = ["Booking", "Airbnb", "Abritel", "Direct"]

    st.subheader("📡 Ajouter un flux iCal")

    with st.form("form_ical"):
        col1, col2 = st.columns(2)
        with col1:
            propriete = st.selectbox(
                "Propriété",
                options=list(PROPRIETES.keys()),
                format_func=lambda x: PROPRIETES[x]
            )
            plateforme = st.selectbox("Plateforme", PLATEFORMES)
        with col2:
            url = st.text_input(
                "URL du flux iCal",
                placeholder="https://www.airbnb.fr/calendar/ical/..."
            )
            st.caption(
                "🔍 Où trouver l'URL :\n"
                "- **Airbnb** : Calendrier → Exporter → Copier le lien\n"
                "- **Booking** : Calendrier → Sync → Exporter\n"
                "- **Abritel** : Calendrier → Partager → iCal"
            )

        col_a, col_b = st.columns(2)
        with col_a:
            btn_preview = st.form_submit_button("👁️ Prévisualiser", use_container_width=True)
        with col_b:
            btn_sync = st.form_submit_button("🔄 Synchroniser", type="primary", use_container_width=True)

    if btn_preview and url:
        with st.spinner("Chargement du flux iCal..."):
            try:
                reservations = load_ical(url)
                df = ical_to_dataframe(reservations)

                st.success(f"✅ {len(df)} réservation(s) trouvée(s) dans le flux")

                if not df.empty:
                    st.dataframe(
                        df[["nom_client", "date_arrivee", "date_depart", "nuitees", "plateforme"]],
                        use_container_width=True, hide_index=True
                    )
            except Exception as e:
                st.error(f"❌ Erreur : {e}")

    if btn_sync and url:
        with st.spinner("Synchronisation en cours..."):
            result = sync_ical(int(propriete), plateforme, url)

        if "erreur" in result:
            st.error(f"❌ {result['erreur']}")
        else:
            st.success(
                f"✅ {result['synchronisées']} réservation(s) synchronisées "
                f"(sur {result['total_ical']} dans le flux)"
            )
            if result["erreurs"] > 0:
                st.warning(f"⚠️ {result['erreurs']} erreur(s) durant l'import")

    st.divider()

    # Aide
    with st.expander("📖 Comment obtenir les URLs iCal"):
        st.markdown("""
        **Airbnb**
        1. Allez dans votre tableau de bord Airbnb
        2. Cliquez sur **Calendrier** → votre annonce
        3. Paramètres de disponibilité → **Synchroniser les calendriers**
        4. Copiez le lien "Exporter le calendrier"

        **Booking.com**
        1. Extranet Booking → **Calendrier**
        2. Paramètres → **Synchroniser le calendrier**
        3. Cliquez sur **Exporter le calendrier** → copiez l'URL

        **Abritel/Vrbo**
        1. Tableau de bord Abritel → **Calendrier**
        2. Cliquez sur **Importer/Exporter**
        3. Copiez l'URL de votre calendrier iCal
        """)
