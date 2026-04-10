"""
Page Propriétés - Gestion des biens locatifs avec fiche complète.
"""
import streamlit as st
from database.proprietes_repo import (
    fetch_all, insert_propriete, update_propriete, delete_propriete
)
from database.supabase_client import is_connected


EQUIP_CATEGORIES = {
    "🌐 Connectivité":  ["WiFi haut débit","Fibre optique","TV connectée","Chromecast","Netflix"],
    "🍳 Cuisine":       ["Cuisine équipée","Lave-vaisselle","Micro-ondes","Four","Cafetière","Nespresso","Barbecue"],
    "🛋️ Confort":       ["Climatisation","Chauffage","Lave-linge","Sèche-linge","Fer à repasser","Aspirateur"],
    "🏊 Extérieur":     ["Piscine","Jacuzzi","Terrasse","Balcon","Jardin","Parking privé","Garage"],
    "👶 Services":      ["Lit bébé","Chaise haute","Accès PMR","Animaux acceptés"],
    "🔒 Sécurité":      ["Alarme","Coffre-fort","Détecteur fumée","Extincteur"],
}


def show():
    st.title("🏠 Gestion des propriétés")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise.")
        return

    _is_admin = st.session_state.get("is_admin", False)
    _prop_id  = st.session_state.get("prop_id", 0) or 0

    all_props = fetch_all(force_refresh=True)

    # Filtrer : admin voit tout, propriétaire voit uniquement sa propriété
    if _is_admin:
        props = all_props
    else:
        props = [p for p in all_props if p["id"] == _prop_id]

    if not props:
        st.warning("Aucune propriété associée à votre compte.")
        return

    st.subheader(f"📋 {len(props)} propriété(s)")

    for prop in props:
        with st.expander(f"🏠 {prop['nom']}  (ID: {prop['id']})", expanded=False):

            tab_info, tab_fiche, tab_equip, tab_reglement = st.tabs([
                "ℹ️ Informations", "📋 Fiche", "🛋️ Équipements", "📜 Règlement"
            ])

            # ── Onglet Informations ───────────────────────────────────────
            with tab_info:
                with st.form(f"form_edit_{prop['id']}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        nom  = st.text_input("Nom *", value=prop.get("nom", ""))
                        rue  = st.text_input("Rue", value=prop.get("rue","") or "")
                        col_cp, col_ville = st.columns([2,3])
                        with col_cp:
                            code_postal = st.text_input("Code postal", value=prop.get("code_postal","") or "")
                        with col_ville:
                            ville = st.text_input("Ville", value=prop.get("ville","") or "")
                        telephone_prop = st.text_input("Téléphone", value=prop.get("telephone","") or "")
                    with col2:
                        ical_url   = st.text_input("URL iCal", value=prop.get("ical_url","") or "")
                        signataire = st.text_input("Signataire", value=prop.get("signataire","") or "")
                        siret      = st.text_input("SIRET", value=prop.get("siret","") or "")
                        actif      = st.checkbox("Propriété active", value=prop.get("actif", True))

                    col_a, col_b = st.columns(2)
                    with col_a:
                        save  = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)
                    with col_b:
                        suppr = st.form_submit_button("🗑️ Désactiver", use_container_width=True)

                if save:
                    try:
                        update_propriete(prop["id"], {
                            "nom": nom.strip(), "rue": rue.strip() or None,
                            "code_postal": code_postal.strip() or None,
                            "ville": ville.strip() or None,
                            "telephone": telephone_prop.strip() or None,
                            "siret": siret.strip() or None,
                            "ical_url": ical_url or None,
                            "signataire": signataire.strip() or None,
                            "actif": actif,
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

            # ── Onglet Fiche ──────────────────────────────────────────────
            with tab_fiche:
                with st.form(f"form_fiche_{prop['id']}"):
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        f_surface   = st.number_input("Surface (m²)", min_value=0.0,
                            value=float(prop.get("surface_m2") or 0), step=1.0)
                        f_chambres  = st.number_input("Chambres", min_value=0, max_value=20,
                            value=int(prop.get("nb_chambres") or 1))
                        f_couchages = st.number_input("Couchages", min_value=0, max_value=50,
                            value=int(prop.get("nb_couchages") or 2))
                        f_sdb       = st.number_input("Salles de bain", min_value=0, max_value=10,
                            value=int(prop.get("nb_salles_bain") or 1))
                    with fc2:
                        f_checkin  = st.text_input("Check-in", value=prop.get("checkin_heure") or "16:00")
                        f_checkout = st.text_input("Check-out", value=prop.get("checkout_heure") or "11:00")
                        f_wifi     = st.text_input("Code WiFi", value=prop.get("code_wifi") or "",
                                                    placeholder="Réseau / mot de passe")
                        f_porte    = st.text_input("Code porte / boîte à clé",
                                                    value=prop.get("code_acces_porte") or "",
                                                    placeholder="Ex: 1234#")
                        st.markdown("**🧹 Équipe ménage**")
                        f_tel_menage = st.text_input("Tél. WhatsApp ménage",
                                                      value=prop.get("tel_menage") or "",
                                                      placeholder="+33612345678")
                        f_nom_menage = st.text_input("Nom équipe ménage",
                                                      value=prop.get("nom_menage") or "",
                                                      placeholder="Ex: Martine, Société XYZ")
                    f_desc = st.text_area("Description courte",
                        value=prop.get("description_courte") or "", height=80)
                    f_infos = st.text_area("Infos pratiques (accès, parking...)",
                        value=prop.get("infos_pratiques") or "", height=100)
                    f_photos = st.text_area("URLs photos (une par ligne)",
                        value="\n".join(prop.get("photos_urls") or []), height=80)

                    if st.form_submit_button("💾 Enregistrer la fiche", type="primary",
                                              use_container_width=True):
                        try:
                            _photos = [u.strip() for u in f_photos.split("\n") if u.strip()]
                            update_propriete(prop["id"], {
                                "surface_m2":        f_surface or None,
                                "nb_chambres":       f_chambres,
                                "nb_couchages":      f_couchages,
                                "nb_salles_bain":    f_sdb,
                                "checkin_heure":     f_checkin.strip() or "16:00",
                                "checkout_heure":    f_checkout.strip() or "11:00",
                                "code_wifi":         f_wifi.strip() or None,
                                "code_acces_porte":  f_porte.strip() or None,
                                "description_courte":f_desc.strip() or None,
                                "infos_pratiques":   f_infos.strip() or None,
                                "photos_urls":       _photos or None,
                                "tel_menage":        f_tel_menage.strip() or None,
                                "nom_menage":        f_nom_menage.strip() or None,
                            })
                            st.success("✅ Fiche mise à jour !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

                # Aperçu photos
                _photos_list = prop.get("photos_urls") or []
                if _photos_list:
                    st.markdown("**📸 Photos**")
                    _pcols = st.columns(min(3, len(_photos_list)))
                    for _i, _url in enumerate(_photos_list[:6]):
                        with _pcols[_i % 3]:
                            try:
                                st.image(_url, use_container_width=True)
                            except: pass

            # ── Onglet Équipements ────────────────────────────────────────
            with tab_equip:
                _equip_actuels = set(prop.get("equipements") or [])
                _equip_choisis = set()

                with st.form(f"form_equip_{prop['id']}"):
                    for _cat, _items in EQUIP_CATEGORIES.items():
                        st.markdown(f"**{_cat}**")
                        _cols_eq = st.columns(3)
                        for _j, _item in enumerate(_items):
                            with _cols_eq[_j % 3]:
                                if st.checkbox(_item, value=_item in _equip_actuels,
                                               key=f"eq_{prop['id']}_{_j}_{_item[:8]}"):
                                    _equip_choisis.add(_item)
                        st.markdown("")

                    if st.form_submit_button("💾 Enregistrer les équipements",
                                              type="primary", use_container_width=True):
                        try:
                            update_propriete(prop["id"], {"equipements": list(_equip_choisis)})
                            st.success(f"✅ {len(_equip_choisis)} équipement(s) enregistré(s) !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

            # ── Onglet Règlement ──────────────────────────────────────────
            with tab_reglement:
                with st.form(f"form_reglement_{prop['id']}"):
                    f_reglement = st.text_area("Règlement intérieur",
                        value=prop.get("reglement_interieur") or "", height=250,
                        placeholder="Interdiction de fumer...\nAnimaux non acceptés...")
                    f_desc_long = st.text_area("Description longue (annonces)",
                        value=prop.get("description_longue") or "", height=120)

                    if st.form_submit_button("💾 Enregistrer", type="primary",
                                              use_container_width=True):
                        try:
                            update_propriete(prop["id"], {
                                "reglement_interieur": f_reglement.strip() or None,
                                "description_longue":  f_desc_long.strip() or None,
                            })
                            st.success("✅ Règlement enregistré !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

    st.divider()

    # ── Numéros SMS ────────────────────────────────────────────────────────
    st.subheader("📱 Numéros SMS par propriété")
    for p in props:
        c1, c2, c3 = st.columns([2, 2, 1])
        with c1:
            st.markdown(f"**{p['nom']}**")
            st.caption(f"📱 {p.get('tel_sms') or 'Aucun numéro SMS'}")
        with c2:
            new_sms = st.text_input("N° SMS", placeholder="+33...",
                                     key=f"sms_{p['id']}", label_visibility="collapsed")
            new_exp = st.text_input("Expéditeur", placeholder="NomProp (max 11 car.)",
                                     key=f"exp_{p['id']}", label_visibility="collapsed")
        with c3:
            if st.button("💾", key=f"save_sms_{p['id']}"):
                updates = {}
                if new_sms.strip(): updates["tel_sms"] = new_sms.strip()
                if new_exp.strip(): updates["nom_expediteur"] = new_exp.strip()[:11]
                if updates:
                    update_propriete(p["id"], updates)
                    st.success("✅")
                    st.rerun()

    st.divider()

    # ── Mots de passe ─────────────────────────────────────────────────────
    st.subheader("🔐 Mots de passe par propriété")
    for p in props:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.markdown(f"**{p['nom']}**")
            st.caption("🔒 Code propriétaire configuré" if p.get("mot_de_passe") else "🔓 Aucun code")
            st.caption("🔑 Code gestionnaire configuré" if p.get("mot_de_passe_gestionnaire") else "🔑 Aucun code gestionnaire")
        with col2:
            new_mdp      = st.text_input("Code propriétaire", type="password",
                                          placeholder="Code accès propriétaire...",
                                          key=f"mdp_{p['id']}")
            new_mdp_gest = st.text_input("Code gestionnaire", type="password",
                                          placeholder="Code ménage / régisseur...",
                                          key=f"mdp_gest_{p['id']}")
        with col3:
            if st.button("💾 Appliquer", key=f"save_mdp_{p['id']}"):
                import hashlib as _hl
                updates = {}
                if new_mdp.strip():
                    updates["mot_de_passe"] = _hl.sha256(new_mdp.strip().encode()).hexdigest()
                if new_mdp_gest.strip():
                    updates["mot_de_passe_gestionnaire"] = _hl.sha256(new_mdp_gest.strip().encode()).hexdigest()
                if updates:
                    update_propriete(p["id"], updates)
                    st.success(f"✅ Codes mis à jour")
                    st.rerun()
                else:
                    st.warning("Saisissez au moins un code.")
            if st.button("🗑️ Suppr. code prop.", key=f"del_mdp_{p['id']}"):
                update_propriete(p["id"], {"mot_de_passe": None})
                st.success("✅ Code supprimé")
                st.rerun()

    st.divider()

    # ── Ajouter une propriété ─────────────────────────────────────────────
    st.subheader("➕ Ajouter une propriété")
    with st.form("form_new_prop", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_nom   = st.text_input("Nom *", placeholder="Ex: Appartement Paris 11")
            new_rue   = st.text_input("Rue")
            c_cp, c_v = st.columns([2,3])
            with c_cp:  new_cp    = st.text_input("Code postal")
            with c_v:   new_ville = st.text_input("Ville")
            new_tel   = st.text_input("Téléphone")
        with col2:
            new_ical       = st.text_input("URL iCal")
            new_signataire = st.text_input("Signataire")
            new_siret      = st.text_input("SIRET")

        if st.form_submit_button("✅ Créer la propriété", type="primary", use_container_width=True):
            if not new_nom:
                st.error("Le nom est obligatoire.")
            else:
                try:
                    result = insert_propriete({
                        "nom": new_nom.strip(), "rue": new_rue.strip() or None,
                        "code_postal": new_cp.strip() or None,
                        "ville": new_ville.strip() or None,
                        "telephone": new_tel.strip() or None,
                        "siret": new_siret.strip() or None,
                        "ical_url": new_ical or None,
                        "signataire": new_signataire.strip() or None,
                        "actif": True,
                    })
                    st.success(f"✅ Propriété '{new_nom}' créée ! (ID: {result.get('id','?')})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    st.info("💡 Après modification des noms, le sélecteur se mettra à jour automatiquement.")
