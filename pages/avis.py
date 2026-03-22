"""
Page Livre d'or - Notes par critere + questionnaire envoyable aux clients.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import secrets
from datetime import date, datetime, timezone, timedelta
from database.avis_repo import get_avis, save_avis, delete_avis, CRITERES
from database.proprietes_repo import fetch_all as _fa_props
from services.auth_service import is_unlocked
from services.reservation_service import load_reservations
from services.proprietes_service import (
    get_proprietes_dict, get_propriete_selectionnee, get_label, filter_df
)
from database.supabase_client import is_connected
from config import _get

ETOILES = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}
CRITERES_LABELS = {k: v for k, v in CRITERES}

# URL de base de l'app Streamlit Cloud (configurable dans secrets)
def _app_url() -> str:
    url = _get("APP_URL", "")
    if not url:
        try:
            url = st.secrets.get("APP_URL", "")
        except Exception:
            url = ""
    return url.rstrip("/")


def show():
    st.title("⭐ Livre d'or")

    prop_id  = get_propriete_selectionnee()
    prop_nom = get_label(prop_id)
    props    = get_proprietes_dict()

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise pour le livre d'or.")

    tab_livret, tab_envoyer, tab_ajout, tab_stats = st.tabs([
        "📖 Livre d'or",
        "📨 Envoyer questionnaire",
        "✍️ Saisir manuellement",
        "📊 Statistiques",
    ])

    with tab_livret:
        _show_livret(prop_id, props)

    with tab_envoyer:
        _show_envoyer(prop_id, prop_nom, props)

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
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtre_note = st.selectbox("Note minimum", [0, 1, 2, 3, 4, 5],
                                   index=0, key="av_note",
                                   format_func=lambda x: "Tous" if x == 0 else f"{x}★ et +")
    with col2:
        filtre_plat = st.selectbox(
            "Plateforme",
            ["Toutes"] + sorted(set(a.get("plateforme", "") or "" for a in avis_list if a.get("plateforme"))),
            key="av_plat"
        )
    with col3:
        tri = st.selectbox("Trier par", ["Plus récent", "Meilleure note", "Moins bonne note"], key="av_tri")
    with col4:
        afficher_attente = st.checkbox("Afficher en attente", value=True, key="av_attente")

    # KPIs
    notes_val = [a["note"] for a in avis_list if a.get("note")]
    if notes_val:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("⭐ Note moyenne", f"{sum(notes_val)/len(notes_val):.1f} / 5")
        c2.metric("📝 Total avis",   len(avis_list))
        c3.metric("🏆 5 étoiles",    sum(1 for n in notes_val if n == 5))
        attente = sum(1 for a in avis_list if not a.get("token_used") and a.get("token"))
        c4.metric("⏳ En attente",   attente)

    # Radar moyen des critères
    moyennes = {}
    for col_key, label in CRITERES:
        vals = [a[col_key] for a in avis_list if a.get(col_key)]
        if vals:
            moyennes[label] = round(sum(vals) / len(vals), 1)

    if moyennes:
        fig_radar = go.Figure(go.Scatterpolar(
            r=list(moyennes.values()) + [list(moyennes.values())[0]],
            theta=list(moyennes.keys()) + [list(moyennes.keys())[0]],
            fill="toself", fillcolor="rgba(21,101,192,0.15)",
            line=dict(color="#1565C0", width=2),
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(range=[0, 5], tickvals=[1,2,3,4,5])),
            height=280, margin=dict(t=20, b=20), showlegend=False,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    st.divider()

    # Filtrage et tri
    filtered = [a for a in avis_list
                if filtre_note == 0 or (a.get("note") or 0) >= filtre_note]
    if filtre_plat != "Toutes":
        filtered = [a for a in filtered if a.get("plateforme") == filtre_plat]
    if not afficher_attente:
        filtered = [a for a in filtered if a.get("token_used") or not a.get("token")]
    if tri == "Meilleure note":
        filtered = sorted(filtered, key=lambda x: x.get("note", 0), reverse=True)
    elif tri == "Moins bonne note":
        filtered = sorted(filtered, key=lambda x: x.get("note", 0))

    st.caption(f"**{len(filtered)} avis affichés** sur {len(avis_list)} au total")

    # Pagination
    NB_PAR_PAGE = 10
    nb_pages = max(1, (len(filtered) + NB_PAR_PAGE - 1) // NB_PAR_PAGE)
    if nb_pages > 1:
        page_num = st.number_input("Page", min_value=1, max_value=nb_pages, value=1,
                                    key="av_page", step=1)
        st.caption(f"Page {page_num} / {nb_pages}")
        filtered = filtered[(page_num-1)*NB_PAR_PAGE : page_num*NB_PAR_PAGE]

    for a in filtered:
        _render_avis_card(a, props)


def _render_avis_card(a: dict, props: dict):
    note     = a.get("note", 0)
    etoiles  = ETOILES.get(note, "")
    prop_nom = props.get(a.get("propriete_id"), "")
    date_str = (a.get("date_sejour") or "")[:10]
    pending  = a.get("token") and not a.get("token_used")

    if pending:
        st.markdown(
            f"<div style='background:#FFF8E1;border-left:4px solid #FFB300;"
            f"padding:10px 16px;border-radius:0 8px 8px 0;margin-bottom:8px;"
            f"color:#F57F17;font-style:italic'>"
            f"⏳ Questionnaire envoyé à <b>{a.get('nom_client','')}</b> — en attente de réponse</div>",
            unsafe_allow_html=True
        )
        col_del, _ = st.columns([1, 9])
        if col_del.button("🗑️", key=f"del_pend_{a['id']}"):
            delete_avis(a["id"]); st.rerun()
        return

    # Barres mini par critère
    criteres_html = ""
    for col_key, label in CRITERES:
        val = a.get(col_key)
        if val:
            pct = val / 5 * 100
            color = "#4CAF50" if val >= 4 else "#FF9800" if val >= 3 else "#F44336"
            criteres_html += f"""
            <div style='display:flex;align-items:center;gap:8px;margin:3px 0'>
              <span style='width:150px;font-size:12px;color:#666'>{label}</span>
              <div style='flex:1;background:#E0E0E0;border-radius:4px;height:8px'>
                <div style='background:{color};width:{pct:.0f}%;height:8px;border-radius:4px'></div>
              </div>
              <span style='font-size:12px;font-weight:bold;width:20px'>{val}</span>
            </div>"""

    col_card, col_del = st.columns([11, 1])
    with col_card:
        st.markdown(f"""
