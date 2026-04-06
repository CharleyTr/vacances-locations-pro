"""
Page Chat interne — messagerie entre utilisateurs de l'app.
"""
import streamlit as st
from database.supabase_client import get_supabase
from services.auth_service import is_unlocked

def _get_messages():
    sb = get_supabase()
    if sb is None: return []
    try:
        return sb.table("messages_internes").select("*")\
            .order("created_at", desc=False).limit(100).execute().data or []
    except: return []

def _send_message(auteur, contenu):
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.table("messages_internes").insert({
            "auteur": auteur,
            "contenu": contenu,
        }).execute()
        return True
    except Exception as e:
        print(f"chat error: {e}"); return False

def show():
    st.title("💬 Chat interne")
    st.caption("Messagerie entre membres de l'équipe.")

    # Nom auteur depuis session
    auteur = st.session_state.get("chat_auteur_nom") or \
             st.session_state.get("user_name") or "Utilisateur"

    # Charger messages
    messages = _get_messages()

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
            f"</div>",
            unsafe_allow_html=True
        )

    st.markdown("")

    # Formulaire envoi — tous les widgets sont dans le form, pas de conflit possible
    if "chat_form_id" not in st.session_state:
        st.session_state["chat_form_id"] = 0
    _form_key = f"chat_form_{st.session_state['chat_form_id']}"
    with st.form(_form_key, clear_on_submit=True):
        f_c1, f_c2, f_c3 = st.columns([2, 4, 1])
        with f_c1:
            nom_saisi = st.text_input("Nom", value=auteur,
                                       placeholder="Votre nom",
                                       label_visibility="visible")
        with f_c2:
            msg_input = st.text_input("Message", placeholder="Écrire un message...",
                                       label_visibility="visible")
        with f_c3:
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("📤 Envoyer", type="primary",
                                               use_container_width=True)

        if submitted:
            _nom = nom_saisi.strip() or auteur
            st.session_state["chat_auteur_nom"] = _nom
            if not msg_input.strip():
                st.warning("Message vide.")
            elif _send_message(_nom, msg_input.strip()):
                st.session_state["chat_form_id"] = st.session_state.get("chat_form_id", 0) + 1
                st.rerun()
            else:
                st.error("❌ Erreur — vérifiez que la table messages_internes existe (SQL 030).")

    if st.button("🔄 Rafraîchir les messages"):
        st.rerun()
