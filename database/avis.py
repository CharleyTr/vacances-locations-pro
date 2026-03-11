"""
Page Livre d'or - Collecte et affichage des avis clients.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from database.avis_repo import get_avis, save_avis, delete_avis
from services.reservation_service import load_reservations
from services.proprietes_service import (
    get_proprietes_dict, get_propriete_selectionnee, get_label, filter_df
)
from database.supabase_client import is_connected

ETOILES = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}


def show():
    st.title("⭐ Livre d'or")

    prop_id  = get_propriete_selectionnee()
    prop_nom = get_label(prop_id)
    props    = get_proprietes_dict()

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise pour le livre d'or.")

    tab_livret, tab_ajout, tab_stats = st.tabs([
        "📖 Livre d'or",
        "✍️ Ajouter un avis",
        "📊 Statistiques",
    ])

    with tab_livret:
        _show_livret(prop_id, props)

    with tab_ajout:
        _show_ajout(prop_id, prop_nom, props)

    with tab_stats:
        _show_stats(prop_id, props)


# ─────────────────────────────────────────────────────────────────────────────
# LIVRE D'OR
# ─────────────────────────────────────────────────────────────────────────────

def _show_livret(prop_id: int, props: dict):
    avis_list = get_avis(prop_id if prop_id != 0 else None)

    if not avis_list:
        st.info("Aucun avis enregistré pour le moment.")
        if not is_connected():
            st.caption("Connectez Supabase pour enregistrer des avis.")
        return

    # Filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        filtre_note = st.selectbox("Note minimum", [1, 2, 3, 4, 5], index=0, key="av_note")
    with col2:
        filtre_plat = st.selectbox("Plateforme", ["Toutes"] +
                                   sorted(set(a.get("plateforme", "") or "" for a in avis_list)),
                                   key="av_plat")
    with col3:
        filtre_prop = st.selectbox("Propriété", ["Toutes"] + list(props.values()),
                                   key="av_prop") if len(props) > 1 else None

    # KPIs rapides
    notes = [a["note"] for a in avis_list if a.get("note")]
    if notes:
        c1, c2, c3 = st.columns(3)
        c1.metric("⭐ Note moyenne",  f"{sum(notes)/len(notes):.1f} / 5")
        c2.metric("📝 Total avis",    len(avis_list))
        c3.metric("🏆 5 étoiles",     sum(1 for n in notes if n == 5))
    st.divider()

    # Affichage avis
    for a in avis_list:
        note = a.get("note", 0)
        if note < filtre_note:
            continue
        if filtre_plat != "Toutes" and a.get("plateforme") != filtre_plat:
            continue

        _render_avis_card(a, props)


def _render_avis_card(a: dict, props: dict):
    note = a.get("note", 0)
    etoiles = ETOILES.get(note, "")
    prop_nom = props.get(a.get("propriete_id"), "")
    date_str = a.get("date_sejour", "")[:10] if a.get("date_sejour") else ""

    col_card, col_actions = st.columns([10, 1])
    with col_card:
        st.markdown(f"""
<div style='background:#FAFAFA;border-left:4px solid #FFD700;
            padding:14px 18px;border-radius:8px;margin-bottom:12px'>
  <div style='display:flex;justify-content:space-between;align-items:center'>
    <span style='font-weight:bold;font-size:16px'>{a.get('nom_client','Client')} &nbsp; {etoiles}</span>
    <span style='color:#9E9E9E;font-size:13px'>
      {date_str} &nbsp;|&nbsp; {a.get('plateforme','')} &nbsp;|&nbsp; {prop_nom}
    </span>
  </div>
  <div style='margin-top:8px;font-size:15px;color:#212121'>
    {a.get('commentaire','') or '<em style="color:#9E9E9E">Pas de commentaire</em>'}
  </div>
  {'<div style="margin-top:8px;background:#E3F2FD;padding:8px 12px;border-radius:6px;font-size:13px"><b>Réponse de l\'hôte :</b> ' + a.get('reponse_hote','') + '</div>' if a.get('reponse_hote') else ''}
