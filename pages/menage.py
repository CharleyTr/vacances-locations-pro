"""
Page Menage - Planning des interventions + Checklist par propriete.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database.proprietes_repo import fetch_all as _fa_props
from services.auth_service import is_unlocked
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_dict
from services.proprietes_service import get_proprietes_autorises, filter_df, get_propriete_selectionnee
from database.checklist_repo import get_items, save_item, delete_item, get_done, set_done
from database.supabase_client import is_connected

CATEGORIES_DEFAUT = [
    ("Chambres",       ["Changer les draps", "Taies d'oreillers", "Housses de couette", "Aspirer tapis", "Dépoussiérer"]),
    ("Salle de bain",  ["Nettoyer douche/baignoire", "Nettoyer WC", "Lavabo et robinets", "Miroirs", "Changer serviettes", "Réapprovisionner savon/shampoing"]),
    ("Cuisine",        ["Nettoyer plan de travail", "Nettoyer four/micro-ondes", "Nettoyer réfrigérateur", "Vaisselle rangée", "Vider poubelles"]),
    ("Salon/Séjour",   ["Aspirer/balayer", "Dépoussiérer meubles", "Nettoyer vitres", "Coussins arrangés"]),
    ("Général",        ["Vérifier ampoules", "Relever compteurs", "Laisser livret accueil", "Vérifier clés/badges", "Inventaire équipements"]),
]

def show():
    st.title("🧹 Planning Ménage")

    tab_planning, tab_checklist, tab_modele = st.tabs([
        "📅 Planning", "✅ Checklist", "⚙️ Configurer checklist"
    ])

    with tab_planning:
        _show_planning()

    with tab_checklist:
        _show_checklist()

    with tab_modele:
        _show_modele()


# ─────────────────────────────────────────────────────────────────────────────
# PLANNING
# ─────────────────────────────────────────────────────────────────────────────

def _show_planning():
    df_all = load_reservations()
    _auth = [p["id"] for p in _fa_props() if not p.get("mot_de_passe") or is_unlocked(p["id"])]
    df_all = df_all[df_all["propriete_id"].isin(_auth)]
    df = filter_df(df_all)
    if df.empty:
        st.info("Aucune réservation disponible.")
        return

    today = pd.Timestamp(date.today())
    in_7  = today + timedelta(days=7)
    in_30 = today + timedelta(days=30)

    planning = _build_planning(df, today)
    if planning.empty:
        st.info("Aucun ménage planifié.")
        return

    urgents = planning[planning["date_menage"] <= in_7]
    a_venir = planning[(planning["date_menage"] > in_7) & (planning["date_menage"] <= in_30)]
    passes  = planning[planning["date_menage"] < today]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Cette semaine", len(urgents))
    c2.metric("🟡 Dans 30 jours", len(a_venir))
    c3.metric("📋 Total à venir", len(planning[planning["date_menage"] >= today]))
    c4.metric("✅ Passés",        len(passes))

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        periode = st.selectbox("Période", [
            "Cette semaine", "Ce mois", "Tous à venir", "Historique complet"
        ], key="menage_periode")
    with col2:
        _props = get_proprietes_autorises()
        prop_filter = st.multiselect(
            "Propriété",
            options=list(_props.keys()),
            default=list(_props.keys()),
            format_func=lambda x: _props.get(x, f"Propriété {x}"),
            key="menage_prop_filter"
        )

    df_plan = planning.copy()
    if prop_filter:
        df_plan = df_plan[df_plan["propriete_id"].isin(prop_filter)]
    if periode == "Cette semaine":
        df_plan = df_plan[(df_plan["date_menage"] >= today) & (df_plan["date_menage"] <= in_7)]
    elif periode == "Ce mois":
        df_plan = df_plan[(df_plan["date_menage"] >= today) & (df_plan["date_menage"] <= in_30)]
    elif periode == "Tous à venir":
        df_plan = df_plan[df_plan["date_menage"] >= today]

    df_plan = df_plan.sort_values("date_menage")
    if df_plan.empty:
        st.info("Aucun ménage pour cette période.")
        return

    st.subheader(f"📋 {len(df_plan)} intervention(s)")

    for prop_id in sorted(df_plan["propriete_id"].unique()):
        nom_prop = get_proprietes_autorises().get(int(prop_id), f"Propriété {prop_id}")
        df_prop  = df_plan[df_plan["propriete_id"] == prop_id]

        with st.expander(f"🏠 {nom_prop} — {len(df_prop)} ménage(s)", expanded=True):
            for _, row in df_prop.iterrows():
                date_m = row["date_menage"]
                jours  = (date_m - today).days

                if jours < 0:     badge, color = "✅ Passé",          "#E8F5E9"
                elif jours == 0:  badge, color = "🔴 Aujourd'hui !",  "#FFEBEE"
                elif jours <= 2:  badge, color = f"🔴 Dans {jours}j", "#FFEBEE"
                elif jours <= 7:  badge, color = f"🟡 Dans {jours}j", "#FFFDE7"
                else:             badge, color = f"🟢 Dans {jours}j", "#F1F8E9"

                prochain  = row.get("prochain_client", "-")
                duree     = row.get("nuitees_suivantes", "")
                duree_txt = f" ({duree} nuits)" if duree else ""

                col_info, col_btn = st.columns([8, 2])
                with col_info:
                    st.markdown(
                        f"""<div style='background:{color};padding:10px 14px;
                        border-radius:8px;margin-bottom:8px'>
                        <b>{date_m.strftime('%A %d %B %Y').capitalize()}</b> &nbsp;-&nbsp; {badge}<br>
                        <small>🛏 Départ : <b>{row['nom_client']}</b> &nbsp;|&nbsp;
                        ➡ Arrivée : <b>{prochain}{duree_txt}</b></small>
                        </div>""", unsafe_allow_html=True
                    )
                with col_btn:
                    date_str = date_m.strftime("%Y-%m-%d")
                    if st.button("✅ Checklist", key=f"ck_{prop_id}_{date_str}",
                                 help="Ouvrir la checklist pour ce ménage"):
                        st.session_state["checklist_prop_id"]  = int(prop_id)
                        st.session_state["checklist_date"]     = date_str
                        st.session_state["active_tab_menage"]  = 1
                        st.rerun()

    st.divider()
    export = df_plan.copy()
    export["date_menage"] = export["date_menage"].dt.strftime("%d/%m/%Y")
    export["propriete"] = export["propriete_id"].map(
        lambda x: get_proprietes_autorises().get(int(x), f"Propriété {x}")
    )
    csv = export[["date_menage","propriete","nom_client","prochain_client"]]\
        .to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exporter planning ménage", csv,
                       file_name="planning_menage.csv", mime="text/csv")


# ─────────────────────────────────────────────────────────────────────────────
# CHECKLIST
# ─────────────────────────────────────────────────────────────────────────────

def _show_checklist():
    props = get_proprietes_dict()
    if not props:
        st.info("Aucune propriété configurée.")
        return

    col1, col2 = st.columns(2)
    with col1:
        default_prop = st.session_state.get("checklist_prop_id", list(props.keys())[0])
        prop_id = st.selectbox(
            "Propriété", options=list(props.keys()),
            format_func=lambda x: props[x],
            index=list(props.keys()).index(default_prop) if default_prop in props else 0,
            key="ck_prop"
        )
    with col2:
        default_date = st.session_state.get("checklist_date", date.today().isoformat())
        date_menage  = st.date_input("Date du ménage",
                                      value=date.fromisoformat(default_date),
                                      key="ck_date")

    items = get_items(prop_id)
    if not items:
        st.info("Aucun item de checklist. Configurez-les dans l'onglet ⚙️.")
        return

    # Charger état depuis Supabase
    date_str = date_menage.isoformat()
    if is_connected():
        done_map = get_done(prop_id, date_str)
    else:
        if "ck_state" not in st.session_state:
            st.session_state["ck_state"] = {}
        done_map = st.session_state["ck_state"].get(f"{prop_id}_{date_str}", {})

    # Grouper par catégorie
    categories = {}
    for item in items:
        cat = item.get("categorie", "Général")
        categories.setdefault(cat, []).append(item)

    total = len(items)
    fait  = sum(1 for item in items if done_map.get(item["id"], False))

    # Barre de progression
    pct = fait / total if total > 0 else 0
    couleur_prog = "#4CAF50" if pct == 1 else "#FF9800" if pct > 0.5 else "#2196F3"
    st.markdown(
        f"""<div style='margin-bottom:12px'>
        <div style='display:flex;justify-content:space-between'>
          <b>Progression ménage</b> <b>{fait}/{total} items ({pct*100:.0f}%)</b>
        </div>
        <div style='background:#E0E0E0;border-radius:8px;height:14px;margin-top:6px'>
          <div style='background:{couleur_prog};width:{pct*100:.0f}%;height:14px;border-radius:8px'></div>
        </div></div>""", unsafe_allow_html=True
    )

    if pct == 1:
        st.success("🎉 Ménage terminé ! Toutes les tâches sont complétées.")

    # Affichage par catégorie
    for cat, cat_items in categories.items():
        nb_cat  = len(cat_items)
        fait_cat = sum(1 for i in cat_items if done_map.get(i["id"], False))
        with st.expander(f"{'✅' if fait_cat == nb_cat else '🔲'} **{cat}** — {fait_cat}/{nb_cat}",
                         expanded=fait_cat < nb_cat):
            for item in cat_items:
                item_id  = item["id"]
                is_done  = done_map.get(item_id, False)
                new_done = st.checkbox(
                    item["item"],
                    value=is_done,
                    key=f"ck_{prop_id}_{date_str}_{item_id}"
                )
                if new_done != is_done:
                    if is_connected():
                        set_done(prop_id, date_str, item_id, new_done)
                    else:
                        key = f"{prop_id}_{date_str}"
                        if key not in st.session_state.get("ck_state", {}):
                            st.session_state.setdefault("ck_state", {})[key] = {}
                        st.session_state["ck_state"][key][item_id] = new_done
                    done_map[item_id] = new_done

    # Bouton tout cocher
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("☑️ Tout cocher", use_container_width=True):
            for item in items:
                if is_connected():
                    set_done(prop_id, date_str, item["id"], True)
            st.rerun()
    with col_b:
        if st.button("⬜ Tout décocher", use_container_width=True):
            for item in items:
                if is_connected():
                    set_done(prop_id, date_str, item["id"], False)
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION MODÈLE CHECKLIST
# ─────────────────────────────────────────────────────────────────────────────

def _show_modele():
    props = get_proprietes_dict()
    if not props:
        st.info("Aucune propriété configurée.")
        return

    prop_id = st.selectbox(
        "Propriété", options=list(props.keys()),
        format_func=lambda x: props[x], key="ck_mod_prop"
    )

    items = get_items(prop_id)

    if not items and is_connected():
        if st.button("📋 Initialiser checklist par défaut", type="secondary"):
            ordre = 0
            for cat, cat_items in CATEGORIES_DEFAUT:
                for item_txt in cat_items:
                    save_item({
                        "propriete_id": prop_id,
                        "categorie": cat,
                        "item": item_txt,
                        "ordre": ordre
                    })
                    ordre += 1
            st.success("✅ Checklist initialisée !")
            st.rerun()
        return

    # Afficher items existants par catégorie
    categories = {}
    for item in items:
        cat = item.get("categorie", "Général")
        categories.setdefault(cat, []).append(item)

    for cat, cat_items in categories.items():
        with st.expander(f"**{cat}** ({len(cat_items)} items)"):
            for item in cat_items:
                col1, col2 = st.columns([8, 1])
                col1.write(f"• {item['item']}")
                if col2.button("🗑️", key=f"del_item_{item['id']}"):
                    delete_item(item["id"])
                    st.rerun()

    st.divider()

    # Ajouter un item
    with st.expander("➕ Ajouter un item", expanded=False):
        cats_existantes = list(set(i.get("categorie","Général") for i in items))
        cats_all = sorted(set(cats_existantes + [c for c, _ in CATEGORIES_DEFAUT]))

        c1, c2 = st.columns(2)
        with c1:
            cat_choix = st.selectbox("Catégorie", cats_all + ["+ Nouvelle catégorie"], key="new_cat")
        with c2:
            if cat_choix == "+ Nouvelle catégorie":
                cat_choix = st.text_input("Nom de la nouvelle catégorie", key="new_cat_nom")

        new_item = st.text_input("Description de la tâche", key="new_item_txt")

        if st.button("➕ Ajouter", type="primary"):
            if new_item and cat_choix:
                save_item({
                    "propriete_id": prop_id,
                    "categorie": cat_choix,
                    "item": new_item,
                    "ordre": len(items)
                })
                st.success(f"✅ '{new_item}' ajouté !")
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# PLANNING BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_planning(df: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for prop_id in df["propriete_id"].unique():
        df_prop = df[df["propriete_id"] == prop_id].sort_values("date_arrivee").reset_index(drop=True)
        for i, row in df_prop.iterrows():
            prochain_client = "-"
            nuitees_suiv    = None
            if i + 1 < len(df_prop):
                nr = df_prop.iloc[i + 1]
                prochain_client = nr["nom_client"]
                nuitees_suiv    = int(nr.get("nuitees", 0) or 0)
            rows.append({
                "propriete_id":      prop_id,
                "date_menage":       pd.Timestamp(row["date_depart"]),
                "nom_client":        row["nom_client"],
                "prochain_client":   prochain_client,
                "nuitees_suivantes": nuitees_suiv,
            })
    return pd.DataFrame(rows) if rows else pd.DataFrame()