<div style='background:#FAFAFA;border-left:4px solid #FFD700;
            padding:14px 18px;border-radius:8px;margin-bottom:12px'>
  <div style='display:flex;justify-content:space-between;align-items:flex-start'>
    <div>
      <span style='font-weight:bold;font-size:16px'>{a.get('nom_client','Client')}</span>
      &nbsp; <span style='font-size:20px'>{etoiles}</span>
      <span style='font-size:13px;font-weight:bold;color:#1565C0'> {note}/5</span>
    </div>
    <span style='color:#9E9E9E;font-size:12px'>{date_str} | {a.get('plateforme','')} | {prop_nom}</span>
  </div>
  <div style='margin:10px 0 8px 0;font-size:15px;color:#212121'>
    {a.get('commentaire','') or '<em style="color:#9E9E9E">Pas de commentaire</em>'}
  </div>
  {f"<div style='margin-top:4px'>{criteres_html}</div>" if criteres_html else ""}
  {'<div style="margin-top:10px;background:#E3F2FD;padding:8px 12px;border-radius:6px;font-size:13px"><b>💬 Réponse :</b> ' + a.get('reponse_hote','') + '</div>' if a.get('reponse_hote') else ''}
</div>""", unsafe_allow_html=True)

    with col_del:
        if st.button("🗑️", key=f"del_avis_{a['id']}"):
            delete_avis(a["id"]); st.rerun()

    if not a.get("reponse_hote"):
        with st.expander(f"💬 Répondre à {a.get('nom_client','')}"):
            rep = st.text_area("Votre réponse", key=f"rep_{a['id']}")
            if st.button("Publier", key=f"pub_{a['id']}"):
                save_avis({**a, "reponse_hote": rep}); st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# ENVOYER QUESTIONNAIRE
# ─────────────────────────────────────────────────────────────────────────────

def _show_envoyer(prop_id: int, prop_nom: str, props: dict):
    st.subheader("📨 Envoyer un questionnaire au client")
    st.markdown(
        "Génère un **lien unique** valable 30 jours que le client remplit en ligne. "
        "Son avis s'intègre automatiquement dans le livre d'or."
    )

    app_url = _app_url()
    if not app_url:
        st.warning(
            "⚠️ Configurez l'URL de votre app dans les secrets Streamlit Cloud :\n"
            "```\nAPP_URL = \"https://votre-app.streamlit.app\"\n```"
        )
        app_url = "https://votre-app.streamlit.app"

    # Sélection source : depuis une réservation ou manuel
    source = st.radio("Depuis", ["Une réservation existante", "Saisir manuellement"],
                       horizontal=True, key="env_source")

    if source == "Une réservation existante":
        df_res = load_reservations()
        df_prop = filter_df(df_res)
        df_prop = df_prop[df_prop["plateforme"] != "Fermeture"] if not df_prop.empty else df_prop
        df_prop = df_prop.sort_values("date_arrivee", ascending=False) if not df_prop.empty else df_prop

        if df_prop.empty:
            st.info("Aucune réservation disponible.")
            return

        options = {
            f"{r['nom_client']} — {str(r.get('date_arrivee',''))[:10]} ({r.get('plateforme','')})": r
            for _, r in df_prop.head(50).iterrows()
        }
        choix = st.selectbox("Réservation", list(options.keys()), key="env_res")
        row   = options[choix]

        nom_client   = str(row.get("nom_client", ""))
        email        = str(row.get("email", "") or "")
        telephone    = str(row.get("telephone", "") or "")
        date_arrivee = str(row.get("date_arrivee", ""))[:10]
        date_depart  = str(row.get("date_depart",  ""))[:10]
        date_sejour  = date_arrivee
        plateforme   = str(row.get("plateforme", ""))
        res_prop_id  = int(row.get("propriete_id", prop_id) or prop_id)
        res_prop_nom = props.get(res_prop_id, prop_nom)

    else:
        c1, c2 = st.columns(2)
        with c1:
            nom_client  = st.text_input("Nom du client *", key="env_nom")
            email       = st.text_input("Email", key="env_email")
        with c2:
            telephone   = st.text_input("Téléphone / WhatsApp", key="env_tel")
            date_sejour = str(st.date_input("Date du séjour", key="env_date"))
        res_prop_id  = prop_id if prop_id != 0 else (list(props.keys())[0] if props else 0)
        res_prop_nom = props.get(res_prop_id, prop_nom)
        plateforme   = st.selectbox("Plateforme", ["Airbnb","Booking","Abritel","Direct","Autre"], key="env_plat")
        date_arrivee = date_sejour
        date_depart  = ""

    if st.button("🔗 Générer le lien questionnaire", type="primary", use_container_width=True):
        if not nom_client:
            st.error("Le nom du client est requis.")
            return
        if not is_connected():
            st.error("Supabase non connecté.")
            return

        token   = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

        data = {
            "propriete_id":      res_prop_id,
            "nom_client":        nom_client,
            "plateforme":        plateforme,
            "date_sejour":       date_sejour,
            "token":             token,
            "token_used":        False,
            "token_expires_at":  expires,
            "visible":           True,
        }
        if save_avis(data):
            lien = f"{app_url}/?token={token}"

            st.success(f"✅ Lien généré pour **{nom_client}** — valable 30 jours")
            st.code(lien, language=None)

            import urllib.parse

            # Infos séjour formatées
            sejour_fr = f"{date_arrivee}"
            sejour_en = f"{date_arrivee}"
            if date_depart:
                sejour_fr += f" au {date_depart}"
                sejour_en += f" to {date_depart}"

            # ── Message WhatsApp bilingue FR/EN ───────────────────────────
            msg_wa = (
                f"Bonjour {nom_client} 😊 / Hello {nom_client} 😊\n\n"
                f"🏠 {res_prop_nom}\n"
                f"📅 {sejour_fr} ({plateforme})\n\n"
                f"🇫🇷 Merci pour votre séjour ! Votre avis nous aide beaucoup.\n"
                f"🇬🇧 Thank you for your stay! Your review means a lot to us.\n\n"
                f"⏱️ 2 min · 👉 {lien}\n\n"
                f"Merci / Thank you! 🙏"
            )
            wa_num = telephone.replace("+", "").replace(" ", "").replace("-", "") if telephone else ""
            wa_url = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg_wa)}" if wa_num else \
                     f"https://wa.me/?text={urllib.parse.quote(msg_wa)}"

            # ── Message email bilingue FR/EN ──────────────────────────────
            msg_email = (
                f"Bonjour {nom_client} / Hello {nom_client},\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏠 {res_prop_nom}\n"
                f"📅 {sejour_fr}\n"
                f"🔑 {plateforme}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🇫🇷 Merci pour votre séjour !\n"
                f"Nous serions ravis d'avoir votre avis en 2 minutes :\n"
                f"👉 {lien}\n\n"
                f"🇬🇧 Thank you for your stay!\n"
                f"We would love to hear your feedback (2 minutes):\n"
                f"👉 {lien}\n\n"
                f"Ce lien est valable 30 jours / This link is valid for 30 days.\n\n"
                f"Merci / Thank you! 🙏"
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <a href="{wa_url}" target="_blank">
                  <div style='background:#25D366;color:white;text-align:center;
                    padding:12px;border-radius:8px;font-weight:bold;font-size:15px;
                    cursor:pointer'>
                    📱 Envoyer par WhatsApp
                  </div>
                </a>""", unsafe_allow_html=True)
            with col2:
                if email:
                    mailto = f"mailto:{email}?subject=Votre avis sur {res_prop_nom}&body={urllib.parse.quote(msg_email)}"
                    st.markdown(f"""
                    <a href="{mailto}">
                      <div style='background:#1565C0;color:white;text-align:center;
                        padding:12px;border-radius:8px;font-weight:bold;font-size:15px;
                        cursor:pointer'>
                        📧 Ouvrir dans la messagerie
                      </div>
                    </a>""", unsafe_allow_html=True)
                else:
                    st.info("Renseignez l'email pour envoyer par mail.")

            # Aperçu du message
            with st.expander("📋 Aperçu du message"):
                st.text(msg_email)
        else:
            st.error("Erreur lors de la création du questionnaire.")


