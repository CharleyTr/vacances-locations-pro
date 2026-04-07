"""
Page Chat interne — messagerie entre utilisateurs de l'app.
"""
import streamlit as st
import streamlit.components.v1 as _cv_chat
from database.supabase_client import get_supabase
from services.auth_service import is_unlocked


def _get_messages(propriete_id=None):
    sb = get_supabase()
    if sb is None: return []
    try:
        data = sb.table("messages_internes").select("*")            .order("created_at", desc=False).limit(200).execute().data or []
        if propriete_id is None:
            # Canal général : uniquement les messages sans propriété
            return [m for m in data if not m.get("propriete_id")]
        else:
            # Canal propriété : uniquement les messages de cette propriété
            return [m for m in data if m.get("propriete_id") == propriete_id]
    except: return []


def _count_unread(auteur, propriete_id=None):
    """Compte les messages non lus par cet auteur dans ce canal."""
    sb = get_supabase()
    if sb is None: return 0
    try:
        q = sb.table("messages_internes").select("id, lu_par")
        if propriete_id:
            q = q.eq("propriete_id", propriete_id)
        else:
            q = q.is_("propriete_id", None)
        rows = q.execute().data or []
        return sum(1 for r in rows
                   if auteur not in (r.get("lu_par") or [])
                   and r.get("auteur") != auteur)
    except: return 0

def _mark_all_read(auteur, propriete_id=None):
    """Marque tous les messages du canal comme lus par cet auteur."""
    sb = get_supabase()
    if sb is None: return
    try:
        q = sb.table("messages_internes").select("id, lu_par")
        if propriete_id:
            q = q.eq("propriete_id", propriete_id)
        else:
            q = q.is_("propriete_id", None)
        rows = q.execute().data or []
        for r in rows:
            lu_par = r.get("lu_par") or []
            if auteur not in lu_par:
                lu_par.append(auteur)
                sb.table("messages_internes").update({"lu_par": lu_par})                  .eq("id", r["id"]).execute()
    except: pass


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


def show():
    st.title("💬 Chat interne")
    st.caption("Messagerie entre membres de l'équipe.")

    # Nom auteur
    auteur = st.session_state.get("chat_auteur_nom") or st.session_state.get("user_name") or "Utilisateur"

    # Sélection canal
    from database.proprietes_repo import fetch_all as _fa
    _props = {p["id"]: p["nom"] for p in _fa() if not p.get("mot_de_passe") or is_unlocked(p["id"])}
    _canal_opts = {"__general__": "🌐 Général"}
    _canal_opts.update({str(k): v for k, v in _props.items()})

    if "chat_canal_sel" not in st.session_state:
        st.session_state["chat_canal_sel"] = "__general__"

    st.markdown("**Canal :**")
    _btn_cols = st.columns(len(_canal_opts))
    for _i, (_k, _lbl) in enumerate(_canal_opts.items()):
        with _btn_cols[_i]:
            _active = (st.session_state["chat_canal_sel"] == _k)
            if st.button(("✅ " if _active else "") + _lbl,
                          key=f"pg_chat_canal_btn_{_i}",
                          use_container_width=True,
                          type="primary" if _active else "secondary"):
                st.session_state["chat_canal_sel"] = _k
                st.rerun()

    _canal = st.session_state["chat_canal_sel"]
    _prop_id = int(_canal) if _canal != "__general__" else None

    # Charger messages et marquer comme lus
    messages = _get_messages(_prop_id)
    _mark_all_read(auteur, _prop_id)

    # Affichage
    if not messages:
        st.info("Aucun message. Soyez le premier à écrire !")
    else:
        chat_html = ""
        for msg in messages:
            _a = msg.get("auteur", "?")
            _c = msg.get("contenu", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            _d = msg.get("created_at", "")[:16].replace("T", " ")
            _me = (_a == auteur)
            _bg = "#1565C0" if _me else "#37474F"
            _r = "18px 18px 4px 18px" if _me else "18px 18px 18px 4px"
            _j = "flex-end" if _me else "flex-start"
            chat_html += (
                f"<div style='display:flex;justify-content:{_j};margin-bottom:10px'>"
                f"<div style='max-width:78%;background:{_bg};color:white;"
                f"padding:10px 14px;border-radius:{_r};"
                f"font-size:13px;line-height:1.5;word-break:break-word'>"
                + ("" if _me else f"<div style='font-size:11px;font-weight:bold;opacity:0.8;margin-bottom:3px'>{_a}</div>")
                + _c.replace("\n", "<br>")
                + f"<div style='font-size:10px;opacity:0.55;margin-top:5px;text-align:right'>{_d}</div>"
                + "</div></div>"
            )

        _cv_chat.html(
            "<div style='height:460px;overflow-y:auto;padding:14px;"
            "background:#111827;border-radius:12px;border:1px solid #2D3748'>"
            + chat_html
            + "<div id='chat-end'></div></div>"
            "<script>document.getElementById('chat-end').scrollIntoView();</script>",
            height=480
        )

    st.markdown("")

    # Formulaire envoi
    if "chat_form_id" not in st.session_state:
        st.session_state["chat_form_id"] = 0

    with st.form(f"chat_form_{st.session_state['chat_form_id']}", clear_on_submit=True):
        f_c1, f_c2, f_c3 = st.columns([2, 4, 1])
        with f_c1:
            nom_saisi = st.text_input("Nom", value=auteur, placeholder="Votre nom")
        with f_c2:
            msg_input = st.text_input("Message", placeholder="Écrire un message...")
        with f_c3:
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("📤", type="primary", use_container_width=True)

        if submitted:
            _nom = nom_saisi.strip() or auteur
            st.session_state["chat_auteur_nom"] = _nom
            if not msg_input.strip():
                st.warning("Message vide.")
            elif _send_message(_nom, msg_input.strip(), _prop_id):
                st.session_state["chat_form_id"] += 1
                st.rerun()
            else:
                st.error("❌ Erreur — vérifiez que la table messages_internes existe (SQL 030).")

    if st.button("🔄 Rafraîchir"):
        st.rerun()
