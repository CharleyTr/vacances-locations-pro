"""
Page Propriétés - Gestion des biens locatifs.
"""
import streamlit as st
from database.proprietes_repo import (
    fetch_all, insert_propriete, update_propriete, delete_propriete
)
from database.supabase_client import is_connected


def show():
    st.title("🏠 Gestion des propriétés")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise.")
        return

    props = fetch_all(force_refresh=True)

    # ── Liste des propriétés ──────────────────────────────────────────────
    st.subheader(f"📋 {len(props)} propriété(s)")

    for prop in props:
        with st.expander(f"🏠 {prop['nom']}  (ID: {prop['id']})", expanded=False):
            with st.form(f"form_edit_{prop['id']}"):
                col1, col2 = st.columns(2)
                with col1:
                    nom     = st.text_input("Nom *", value=prop.get("nom", ""))
                    rue     = st.text_input("Rue", value=prop.get("rue", "") or "", placeholder="Ex: 12 rue de la Paix")
                    col_cp, col_ville = st.columns([2, 3])
                    with col_cp:
                        code_postal = st.text_input("Code postal", value=prop.get("code_postal", "") or "", placeholder="75001")
                    with col_ville:
                        ville = st.text_input("Ville", value=prop.get("ville", "") or "", placeholder="Paris")
                    telephone_prop = st.text_input("Téléphone", value=prop.get("telephone", "") or "", placeholder="+33 6 12 34 56 78")
                with col2:
                    ical_url = st.text_input(
                        "URL iCal (optionnel)",
                        value=prop.get("ical_url", "") or "",
                        placeholder="https://www.airbnb.fr/calendar/ical/..."
                    )
                    signataire = st.text_input(
                        "✍️ Signataire des messages",
                        value=prop.get("signataire", "") or "",
                        placeholder="Ex: Christophe & Marie"
                    )
                    siret = st.text_input(
                        "SIRET (optionnel)",
                        value=prop.get("siret", "") or "",
                        placeholder="XXX XXX XXX XXXXX"
                    )
                    actif = st.checkbox("Propriété active", value=prop.get("actif", True))

                col_a, col_b = st.columns(2)
                with col_a:
                    save = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)
                with col_b:
                    suppr = st.form_submit_button("🗑️ Désactiver", use_container_width=True)

            if save:
                try:
                    update_propriete(prop["id"], {
                        "nom":        nom.strip(),
                        "rue":        rue.strip() or None,
                        "code_postal":code_postal.strip() or None,
                        "ville":      ville.strip() or None,
                        "telephone":  telephone_prop.strip() or None,
                        "siret":      siret.strip() or None,
                        "ical_url":   ical_url or None,
                        "signataire": signataire.strip() or None,
                        "actif":      actif,
                    })
                    st.success(f"✅ '{nom}' mis à jour !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

            if suppr:
                try:
                    delete_propriete(prop["id"])
                    st.warning(f"🗑️ '{prop['nom']}' désactivée.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.divider()

    # ── Gestion des mots de passe ─────────────────────────────────────────
    st.subheader("🔐 Mots de passe par propriété")
    st.caption("Protégez l'accès à chaque appartement. Le mot de passe sera demandé à la sélection.")

    props_list = fetch_all()
    for p in props_list:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"**{p['nom']}**")
            if p.get("mot_de_passe"):
                st.caption("🔒 Code propriétaire configuré")
            else:
                st.caption("🔓 Aucun code propriétaire")
            if p.get("mot_de_passe_gestionnaire"):
                st.caption("🔑 Code gestionnaire configuré")
            else:
                st.caption("🔑 Aucun code gestionnaire")
        with col2:
            new_mdp = st.text_input(
                "Code propriétaire",
                type="password",
                placeholder="Code accès propriétaire...",
                key=f"mdp_{p['id']}"
            )
            new_mdp_gest = st.text_input(
                "Code gestionnaire",
                type="password",
                placeholder="Code ménage / régisseur...",
                key=f"mdp_gest_{p['id']}",
                help="Accès limité : Dashboard, Calendrier, Ménage, Messages"
            )
        with col3:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            if st.button("💾 Appliquer", key=f"save_mdp_{p['id']}"):
                import hashlib as _hl
                updates = {}
                if new_mdp.strip():
                    updates["mot_de_passe"] = _hl.sha256(new_mdp.strip().encode()).hexdigest()
                if new_mdp_gest.strip():
                    updates["mot_de_passe_gestionnaire"] = _hl.sha256(new_mdp_gest.strip().encode()).hexdigest()
                if updates:
                    update_propriete(p["id"], updates)
                    st.success(f"✅ Codes mis à jour pour {p['nom']}")
                    st.rerun()
                else:
                    st.warning("Saisissez au moins un code.")

    st.divider()

    # ── Ajouter une propriété ─────────────────────────────────────────────
    st.subheader("➕ Ajouter une propriété")

    with st.form("form_new_prop", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_nom     = st.text_input("Nom *", placeholder="Ex: Appartement Paris 11")
            new_rue     = st.text_input("Rue", placeholder="Ex: 15 rue de la Paix")
            col_cp2, col_ville2 = st.columns([2, 3])
            with col_cp2:
                new_cp  = st.text_input("Code postal", placeholder="75011")
            with col_ville2:
                new_ville = st.text_input("Ville", placeholder="Paris")
            new_tel = st.text_input("Téléphone", placeholder="+33 6 12 34 56 78")
        with col2:
            new_ical = st.text_input(
                "URL iCal (optionnel)",
                placeholder="https://www.airbnb.fr/calendar/ical/..."
            )
            new_signataire = st.text_input(
                "✍️ Signataire des messages",
                placeholder="Ex: Christophe & Marie"
            )
            new_siret = st.text_input("SIRET (optionnel)", placeholder="XXX XXX XXX XXXXX")

        submitted = st.form_submit_button("✅ Créer la propriété", type="primary", use_container_width=True)

    if submitted:
        if not new_nom:
            st.error("Le nom est obligatoire.")
        else:
            try:
                import streamlit as _st2
                _owner_id = _st2.session_state.get("auth_user_id") or None
                _data_prop = {
                    "nom":        new_nom.strip(),
                    "rue":        new_rue.strip() or None,
                    "code_postal":new_cp.strip() or None,
                    "ville":      new_ville.strip() or None,
                    "telephone":  new_tel.strip() or None,
                    "siret":      new_siret.strip() or None,
                    "ical_url":   new_ical or None,
                    "signataire": new_signataire.strip() or None,
                    "actif":      True,
                }
                if _owner_id:
                    _data_prop["owner_id"] = _owner_id
                result = insert_propriete(_data_prop)
                st.success(f"✅ Propriété '{new_nom}' créée ! (ID: {result.get('id', '?')})")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.divider()
    st.info(
        "💡 **Astuce** : après avoir modifié les noms, "
        "le sélecteur de propriété dans la sidebar se mettra à jour automatiquement."
    )
