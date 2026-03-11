"""
Page publique - Questionnaire de satisfaction client.
URL : https://votre-app.streamlit.app/Questionnaire?token=XXXX
"""
import streamlit as st
from datetime import datetime, timezone
from database.avis_repo import get_avis_by_token, submit_questionnaire, CRITERES

st.set_page_config(
    page_title="Votre avis",
    page_icon="⭐",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Masquer TOUT le chrome Streamlit
st.markdown("""
<style>
/* Toutes les versions de Streamlit */
[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="collapsedControl"],
[data-testid="stSidebarNavSeparator"],
section[data-testid="stSidebarNav"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
#MainMenu, header, footer,
button[data-testid="baseButton-header"],
.stDeployButton,
[data-testid="stAppViewBlockContainer"] > div:first-child > div:first-child > div:first-child > div[data-testid="stVerticalBlock"] > div:first-child {
    display: none !important;
    visibility: hidden !important;
    width: 0 !important;
    height: 0 !important;
    overflow: hidden !important;
}
.stApp > header { display: none !important; }
.stApp { background: #FAFAFA; }
.main .block-container {
    max-width: 680px;
    padding: 1rem 1.5rem 4rem 1.5rem;
    margin: 0 auto;
}
/* Forcer la largeur pleine sans sidebar */
.main { margin-left: 0 !important; }
section.main > div { padding-left: 1rem !important; }
</style>
""", unsafe_allow_html=True)

ETOILES = {1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐", 4: "⭐⭐⭐⭐", 5: "⭐⭐⭐⭐⭐"}

# ── Lire le token ─────────────────────────────────────────────────────────────
# Lecture robuste des query params (Streamlit Cloud peut retourner liste ou string)
_params = st.query_params
try:
    _token_raw = _params.get("token", "") or _params.get("Token", "")
    token = _token_raw[0] if isinstance(_token_raw, list) else str(_token_raw or "")
except Exception:
    token = ""

if not token:
    st.markdown("""
    <div style='text-align:center;padding:4rem 1rem'>
      <div style='font-size:56px'>❌</div>
      <h2 style='color:#C62828'>Lien invalide</h2>
      <p style='color:#666'>Utilisez le lien reçu par email ou WhatsApp.</p>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Récupérer l'avis depuis Supabase ─────────────────────────────────────────
avis = get_avis_by_token(token)

if avis is None:
    st.markdown("""
    <div style='text-align:center;padding:4rem 1rem'>
      <div style='font-size:56px'>❌</div>
      <h2 style='color:#C62828'>Lien invalide ou expiré</h2>
      <p style='color:#666'>Ce lien ne correspond à aucun questionnaire actif.</p>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Vérifier expiration ───────────────────────────────────────────────────────
if avis.get("token_expires_at"):
    try:
        exp = datetime.fromisoformat(avis["token_expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > exp:
            st.markdown("""
            <div style='text-align:center;padding:4rem 1rem'>
              <div style='font-size:56px'>⏰</div>
              <h2 style='color:#E65100'>Lien expiré</h2>
              <p style='color:#666'>Ce lien était valable 30 jours. Contactez votre hôte.</p>
            </div>""", unsafe_allow_html=True)
            st.stop()
    except Exception:
        pass

# ── Déjà rempli ───────────────────────────────────────────────────────────────
if avis.get("token_used"):
    nom  = avis.get("nom_client", "")
    note = avis.get("note", 5)
    st.markdown(f"""
    <div style='text-align:center;padding:3rem 1rem'>
      <div style='font-size:64px'>{ETOILES.get(note, "⭐")}</div>
      <h1 style='color:#2E7D32'>Merci {nom} !</h1>
      <p style='color:#555;font-size:16px'>
        Votre avis a déjà été enregistré.<br>
        Vous ne pouvez répondre qu'une seule fois.
      </p>
    </div>""", unsafe_allow_html=True)
    st.stop()

# ── Questionnaire ─────────────────────────────────────────────────────────────
nom = avis.get("nom_client", "")

st.markdown(f"""
<div style='text-align:center;margin-bottom:2rem;padding:1.5rem;
     background:linear-gradient(135deg,#1565C0,#1976D2);
     border-radius:16px;color:white'>
  <div style='font-size:48px'>🏠</div>
  <h1 style='color:white;margin:8px 0 4px 0;font-size:26px'>Votre avis compte !</h1>
  <p style='opacity:0.9;margin:0;font-size:15px'>
    Bonjour <b>{nom}</b>, merci pour votre séjour.<br>
    2 minutes pour partager votre expérience.
  </p>
</div>
""", unsafe_allow_html=True)

# Notes par critère
st.markdown("### ⭐ Évaluez votre séjour")

notes = {}
for col_key, label in CRITERES:
    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(f"<div style='padding-top:8px;font-weight:500'>{label}</div>",
                    unsafe_allow_html=True)
    with c2:
        notes[col_key] = st.select_slider(
            label, options=[1,2,3,4,5], value=5,
            format_func=lambda x: ETOILES[x],
            key=f"q_{col_key}", label_visibility="collapsed"
        )

note_globale = round(sum(notes.values()) / len(notes))
couleur = "#4CAF50" if note_globale >= 4 else "#FF9800" if note_globale == 3 else "#F44336"
st.markdown(f"""
<div style='background:{couleur}15;border:2px solid {couleur};border-radius:10px;
            padding:12px;text-align:center;margin:16px 0'>
  <b style='color:{couleur};font-size:18px'>
    Note globale : {ETOILES[note_globale]} {note_globale}/5
  </b>
</div>""", unsafe_allow_html=True)

st.divider()

# Commentaire
st.markdown("### 💬 Votre commentaire")
commentaire = st.text_area(
    "Décrivez votre séjour",
    height=120,
    placeholder="Excellent séjour ! Appartement très propre, bien équipé, vue magnifique...",
    key="q_comment", label_visibility="collapsed"
)

c1, c2 = st.columns(2)
with c1:
    points_forts = st.text_area("👍 Points forts", height=80,
                                 placeholder="Vue, literie, équipements...",
                                 key="q_forts")
with c2:
    ameliorations = st.text_area("💡 Suggestions", height=80,
                                  placeholder="Ce qui pourrait être amélioré...",
                                  key="q_amelio")

st.markdown("### 🔄 Recommanderiez-vous ce logement ?")
recommande = st.radio("", ["Oui, absolument !", "Oui, probablement", "Peut-être", "Non"],
                       horizontal=True, key="q_reco", label_visibility="collapsed")

st.divider()

if st.button("✅ Envoyer mon avis", type="primary", use_container_width=True):
    comment_final = commentaire or ""
    if points_forts:
        comment_final += f"\n\n👍 Points forts : {points_forts}"
    if ameliorations:
        comment_final += f"\n\n💡 Suggestions : {ameliorations}"
    comment_final += f"\n\n🔄 Recommande : {recommande}"

    reponses = {
        "note":        note_globale,
        "commentaire": comment_final.strip(),
        **notes,
    }

    if submit_questionnaire(token, reponses):
        st.balloons()
        st.markdown(f"""
        <div style='text-align:center;padding:2rem;background:#E8F5E9;
                    border-radius:16px;margin-top:1rem'>
          <div style='font-size:56px'>{ETOILES[note_globale]}</div>
          <h2 style='color:#2E7D32'>Merci {nom} !</h2>
          <p style='color:#555'>Votre avis a bien été enregistré.<br>
          Il aide les prochains voyageurs et nous aide à nous améliorer.</p>
        </div>""", unsafe_allow_html=True)
        st.stop()
    else:
        st.error("Une erreur s'est produite. Veuillez réessayer.")