</div>""", unsafe_allow_html=True)

    with col_actions:
        if st.button("🗑️", key=f"del_avis_{a['id']}", help="Supprimer"):
            delete_avis(a["id"])
            st.rerun()

    # Réponse hôte
    if not a.get("reponse_hote"):
        with st.expander(f"✍️ Répondre à {a.get('nom_client','')}"):
            rep = st.text_area("Votre réponse", key=f"rep_{a['id']}")
            if st.button("Publier la réponse", key=f"pub_{a['id']}"):
                save_avis({**a, "reponse_hote": rep})
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# AJOUT
# ─────────────────────────────────────────────────────────────────────────────

def _show_ajout(prop_id: int, prop_nom: str, props: dict):
    st.subheader("✍️ Enregistrer un avis client")
    st.markdown("Saisissez manuellement les avis reçus sur les plateformes.")

    # Sélection propriété
    if len(props) > 1:
        prop_sel = st.selectbox("Propriété", options=list(props.keys()),
                                format_func=lambda x: props[x],
                                index=list(props.keys()).index(prop_id) if prop_id in props else 0,
                                key="av_prop_sel")
    else:
        prop_sel = prop_id

    # Chercher réservations pour auto-complétion
    df_res = load_reservations()
    df_prop = df_res[df_res["propriete_id"] == prop_sel] if prop_sel and not df_res.empty else df_res
    res_options = {}
    if not df_prop.empty:
        for _, r in df_prop.sort_values("date_arrivee", ascending=False).head(30).iterrows():
            arr = str(r.get("date_arrivee",""))[:10]
            label = f"{r.get('nom_client','?')} — {arr}"
            res_options[label] = r

    c1, c2 = st.columns(2)
    with c1:
        choix_res = st.selectbox("Lier à une réservation (optionnel)",
                                  ["— Aucune —"] + list(res_options.keys()),
                                  key="av_res")
        nom_client = st.text_input("Nom du client", key="av_nom",
                                    value=res_options[choix_res]["nom_client"]
                                    if choix_res != "— Aucune —" else "")
    with c2:
        note = st.select_slider("Note", options=[1,2,3,4,5], value=5,
                                 format_func=lambda x: ETOILES[x], key="av_note_val")
        plateforme = st.selectbox("Plateforme", ["Airbnb","Booking","Abritel","Direct","Autre"],
                                   key="av_plat_sel")

    c3, c4 = st.columns(2)
    with c3:
        date_sejour = st.date_input("Date du séjour", value=date.today(), key="av_date")
    with c4:
        visible = st.checkbox("Visible dans le livre d'or", value=True, key="av_visible")

    commentaire = st.text_area("Commentaire du client", height=120, key="av_comment",
                                placeholder="Très beau appartement, vue magnifique...")
    reponse = st.text_area("Votre réponse (optionnel)", height=80, key="av_rep",
                            placeholder="Merci beaucoup pour votre séjour...")

    if st.button("⭐ Enregistrer l'avis", type="primary", use_container_width=True):
        if not nom_client:
            st.error("Le nom du client est requis.")
        elif not is_connected():
            st.error("Supabase non connecté.")
        else:
            data = {
                "propriete_id":   prop_sel,
                "nom_client":     nom_client,
                "note":           note,
                "commentaire":    commentaire,
                "plateforme":     plateforme,
                "date_sejour":    date_sejour.isoformat(),
                "reponse_hote":   reponse or None,
                "visible":        visible,
            }
            if choix_res != "— Aucune —":
                data["reservation_id"] = int(res_options[choix_res].get("id", 0) or 0)

            if save_avis(data):
                st.success(f"✅ Avis de {nom_client} enregistré ! {ETOILES[note]}")
                st.balloons()
            else:
                st.error("Erreur lors de l'enregistrement.")


# ─────────────────────────────────────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────────────────────────────────────

def _show_stats(prop_id: int, props: dict):
    st.subheader("📊 Statistiques des avis")

    avis_list = get_avis(prop_id if prop_id != 0 else None)
    if not avis_list:
        st.info("Aucun avis disponible.")
        return

    df = pd.DataFrame(avis_list)
    df["note"] = pd.to_numeric(df["note"], errors="coerce")
    df_valid = df.dropna(subset=["note"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⭐ Note moyenne",  f"{df_valid['note'].mean():.1f}")
    c2.metric("📝 Total",         len(df_valid))
    c3.metric("🏆 5 étoiles",     int((df_valid["note"] == 5).sum()))
    c4.metric("👎 1-2 étoiles",   int((df_valid["note"] <= 2).sum()))

    col1, col2 = st.columns(2)

    with col1:
        # Distribution notes
        dist = df_valid["note"].value_counts().sort_index().reset_index()
        dist.columns = ["Note", "Nombre"]
        dist["Etoiles"] = dist["Note"].map(ETOILES)
        fig = px.bar(dist, x="Etoiles", y="Nombre", title="Distribution des notes",
                     color="Nombre", color_continuous_scale="Reds")
        fig.update_layout(height=280, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Par plateforme
        if "plateforme" in df_valid.columns:
            plat = df_valid.groupby("plateforme")["note"].mean().reset_index()
            plat.columns = ["Plateforme", "Note moyenne"]
            fig2 = px.bar(plat, x="Plateforme", y="Note moyenne", title="Note par plateforme",
                          color="Note moyenne", color_continuous_scale="Greens",
                          range_y=[0, 5])
            fig2.update_layout(height=280, showlegend=False, coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)

    # Comparaison propriétés
    if len(props) > 1:
        st.divider()
        st.markdown("**Comparaison par propriété :**")
        cols = st.columns(len(props))
        for i, (pid, pnom) in enumerate(props.items()):
            av = get_avis(pid)
            notes_p = [a["note"] for a in av if a.get("note")]
            with cols[i]:
                st.markdown(f"**🏠 {pnom}**")
                if notes_p:
                    moy = sum(notes_p)/len(notes_p)
                    st.metric("Note", f"{moy:.1f} ⭐")
                    st.caption(f"{len(notes_p)} avis")
                else:
                    st.caption("Aucun avis")
