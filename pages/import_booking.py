"""
Page Import Booking - Import XLS reservation_statements_overview.
"""
import streamlit as st
import pandas as pd
from services.import_booking_service import parse_booking_xls, preview_booking_xls
from database.reservations_repo import upsert_reservations, fetch_all
from services.proprietes_service import get_proprietes_dict, get_propriete_selectionnee
from database.supabase_client import is_connected


def show():
    st.title("📥 Import Booking.com")
    st.markdown(
        "Importez le fichier **reservation_statements_overview_YYYY-MM.xls** "
        "téléchargeable depuis votre extranet Booking.com."
    )

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise.")
        return

    props = get_proprietes_dict()

    # ── Guide téléchargement ──────────────────────────────────────────────
    with st.expander("📖 Comment télécharger ce fichier sur Booking.com ?"):
        st.markdown("""
        1. Connectez-vous à **extranet.booking.com**
        2. Menu **Finance** → **Relevés de réservations**
        3. Sélectionnez le **mois** souhaité
        4. Cliquez **Télécharger** → format **Excel (.xls)**
        5. Uploadez le fichier ci-dessous
        """)

    st.divider()

    # ── Upload fichier ────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "📂 Sélectionner le fichier Booking.com (.xls)",
        type=["xls", "xlsx"],
        key="booking_upload"
    )

    if not uploaded:
        st.info("Uploadez un fichier XLS Booking pour commencer.")
        return

    file_bytes = uploaded.read()

    try:
        df_preview = preview_booking_xls(file_bytes)
        df_full    = parse_booking_xls(file_bytes)
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")
        return

    if df_full.empty:
        st.warning("Aucune réservation valide trouvée (statut OK) dans ce fichier.")
        return

    # ── Stats rapides ─────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Réservations", len(df_full))
    c2.metric("🌙 Nuits totales", int(df_full["nuitees"].sum()))
    c3.metric("💶 CA Brut",  f"{df_full['prix_brut'].sum():,.0f} €")
    c4.metric("💵 CA Net",   f"{df_full['prix_net'].sum():,.0f} €")

    # ── Aperçu ────────────────────────────────────────────────────────────
    st.markdown("### 👁️ Aperçu des réservations")

    # Vérifier doublons avec base existante
    try:
        df_exist = fetch_all()
        existing_nums = set(df_exist["numero_reservation"].dropna().astype(str).tolist()) \
                        if not df_exist.empty else set()
    except Exception:
        existing_nums = set()

    df_display = df_preview.copy()
    df_display["Statut"] = df_full["numero_reservation"].apply(
        lambda x: "⚠️ Existe déjà" if str(x) in existing_nums else "✅ Nouveau"
    )

    # Colorier le tableau
    def color_status(val):
        if "Existe" in str(val): return "background-color:#FFF8E1;color:#F57F17"
        if "Nouveau" in str(val): return "background-color:#E8F5E9;color:#2E7D32"
        return ""

    st.dataframe(
        df_display.style.applymap(color_status, subset=["Statut"]),
        use_container_width=True, hide_index=True
    )

    nouveaux   = df_display[df_display["Statut"] == "✅ Nouveau"]
    doublons   = df_display[df_display["Statut"] == "⚠️ Existe déjà"]

    if doublons.shape[0] > 0:
        st.warning(f"⚠️ {doublons.shape[0]} réservation(s) existent déjà — elles seront **mises à jour**.")
    if nouveaux.shape[0] > 0:
        st.success(f"✅ {nouveaux.shape[0]} nouvelle(s) réservation(s) à importer.")

    # ── Options avant import ──────────────────────────────────────────────
    st.divider()
    st.markdown("### ⚙️ Options d'import")

    col1, col2 = st.columns(2)
    with col1:
        # Vérifier si prop_id = 0 pour certaines lignes
        if 0 in df_full["propriete_id"].values:
            st.warning("⚠️ Certaines propriétés n'ont pas pu être identifiées automatiquement.")
            prop_fallback = st.selectbox(
                "Attribuer à la propriété :",
                options=list(props.keys()),
                format_func=lambda x: props[x],
                key="import_prop_fallback"
            )
            df_full.loc[df_full["propriete_id"] == 0, "propriete_id"] = prop_fallback

    with col2:
        menage_defaut = st.number_input(
            "🧹 Frais ménage par défaut (€)",
            min_value=0.0, value=70.0, step=5.0,
            help="Sera appliqué à toutes les réservations importées",
            key="import_menage"
        )
        df_full["menage"] = menage_defaut
        df_full["frais_menage"] = menage_defaut
        df_full["prix_net"] = df_full.apply(
            lambda r: round(r["prix_brut"] - r["commissions"], 2), axis=1
        )

    # ── Bouton import ─────────────────────────────────────────────────────
    st.divider()

    col_btn, col_info = st.columns([3, 5])
    with col_btn:
        go = st.button(
            f"⬆️ Importer {len(df_full)} réservation(s)",
            type="primary", use_container_width=True
        )
    with col_info:
        st.caption(
            "L'import utilise **upsert** sur le numéro de réservation — "
            "les réservations existantes seront mises à jour, pas dupliquées."
        )

    if go:
        rows = df_full.to_dict("records")
        # Nettoyer les NaN
        for row in rows:
            for k, v in row.items():
                if pd.isna(v) if not isinstance(v, (bool, list, dict)) else False:
                    row[k] = None

        with st.spinner("Import en cours..."):
            try:
                nb = upsert_reservations(rows)
                st.success(f"🎉 {nb} réservation(s) importée(s) avec succès !")
                st.balloons()

                # Résumé post-import
                st.markdown("**Résumé de l'import :**")
                cc1, cc2, cc3 = st.columns(3)
                cc1.metric("✅ Importées", nb)
                cc2.metric("💶 CA Brut",   f"{df_full['prix_brut'].sum():,.0f} €")
                cc3.metric("💵 CA Net",    f"{df_full['prix_net'].sum():,.0f} €")

            except Exception as e:
                st.error(f"Erreur lors de l'import : {e}")
