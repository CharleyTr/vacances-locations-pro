"""
Page Tarifs - Prix par saison et calculateur de prix.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from services.tarif_service import (
    get_tarifs, save_tarif, delete_tarif, calcul_prix, TARIFS_DEFAUT
)
from services.proprietes_service import (
    get_proprietes_dict, get_propriete_selectionnee, get_label, filter_df
)
from services.reservation_service import load_reservations
from database.supabase_client import is_connected

COULEURS_SAISON = [
    "#90CAF9", "#FFF176", "#FFAB91", "#CE93D8",
    "#EF9A9A", "#A5D6A7", "#80DEEA", "#FFCC80",
]


def show():
    st.title("💶 Tarifs & Simulateur de prix")

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise pour enregistrer les tarifs.")

    prop_id  = get_propriete_selectionnee()
    prop_nom = get_label(prop_id)
    props    = get_proprietes_dict()

    if prop_id == 0 and len(props) > 0:
        st.info("Sélectionnez une propriété dans la sidebar pour gérer ses tarifs.")
        prop_id = list(props.keys())[0]
        prop_nom = props[prop_id]

    tab_config, tab_calc, tab_visu = st.tabs([
        "⚙️ Configuration des saisons",
        "🧮 Simulateur de prix",
        "📊 Visualisation tarifaire",
    ])

    with tab_config:
        _show_config(prop_id, prop_nom, props)

    with tab_calc:
        _show_calculateur(prop_id, prop_nom, props)

    with tab_visu:
        _show_visualisation(prop_id, prop_nom, props)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG SAISONS
# ─────────────────────────────────────────────────────────────────────────────

def _show_config(prop_id: int, prop_nom: str, props: dict):
    st.subheader(f"⚙️ Tarifs — {prop_nom}")

    tarifs = get_tarifs(prop_id)

    # ── Initialiser avec tarifs par défaut ───────────────────────────────
    if not tarifs and is_connected():
        if st.button("📋 Initialiser avec les tarifs par défaut", type="secondary"):
            annee = date.today().year
            defaults = [
                {"propriete_id": prop_id, "nom": "Basse saison",
                 "date_debut": f"{annee}-01-01", "date_fin": f"{annee}-06-14",
                 "prix_nuit": 80, "prix_menage": 60, "couleur": "#90CAF9"},
                {"propriete_id": prop_id, "nom": "Haute saison",
                 "date_debut": f"{annee}-06-15", "date_fin": f"{annee}-08-31",
                 "prix_nuit": 140, "prix_menage": 80, "couleur": "#FFAB91"},
                {"propriete_id": prop_id, "nom": "Vacances scolaires",
                 "date_debut": f"{annee}-07-01", "date_fin": f"{annee}-08-31",
                 "prix_nuit": 120, "prix_menage": 75, "couleur": "#CE93D8"},
                {"propriete_id": prop_id, "nom": "Basse saison (automne)",
                 "date_debut": f"{annee}-09-01", "date_fin": f"{annee}-12-23",
                 "prix_nuit": 80, "prix_menage": 60, "couleur": "#90CAF9"},
                {"propriete_id": prop_id, "nom": "Noël / Nouvel An",
                 "date_debut": f"{annee}-12-24", "date_fin": f"{annee+1}-01-06",
                 "prix_nuit": 160, "prix_menage": 90, "couleur": "#EF9A9A"},
            ]
            for d in defaults:
                save_tarif(d)
            st.success("✅ Tarifs initialisés !")
            st.rerun()

    # ── Affichage tarifs existants ────────────────────────────────────────
    if tarifs:
        st.markdown(f"**{len(tarifs)} période(s) configurée(s)**")
        for t in tarifs:
            col1, col2, col3, col4, col5, col6 = st.columns([3, 2, 2, 1.5, 1.5, 0.8])
            col1.markdown(
                f"<span style='background:{t.get('couleur','#90CAF9')};padding:3px 10px;"
                f"border-radius:12px;font-weight:bold;font-size:13px'>{t['nom']}</span>",
                unsafe_allow_html=True
            )
            col2.write(f"📅 {t['date_debut']} → {t['date_fin']}")
            col3.write(f"🌙 **{t['prix_nuit']:.0f} €**/nuit")
            col4.write(f"🧹 {t['prix_menage']:.0f} €")
            col5.write("")
            if col6.button("🗑️", key=f"del_tarif_{t['id']}", help="Supprimer"):
                delete_tarif(t["id"])
                st.rerun()

        st.divider()

    # ── Formulaire ajout ──────────────────────────────────────────────────
    with st.expander("➕ Ajouter une période tarifaire", expanded=not tarifs):
        annee_ref = date.today().year
        c1, c2 = st.columns(2)
        with c1:
            nom = st.text_input("Nom de la période", placeholder="Ex: Haute saison été 2026", key="t_nom")
            prix_nuit = st.number_input("Prix / nuit (€)", min_value=0.0, value=100.0, step=5.0, key="t_prix")
        with c2:
            prix_menage = st.number_input("Frais ménage (€)", min_value=0.0, value=70.0, step=5.0, key="t_menage")
            couleur = st.selectbox("Couleur", COULEURS_SAISON, key="t_couleur",
                                   format_func=lambda c: f"●  {c}")

        c3, c4 = st.columns(2)
        with c3:
            date_debut = st.date_input("Date début", value=date(annee_ref, 6, 15), key="t_debut")
        with c4:
            date_fin   = st.date_input("Date fin",   value=date(annee_ref, 8, 31), key="t_fin")

        if st.button("💾 Enregistrer la période", type="primary", use_container_width=True):
            if not nom:
                st.error("Le nom est requis.")
            elif date_debut > date_fin:
                st.error("La date de début doit être avant la date de fin.")
            elif not is_connected():
                st.error("Supabase non connecté.")
            else:
                ok = save_tarif({
                    "propriete_id": prop_id,
                    "nom": nom,
                    "date_debut": date_debut.isoformat(),
                    "date_fin": date_fin.isoformat(),
                    "prix_nuit": prix_nuit,
                    "prix_menage": prix_menage,
                    "couleur": couleur,
                })
                if ok:
                    st.success(f"✅ Période '{nom}' enregistrée !")
                    st.rerun()
                else:
                    st.error("Erreur lors de l'enregistrement.")


# ─────────────────────────────────────────────────────────────────────────────
# SIMULATEUR
# ─────────────────────────────────────────────────────────────────────────────

def _show_calculateur(prop_id: int, prop_nom: str, props: dict):
    st.subheader("🧮 Simulateur de prix")
    st.markdown("Calculez le prix d'un séjour selon les tarifs configurés.")

    # Sélection propriété si "toutes"
    if len(props) > 1:
        prop_calc = st.selectbox(
            "Propriété",
            options=list(props.keys()),
            format_func=lambda x: props[x],
            index=list(props.keys()).index(prop_id) if prop_id in props else 0,
            key="calc_prop"
        )
    else:
        prop_calc = prop_id

    c1, c2 = st.columns(2)
    with c1:
        arr = st.date_input("Date d'arrivée",  value=date.today(), key="calc_arr")
    with c2:
        dep = st.date_input("Date de départ",  value=date.today() + timedelta(days=7), key="calc_dep")

    if arr >= dep:
        st.warning("La date de départ doit être après l'arrivée.")
        return

    result = calcul_prix(arr, dep, prop_calc)

    if "erreur" in result:
        st.warning(f"⚠️ {result['erreur']} — Configurez d'abord vos tarifs dans l'onglet Configuration.")
        return

    st.divider()

    # KPIs résultat
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌙 Nuitées",         result["nuitees"])
    c2.metric("🌙 Prix moyen/nuit", f"{result['prix_nuit_moy']:.0f} €")
    c3.metric("🧹 Frais ménage",    f"{result['frais_menage']:.0f} €")
    c4.metric("💶 Total TTC",       f"{result['prix_ttc']:.0f} €",
              delta=f"dont {result['prix_total']:.0f} € loyer")

    # Détail par saison
    if result["detail"]:
        st.markdown("**Décomposition par saison :**")
        for d in result["detail"]:
            col1, col2, col3 = st.columns([3, 2, 2])
            col1.markdown(
                f"<span style='background:{d['couleur']};padding:3px 10px;"
                f"border-radius:12px;font-weight:bold'>{d['saison']}</span>",
                unsafe_allow_html=True
            )
            col2.write(f"🌙 {d['nuits']} nuit(s) × {d['prix_nuit']:.0f} €")
            col3.write(f"= **{d['nuits'] * d['prix_nuit']:.0f} €**")

    # Bouton pré-remplir réservation
    st.divider()
    st.info(
        f"💡 Pour créer une réservation avec ces paramètres, allez dans **📋 Réservations** "
        f"et utilisez le formulaire d'ajout."
    )


# ─────────────────────────────────────────────────────────────────────────────
# VISUALISATION
# ─────────────────────────────────────────────────────────────────────────────

def _show_visualisation(prop_id: int, prop_nom: str, props: dict):
    st.subheader("📊 Calendrier tarifaire")

    annee = st.selectbox("Année", [date.today().year, date.today().year + 1], key="visu_annee")

    tarifs = get_tarifs(prop_id)
    if not tarifs:
        st.info("Aucun tarif configuré pour cette propriété.")
        return

    # Graphique Gantt des périodes tarifaires
    rows = []
    for t in tarifs:
        rows.append({
            "Saison":    t["nom"],
            "Début":     pd.Timestamp(t["date_debut"]),
            "Fin":       pd.Timestamp(t["date_fin"]) + pd.Timedelta(days=1),
            "Prix/nuit": f"{t['prix_nuit']:.0f} €/nuit",
            "Couleur":   t.get("couleur", "#90CAF9"),
        })

    df_t = pd.DataFrame(rows)
    fig = px.timeline(
        df_t, x_start="Début", x_end="Fin", y="Saison",
        color="Saison",
        hover_data=["Prix/nuit"],
        color_discrete_sequence=df_t["Couleur"].tolist(),
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=300, showlegend=False, margin=dict(t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    # Tableau récap ÉDITABLE
    st.markdown("**Récapitulatif des tarifs — modifiez directement les montants :**")
    df_edit = pd.DataFrame([{
        "_id":        t["id"],
        "Période":    t["nom"],
        "Début":      t["date_debut"],
        "Fin":        t["date_fin"],
        "Prix/nuit €": float(t["prix_nuit"]),
        "Ménage €":   float(t["prix_menage"]),
    } for t in tarifs])

    edited = st.data_editor(
        df_edit,
        use_container_width=True,
        hide_index=True,
        column_config={
            "_id":         st.column_config.Column(disabled=True, width="small"),
            "Période":     st.column_config.TextColumn("Période", disabled=True),
            "Début":       st.column_config.TextColumn("Début", disabled=True),
            "Fin":         st.column_config.TextColumn("Fin", disabled=True),
            "Prix/nuit €": st.column_config.NumberColumn(
                "Prix/nuit €", min_value=0, max_value=9999, step=1, format="%.0f €"
            ),
            "Ménage €":    st.column_config.NumberColumn(
                "Ménage €", min_value=0, max_value=999, step=1, format="%.0f €"
            ),
        },
        key="tarif_editor"
    )

    if st.button("💾 Enregistrer les modifications", type="primary", key="save_tarifs_edit"):
        nb_ok = 0
        for _, row in edited.iterrows():
            ok = save_tarif({
                "id":          int(row["_id"]),
                "propriete_id": prop_id,
                "nom":         row["Période"],
                "date_debut":  row["Début"],
                "date_fin":    row["Fin"],
                "prix_nuit":   float(row["Prix/nuit €"]),
                "prix_menage": float(row["Ménage €"]),
            })
            if ok:
                nb_ok += 1
        if nb_ok > 0:
            st.success(f"✅ {nb_ok} tarif(s) mis à jour !")
            st.rerun()
        else:
            st.error("Erreur lors de la sauvegarde.")

    # Comparaison propriétés
    if len(props) > 1:
        st.divider()
        st.markdown("**Comparaison entre propriétés :**")
        cols = st.columns(len(props))
        for i, (pid, pnom) in enumerate(props.items()):
            t_list = get_tarifs(pid)
            with cols[i]:
                st.markdown(f"**🏠 {pnom}**")
                if not t_list:
                    st.caption("Aucun tarif")
                else:
                    prix = [t["prix_nuit"] for t in t_list]
                    st.metric("Prix min", f"{min(prix):.0f} €/nuit")
                    st.metric("Prix max", f"{max(prix):.0f} €/nuit")
                    st.metric("Saisons",  len(t_list))
