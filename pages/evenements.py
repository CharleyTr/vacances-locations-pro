"""
Page gestion des événements de la ville.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database.evenements_repo import (
    get_evenements, save_evenement, delete_evenement,
    TYPE_LABELS, IMPACT_LABELS, COULEURS_TYPE
)
from database.proprietes_repo import fetch_all
from services.auth_service import is_unlocked


def show():
    st.title("🎪 Événements & Agenda")
    st.caption("Enregistrez les grands événements locaux pour optimiser vos tarifs.")

    props = [p for p in fetch_all() if not p.get("mot_de_passe") or is_unlocked(p["id"])]
    if not props:
        st.warning("Aucune propriété disponible.")
        return

    tab_liste, tab_ajouter, tab_calendrier = st.tabs([
        "📋 Liste des événements", "➕ Ajouter un événement", "📅 Vue calendrier"
    ])

    with tab_liste:
        _show_liste(props)

    with tab_ajouter:
        _show_formulaire(props)

    with tab_calendrier:
        _show_calendrier(props)


def _show_liste(props):
    st.subheader("📋 Événements enregistrés")

    col1, col2, col3 = st.columns(3)
    with col1:
        props_opt = {0: "Toutes les propriétés"}
        props_opt.update({p["id"]: p["nom"] for p in props})
        prop_f = st.selectbox("Propriété", list(props_opt.keys()),
                               format_func=lambda x: props_opt[x], key="evt_prop_f")
    with col2:
        annee_f = st.number_input("Année", value=date.today().year,
                                   min_value=2020, max_value=2030, key="evt_annee_f")
    with col3:
        type_f = st.selectbox("Type", ["Tous"] + list(TYPE_LABELS.keys()),
                               format_func=lambda x: TYPE_LABELS.get(x, x) if x != "Tous" else "Tous",
                               key="evt_type_f")

    evts = get_evenements(prop_id if (prop_id := prop_f) != 0 else None, int(annee_f))
    if type_f != "Tous":
        evts = [e for e in evts if e.get("type") == type_f]

    if not evts:
        st.info("Aucun événement pour cette sélection.")
        return

    st.caption(f"**{len(evts)} événement(s)**")

    for e in evts:
        impact = e.get("impact_tarif", "moyen")
        type_e = e.get("type", "evenement")
        couleur = e.get("couleur") or COULEURS_TYPE.get(type_e, "#FF6B35")
        nb_jours = (pd.to_datetime(e["date_fin"]) - pd.to_datetime(e["date_debut"])).days + 1

        with st.expander(
            f"{TYPE_LABELS.get(type_e,'📅')} **{e['nom']}** — "
            f"{e['date_debut']} → {e['date_fin']} ({nb_jours}j) — "
            f"{IMPACT_LABELS.get(impact,impact)}",
            expanded=False
        ):
            c1, c2, c3 = st.columns([3, 2, 1])
            with c1:
                if e.get("description"):
                    st.caption(e["description"])
                if e.get("ville"):
                    st.caption(f"📍 {e['ville']}")
            with c2:
                prop_nom = next((p["nom"] for p in props if p["id"] == e.get("propriete_id")), "Toutes")
                st.caption(f"🏠 {prop_nom}")
                st.markdown(
                    f"<span style='background:{couleur};color:white;padding:2px 8px;"
                    f"border-radius:10px;font-size:11px'>{IMPACT_LABELS.get(impact,impact)}</span>",
                    unsafe_allow_html=True
                )
            with c3:
                if st.button("✏️", key=f"edit_evt_{e['id']}", help="Modifier"):
                    st.session_state["edit_evt"] = e
                    st.rerun()
                if st.button("🗑️", key=f"del_evt_{e['id']}", help="Supprimer"):
                    delete_evenement(e["id"])
                    st.success("Supprimé !")
                    st.rerun()


def _show_formulaire(props):
    editing = st.session_state.get("edit_evt")
    st.subheader("✏️ Modifier" if editing else "➕ Nouvel événement")

    with st.form("form_evt", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nom = st.text_input("Nom *", value=editing["nom"] if editing else "",
                                 placeholder="Ex: Carnaval de Nice")
            desc = st.text_area("Description", value=editing.get("description","") if editing else "",
                                 height=80)
            ville = st.text_input("Ville", value=editing.get("ville","") if editing else "",
                                   placeholder="Nice, Cannes, Monaco...")
            props_opt = {p["id"]: p["nom"] for p in props}
            prop_id = st.selectbox("Propriété concernée",
                                    options=list(props_opt.keys()),
                                    format_func=lambda x: props_opt[x],
                                    index=list(props_opt.keys()).index(editing["propriete_id"])
                                          if editing and editing.get("propriete_id") in props_opt else 0,
                                    key="evt_form_prop")

        with col2:
            date_debut = st.date_input("Date début *",
                                        value=pd.to_datetime(editing["date_debut"]).date()
                                              if editing else date.today(),
                                        key="evt_deb")
            date_fin = st.date_input("Date fin *",
                                      value=pd.to_datetime(editing["date_fin"]).date()
                                            if editing else date.today(),
                                      key="evt_fin")
            type_e = st.selectbox("Type",
                                   options=list(TYPE_LABELS.keys()),
                                   format_func=lambda x: TYPE_LABELS[x],
                                   index=list(TYPE_LABELS.keys()).index(editing.get("type","evenement"))
                                         if editing else 0,
                                   key="evt_type")
            impact = st.selectbox("Impact tarifaire",
                                   options=list(IMPACT_LABELS.keys()),
                                   format_func=lambda x: IMPACT_LABELS[x],
                                   index=list(IMPACT_LABELS.keys()).index(editing.get("impact_tarif","fort"))
                                         if editing else 0,
                                   key="evt_impact")
            couleur = st.color_picker("Couleur sur calendrier",
                                       value=editing.get("couleur", COULEURS_TYPE.get(type_e,"#FF6B35"))
                                             if editing else "#FF6B35",
                                       key="evt_couleur")

        c1, c2 = st.columns(2)
        with c1:
            submitted = st.form_submit_button("💾 Enregistrer", type="primary",
                                               use_container_width=True)
        with c2:
            if editing:
                cancel = st.form_submit_button("❌ Annuler", use_container_width=True)
            else:
                cancel = False

        if submitted:
            if not nom:
                st.error("Le nom est obligatoire.")
            elif date_fin < date_debut:
                st.error("La date de fin doit être après la date de début.")
            else:
                data = {
                    "nom": nom, "description": desc, "ville": ville,
                    "propriete_id": prop_id,
                    "date_debut": date_debut.isoformat(),
                    "date_fin":   date_fin.isoformat(),
                    "type":          type_e,
                    "impact_tarif":  impact,
                    "couleur":       couleur,
                    "actif":         True,
                }
                if editing:
                    data["id"] = editing["id"]
                if save_evenement(data):
                    st.success("✅ Événement enregistré !")
                    st.session_state.pop("edit_evt", None)
                    st.rerun()
                else:
                    st.error("Erreur lors de l'enregistrement.")

        if cancel:
            st.session_state.pop("edit_evt", None)
            st.rerun()


def _show_calendrier(props):
    st.subheader("📅 Calendrier des événements")

    col1, col2, col3 = st.columns(3)
    with col1:
        annee_c = st.number_input("Année", value=date.today().year,
                                   min_value=2020, max_value=2030, key="evt_cal_annee")
    with col2:
        MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun",
                   "Jul","Aoû","Sep","Oct","Nov","Déc"]
        mois_c = st.selectbox("Mois", range(1,13),
                               format_func=lambda x: MOIS_FR[x-1],
                               index=date.today().month - 1, key="evt_cal_mois")
    with col3:
        props_opt = {0: "Toutes"}
        props_opt.update({p["id"]: p["nom"] for p in props})
        prop_c = st.selectbox("Propriété", list(props_opt.keys()),
                               format_func=lambda x: props_opt[x], key="evt_cal_prop")

    from database.evenements_repo import get_evenements_mois
    evts = get_evenements_mois(int(annee_c), int(mois_c), prop_c if prop_c != 0 else None)

    if not evts:
        st.info("Aucun événement ce mois.")
    else:
        st.markdown(f"**{len(evts)} événement(s) en {MOIS_FR[mois_c-1]} {annee_c} :**")
        for e in evts:
            couleur = e.get("couleur") or COULEURS_TYPE.get(e.get("type",""), "#FF6B35")
            impact  = e.get("impact_tarif","moyen")
            badge_c = {"fort":"#E53935","moyen":"#FF9800","faible":"#FFC107"}.get(impact,"#FF9800")
            st.markdown(f"""
            <div style='border-left:4px solid {couleur};background:{couleur}15;
                        padding:10px 16px;border-radius:0 8px 8px 0;margin-bottom:8px'>
                <b style='color:{couleur}'>{TYPE_LABELS.get(e.get("type",""),"📅")} {e["nom"]}</b>
                <span style='background:{badge_c};color:white;padding:1px 8px;
                             border-radius:10px;font-size:11px;margin-left:8px'>
                    {IMPACT_LABELS.get(impact,impact)}
                </span><br>
                <small>📅 {e["date_debut"]} → {e["date_fin"]}
                {"  📍 " + e["ville"] if e.get("ville") else ""}
                {"  | " + e.get("description","") if e.get("description") else ""}
                </small>
            </div>""", unsafe_allow_html=True)

    # ── Timeline annuelle ──────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📊 Timeline annuelle")
    all_evts = get_evenements(prop_c if prop_c != 0 else None, int(annee_c))
    if all_evts:
        try:
            import plotly.express as px
            df_evts = pd.DataFrame([{
                "Événement": e["nom"],
                "Début":     pd.to_datetime(e["date_debut"]),
                "Fin":       pd.to_datetime(e["date_fin"]) + timedelta(days=1),
                "Type":      TYPE_LABELS.get(e.get("type",""), "📅"),
                "Impact":    IMPACT_LABELS.get(e.get("impact_tarif",""), ""),
                "Couleur":   e.get("couleur") or COULEURS_TYPE.get(e.get("type",""), "#FF6B35"),
            } for e in all_evts])
            fig = px.timeline(
                df_evts, x_start="Début", x_end="Fin",
                y="Événement", color="Type",
                hover_data=["Impact"],
                title=f"Événements {annee_c}",
            )
            fig.update_layout(height=max(300, len(all_evts) * 35),
                               showlegend=True,
                               xaxis_title="",
                               margin=dict(l=0, r=0, t=40, b=0))
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Timeline non disponible : {e}")
