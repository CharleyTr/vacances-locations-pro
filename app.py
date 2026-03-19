import streamlit as st

# ── QUESTIONNAIRE PUBLIC - intercepté en tout premier ─────────────────────────
# Le token arrive sur l'URL racine : https://app.streamlit.app/?token=XXX
# set_page_config DOIT être le tout premier appel Streamlit
_token = st.query_params.get("token", "")

if _token:
    # Mode questionnaire : page épurée sans sidebar
    st.set_page_config(
        page_title="Votre avis",
        page_icon="⭐",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown("""
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarNavItems"],
    [data-testid="collapsedControl"],
    #MainMenu, header, footer,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stDeployButton { display: none !important; }
    .main .block-container { max-width: 680px; margin: 0 auto; padding: 2rem 1.5rem; }
    .stApp { background: #FAFAFA; }
    </style>
    """, unsafe_allow_html=True)

    # Charger et afficher le questionnaire
    from datetime import datetime, timezone
    from database.avis_repo import get_avis_by_token, submit_questionnaire, CRITERES
    ETOILES = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}

    avis = get_avis_by_token(_token)

    if avis is None:
        st.markdown("""<div style='text-align:center;padding:4rem'>
        <div style='font-size:56px'>❌</div>
        <h2 style='color:#C62828'>Lien invalide ou expiré</h2>
        <p style='color:#666'>Ce lien ne correspond à aucun questionnaire actif.</p>
        </div>""", unsafe_allow_html=True)
        st.stop()

    if avis.get("token_expires_at"):
        try:
            exp = datetime.fromisoformat(avis["token_expires_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                st.markdown("""<div style='text-align:center;padding:4rem'>
                <div style='font-size:56px'>⏰</div>
                <h2 style='color:#E65100'>Lien expiré</h2>
                <p style='color:#666'>Ce lien était valable 30 jours.</p>
                </div>""", unsafe_allow_html=True)
                st.stop()
        except Exception:
            pass

    if avis.get("token_used"):
        note = avis.get("note", 5)
        st.markdown(f"""<div style='text-align:center;padding:3rem'>
        <div style='font-size:64px'>{ETOILES.get(note,"⭐")}</div>
        <h1 style='color:#2E7D32'>Merci {avis.get("nom_client","")} !</h1>
        <p style='color:#555'>Votre avis a déjà été enregistré.</p>
        </div>""", unsafe_allow_html=True)
        st.stop()

    # ── Formulaire questionnaire ───────────────────────────────────────────────
    nom = avis.get("nom_client", "")
    # Infos séjour depuis l'avis
    _prop_nom   = avis.get("_prop_nom", "")
    _plateforme = avis.get("plateforme", "")
    _date_arr   = (avis.get("date_sejour") or "")[:10]

    _sejour_info = ""
    if _prop_nom or _plateforme or _date_arr:
        parts = []
        if _prop_nom:   parts.append(f"🏠 {_prop_nom}")
        if _date_arr:   parts.append(f"📅 {_date_arr}")
        if _plateforme: parts.append(f"🔑 {_plateforme}")
        sep = " &nbsp;|&nbsp; "
    _sejour_info = "<p style='opacity:.8;font-size:13px;margin:4px 0 0 0'>" + sep.join(parts) + "</p>"

    st.markdown(f"""
    <div style='text-align:center;margin-bottom:2rem;padding:1.5rem;
         background:linear-gradient(135deg,#1565C0,#1976D2);
         border-radius:16px;color:white'>
      <div style='font-size:44px'>🏠</div>
      <h1 style='color:white;margin:8px 0 4px 0;font-size:22px'>
        🇫🇷 Votre avis compte !&nbsp;&nbsp;🇬🇧 Your review matters!
      </h1>
      <p style='opacity:.9;margin:4px 0 2px 0;font-size:15px'>
        🇫🇷 Bonjour <b>{nom}</b>, merci pour votre séjour. 2 minutes pour partager votre expérience.<br>
        🇬🇧 Hello <b>{nom}</b>, thank you for your stay. 2 minutes to share your experience.
      </p>
      {_sejour_info}
    </div>""", unsafe_allow_html=True)

    CRITERES_BILINGUES = {
        "note_proprete":     ("🧹 Propreté / Cleanliness"),
        "note_emplacement":  ("📍 Emplacement / Location"),
        "note_personnel":    ("👤 Personnel / Staff"),
        "note_confort":      ("🛋️ Confort / Comfort"),
        "note_equipements":  ("⚙️ Équipements / Amenities"),
        "note_qualite_prix": ("💶 Rapport qualité/prix / Value for money"),
    }

    st.markdown("### ⭐ Évaluez votre séjour / Rate your stay")
    notes = {}
    for col_key, label in CRITERES_BILINGUES.items():
        c1, c2 = st.columns([3, 3])
        with c1:
            st.markdown(f"<div style='padding-top:8px;font-weight:500;font-size:14px'>{label}</div>",
                        unsafe_allow_html=True)
        with c2:
            notes[col_key] = st.select_slider(
                label, options=[1,2,3,4,5], value=5,
                format_func=lambda x: ETOILES[x],
                key=f"q_{col_key}", label_visibility="collapsed"
            )

    note_globale = round(sum(notes.values()) / len(notes))
    couleur = "#4CAF50" if note_globale >= 4 else "#FF9800" if note_globale == 3 else "#F44336"
    st.markdown(f"""<div style='background:{couleur}18;border:2px solid {couleur};
        border-radius:10px;padding:12px;text-align:center;margin:16px 0'>
        <b style='color:{couleur};font-size:18px'>🇫🇷 Note globale / 🇬🇧 Overall score : {ETOILES[note_globale]} {note_globale}/5</b>
        </div>""", unsafe_allow_html=True)

    st.divider()
    st.markdown("### 💬 Votre commentaire / Your review")
    commentaire = st.text_area("Décrivez votre séjour", height=120,
        placeholder="🇫🇷 Excellent séjour, appartement très propre...  /  🇬🇧 Excellent stay, very clean apartment...",
        key="q_comment", label_visibility="collapsed")

    c1, c2 = st.columns(2)
    with c1:
        points_forts  = st.text_area("👍 Points forts", height=80,
                                      placeholder="Vue, literie, équipements...", key="q_forts")
    with c2:
        ameliorations = st.text_area("💡 Suggestions", height=80,
                                      placeholder="Ce qui pourrait être amélioré...", key="q_amelio")

    st.markdown("### 🔄 Recommanderiez-vous ce logement ? / Would you recommend this place?")
    recommande = st.radio("", ["Oui, absolument !", "Oui, probablement", "Peut-être", "Non"],
                           horizontal=True, key="q_reco", label_visibility="collapsed")

    st.divider()
    if st.button("✅ Envoyer mon avis / Submit my review", type="primary", use_container_width=True):
        comment_final = commentaire or ""
        if points_forts:   comment_final += f"\n\n👍 Points forts : {points_forts}"
        if ameliorations:  comment_final += f"\n\n💡 Suggestions : {ameliorations}"
        comment_final += f"\n\n🔄 Recommande : {recommande}"

        if submit_questionnaire(_token, {"note": note_globale,
                                         "commentaire": comment_final.strip(), **notes}):
            st.balloons()
            st.markdown(f"""<div style='text-align:center;padding:2rem;background:#E8F5E9;
                border-radius:16px;margin-top:1rem'>
                <div style='font-size:56px'>{ETOILES[note_globale]}</div>
                <h2 style='color:#2E7D32'>Merci {nom} !</h2>
                <p style='color:#555'>Votre avis a bien été enregistré.</p>
                </div>""", unsafe_allow_html=True)
            st.stop()
        else:
            st.error("Une erreur s'est produite. Veuillez réessayer.")
    st.stop()

# ── MODE NORMAL : application complète ────────────────────────────────────────
st.set_page_config(
    page_title="Vacances-Locations PRO",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded",
)
from components.sidebar import sidebar

# ── PAGE D'ACCUEIL — LOGIN PAR PROPRIÉTÉ ─────────────────────────────────────
import hashlib as _hashlib

def _hash_mdp(mdp: str) -> str:
    return _hashlib.sha256(mdp.strip().encode()).hexdigest()

def _show_splash_login():
    """
    Login hybride : supporte les deux modes simultanément.
    Mode A — Email/mot de passe Supabase Auth (nouveaux utilisateurs)
    Mode B — Code PIN propriété (mode actuel, rétrocompatible)
    """
    from database.proprietes_repo import fetch_all as _fetch_props
    import os

    st.markdown("""
    <style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="collapsedControl"],
    #MainMenu, footer { display: none !important; }
    .main .block-container { max-width: 420px; margin: 3rem auto; padding: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center; padding:1.5rem 0 1.5rem 0'>
        <div style='font-size:64px'>🏖️</div>
        <h1 style='font-size:2rem; margin:0.5rem 0 0.2rem 0; color:#1565C0'>
            Vacances-Locations Pro
        </h1>
        <p style='color:#666; font-size:0.9rem; margin:0'>
            Gestion locative
        </p>
    </div>
    """, unsafe_allow_html=True)

    props = [p for p in _fetch_props() if p.get("actif")]

    # Si aucune propriété n'a de mot de passe → accès direct admin
    if not props or all(not p.get("mot_de_passe") for p in props):
        st.session_state["global_logged_in"] = True
        st.session_state["is_admin"] = True
        st.rerun()
        return

    # ID admin = propriété marquée admin dans les secrets, ou Villa Tobias par défaut
    admin_prop_id = int(st.secrets.get("ADMIN_PROP_ID", os.environ.get("ADMIN_PROP_ID", 2)))

    # ── Choisir le mode de connexion ─────────────────────────────────
    mode = st.radio("Mode de connexion", ["🔑 Code d'accès", "📧 Email / Mot de passe"],
                    horizontal=True, key="login_mode", label_visibility="collapsed")

    if mode == "📧 Email / Mot de passe":
        # ── Mode Supabase Auth ────────────────────────────────────────
        with st.form("form_email_login"):
            email_input = st.text_input("📧 Email", placeholder="votre@email.fr")
            pwd_input   = st.text_input("🔑 Mot de passe", type="password")
            submitted_email = st.form_submit_button("🔓 Se connecter", type="primary",
                                                     use_container_width=True)

        if submitted_email:
            from database.auth_repo import sign_in_with_email, get_profile, get_proprietes_for_user
            result = sign_in_with_email(email_input, pwd_input)
            if result and result.get("user"):
                user = result["user"]
                profile = get_profile(str(user.id))
                role = profile.get("role","proprietaire") if profile else "proprietaire"
                is_admin = (role == "admin")

                # Récupérer les propriétés accessibles
                props_user = get_proprietes_for_user(str(user.id), role)
                prop_ids = [p["id"] for p in props_user]

                st.session_state["global_logged_in"] = True
                st.session_state["is_admin"] = is_admin
                st.session_state["auth_user_id"] = str(user.id)
                st.session_state["auth_user_email"] = user.email
                st.session_state["prop_id"] = 0 if is_admin else (prop_ids[0] if prop_ids else 0)
                for pid in prop_ids:
                    st.session_state[f"unlocked_{pid}"] = True
                if is_admin:
                    for p in props:
                        st.session_state[f"unlocked_{p['id']}"] = True
                st.rerun()
            else:
                st.error("❌ Email ou mot de passe incorrect.")
                # Bouton réinitialisation
                if st.button("🔑 Mot de passe oublié ?", key="btn_forgot"):
                    st.session_state["show_reset"] = True

        if st.session_state.get("show_reset"):
            with st.form("form_reset_pwd"):
                reset_email = st.text_input("📧 Votre email", key="reset_email_input")
                send_reset  = st.form_submit_button("📧 Envoyer le lien de réinitialisation",
                                                     use_container_width=True)
            if send_reset and reset_email:
                import requests as _req, os as _os
                _surl = st.secrets.get("SUPABASE_URL", _os.environ.get("SUPABASE_URL",""))
                _skey = st.secrets.get("SUPABASE_KEY", _os.environ.get("SUPABASE_KEY",""))
                _app  = st.secrets.get("APP_URL", _os.environ.get("APP_URL",""))
                try:
                    # redirect_to doit pointer vers la page HTML intermédiaire GitHub Pages
                    _github_redirect = st.secrets.get("AUTH_REDIRECT_URL",
                                       _os.environ.get("AUTH_REDIRECT_URL",
                                       "https://charleytr.github.io/vlp-auth/"))
                    r = _req.post(
                        f"{_surl}/auth/v1/recover",
                        headers={"apikey": _skey, "Content-Type": "application/json"},
                        json={"email": reset_email,
                              "redirect_to": _github_redirect},
                        timeout=10
                    )
                    if r.status_code in (200, 201):
                        st.success("✅ Email envoyé ! Vérifiez votre boîte de réception.")
                    else:
                        err = r.json().get("message","Erreur inconnue")
                        st.error(f"❌ {r.status_code} — {err}")
                    st.session_state.pop("show_reset", None)
                except Exception as e:
                    st.error(f"❌ Erreur réseau : {e}")

    else:
        # ── Mode PIN (rétrocompatible) ────────────────────────────────
        with st.form("form_pin_login"):
            pin_input = st.text_input(
                "🔑 Code d'accès",
                type="password",
                placeholder="Entrez votre code...",
                max_chars=20,
            )
            submitted = st.form_submit_button(
                "🔓 Accéder",
                type="primary",
                use_container_width=True
            )

        if submitted and pin_input:
            prop_trouvee = None
            for p in props:
                stored = p.get("mot_de_passe", "")
                if not stored: continue
                if _hash_mdp(pin_input) == stored or pin_input == stored:
                    prop_trouvee = p
                    break

            if prop_trouvee:
                pid = prop_trouvee["id"]
                is_admin = (pid == admin_prop_id)

                # Détecter si c'est le code gestionnaire
                stored_gest = prop_trouvee.get("mot_de_passe_gestionnaire","") or ""
                is_gestionnaire = (not is_admin and stored_gest and
                                   (_hash_mdp(pin_input) == stored_gest or pin_input == stored_gest))
                user_role = "admin" if is_admin else ("gestionnaire" if is_gestionnaire else "proprietaire")

                st.session_state["global_logged_in"] = True
                st.session_state["is_admin"]   = is_admin
                st.session_state["user_role"]  = user_role
                st.session_state["prop_id"]    = 0 if is_admin else pid
                if is_admin:
                    for p in props:
                        st.session_state[f"unlocked_{p['id']}"] = True
                else:
                    st.session_state[f"unlocked_{pid}"] = True
                try:
                    from database.journal_repo import log_connexion as _log_pin
                    _log_pin(mode="pin", statut="succes",
                             propriete_id=pid, propriete_nom=prop_trouvee.get("nom",""),
                             detail=user_role)
                except: pass
                st.rerun()
            else:
                try:
                    from database.journal_repo import log_connexion as _log_pin
                    _log_pin(mode="pin", statut="echec", detail="Code PIN incorrect")
                except: pass
                st.error("❌ Code incorrect.")

    st.markdown("""
    <div style='text-align:center; margin-top:2.5rem; color:#BBBBBB; font-size:0.75rem'>
        Développé par <strong>Charley Trigano</strong> — 2026
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center; margin-top:2.5rem; color:#AAAAAA; font-size:0.78rem'>
        Développé par <strong>Charley Trigano</strong> — 2026<br>
        <span style='font-size:0.72rem'>© Tous droits réservés</span>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not st.session_state.get("global_logged_in", False):
    _show_splash_login()


from pages import dashboard, reservations, calendar, analytics, gaps

try:
    from pages import paiements
except ImportError:
    paiements = None
try:
    from pages import menage
except ImportError:
    menage = None
try:
    from pages import messages
except ImportError:
    messages = None
try:
    from pages import ical_sync
except ImportError:
    ical_sync = None
try:
    from pages import proprietes as _page_proprietes
except ImportError:
    _page_proprietes = None
proprietes = _page_proprietes

try:
    from pages import rapport
except ImportError:
    rapport = None

try:
    from pages import tarifs
except ImportError:
    tarifs = None

try:
    from pages import avis
except ImportError:
    avis = None

try:
    from pages import import_booking
except ImportError:
    import_booking = None

try:
    from pages import import_airbnb
except ImportError:
    import_airbnb = None

try:
    from pages import templates
except ImportError:
    templates = None

try:
    from pages import export_comptable
except ImportError:
    export_comptable = None
try:
    from pages import fiscal
except ImportError:
    fiscal = None
try:
    from pages import pricing
except ImportError:
    pricing = None
try:
    from pages import baremes
except ImportError:
    baremes = None
try:
    from pages import documentation
except ImportError:
    documentation = None
try:
    from pages import factures
except ImportError:
    factures = None
try:
    from pages import journal
except ImportError:
    journal = None
try:
    from pages import chat
except ImportError:
    chat = None
try:
    from pages import mon_profil
except ImportError:
    mon_profil = None
try:
    from pages import utilisateurs
except ImportError:
    utilisateurs = None

try:
    from pages import questionnaire
except ImportError:
    questionnaire = None

page = sidebar()

# ── Vérification propriété depuis sidebar (si changement) ────────────────────
# Les admins ont accès à tout, les autres uniquement à leur propriété
_is_admin = st.session_state.get("is_admin", False)
if not _is_admin:
    # Pour les non-admins : s'assurer que prop_id est bien leur propriété
    from database.proprietes_repo import fetch_all as _fetch_props
    _props_unlocked = [p["id"] for p in _fetch_props()
                       if st.session_state.get(f"unlocked_{p['id']}", False)]
    if _props_unlocked:
        # Utiliser une clé différente pour ne pas conflicter avec le widget sidebar
        _current = st.session_state.get("prop_id", _props_unlocked[0])
        if _current not in _props_unlocked:
            # Forcer via rerun après avoir stocké dans une clé intermédiaire
            st.session_state["_forced_prop_id"] = _props_unlocked[0]
            st.rerun()
        elif st.session_state.get("_forced_prop_id"):
            st.session_state.pop("_forced_prop_id", None)

if page == "Dashboard":       dashboard.show()
elif page == "Réservations":  reservations.show()
elif page == "Calendrier":    calendar.show()
elif page == "Analyses":      analytics.show()
elif page == "Créneaux":      gaps.show()
elif page == "Paiements":     paiements.show() if paiements else st.error("Uploadez pages/paiements.py")
elif page == "Ménage":        menage.show()    if menage    else st.error("Uploadez pages/menage.py")
elif page == "Messages":      messages.show() if messages  else st.error("Uploadez pages/messages.py")
elif page == "iCal":          ical_sync.show() if ical_sync else st.error("Uploadez pages/ical_sync.py")
elif page == "Propriétés":    _page_proprietes.show() if _page_proprietes else st.error("Uploadez pages/proprietes.py")
elif page == "Rapports":      rapport.show()    if rapport    else st.error("Uploadez pages/rapport.py")
elif page == "Tarifs":        tarifs.show()     if tarifs     else st.error("Uploadez pages/tarifs.py")
elif page == "Livre d'or":    avis.show()       if avis       else st.error("Uploadez pages/avis.py")
elif page == "Import Booking": import_booking.show() if import_booking else st.error("Uploadez pages/import_booking.py")
elif page == "Import Airbnb":  import_airbnb.show()  if import_airbnb  else st.error("Uploadez pages/import_airbnb.py")
elif page == "Modèles msgs":  templates.show()      if templates      else st.error("Uploadez pages/templates.py")
elif page == "Export comptable": export_comptable.show() if export_comptable else st.error("Uploadez pages/export_comptable.py")
elif page == "Fiscal LMNP":      fiscal.show()           if fiscal          else st.error("Uploadez pages/fiscal.py")
elif page == "Revenus & Pricing": pricing.show()          if pricing         else st.error("Uploadez pages/pricing.py")
elif page == "Barèmes fiscaux":   baremes.show()          if baremes         else st.error("Uploadez pages/baremes.py")
elif page == "Documentation":     documentation.show()    if documentation   else st.error("Uploadez pages/documentation.py")
elif page == "Factures":          factures.show()         if factures         else st.error("Uploadez pages/factures.py")
elif page == "Utilisateurs":      utilisateurs.show()     if utilisateurs     else st.error("Uploadez pages/utilisateurs.py")
elif page == "Journal":           journal.show()          if journal          else st.error("Uploadez pages/journal.py")
elif page == "Chat":              chat.show()
elif page == "Mon profil":        mon_profil.show()       if mon_profil       else st.error("Uploadez pages/mon_profil.py")
elif page == "Questionnaire": questionnaire.show() if questionnaire else st.error("Uploadez pages/questionnaire.py")