# ─────────────────────────────────────────────────────────────────────────────
# SAISIE MANUELLE
# ─────────────────────────────────────────────────────────────────────────────

def _show_ajout(prop_id: int, prop_nom: str, props: dict):
    st.subheader("✍️ Saisir un avis manuellement")
    st.caption("Pour les avis reçus directement sur les plateformes.")

    if len(props) > 1:
        prop_sel = st.selectbox("Propriété", list(props.keys()),
                                 format_func=lambda x: props[x],
                                 index=list(props.keys()).index(prop_id) if prop_id in props else 0,
                                 key="av_prop_sel")
    else:
        prop_sel = prop_id

    c1, c2 = st.columns(2)
    with c1:
        nom_client  = st.text_input("Nom du client *", key="av_nom")
        plateforme  = st.selectbox("Plateforme", ["Airbnb","Booking","Abritel","Direct","Autre"], key="av_plat_sel")
    with c2:
        date_sejour = st.date_input("Date du séjour", value=date.today(), key="av_date")
        visible     = st.checkbox("Visible dans le livre d'or", value=True, key="av_visible")

    st.markdown("**⭐ Notes par critère :**")
    notes = {}
    cols_notes = st.columns(3)
    for i, (col_key, label) in enumerate(CRITERES):
        with cols_notes[i % 3]:
            notes[col_key] = st.select_slider(
                label, options=[1,2,3,4,5], value=5,
                format_func=lambda x: ETOILES[x],
                key=f"man_{col_key}"
            )

    note_globale = round(sum(notes.values()) / len(notes))
    st.info(f"Note globale calculée : **{ETOILES[note_globale]} ({note_globale}/5)**")

    commentaire = st.text_area("Commentaire *", height=100, key="av_comment")
    reponse     = st.text_area("Votre réponse (optionnel)", height=70, key="av_rep")

    if st.button("⭐ Enregistrer l'avis", type="primary", use_container_width=True):
        if not nom_client:
            st.error("Le nom du client est requis.")
        elif not commentaire:
            st.error("Le commentaire est requis.")
        elif not is_connected():
            st.error("Supabase non connecté.")
        else:
            data = {
                "propriete_id":  prop_sel,
                "nom_client":    nom_client,
                "note":          note_globale,
                "commentaire":   commentaire,
                "plateforme":    plateforme,
                "date_sejour":   date_sejour.isoformat(),
                "reponse_hote":  reponse or None,
                "visible":       visible,
                "token_used":    True,
                **notes,
            }
            if save_avis(data):
                st.success(f"✅ Avis de {nom_client} enregistré ! {ETOILES[note_globale]}")
                st.balloons()
            else:
                st.error("Erreur lors de l'enregistrement.")


