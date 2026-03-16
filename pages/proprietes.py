"""
Page Propriétés - Gestion des biens locatifs.
"""
import streamlit as st
from database.proprietes_repo import (
    fetch_all, insert_propriete, update_propriete, delete_propriete
)
from services.auth_service import set_password, remove_password
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
                    adresse = st.text_input("Adresse", value=prop.get("adresse", "") or "")
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
                        "adresse":    adresse or None,
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
                st.caption("🔒 Mot de passe configuré")
            else:
                st.caption("🔓 Aucun mot de passe")
        with col2:
            new_mdp = st.text_input(
                "Nouveau mot de passe",
                type="password",
                placeholder="Laisser vide = pas de protection",
                key=f"mdp_{p['id']}"
            )
        with col3:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            if st.button("💾 Appliquer", key=f"save_mdp_{p['id']}"):
                if new_mdp.strip():
                    if set_password(p["id"], new_mdp.strip()):
                        st.success(f"✅ Mot de passe défini pour {p['nom']}")
                        st.rerun()
                else:
                    if remove_password(p["id"]):
                        st.success(f"🔓 Mot de passe supprimé pour {p['nom']}")
                        st.rerun()

    st.divider()

    # ── Ajouter une propriété ─────────────────────────────────────────────
    st.subheader("➕ Ajouter une propriété")

    with st.form("form_new_prop", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_nom     = st.text_input("Nom *", placeholder="Ex: Appartement Paris 11")
            new_adresse = st.text_input("Adresse", placeholder="Ex: 15 rue de la Paix, Paris")
        with col2:
            new_ical = st.text_input(
                "URL iCal (optionnel)",
                placeholder="https://www.airbnb.fr/calendar/ical/..."
            )
            new_signataire = st.text_input(
                "✍️ Signataire des messages",
                placeholder="Ex: Christophe & Marie"
            )

        submitted = st.form_submit_button("✅ Créer la propriété", type="primary", use_container_width=True)

    if submitted:
        if not new_nom:
            st.error("Le nom est obligatoire.")
        else:
            try:
                result = insert_propriete({
                    "nom":        new_nom.strip(),
                    "adresse":    new_adresse or None,
                    "ical_url":   new_ical or None,
                    "signataire": new_signataire.strip() or None,
                    "actif":      True,
                })
                st.success(f"✅ Propriété '{new_nom}' créée ! (ID: {result.get('id', '?')})")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.divider()
    st.info(
        "💡 **Astuce** : après avoir modifié les noms, "
        "le sélecteur de propriété dans la sidebar se mettra à jour automatiquement."
    )
