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

    # Canal sélectionné via session_state — pas de widget radio pour éviter les conflits
    if "chat_canal" not in st.session_state:
        st.session_state["chat_canal"] = "all"

    col_name, col_refresh = st.columns([3, 1])
    with col_name:
        new_name = st.text_input("Mon nom dans le chat", value=auteur,
                                  key="pg_chat_v3_name")
        if new_name and new_name != auteur:
            st.session_state["user_name"] = new_name
            auteur = new_name

    # Boutons canal
    _btn_cols = st.columns(len(prop_opts))
    for _i, (_k, _label) in enumerate(prop_opts.items()):
        with _btn_cols[_i]:
            _active = st.session_state["chat_canal"] == _k
            if st.button(_label, key=f"chat_canal_btn_{_i}",
                          type="primary" if _active else "secondary",
                          use_container_width=True):
                st.session_state["chat_canal"] = _k
                st.rerun()

    prop_key = st.session_state["chat_canal"]
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
                label_visibility="collapsed", key="pg_chat_v3_chat_msg_input"
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
    if st.button("🔄 Rafraîchir", use_container_width=False, key="pg_chat_v3_chat_btn_refresh"):
        st.rerun()
