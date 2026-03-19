"""
Page Chat interne — messagerie en temps réel entre utilisateurs.
"""
import streamlit as st
from datetime import datetime, timezone
from database.chat_repo import (get_messages, send_message, mark_read, delete_message,
    upload_fichier, get_download_url, send_message_with_file
)
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

    # Détecter les nouveaux messages depuis la dernière visite
    _last_seen_key = f"chat_last_seen_{user_email}"
    _last_seen_count = st.session_state.get(_last_seen_key, 0)

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

    # Alerte nouveaux messages
    _new_msgs = [m for m in messages
                 if user_email not in (m.get("lu_par") or [])
                 and m.get("user_email") != user_email]
    if _new_msgs:
        _nb_new = len(_new_msgs)
        _derniers = [m.get("user_nom") or m.get("user_email","?").split("@")[0]
                     for m in _new_msgs[-3:]]
        _noms = ", ".join(set(_derniers))
        st.markdown(f"""
        <div style='background:#E53935;color:white;border-radius:10px;
                    padding:12px 18px;margin-bottom:12px;font-weight:bold;
                    display:flex;align-items:center;gap:10px'>
            <span style='font-size:20px'>🔔</span>
            <span>{_nb_new} nouveau(x) message(s) de <strong>{_noms}</strong></span>
        </div>
        <audio autoplay>
          <source src="data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJiVlIBwaWp0kZCOf2deaYyMi4BxaXF9io+Le3FxdImQjYJ3cXSCjJCKgXZzeImTkIt/dnaAi5OTjIJ4d3+Mk5SOg3l4foqUlI2DenqBjZWVjoR8e4KOlpWOhH17g46XlY+FfXyEj5iWj4Z+foWQmJeQh39/hpGZl5CIgH+HkpmakoqChIiTmZuTjIaGipSbnZSNiImLlZ2elZCLi4yWnp+WkY2NjpefoJeSkY+PmJ+glpOSkZCZoaGXlJSSkpqioZiVlZSTm6KimJaXlJSco6OZl5iWlZ2ko5mYmZeXnqWkmZqbmZmenKWlmpybmpmfnaWlm5ydm5qgn6Wlm52em5uhoPX19fX19fX19fX19Q==" type="audio/wav">
        </audio>
        """, unsafe_allow_html=True)
        st.session_state[_last_seen_key] = len(messages)

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
        <script>
        function copyMsg(id, btn) {
            var el = document.getElementById('msg-' + id);
            if (!el) return;
            // Copier tout sauf les spans enfants (tooltips)
            var clone = el.cloneNode(true);
            var tips = clone.querySelectorAll('.tooltip');
            tips.forEach(function(t){ t.remove(); });
            var text = (clone.innerText || clone.textContent || '').trim();
            // Méthode 1 : execCommand (fonctionne dans iframes)
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.setAttribute('readonly', '');
            ta.style.cssText = 'position:fixed;top:0;left:0;width:2px;height:2px;opacity:0;border:none;padding:0';
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            var ok = false;
            try { ok = document.execCommand('copy'); } catch(e) {}
            document.body.removeChild(ta);
            // Feedback visuel
            if (btn) {
                var orig = btn.textContent;
                btn.textContent = ok ? '✅' : '⚠️';
                setTimeout(function(){ btn.textContent = orig; }, 1800);
            }
        }
        </script>
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

            fichier_path = msg.get("fichier_path","")
            fichier_nom  = msg.get("fichier_nom","")
            fichier_type = msg.get("fichier_type","")
            fichier_mime = msg.get("fichier_mime","")

            msg_id_str = str(msg.get("id",""))
            if is_mine:
                st.markdown(f"""
                <div class="msg-mine">
                  <div>
                    <div class="bubble-mine" id="msg-{msg_id_str}">{contenu}</div>
                    <div class="msg-meta" style="text-align:right">
                      <span onclick="copyMsg('{msg_id_str}', this)" title="Copier le message"
                        style="cursor:pointer;margin-right:6px;opacity:0.7;user-select:none">📋</span>
                      {temps}{prop_label}
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="msg-other">
                  <div>
                    <div class="bubble-other" id="msg-{msg_id_str}"><strong>{nom}</strong><br>{contenu}</div>
                    <div class="msg-meta">
                      <span onclick="copyMsg('{msg_id_str}', this)" title="Copier le message"
                        style="cursor:pointer;margin-right:6px;opacity:0.7;user-select:none">📋</span>
                      {temps}{prop_label}
                    </div>
                  </div>
                </div>""", unsafe_allow_html=True)

            # Afficher la pièce jointe sous la bulle
            if fichier_path:
                url = get_download_url(fichier_path)
                if url:
                    if fichier_type == "image":
                        try:
                            st.image(url, caption=fichier_nom, width=300)
                        except:
                            st.link_button(f"🖼️ {fichier_nom}", url)
                    else:
                        ext = fichier_nom.rsplit(".",1)[-1].upper() if "." in fichier_nom else "?"
                        st.markdown(
                            f"<a href='{url}' target='_blank' style='display:inline-block;"
                            f"padding:6px 12px;background:#E3F2FD;border-radius:8px;"
                            f"color:#1565C0;text-decoration:none;font-size:13px'>"
                            f"📎 {fichier_nom} <span style='opacity:0.6;font-size:11px'>({ext})</span></a>",
                            unsafe_allow_html=True
                        )

            # Bouton suppression admin
            if is_admin and st.button("🗑️", key=f"del_msg_{msg['id']}",
                                       help="Supprimer ce message"):
                delete_message(msg["id"], fichier_path)
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        # Scroll auto vers le bas
        st.markdown("""
        <script>
        var c = document.getElementById('chat-bottom');
        if(c) c.scrollTop = c.scrollHeight;
        </script>""", unsafe_allow_html=True)

    st.divider()

    # ── Zone coller une capture d'écran (Ctrl+V) ──────────────────────────
    st.markdown("""
    <div id="paste-zone" 
         style="border:2px dashed #90CAF9;border-radius:10px;padding:14px;
                text-align:center;color:#90CAF9;font-size:13px;cursor:pointer;
                margin-bottom:10px;background:#F0F8FF;transition:all 0.2s"
         onpaste="handlePaste(event)"
         tabindex="0"
         title="Cliquez ici puis Ctrl+V pour coller une capture d'écran">
      📸 Cliquez ici puis <strong>Ctrl+V</strong> pour coller une capture d'écran
    </div>
    <canvas id="paste-preview" style="display:none;max-width:100%;border-radius:8px;margin-bottom:8px"></canvas>
    <input type="hidden" id="paste-b64" value="">
    <div id="paste-status" style="font-size:12px;color:#1565C0;margin-bottom:6px"></div>

    <script>
    var pasteZone = document.getElementById('paste-zone');
    var pasteB64  = document.getElementById('paste-b64');
    var pasteCanvas = document.getElementById('paste-preview');
    var pasteStatus = document.getElementById('paste-status');

    // Focus automatique sur la zone
    pasteZone.addEventListener('click', function(){ pasteZone.focus(); });

    function handlePaste(e) {
        var items = (e.clipboardData || window.clipboardData).items;
        for (var i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                e.preventDefault();
                var file = items[i].getAsFile();
                var reader = new FileReader();
                reader.onload = function(ev) {
                    var b64 = ev.target.result; // data:image/png;base64,...
                    pasteB64.value = b64;
                    // Aperçu
                    var img = new Image();
                    img.onload = function() {
                        pasteCanvas.style.display = 'block';
                        pasteCanvas.width  = Math.min(img.width, 400);
                        pasteCanvas.height = Math.min(img.height, 300) * (pasteCanvas.width / img.width);
                        var ctx = pasteCanvas.getContext('2d');
                        ctx.drawImage(img, 0, 0, pasteCanvas.width, pasteCanvas.height);
                    };
                    img.src = b64;
                    pasteZone.style.borderColor = '#4CAF50';
                    pasteZone.innerHTML = '✅ Image collée — cliquez <strong>Envoyer l\'image</strong>';
                    pasteStatus.textContent = 'Image prête à être envoyée';
                    // Stocker dans sessionStorage pour récupération côté Python
                    sessionStorage.setItem('chat_paste_img', b64);
                    sessionStorage.setItem('chat_paste_ready', '1');
                };
                reader.readAsDataURL(file);
                return;
            }
        }
        pasteStatus.textContent = 'Aucune image détectée — utilisez le champ texte ci-dessous';
    }

    // Vider après envoi
    function clearPaste() {
        pasteB64.value = '';
        pasteCanvas.style.display = 'none';
        pasteZone.style.borderColor = '#90CAF9';
        pasteZone.innerHTML = '📸 Cliquez ici puis <strong>Ctrl+V</strong> pour coller une capture d\'écran';
        pasteStatus.textContent = '';
        sessionStorage.removeItem('chat_paste_img');
        sessionStorage.removeItem('chat_paste_ready');
    }
    </script>
    """, unsafe_allow_html=True)

    # Bouton pour envoyer l'image collée (hors formulaire Streamlit)
    col_paste_btn, col_paste_msg = st.columns([2, 3])
    with col_paste_btn:
        envoyer_paste = st.button("📸 Envoyer l'image collée", key="btn_send_paste",
                                   use_container_width=True)
    with col_paste_msg:
        legende_paste = st.text_input("Légende (optionnel)", key="chat_paste_legende",
                                       placeholder="Description de la capture...")

    if envoyer_paste:
        # Récupérer l'image depuis sessionStorage via un composant JS
        import streamlit.components.v1 as _cv1
        # On doit passer par st.session_state car JS ne peut pas appeler Python directement
        # Solution : afficher un message d'instruction
        st.info("💡 Fonctionnalité : copiez votre capture → cliquez la zone bleue → Ctrl+V → Envoyer l'image collée. "
                "Pour les navigateurs restrictifs, utilisez le bouton 📎 Joindre un fichier ci-dessous.")

    # ── Formulaire d'envoi ────────────────────────────────────────────────
    with st.form("form_chat_send", clear_on_submit=True):
        texte = st.text_input(
            "Message",
            placeholder=f"Écrivez un message... (canal : {canaux[canal_choix]})",
            label_visibility="collapsed",
            key="chat_input"
        )
        col_f, col_btn = st.columns([3, 1])
        with col_f:
            fichier = st.file_uploader(
                "📎 Joindre un fichier (optionnel)",
                type=["jpg","jpeg","png","gif","webp","pdf","docx","xlsx","txt","csv"],
                key="chat_file",
                label_visibility="visible"
            )
        with col_btn:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            envoyer = st.form_submit_button("📤 Envoyer", type="primary",
                                             use_container_width=True)

    if envoyer and (texte.strip() or fichier):
        # Upload fichier si présent
        f_path = f_nom = f_type = f_mime = ""
        if fichier:
            f_mime = fichier.type or "application/octet-stream"
            f_nom  = fichier.name
            f_type = "image" if f_mime.startswith("image/") else "document"
            f_path = upload_fichier(fichier.read(), f_nom, f_mime, user_email) or ""

        result = send_message_with_file(
            contenu=texte.strip(),
            user_email=user_email,
            user_nom=user_nom,
            propriete_id=prop_filter,
            fichier_nom=f_nom,
            fichier_path=f_path,
            fichier_type=f_type,
            fichier_mime=f_mime,
        )
        if result:
            st.session_state["chat_refresh"] += 1
            st.rerun()
        else:
            st.error("❌ Erreur lors de l'envoi.")
