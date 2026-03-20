"""
Page Réservations - Liste + Filtres + Formulaire Ajout/Modification/Suppression + Import CSV.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_dict
from database.proprietes_repo import fetch_all as _fetch_all_props
from services.auth_service import is_unlocked

def _get_props_autorises() -> dict:
    """Retourne uniquement les propriétés déverrouillées."""
    return {
        p["id"]: p["nom"] for p in _fetch_all_props()
        if not p.get("mot_de_passe") or is_unlocked(p["id"])
    }
from services.import_service import import_csv_file, preview_csv
from database.supabase_client import is_connected
import database.reservations_repo as repo


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
    df = load_reservations()
    if df.empty:
        st.warning("Aucune réservation disponible.")
        return
    # Restreindre aux propriétés autorisées
    _autorises = list(_get_props_autorises().keys())
    df = df[df["propriete_id"].isin(_autorises)]
    if df.empty:
        st.warning("Aucune réservation disponible pour vos propriétés.")
        return

    with st.expander("🔍 Filtres", expanded=True):
        # Recherche par nom — en premier, bien visible
        search_nom = st.text_input(
            "🔎 Rechercher un client",
            placeholder="Tapez un nom...",
            key="filt_nom"
        )
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            plateforme = st.multiselect("Plateforme", PLATEFORMES, key="filt_plat")
        with col2:
            from datetime import date as _date
            if "annee" in df.columns:
                annees_options = sorted(df["annee"].dropna().astype(int).unique().tolist(), reverse=True)
            else:
                annees_options = list(range(_date.today().year, 2013, -1))
            annee = st.selectbox("Année", ["Toutes"] + annees_options, key="filt_annee")
        with col3:
            statut_paye = st.selectbox("Paiement", ["Tous", "Payés", "En attente"], key="filt_paye")
        with col4:
            _props = _get_props_autorises()
            prop_labels  = ["Toutes"] + list(_props.values())
            prop_choix   = st.selectbox("Propriété", prop_labels, key="filt_prop")

    if search_nom:
        df = df[df["nom_client"].str.contains(search_nom, case=False, na=False)]
    if plateforme:
        df = df[df["plateforme"].isin(plateforme)]
    if annee != "Toutes":
        df = df[df["annee"] == int(annee)]
    if statut_paye == "Payés":
        df = df[df["paye"] == True]
    elif statut_paye == "En attente":
        df = df[df["paye"] == False]
    if prop_choix != "Toutes":
        _props = get_proprietes_dict()
        prop_id = next((k for k, v in _props.items() if v == prop_choix), None)
        if prop_id:
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

    # ── Téléphone hors formulaire → pays temps réel ─────────────────────
    _tel_pre = st.text_input("📞 Téléphone", placeholder="+33 6 12 34 56 78",
                              key="res_tel_pre")
    try:
        from services.indicatifs_service import detect_pays as _dp
        _det = _dp(_tel_pre) if _tel_pre else None
    except:
        _det = None

    if _det:
        st.success(f"{_det[2]} **{_det[0]}**")
    elif _tel_pre:
        st.caption("Indicatif non reconnu — pays non détecté")
    
    st.divider()

    with st.form("form_ajout", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**👤 Client**")
            nom_client  = st.text_input("Nom du client *", placeholder="Ex: DUPONT Jean")
            email       = st.text_input("Email", placeholder="jean@email.com")
            telephone   = st.text_input("Téléphone",
                                        value=st.session_state.get("res_tel_pre",""),
                                        placeholder="+33 6 00 00 00 00")
            # Pays détecté automatiquement
            _pays_val = st.session_state.get("res_pays_pre","")
            if _pays_val and "🇫🇷" in _pays_val or any(c for c in _pays_val if ord(c)>127):
                # Enlever l'emoji pour la valeur stockée
                import re as _re
                _pays_val_clean = _re.sub(r'[^-À-ɏ ]+', '', _pays_val).strip()
            else:
                _pays_val_clean = _pays_val
            pays = st.text_input("Pays", value=_pays_val_clean,
                                  placeholder="France")

        with col2:
            st.markdown("**🏠 Séjour**")
            propriete_id = st.selectbox(
                "Propriété *",
                options=list(_get_props_autorises().keys()),
                format_func=lambda x: _get_props_autorises()[x]
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
            "pays":              (pays.strip() if pays.strip() else (
                __import__('services.indicatifs_service', fromlist=['get_pays_from_tel'])
                .get_pays_from_tel(telephone) if telephone else ""
            )) or None,
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
    _autorises = list(_get_props_autorises().keys())
    df = df[df["propriete_id"].isin(_autorises)]

    # Recherche par nom avant le selectbox
    search_mod = st.text_input("🔎 Rechercher un client", placeholder="Tapez un nom...", key="mod_search")
    df_sorted = df.sort_values("date_arrivee", ascending=False)
    if search_mod:
        df_sorted = df_sorted[df_sorted["nom_client"].str.contains(search_mod, case=False, na=False)]

    if df_sorted.empty:
        st.info("Aucune réservation trouvée pour ce nom.")
        return

    options = {
        row["id"]: f"{row['nom_client']}  |  "
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
            telephone = st.text_input("Téléphone",
                                    value=str(row.get("telephone","") or ""),
                                    key="tel_edit_form")
            # Pays auto depuis téléphone, ou valeur existante
            _tel_edit = st.session_state.get("tel_edit_form","") or str(row.get("telephone","") or "")
            try:
                from services.indicatifs_service import detect_pays
                _det_e = detect_pays(_tel_edit) if _tel_edit else None
                _pays_display_e = f"{_det_e[2]} {_det_e[0]}" if _det_e else str(row.get("pays","") or "")
                pays = _det_e[0] if _det_e else str(row.get("pays","") or "")
            except:
                _pays_display_e = str(row.get("pays","") or "")
                pays = str(row.get("pays","") or "")
            st.markdown(
                f"<div style='background:#F0F4FF;border-radius:6px;padding:7px 12px;"
                f"font-size:14px;border:1px solid #E0E0E0;min-height:36px'>"
                f"{'🌍 <strong>' + _pays_display_e + '</strong>' if _pays_display_e else '<span style="color:#aaa">🌍 Pays — détecté depuis le tél.</span>'}"
                f"</div>",
                unsafe_allow_html=True
            )

        with col2:
            st.markdown("**🏠 Séjour**")
            _props_auth = _get_props_autorises()
            _prop_ids = list(_props_auth.keys())
            _current_pid = int(row.get("propriete_id", _prop_ids[0] if _prop_ids else 1))
            _idx = _prop_ids.index(_current_pid) if _current_pid in _prop_ids else 0
            propriete_id = st.selectbox(
                "Propriété *",
                options=_prop_ids,
                format_func=lambda x: _props_auth[x],
                index=_idx,
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
            "pays":              (pays.strip() if pays.strip() else (
                __import__('services.indicatifs_service', fromlist=['get_pays_from_tel'])
                .get_pays_from_tel(telephone) if telephone else ""
            )) or None,
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
