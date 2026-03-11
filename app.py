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
        layout="wide",
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
from components.sidebar import sidebar


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
    from pages import proprietes
except ImportError:
    proprietes = None

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
    from pages import questionnaire
except ImportError:
    questionnaire = None

page = sidebar()

if page == "Dashboard":       dashboard.show()
elif page == "Réservations":  reservations.show()
elif page == "Calendrier":    calendar.show()
elif page == "Analyses":      analytics.show()
elif page == "Créneaux":      gaps.show()
elif page == "Paiements":     paiements.show() if paiements else st.error("Uploadez pages/paiements.py")
elif page == "Ménage":        menage.show()    if menage    else st.error("Uploadez pages/menage.py")
elif page == "Messages":      messages.show() if messages  else st.error("Uploadez pages/messages.py")
elif page == "iCal":          ical_sync.show() if ical_sync else st.error("Uploadez pages/ical_sync.py")
elif page == "Propriétés":    proprietes.show() if proprietes else st.error("Uploadez pages/proprietes.py")
elif page == "Rapports":      rapport.show()    if rapport    else st.error("Uploadez pages/rapport.py")
elif page == "Tarifs":        tarifs.show()     if tarifs     else st.error("Uploadez pages/tarifs.py")
elif page == "Livre d'or":    avis.show()       if avis       else st.error("Uploadez pages/avis.py")
elif page == "Questionnaire": questionnaire.show() if questionnaire else st.error("Uploadez pages/questionnaire.py")
