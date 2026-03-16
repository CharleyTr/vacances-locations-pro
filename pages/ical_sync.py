"""
Page Synchronisation iCal
  - IMPORT  : Booking / Airbnb / Abritel → Supabase
  - EXPORT  : Réservations → fichier .ics → Google Calendar / Apple Calendar
"""
import streamlit as st
import pandas as pd
from services.channel_sync_service import sync_ical
from integrations.ical_sync import load_ical, ical_to_dataframe
from integrations.gcal_export import reservations_to_ics
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_dict
from services.proprietes_service import get_proprietes_autorises
from database.supabase_client import is_connected


def show():
    st.title("🔄 Synchronisation Calendriers")

    tab_export, tab_import = st.tabs([
        "📤 Exporter vers Google Calendar",
        "📥 Importer depuis Booking / Airbnb",
    ])

    with tab_export:
        _show_export()

    with tab_import:
        _show_import()


# ──────────────────────────────────────────────────────────────────────────────
# EXPORT VERS GOOGLE CALENDAR
# ──────────────────────────────────────────────────────────────────────────────

def _show_export():
    st.subheader("📤 Exporter vers Google Calendar")
    st.markdown(
        "Générez un fichier **.ics** par propriété et importez-le dans Google Calendar "
        "en 3 clics. Le fichier contient toutes vos réservations avec les détails complets."
    )

    df_all = load_reservations()
    if df_all.empty:
        st.warning("Aucune réservation disponible.")
        return

    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)
    props = get_proprietes_autorises()

    if not props:
        st.warning("Aucune propriété configurée.")
        return

    st.divider()

    # ── Une section par propriété ─────────────────────────────────────────
    for prop_id, prop_nom in props.items():
        df_prop = df_all[df_all["propriete_id"] == prop_id]

        with st.container():
            col_info, col_filtres, col_btn = st.columns([3, 3, 2])

            with col_info:
                st.markdown(f"### 🏠 {prop_nom}")
                st.caption(f"{len(df_prop)} réservation(s) au total")

            with col_filtres:
                annees_dispo = sorted(df_prop["annee"].dropna().unique().tolist(), reverse=True)
                annee_choix  = st.selectbox(
                    "Année",
                    ["Toutes"] + annees_dispo,
                    key=f"export_annee_{prop_id}"
                )
                plateformes_dispo = sorted(df_prop["plateforme"].dropna().unique().tolist())
                plat_choix = st.multiselect(
                    "Plateformes",
                    plateformes_dispo,
                    default=plateformes_dispo,
                    key=f"export_plat_{prop_id}"
                )

            # Appliquer filtres
            df_export = df_prop.copy()
            if annee_choix != "Toutes":
                df_export = df_export[df_export["annee"] == int(annee_choix)]
            if plat_choix:
                df_export = df_export[df_export["plateforme"].isin(plat_choix)]

            with col_btn:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                st.caption(f"**{len(df_export)}** événements à exporter")

                if len(df_export) > 0:
                    ics_bytes = reservations_to_ics(
                        df_export.to_dict("records"),
                        nom_calendrier=prop_nom
                    )
                    safe_name = prop_nom.replace(" ", "_").replace("/", "-")
                    annee_str = str(annee_choix) if annee_choix != "Toutes" else "tout"

                    st.download_button(
                        label=f"⬇️ Télécharger .ics",
                        data=ics_bytes,
                        file_name=f"{safe_name}_{annee_str}.ics",
                        mime="text/calendar",
                        key=f"dl_{prop_id}",
                        type="primary",
                        use_container_width=True,
                    )
                else:
                    st.warning("Aucun événement")

        st.divider()

    # ── Guide d'import Google Calendar ───────────────────────────────────
    with st.expander("📖 Comment importer dans Google Calendar", expanded=False):
        st.markdown("""
        **Sur ordinateur :**
        1. Ouvrez [calendar.google.com](https://calendar.google.com)
        2. Dans la colonne gauche, cliquez sur **⚙️ Paramètres**
        3. Allez dans **Importer et exporter** → **Importer**
        4. Sélectionnez le fichier **.ics** téléchargé
        5. Choisissez dans quel calendrier Google importer (créez-en un par propriété)
        6. Cliquez **Importer** — vos réservations apparaissent immédiatement

        **Sur iPhone / iPad :**
        1. Envoyez-vous le fichier .ics par email
        2. Ouvrez l'email et tapez sur le fichier .ics
        3. iOS vous proposera de l'ajouter à votre Calendrier

        ---
        💡 **Astuce** : créez un calendrier Google dédié par propriété
        (ex: *"Le Turenne - Réservations"*) pour garder une vue claire.
        Vous pouvez réimporter le fichier à tout moment — les événements existants
        seront dédoublonnés automatiquement grâce aux UIDs uniques.
        """)


# ──────────────────────────────────────────────────────────────────────────────
# IMPORT DEPUIS BOOKING / AIRBNB
# ──────────────────────────────────────────────────────────────────────────────

def _show_import():
    st.subheader("📥 Importer depuis Booking / Airbnb / Abritel")
    st.caption("Synchronisez vos réservations externes directement dans Supabase.")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise pour synchroniser.")
        return

    props = get_proprietes_dict()
    PLATEFORMES = ["Booking", "Airbnb", "Abritel", "Direct"]

    with st.form("form_ical"):
        col1, col2 = st.columns(2)
        with col1:
            propriete = st.selectbox(
                "Propriété",
                options=list(props.keys()),
                format_func=lambda x: props.get(x, f"Propriété {x}")
            )
            plateforme = st.selectbox("Plateforme", PLATEFORMES)
        with col2:
            url = st.text_input(
                "URL du flux iCal",
                placeholder="https://www.airbnb.fr/calendar/ical/..."
            )
            st.markdown("""
            <small>
            🔍 <b>Airbnb</b> : Calendrier → Synchroniser → Exporter<br>
            🔍 <b>Booking</b> : Calendrier → Synchroniser → Exporter<br>
            🔍 <b>Abritel</b> : Calendrier → Importer/Exporter
            </small>
            """, unsafe_allow_html=True)

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
                st.success(f"✅ {len(df)} réservation(s) trouvée(s)")
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
            if result.get("erreurs", 0) > 0:
                st.warning(f"⚠️ {result['erreurs']} erreur(s)")
