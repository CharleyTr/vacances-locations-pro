"""
Page Plateformes - Gestion de la liste des plateformes de réservation
(Airbnb, Booking, Abritel, PAP, Direct, VRBO, ...).
"""
import streamlit as st
from database.platforms_repo import fetch_all, insert_platform, update_platform
from database.supabase_client import is_connected


def show():
    st.title("🏷️ Plateformes")
    st.caption("Gère la liste des plateformes de réservation utilisées dans l'app.")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise.")
        return

    # --- Formulaire d'ajout ---
    with st.expander("➕ Ajouter une plateforme", expanded=False):
        with st.form("add_platform_form", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                nom = st.text_input("Nom de la plateforme *")
            with col2:
                couleur = st.color_picker("Couleur", value="#4F46E5")
            with col3:
                commission = st.number_input(
                    "Commission %", min_value=0.0, max_value=100.0, value=0.0, step=0.5
                )

            submitted = st.form_submit_button("Ajouter", type="primary")
            if submitted:
                if not nom.strip():
                    st.error("Le nom est obligatoire.")
                else:
                    try:
                        insert_platform({
                            "nom": nom.strip(),
                            "couleur": couleur,
                            "commission_pct": commission,
                            "actif": True,
                        })
                        st.success(f"Plateforme '{nom}' ajoutée.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'ajout (nom probablement déjà utilisé) : {e}")

    st.divider()

    # --- Liste des plateformes existantes ---
    platforms = fetch_all(force_refresh=True)

    if not platforms:
        st.info("Aucune plateforme enregistrée pour le moment.")
        return

    st.subheader("Plateformes existantes")

    for p in platforms:
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        with col1:
            st.markdown(f"**{p['nom']}**")
        with col2:
            st.markdown(
                f"<div style='width:24px;height:24px;border-radius:4px;"
                f"background:{p.get('couleur') or '#CCCCCC'};border:1px solid #999'></div>",
                unsafe_allow_html=True,
            )
        with col3:
            st.text(f"{p.get('commission_pct', 0) or 0}%")
        with col4:
            actif = st.toggle("Actif", value=p["actif"], key=f"actif_{p['id']}")
            if actif != p["actif"]:
                update_platform(p["id"], {"actif": actif})
                st.rerun()
        with col5:
            if st.button("✏️", key=f"edit_{p['id']}"):
                st.session_state[f"editing_{p['id']}"] = not st.session_state.get(f"editing_{p['id']}", False)

        if st.session_state.get(f"editing_{p['id']}"):
            with st.form(f"edit_form_{p['id']}"):
                new_nom = st.text_input("Nom", value=p["nom"])
                new_couleur = st.color_picker("Couleur", value=p.get("couleur") or "#CCCCCC")
                new_commission = st.number_input(
                    "Commission %", value=float(p.get("commission_pct") or 0),
                    min_value=0.0, max_value=100.0, step=0.5
                )
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.form_submit_button("Enregistrer"):
                        update_platform(p["id"], {
                            "nom": new_nom.strip(),
                            "couleur": new_couleur,
                            "commission_pct": new_commission,
                        })
                        st.session_state[f"editing_{p['id']}"] = False
                        st.rerun()
                with col_cancel:
                    if st.form_submit_button("Annuler"):
                        st.session_state[f"editing_{p['id']}"] = False
                        st.rerun()
