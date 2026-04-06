"""
Page Chat interne — messagerie entre utilisateurs de l'app.
"""
import streamlit as st
from datetime import datetime
from database.supabase_client import get_supabase
from services.auth_service import is_unlocked

def _get_messages(propriete_id=None):
    sb = get_supabase()
    if sb is None: return []
    try:
        q = sb.table("messages_internes").select("*").order("created_at", desc=False)
        if propriete_id:
            q = q.or_(f"propriete_id.eq.{propriete_id},propriete_id.is.null")
        return q.limit(100).execute().data or []
    except: return []

def _send_message(auteur, contenu, propriete_id=None):
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.table("messages_internes").insert({
            "auteur": auteur,
            "contenu": contenu,
            "propriete_id": propriete_id,
        }).execute()
        return True
    except Exception as e:
        print(f"chat error: {e}"); return False

def _mark_read(propriete_id=None):
    sb = get_supabase()
    if sb is None: return
    try:
        q = sb.table("messages_internes").update({"lu": True}).eq("lu", False)
        if propriete_id:
            q = q.or_(f"propriete_id.eq.{propriete_id},propriete_id.is.null")
        q.execute()
    except: pass

def _count_unread(propriete_id=None):
    sb = get_supabase()
    if sb is None: return 0
    try:
        q = sb.table("messages_internes").select("id", count="exact").eq("lu", False)
        if propriete_id:
            q = q.or_(f"propriete_id.eq.{propriete_id},propriete_id.is.null")
        return q.execute().count or 0
    except: return 0

def show():
    st.title("💬 Chat interne")
    st.caption("Messagerie entre membres de l'équipe.")

    # Nom utilisateur depuis session
    auteur = st.session_state.get("user_name") or \
             st.session_state.get("user_email") or "Utilisateur"

    # Canaux disponibles
    from database.proprietes_repo import fetch_all as _fa
    _props = {p["id"]: p["nom"] for p in _fa()
              if not p.get("mot_de_passe") or is_unlocked(p["id"])}

    prop_opts = {"all": "🌐 Général"} | {str(k): v for k, v in _props.items()}

    col_chan, col_name = st.columns([3, 1])
    with col_chan:
        _canal_labels = list(prop_opts.values())
        _canal_keys   = list(prop_opts.keys())
        _canal_idx    = st.radio("Canal", range(len(_canal_labels)),
                                  format_func=lambda i: _canal_labels[i],
                                  horizontal=True, key="chat_radio_canal")
        prop_key = _canal_keys[_canal_idx]
    with col_name:
        new_name = st.text_input("Mon nom", value=auteur, key="chat_user_name_inp")
        if new_name and new_name != auteur:
            st.session_state["user_name"] = new_name
            auteur = new_name

    prop_id = int(prop_key) if prop_key != "all" else None

    # Charger et marquer comme lus
    messages = _get_messages(prop_id)
    _mark_read(prop_id)

    # Affichage chat
    if not messages:
        st.info("Aucun message. Soyez le premier à écrire !")
    else:
        chat_html = ""
        for msg in messages:
            _auteur  = msg.get("auteur", "?")
            _contenu = msg.get("contenu", "").replace("<", "&lt;").replace(">", "&gt;")
            _date    = msg.get("created_at", "")[:16].replace("T", " ")
            _is_me   = (_auteur == auteur)
            _bg      = "#1565C0" if _is_me else "#37474F"
            _radius  = "18px 18px 4px 18px" if _is_me else "18px 18px 18px 4px"
            _justify = "flex-end" if _is_me else "flex-start"

            chat_html += f"""
            <div style='display:flex;justify-content:{_justify};margin-bottom:10px'>
              <div style='max-width:78%;background:{_bg};color:white;
                          padding:10px 14px;border-radius:{_radius};
                          font-size:13px;line-height:1.5;word-break:break-word'>
                {"" if _is_me else f'<div style="font-size:11px;font-weight:bold;opacity:0.8;margin-bottom:3px">{_auteur}</div>'}
                {_contenu.replace(chr(10), "<br>")}
                <div style='font-size:10px;opacity:0.55;margin-top:5px;text-align:right'>{_date}</div>
              </div>
            </div>"""

        st.markdown(
            f"<div style='height:460px;overflow-y:auto;padding:14px;"
            f"background:#111827;border-radius:12px;border:1px solid #2D3748'>"
            f"{chat_html}"
            f"<div id='chat-bottom'></div>"
            f"</div>"
            f"<script>document.getElementById('chat-bottom')?.scrollIntoView({{behavior:'smooth'}});</script>",
            unsafe_allow_html=True
        )

    st.markdown("")

    # Formulaire envoi
    with st.form("form_chat", clear_on_submit=True):
        cols = st.columns([5, 1])
        with cols[0]:
            msg_input = st.text_input(
                "msg", placeholder=f"Écrire à l'équipe... (en tant que {auteur})",
                label_visibility="collapsed", key="chat_msg_input"
            )
        with cols[1]:
            submitted = st.form_submit_button("📤", use_container_width=True, type="primary")

        if submitted:
            if not msg_input.strip():
                st.warning("Message vide.")
            elif _send_message(auteur, msg_input.strip(), prop_id):
                st.rerun()
            else:
                st.error("❌ Erreur d'envoi — vérifiez la table messages_internes (SQL 030).")

    # Bouton rafraîchir
    if st.button("🔄 Rafraîchir", use_container_width=False, key="chat_btn_refresh"):
        st.rerun()