# ─────────────────────────────────────────────────────────────────────────────
# STATISTIQUES
# ─────────────────────────────────────────────────────────────────────────────

def _show_stats(prop_id: int, props: dict):
    st.subheader("📊 Statistiques des avis")

    avis_list = get_avis(prop_id if prop_id != 0 else None)
    avis_reel = [a for a in avis_list if a.get("token_used") or not a.get("token")]

    if not avis_reel:
        st.info("Aucun avis complété disponible.")
        return

    df = pd.DataFrame(avis_reel)

    c1, c2, c3, c4 = st.columns(4)
    notes_val = [a.get("note") for a in avis_reel if a.get("note")]
    c1.metric("⭐ Note globale",  f"{sum(notes_val)/len(notes_val):.1f}/5" if notes_val else "—")
    c2.metric("📝 Avis reçus",   len(avis_reel))
    c3.metric("🏆 5 étoiles",    sum(1 for n in notes_val if n == 5))
    envois = sum(1 for a in avis_list if a.get("token") and not a.get("token_used"))
    c4.metric("📨 En attente",   envois)

    col1, col2 = st.columns(2)

    with col1:
        # Radar par critère
        moyennes = {}
        for col_key, label in CRITERES:
            vals = [a[col_key] for a in avis_reel if a.get(col_key)]
            if vals:
                moyennes[label] = round(sum(vals) / len(vals), 2)

        if moyennes:
            fig = go.Figure(go.Scatterpolar(
                r=list(moyennes.values()) + [list(moyennes.values())[0]],
                theta=list(moyennes.keys()) + [list(moyennes.keys())[0]],
                fill="toself", fillcolor="rgba(21,101,192,0.15)",
                line=dict(color="#1565C0", width=2),
                text=[f"{v:.1f}" for v in list(moyennes.values()) + [list(moyennes.values())[0]]],
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(range=[0, 5], tickvals=[1,2,3,4,5])),
                height=320, margin=dict(t=30, b=20), showlegend=False,
                title="Notes moyennes par critère"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Distribution notes globales
        dist = pd.Series(notes_val).value_counts().sort_index().reset_index()
        dist.columns = ["Note", "Nombre"]
        dist["Etoiles"] = dist["Note"].map(ETOILES)
        fig2 = px.bar(dist, x="Etoiles", y="Nombre", title="Distribution des notes",
                      color="Note", color_continuous_scale=["#F44336","#FF9800","#FFC107","#8BC34A","#4CAF50"])
        fig2.update_layout(height=320, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Tableau détail critères
    if moyennes:
        st.divider()
        st.markdown("**Détail par critère :**")
        rows = []
        for col_key, label in CRITERES:
            vals = [a[col_key] for a in avis_reel if a.get(col_key)]
            if vals:
                moy = sum(vals) / len(vals)
                rows.append({
                    "Critère":       label,
                    "Moyenne":       f"{moy:.1f} / 5",
                    "Note mini":     min(vals),
                    "Note maxi":     max(vals),
                    "Nb réponses":   len(vals),
                })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Comparaison propriétés
    if len(props) > 1:
        st.divider()
        st.markdown("**Comparaison par propriété :**")
        cols = st.columns(len(props))
        for i, (pid, pnom) in enumerate(props.items()):
            av = [a for a in get_avis(pid) if a.get("token_used") or not a.get("token")]
            notes_p = [a["note"] for a in av if a.get("note")]
            with cols[i]:
                st.markdown(f"**🏠 {pnom}**")
                if notes_p:
                    st.metric("Note", f"{sum(notes_p)/len(notes_p):.1f} ⭐")
                    st.caption(f"{len(notes_p)} avis")
                else:
                    st.caption("Aucun avis")
