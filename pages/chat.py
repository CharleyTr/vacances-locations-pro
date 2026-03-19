"""
Page Chat interne — messagerie en temps réel entre utilisateurs.
"""
import streamlit as st
from datetime import datetime, timezone
from database.chat_repo import get_messages, send_message, mark_read, delete_message
from services.proprietes_service import get_proprietes_autorises


def _get_user_info() -> tuple[str, str]:
    """Retourne (email, nom) de l'utilisateur connecté."""
    email = st.session_state.get("auth_user_email", "")
    if not email:
        # Mode PIN — identifier par la propriété
        prop_id = st.session_state.get("prop_id", 0)
        props = get_proprietes_autorises()
        nom = props.get(prop_id, f"Utilisateur #{prop_id}") if prop_id else "Administrateur"
        email = f"pin_{prop_id}@local"
        return email, nom
    nom = email.split("@")[0].replace(".", " ").title()
    return email, nom


def _fmt_time(ts: str) -> str:
    """Formate la date relative."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = (now - dt).total_seconds()
        if diff < 60:     return "à l'instant"
        if diff < 3600:   return f"il y a {int(diff/60)} min"
        if diff < 86400:  return f"il y a {int(diff/3600)} h"
        return dt.strftime("%d/%m %H:%M")
    except:
        return ts[:16].replace("T", " ")


def show():
    st.title("💬 Chat interne")
    st.caption("Messagerie en temps réel entre tous les utilisateurs de l'application.")

    user_email, user_nom = _get_user_info()
    is_admin = st.session_state.get("is_admin", False)

    # Marquer les messages comme lus
    mark_read(user_email)

    # ── Sélecteur de canal ────────────────────────────────────────────────
    props = get_proprietes_autorises()
    canaux = {"0": "💬 Général (tous)"}
    canaux.update({str(k): f"🏠 {v}" for k, v in props.items()})

    canal_choix = st.selectbox(
        "Canal",
        options=list(canaux.keys()),
        format_func=lambda x: canaux[x],
        key="chat_canal",
        label_visibility="collapsed"
    )
    prop_filter = int(canal_choix) if canal_choix != "0" else None

    st.divider()

    # ── Auto-refresh toutes les 5 secondes ────────────────────────────────
    if "chat_refresh" not in st.session_state:
        st.session_state["chat_refresh"] = 0
    refresh_count = st.session_state["chat_refresh"]

    col_r, col_t = st.columns([1, 4])
    with col_r:
        if st.button("🔄 Actualiser", key="btn_refresh_chat"):
            st.session_state["chat_refresh"] += 1
            st.rerun()
    with col_t:
        st.caption("💡 Cliquez 🔄 pour voir les nouveaux messages")

    # ── Messages ──────────────────────────────────────────────────────────
    messages = get_messages(limit=100, propriete_id=prop_filter)

    if not messages:
        st.markdown("""
        <div style='text-align:center;padding:3rem;color:#888'>
            <div style='font-size:48px'>💬</div>
            <p>Aucun message — soyez le premier à écrire !</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Afficher les messages dans un conteneur scrollable
        st.markdown("""
        <style>
        .chat-container { max-height: 450px; overflow-y: auto; padding: 1rem 0; }
        .msg-mine   { display:flex; justify-content:flex-end; margin:6px 0; }
        .msg-other  { display:flex; justify-content:flex-start; margin:6px 0; }
        .bubble-mine  { background:#1565C0; color:white; padding:10px 16px; border-radius:18px 18px 4px 18px; max-width:70%; font-size:14px; }
        .bubble-other { background:#F0F4FF; color:#222; padding:10px 16px; border-radius:18px 18px 18px 4px; max-width:70%; font-size:14px; }
        .msg-meta   { font-size:11px; color:#999; margin:2px 4px; }
        </style>
        <div class="chat-container" id="chat-bottom">
        """, unsafe_allow_html=True)

        for msg in messages:
            is_mine = (msg.get("user_email") == user_email)
            nom     = msg.get("user_nom") or msg.get("user_email","?").split("@")[0]
            temps   = _fmt_time(msg.get("created_at",""))
            contenu = msg.get("contenu","").replace("<","&lt;").replace(">","&gt;")
            prop_id = msg.get("propriete_id")
            prop_label = f" · {props.get(prop_id,'?')}" if prop_id and not prop_filter else ""

            if is_mine:
                st.markdown(f"""
                <div class="msg-mine">
                  <div>
                    <div class="bubble-mine">{contenu}</div>
                    <div class="msg-meta" style="text-align:right">{temps}{prop_label}</div>
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="msg-other">
                  <div>
                    <div class="bubble-other"><strong>{nom}</strong><br>{contenu}</div>
                    <div class="msg-meta">{temps}{prop_label}</div>
                  </div>
                </div>""", unsafe_allow_html=True)

            # Bouton suppression admin
            if is_admin and st.button("🗑️", key=f"del_msg_{msg['id']}",
                                       help="Supprimer ce message"):
                delete_message(msg["id"])
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        # Scroll auto vers le bas
        st.markdown("""
        <script>
        var c = document.getElementById('chat-bottom');
        if(c) c.scrollTop = c.scrollHeight;
        </script>""", unsafe_allow_html=True)

    st.divider()

    # ── Formulaire d'envoi ────────────────────────────────────────────────
    with st.form("form_chat_send", clear_on_submit=True):
        col_msg, col_btn = st.columns([5, 1])
        with col_msg:
            texte = st.text_input(
                "Message",
                placeholder=f"Écrivez un message... (canal : {canaux[canal_choix]})",
                label_visibility="collapsed",
                key="chat_input"
            )
        with col_btn:
            envoyer = st.form_submit_button("📤 Envoyer", type="primary",
                                             use_container_width=True)

    if envoyer and texte.strip():
        result = send_message(
            contenu=texte.strip(),
            user_email=user_email,
            user_nom=user_nom,
            propriete_id=prop_filter,
        )
        if result:
            st.session_state["chat_refresh"] += 1
            st.rerun()
        else:
            st.error("❌ Erreur lors de l'envoi. Vérifiez la connexion Supabase.")
