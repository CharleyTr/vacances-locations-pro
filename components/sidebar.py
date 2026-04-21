import streamlit as st
from database.supabase_client import is_connected, get_connection_error
from services.proprietes_service import get_proprietes_dict
from database.proprietes_repo import fetch_all
from services.auth_service import is_unlocked, lock

PAGES = {
    "📊 Dashboard":      "Dashboard",
    "📋 Réservations":   "Réservations",
    "📅 Calendrier":     "Calendrier",
    "📈 Analyses":       "Analyses",
    "💳 Paiements":      "Paiements",
    "🧹 Ménage":         "Ménage",
    "📋 DADS":           "DADS",
    "📄 Contrats":          "Contrats",
    "📧 Messages":       "Messages",
    "💬 Chat":            "Chat",
    "🔄 Sync iCal":      "iCal",
    "🕳️ Créneaux":      "Créneaux",
    "🏠 Propriétés":     "Propriétés",
    "📊 Rapports":       "Rapports",
    "💶 Tarifs":         "Tarifs",
    "🎪 Événements":      "Événements",
    "⭐ Livre d'or":     "Livre d'or",
    "📥 Import Booking": "Import Booking",
    "📥 Import Airbnb":  "Import Airbnb",
    "📝 Modèles msgs":   "Modèles msgs",
    "📊 Export comptable": "Export comptable",
    "🏛️ Fiscal LMNP":      "Fiscal LMNP",
    "📈 Revenus & Pricing": "Revenus & Pricing",
    "📐 Barèmes fiscaux":    "Barèmes fiscaux",
    "👥 Utilisateurs":       "Utilisateurs",
    "📋 Journal":            "Journal",
    "💾 Sauvegarde":         "Sauvegarde",
    "🔧 Corrections":         "Corrections",
    "👤 Mon profil":         "Mon profil",
    "🧾 Factures":           "Factures",
    "📖 Documentation":      "Documentation",
}


