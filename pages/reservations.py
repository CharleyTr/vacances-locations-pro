"""
Page Réservations — Liste + Filtres + Formulaire Ajout/Modification/Suppression + Import CSV.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services.reservation_service import load_reservations
from services.import_service import import_csv_file, preview_csv
from database.supabase_client import is_connected
import database.reservations_repo as repo

PROPRIETES = {1: "Villa Tobias", 2: "Propriété 2"}
PLATEFORMES = ["Booking", "Airbnb", "Direct", "Abritel", "Fermeture"]

COLONNES_AFFICHAGE = [
    "id", "nom_client", "plateforme", "date_arrivee", "date_depart",
    "nuitees", "prix_brut", "commissions", "prix_net",
    "menage", "taxes_sejour", "paye", "statut_paiement", "pays"
]


def show():
    st.title("📋 Réservations")

    # ── Onglets principaux ────────────────────────────────────────────────
    tab_liste, tab_ajout, tab_modifier, tab_import = st.tabs([
        "📋 Liste", "➕ Nouvelle réservation", "✏️ Modifier / Supprimer", "📤 Import CSV"
    ])

    with tab_liste:
        _show_liste()

    with tab_ajout:
        _show_formulaire_ajout()

    with tab_modifier:
        _show_formulaire_modifier()

    with tab_import:
        _show_import()


# ──────────────────────────────────────────────────────────────────────────────
# TAB 1 : LISTE
# ──────────────────────────────────────────────────────────────────────────────

def _show_liste():
    with st.expander("🔍 Filtres", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            plateforme = st.multiselect("Plateforme", PLATEFORMES, key="filt_plat")
        with col2:
            annees_options = [2024, 2025, 2026]
            annee = st.selectbox("Année", ["Toutes"] + annees_options, key="filt_annee")
        with col3:
            statut_paye = st.selectbox("Paiement", ["Tous", "Payés", "En attente"], key="filt_paye")
        with col4:
            prop_options = list(PROPRIETES.items())
            prop_labels  = ["Toutes"] + [v for _, v in prop_options]
            prop_choix   = st.selectbox("Propriété", prop_labels, key="filt_prop")

    df = load_reservations()
    if df.empty:
        st.warning("Aucune réservation disponible.")
        return

    if plateforme:
        df = df[df["plateforme"].isin(plateforme)]
    if annee != "Toutes":
        df = df[df["annee"] == int(annee)]
    if statut_paye == "Payés":
        df = df[df["paye"] == True]
    elif statut_paye == "En attente":
        df = df[df["paye"] == False]
    if prop_choix != "Toutes":
        prop_id = next(k for k, v in PROPRIETES.items() if v == prop_choix)
        df = df[df["propriete_id"] == prop_id]

    cols = [c for c in COLONNES_AFFICHAGE if c in df.columns]
    st.markdown(f"**{len(df)} réservation(s)**")

    st.dataframe(
        df[cols].sort_values("date_arrivee", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "prix_brut":   st.column_config.NumberColumn("Prix brut",    format="%.2f €"),
            "prix_net":    st.column_config.NumberColumn("Prix net",     format="%.2f €"),
            "commissions": st.column_config.NumberColumn("Commissions",  format="%.2f €"),
            "menage":      st.column_config.NumberColumn("Ménage",       format="%.2f €"),
            "taxes_sejour":st.column_config.NumberColumn("Taxes séjour", format="%.2f €"),
            "paye":        st.column_config.CheckboxColumn("Payé"),
        }
    )

    csv_data = df[cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Exporter CSV", csv_data,
        file_name="reservations_export.csv", mime="text/csv"
    )


# ──────────────────────────────────────────────────────────────────────────────
# TAB 2 : FORMULAIRE AJOUT
# ──────────────────────────────────────────────────────────────────────────────

def _show_formulaire_ajout():
    st.subheader("➕ Nouvelle réservation")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise pour ajouter une réservation.")
        return

    with st.form("form_ajout", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**👤 Client**")
            nom_client  = st.text_input("Nom du client *", placeholder="Ex: DUPONT Jean")
            email       = st.text_input("Email", placeholder="jean@email.com")
            telephone   = st.text_input("Téléphone", placeholder="+33 6 00 00 00 00")
            pays        = st.text_input("Pays", placeholder="France")

        with col2:
            st.markdown("**🏠 Séjour**")
            propriete_id = st.selectbox(
                "Propriété *",
                options=list(PROPRIETES.keys()),
                format_func=lambda x: PROPRIETES[x]
            )
            plateforme = st.selectbox("Plateforme *", PLATEFORMES)
            date_arrivee = st.date_input("Date d'arrivée *", value=date.today())
            date_depart  = st.date_input(
                "Date de départ *",
                value=date.today() + timedelta(days=7)
            )
            numero_reservation = st.text_input("N° réservation", placeholder="Ex: 4521234567")

        st.divider()
        st.markdown("**💶 Finances**")

        col3, col4, col5 = st.columns(3)
        with col3:
            prix_brut    = st.number_input("Prix brut (€) *", min_value=0.0, step=10.0)
            commissions  = st.number_input("Commissions (€)", min_value=0.0, step=1.0)
            frais_cb     = st.number_input("Frais CB (€)", min_value=0.0, step=1.0)
        with col4:
            menage       = st.number_input("Ménage (€)", min_value=0.0, value=50.0, step=5.0)
            taxes_sejour = st.number_input("Taxes séjour (€)", min_value=0.0, step=1.0)
        with col5:
            paye         = st.checkbox("✅ Payé", value=False)
            prix_net_calc = max(0, prix_brut - commissions - frais_cb)
            st.metric("Prix net calculé", f"{prix_net_calc:.2f} €")

        submitted = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)

    if submitted:
        if not nom_client:
            st.error("Le nom du client est obligatoire.")
            return
        if date_depart <= date_arrivee:
            st.error("La date de départ doit être après la date d'arrivée.")
            return

        nuitees = (date_depart - date_arrivee).days
        pct_commission = round(commissions / prix_brut * 100, 2) if prix_brut > 0 else 0

        data = {
            "nom_client":        nom_client.strip(),
            "email":             email or None,
            "telephone":         telephone or None,
            "pays":              pays or None,
            "propriete_id":      propriete_id,
            "plateforme":        plateforme,
            "date_arrivee":      str(date_arrivee),
            "date_depart":       str(date_depart),
            "nuitees":           nuitees,
            "prix_brut":         prix_brut,
            "commissions":       commissions,
            "frais_cb":          frais_cb,
            "prix_net":          prix_net_calc,
            "menage":            menage,
            "taxes_sejour":      taxes_sejour,
            "base":              prix_brut - commissions - menage - taxes_sejour,
            "pct_commission":    pct_commission,
            "commissions_hote":  commissions,
            "frais_menage":      menage,
            "paye":              paye,
            "sms_envoye":        False,
            "post_depart_envoye": False,
            "numero_reservation": numero_reservation or None,
        }

        try:
            result = repo.insert_reservation(data)
            st.success(f"✅ Réservation ajoutée ! (ID: {result.get('id', '—')})")
            st.balloons()
        except Exception as e:
            st.error(f"Erreur : {e}")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 3 : MODIFIER / SUPPRIMER
# ──────────────────────────────────────────────────────────────────────────────

def _show_formulaire_modifier():
    st.subheader("✏️ Modifier ou supprimer une réservation")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise.")
        return

    df = load_reservations()
    if df.empty:
        st.warning("Aucune réservation disponible.")
        return

    # Sélection de la réservation
    df_sorted = df.sort_values("date_arrivee", ascending=False)
    options = {
        row["id"]: f"#{row['id']} — {row['nom_client']}  |  "
                   f"{row['date_arrivee'].strftime('%d/%m/%Y')} → {row['date_depart'].strftime('%d/%m/%Y')}  |  "
                   f"{row['plateforme']}"
        for _, row in df_sorted.iterrows()
    }

    selected_id = st.selectbox(
        "Choisir une réservation",
        options=list(options.keys()),
        format_func=lambda x: options[x]
    )

    if selected_id is None:
        return

    row = df[df["id"] == selected_id].iloc[0]

    st.divider()

    with st.form("form_modifier"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**👤 Client**")
            nom_client  = st.text_input("Nom du client *", value=str(row.get("nom_client", "")))
            email       = st.text_input("Email", value=str(row.get("email", "") or ""))
            telephone   = st.text_input("Téléphone", value=str(row.get("telephone", "") or ""))
            pays        = st.text_input("Pays", value=str(row.get("pays", "") or ""))

        with col2:
            st.markdown("**🏠 Séjour**")
            propriete_id = st.selectbox(
                "Propriété *",
                options=list(PROPRIETES.keys()),
                format_func=lambda x: PROPRIETES[x],
                index=list(PROPRIETES.keys()).index(int(row.get("propriete_id", 1)))
                      if int(row.get("propriete_id", 1)) in PROPRIETES else 0
            )
            plat_idx = PLATEFORMES.index(row["plateforme"]) if row.get("plateforme") in PLATEFORMES else 0
            plateforme   = st.selectbox("Plateforme *", PLATEFORMES, index=plat_idx)
            date_arrivee = st.date_input("Date d'arrivée *",
                                         value=row["date_arrivee"].date()
                                         if hasattr(row["date_arrivee"], "date")
                                         else row["date_arrivee"])
            date_depart  = st.date_input("Date de départ *",
                                         value=row["date_depart"].date()
                                         if hasattr(row["date_depart"], "date")
                                         else row["date_depart"])
            numero_reservation = st.text_input(
                "N° réservation", value=str(row.get("numero_reservation", "") or "")
            )

        st.divider()
        st.markdown("**💶 Finances**")

        col3, col4, col5 = st.columns(3)
        with col3:
            prix_brut   = st.number_input("Prix brut (€) *",  value=float(row.get("prix_brut", 0)),   step=10.0)
            commissions = st.number_input("Commissions (€)",   value=float(row.get("commissions", 0)), step=1.0)
            frais_cb    = st.number_input("Frais CB (€)",      value=float(row.get("frais_cb", 0)),    step=1.0)
        with col4:
            menage       = st.number_input("Ménage (€)",       value=float(row.get("menage", 50)),     step=5.0)
            taxes_sejour = st.number_input("Taxes séjour (€)", value=float(row.get("taxes_sejour", 0)),step=1.0)
        with col5:
            paye = st.checkbox("✅ Payé", value=bool(row.get("paye", False)))
            prix_net_calc = max(0, prix_brut - commissions - frais_cb)
            st.metric("Prix net calculé", f"{prix_net_calc:.2f} €")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submitted = st.form_submit_button("💾 Enregistrer les modifications",
                                              type="primary", use_container_width=True)
        with col_btn2:
            supprimer = st.form_submit_button("🗑️ Supprimer cette réservation",
                                              use_container_width=True)

    if submitted:
        if date_depart <= date_arrivee:
            st.error("La date de départ doit être après la date d'arrivée.")
            return

        nuitees = (date_depart - date_arrivee).days
        pct_commission = round(commissions / prix_brut * 100, 2) if prix_brut > 0 else 0

        data = {
            "nom_client":        nom_client.strip(),
            "email":             email or None,
            "telephone":         telephone or None,
            "pays":              pays or None,
            "propriete_id":      propriete_id,
            "plateforme":        plateforme,
            "date_arrivee":      str(date_arrivee),
            "date_depart":       str(date_depart),
            "nuitees":           nuitees,
            "prix_brut":         prix_brut,
            "commissions":       commissions,
            "frais_cb":          frais_cb,
            "prix_net":          prix_net_calc,
            "menage":            menage,
            "taxes_sejour":      taxes_sejour,
            "pct_commission":    pct_commission,
            "paye":              paye,
            "numero_reservation": numero_reservation or None,
        }

        try:
            repo.update_reservation(selected_id, data)
            st.success(f"✅ Réservation #{selected_id} mise à jour !")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")

    if supprimer:
        try:
            repo.delete_reservation(selected_id)
            st.success(f"🗑️ Réservation #{selected_id} supprimée.")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")


# ──────────────────────────────────────────────────────────────────────────────
# TAB 4 : IMPORT CSV
# ──────────────────────────────────────────────────────────────────────────────

def _show_import():
    st.subheader("📤 Importer un CSV")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise pour l'import.")
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