def sidebar() -> str:
    with st.sidebar:
        _prop_id_sidebar = st.session_state.get("prop_id", 0) or 0
        _is_demo_mode     = _prop_id_sidebar == 5
        try:
            _type_sidebar    = _props_full.get(_prop_id_sidebar, {}).get("type_client", "particulier") or "particulier"
            _is_demo_pro_sb  = _type_sidebar in ("pro", "demo_pro")
        except:
            _is_demo_pro_sb  = 6 <= _prop_id_sidebar <= 25

        if _is_demo_pro_sb:
            st.markdown("""
            <div style='background:linear-gradient(135deg,#7C3AED,#0B1F3A);
                        border-radius:12px;padding:14px;margin-bottom:8px;text-align:center'>
              <div style='font-size:20px;font-weight:900;color:white;
                          font-family:Georgia,serif'>LodgePro <span style="color:#F0B429">Pro</span></div>
              <div style='font-size:10px;color:#A78BFA;font-weight:600;
                          letter-spacing:2px;margin-top:2px'>DÉMO CONCIERGERIE</div>
            </div>
            <div style='background:#7C3AED;color:white;border-radius:8px;
                        padding:8px 12px;font-size:11px;font-weight:600;
                        text-align:center;margin-bottom:8px'>
              🏢 Riviera Conciergerie<br>
              <span style='font-weight:400;font-size:10px'>20 propriétés — Côte d'Azur</span>
            </div>
            <div style='background:#0B1F3A;border:1px solid #7C3AED;border-radius:8px;
                        padding:10px 12px;text-align:center;margin-bottom:8px'>
              <div style='color:rgba(255,255,255,0.6);font-size:10px;margin-bottom:6px'>
                Convaincu ? Découvrez nos tarifs Pro
              </div>
              <a href="https://pro.lodgepro.eu#tarifs" target="_blank"
                 style='display:block;background:#7C3AED;color:white;
                        padding:8px;border-radius:6px;font-weight:700;
                        font-size:12px;text-decoration:none'>
                💳 Voir les tarifs Pro →
              </a>
            </div>""", unsafe_allow_html=True)
        elif _is_demo_mode:
            st.markdown("""
            <div style='background:linear-gradient(135deg,#1565C0,#0B1F3A);
                        border-radius:12px;padding:14px;margin-bottom:8px;text-align:center'>
              <div style='font-size:22px;font-weight:900;color:white;
                          font-family:Georgia,serif'>🏖️ LodgePro</div>
              <div style='font-size:10px;color:#F0B429;font-weight:600;
                          letter-spacing:2px;margin-top:2px'>DÉMONSTRATION</div>
            </div>
            <div style='background:#F0B429;color:#0B1F3A;border-radius:8px;
                        padding:8px 12px;font-size:11px;font-weight:600;
                        text-align:center;margin-bottom:8px'>
              ✨ Bienvenue sur LodgePro !<br>
              <span style='font-weight:400'>Explorez toutes les fonctionnalités</span>
            </div>
            <div style='background:#0B1F3A;border:1px solid #F0B429;border-radius:8px;
                        padding:10px 12px;text-align:center;margin-bottom:8px'>
              <div style='color:rgba(255,255,255,0.6);font-size:10px;margin-bottom:6px'>
                Convaincu ? Passez à l'abonnement
              </div>
              <a href="https://lodgepro.eu#tarifs" target="_blank"
                 style='display:block;background:#F0B429;color:#0B1F3A;
                        padding:8px;border-radius:6px;font-weight:700;
                        font-size:12px;text-decoration:none'>
                💳 Voir les tarifs →
              </a>
            </div>""", unsafe_allow_html=True)
        else:
            st.title("🏖️ Vacances-Locations")
        st.caption("PRO — Gestion locative")

        if is_connected():
            st.success("🟢 Supabase connecté", icon="✅")
        else:
            err = get_connection_error()
            st.error("🔴 Supabase non connecté")
            if err:
                st.caption(f"⚠️ {err}")

        st.divider()
        st.markdown("**🏠 Propriété active**")

        props = get_proprietes_dict()  # {1: "Le Turenne...", 2: "Villa Tobias..."}
        options_ids    = [0] + list(props.keys())
        options_labels = ["🏠 Toutes"] + list(props.values())

        # key="prop_id" → Streamlit écrit DIRECTEMENT la valeur sélectionnée
        # (l'un des options_ids) dans st.session_state["prop_id"]
        # Pas de index=, pas de callback, pas de rerun — Streamlit gère tout seul
        # Non-admin : forcer la propriété déverrouillée, désactiver la sélection
        _forced = st.session_state.get("_forced_prop_id")
        _is_admin_sidebar = st.session_state.get("is_admin", False)

        if _forced and not _is_admin_sidebar and _forced in options_ids:
            # Afficher juste le nom sans selectbox
            idx_forced = options_ids.index(_forced)
            st.markdown(f"**{options_labels[idx_forced]}**")
            # Synchroniser sans toucher au widget
            if st.session_state.get("prop_id") != _forced:
                st.session_state["prop_id"] = _forced
        else:
            st.selectbox(
                "prop_sidebar",
                options=options_ids if _is_admin_sidebar else
                        [i for i in options_ids if i == 0 or
                         st.session_state.get(f"unlocked_{i}", False)],
                format_func=lambda x: options_labels[options_ids.index(x)],
                key="prop_id",
                label_visibility="collapsed",
            )

        current = st.session_state.get("prop_id", 0)
        if current and current != 0:
            # Vérifier si mot de passe configuré
            props_full = {p["id"]: p for p in fetch_all()}
            mdp_hash = props_full.get(current, {}).get("mot_de_passe")
            if mdp_hash:
                if is_unlocked(current):
                    col_cap, col_lock = st.columns([3,1])
                    col_cap.caption(f"📍 {props.get(current, '')}")
                    if col_lock.button("🔒", key="btn_lock", help="Verrouiller"):
                        lock(current)
                        st.rerun()
                else:
                    st.caption(f"🔐 {props.get(current, '')} — *verrouillé*")
            else:
                st.caption(f"📍 {props.get(current, '')}")

        st.divider()

        # Pages admin uniquement (Villa Tobias)
        PAGES_ADMIN_ONLY  = {"📐 Barèmes fiscaux", "👥 Utilisateurs", "📋 Journal", "💾 Sauvegarde", "🔧 Corrections"}
        PAGES_DEMO_HIDDEN = {"🔄 Sync iCal", "📥 Import Booking", "📥 Import Airbnb", "💾 Sauvegarde", "🔧 Corrections", "👥 Utilisateurs", "📋 Journal"}

        # Pages pour les conciergeries Pro
        PAGES_PRO = {
            "📊 Dashboard":         "Dashboard",
            "📋 Réservations":      "Réservations",
            "📅 Calendrier":        "Calendrier",
            "📈 Analyses":          "Analyses",
            "🧹 Ménage":            "Ménage",
            "📋 DADS":              "DADS",
            "📄 Contrats":          "Contrats",
            "📧 Messages":          "Messages",
            "💬 Chat":              "Chat",
            "🏠 Propriétés":        "Propriétés",
            "📊 Rapports":          "Rapports",
            "👤 Mon profil":        "Mon profil",
            "📖 Documentation":     "Documentation",
        }

        is_admin   = st.session_state.get("is_admin", False)
        _user_role = st.session_state.get("user_role", "proprietaire")

        # Détecter si c'est un client Pro via type_client
        _prop_id_cur = st.session_state.get("prop_id", 0) or 0
        try:
            from database.proprietes_repo import fetch_all as _fa_sb
            _props_full  = {p["id"]: p for p in _fa_sb()}
            _prop_cur    = _props_full.get(_prop_id_cur, {})
            _type_client = _prop_cur.get("type_client", "particulier") or "particulier"
            _is_pro_client = _type_client in ("pro", "demo_pro")
        except:
            _is_pro_client = False

        # Pages visibles uniquement pour gestionnaire
        PAGES_GESTIONNAIRE = {
            "📊 Dashboard", "📋 Réservations", "📅 Calendrier",
            "🧹 Ménage", "📋 DADS", "📧 Messages", "👤 Mon profil", "📖 Documentation"
        }

        if is_admin:
            pages_visibles = dict(PAGES)
        elif _is_pro_client:
            # Conciergerie Pro — menu adapté
            pages_visibles = dict(PAGES_PRO)
        elif _user_role == "gestionnaire":
            pages_visibles = {k: v for k, v in PAGES.items()
                              if k in PAGES_GESTIONNAIRE}
        else:
            # Propriétaire particulier : tout sauf pages admin
            pages_visibles = {k: v for k, v in PAGES.items()
                              if k not in PAGES_ADMIN_ONLY}

        # Mode démo particulier : cacher les pages techniques
        if _prop_id_cur == 5:
            pages_visibles = {k: v for k, v in pages_visibles.items()
                              if k not in PAGES_DEMO_HIDDEN}

        # Mode démo Pro (prop_id dans 6-25) : branding Pro
        _is_demo_pro = _type_client in ("demo_pro",)
        if _is_demo_pro and not is_admin:
            pages_visibles = {k: v for k, v in PAGES_PRO.items()
                              if k not in PAGES_DEMO_HIDDEN}

        choice = st.radio(
            "Navigation",
            list(pages_visibles.keys()),
            label_visibility="collapsed",
        )
        # ── Badge non-lus Chat ───────────────────────────────────────────
        try:
            from database.supabase_client import get_supabase as _get_sb
            _auteur = st.session_state.get("auth_user_email") or                       st.session_state.get("chat_auteur_nom") or                       f"pin_{st.session_state.get('prop_id', 0)}"
            _prop_id_sb = st.session_state.get("prop_id", 0) or None
            _sb = _get_sb()
            if _sb and _auteur:
                _q = _sb.table("messages_internes").select("id, lu_par, auteur")
                if _prop_id_sb:
                    _q = _q.eq("propriete_id", _prop_id_sb)
                else:
                    _q = _q.is_("propriete_id", None)
                _rows = _q.execute().data or []
                _unread = sum(1 for r in _rows
                              if _auteur not in (r.get("lu_par") or [])
                              and r.get("auteur") != _auteur)
                if _unread > 0:
                    st.markdown(
                        f"<div style='background:#E53935;color:white;border-radius:12px;"
                        f"padding:4px 12px;font-size:12px;font-weight:bold;text-align:center;"
                        f"margin-bottom:6px'>💬 {_unread} nouveau(x) message(s)</div>",
                        unsafe_allow_html=True
                    )
                    _current_page = st.session_state.get("current_page", "")
                    if _current_page != "Chat":
                        if st.button("💬 Voir les messages", key="btn_goto_chat",
                                      use_container_width=True, type="primary"):
                            st.session_state["nav_page"] = "Chat"
                            st.rerun()
        except: pass

        st.divider()
        # ── Bouton installation PWA ───────────────────────────────────────
        st.markdown("""
<div style='margin-bottom:8px'>
  <button id='pwa-install-btn' onclick='installPWA()'
    style='display:none;width:100%;padding:8px 12px;background:#1565C0;color:white;
           border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:bold'>
    📲 Installer l'application
  </button>
</div>
<p style='font-size:11px;color:#888;margin:0 0 4px 0'>
  📱 iPhone : Safari → <strong>Partager</strong> → <em>Sur l'écran d'accueil</em><br>
  🤖 Android : Menu → <em>Ajouter à l'écran</em>
</p>
""", unsafe_allow_html=True)
        # Infos utilisateur connecté
        auth_email = st.session_state.get("auth_user_email")
        if auth_email:
            st.markdown(
                f"<div style='font-size:11px;color:var(--text-color);opacity:0.6;"
                f"padding:2px 0;overflow:hidden;text-overflow:ellipsis'>"
                f"👤 {auth_email}</div>",
                unsafe_allow_html=True
            )
        # Bouton déconnexion visible pour TOUS (mode PIN ou email)
        if st.button("🚪 Déconnexion", key="btn_logout", use_container_width=True):
            # Effacer localStorage via JS
            import streamlit.components.v1 as _cv_logout
            _cv_logout.html("""
            <script>
            localStorage.removeItem('vlp_session');
            // Nettoyer l'URL de tout paramètre de session
            var url = window.location.origin + window.location.pathname;
            window.location.replace(url);
            </script>
            """, height=0)
            from services.auth_service import logout
            logout()
            st.rerun()
        # ── Mouchard sessions actives (admin only) ──────────────────
        if st.session_state.get("is_admin", False):
            try:
                from database.sessions_repo import get_sessions_actives
                sessions = get_sessions_actives()
                nb = len(sessions)
                if nb > 1:
                    st.markdown(
                        f"<div style='font-size:11px;color:#4CAF50;padding:2px 0'>"
                        f"🟢 <b>{nb}</b> connecté(s) en ce moment</div>",
                        unsafe_allow_html=True
                    )
                    with st.expander(f"👥 Voir ({nb})", expanded=False):
                        for s in sessions:
                            role = s.get("user_role", "")
                            role_icon = "👑" if role == "admin" else ("🔑" if role == "gestionnaire" else "🏠")
                            page_s  = s.get("page_courante", "")
                            email_s = s.get("user_email", "")
                            prop_id = s.get("prop_id", 0)
                            # Afficher email ou rôle+propriété selon le mode de connexion
                            if email_s and email_s != "anonyme":
                                label = email_s
                            else:
                                label = f"{role or 'utilisateur'}"
                                if prop_id:
                                    # Trouver le nom de la propriété
                                    try:
                                        from database.proprietes_repo import fetch_all as _fp
                                        _props = {p["id"]: p["nom"] for p in _fp()}
                                        prop_nom = _props.get(int(prop_id), f"prop {prop_id}")
                                        label += f" — {prop_nom}"
                                    except:
                                        label += f" — prop {prop_id}"
                            st.caption(f"{role_icon} {label} › {page_s}")
                else:
                    st.markdown(
                        "<div style='font-size:11px;color:#9CA3AF;padding:2px 0'>"
                        "🟢 Vous êtes seul connecté</div>",
                        unsafe_allow_html=True
                    )
            except Exception:
                pass
        # ── Bouton WhatsApp groupe ────────────────────────────────────
        st.markdown("""
        <a href="https://chat.whatsapp.com/F7XaE9wpctMLnqK7ZRP" target="_blank"
           style="text-decoration:none">
          <div style="background:#25D366;color:white;border-radius:8px;
                      padding:8px 12px;text-align:center;font-size:13px;
                      font-weight:600;margin:4px 0;cursor:pointer">
            💬 Chat équipe WhatsApp
          </div>
        </a>
        """, unsafe_allow_html=True)

        st.caption("v3.2 — 2026 · © Charley Trigano")

    return pages_visibles[choice]
