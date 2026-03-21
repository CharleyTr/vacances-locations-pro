import streamlit as st
# ── QUESTIONNAIRE PUBLIC - intercepté en tout premier ─────────────────────────
_token = st.query_params.get("token", "")
if _token:
    st.set_page_config(page_title="Votre avis", page_icon="⭐", layout="centered", initial_sidebar_state="collapsed")
    st.markdown("""<style>[data-testid="stSidebar"],[data-testid="stSidebarNav"],[data-testid="stSidebarNavItems"],[data-testid="collapsedControl"],#MainMenu,header,footer,[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],.stDeployButton{display:none!important}.main .block-container{max-width:680px;margin:0 auto;padding:2rem 1.5rem}.stApp{background:#FAFAFA}</style>""", unsafe_allow_html=True)
    from datetime import datetime, timezone
    from database.avis_repo import get_avis_by_token, submit_questionnaire, CRITERES
    ETOILES = {1:"⭐",2:"⭐⭐",3:"⭐⭐⭐",4:"⭐⭐⭐⭐",5:"⭐⭐⭐⭐⭐"}
    avis = get_avis_by_token(_token)
    if avis is None:
        st.markdown("<div style='text-align:center;padding:4rem'><div style='font-size:56px'>❌</div><h2 style='color:#C62828'>Lien invalide ou expiré</h2></div>", unsafe_allow_html=True)
        st.stop()
    if avis.get("token_expires_at"):
        try:
            exp = datetime.fromisoformat(avis["token_expires_at"].replace("Z","+00:00"))
            if datetime.now(timezone.utc) > exp:
                st.markdown("<div style='text-align:center;padding:4rem'><div style='font-size:56px'>⏰</div><h2 style='color:#E65100'>Lien expiré</h2></div>", unsafe_allow_html=True)
                st.stop()
        except: pass
    if avis.get("token_used"):
        note = avis.get("note",5)
        st.markdown(f"<div style='text-align:center;padding:3rem'><div style='font-size:64px'>{ETOILES.get(note,'⭐')}</div><h1 style='color:#2E7D32'>Merci {avis.get('nom_client','')} !</h1><p>Votre avis a déjà été enregistré.</p></div>", unsafe_allow_html=True)
        st.stop()
    nom = avis.get("nom_client","")
    _prop_nom=avis.get("_prop_nom",""); _plateforme=avis.get("plateforme",""); _date_arr=(avis.get("date_sejour") or "")[:10]
    parts=[]; 
    if _prop_nom: parts.append(f"🏠 {_prop_nom}")
    if _date_arr: parts.append(f"📅 {_date_arr}")
    if _plateforme: parts.append(f"🔑 {_plateforme}")
    sep=" &nbsp;|&nbsp; "
    _sejour_info=f"<p style='opacity:.8;font-size:13px;margin:4px 0 0 0'>{sep.join(parts)}</p>" if parts else ""
    st.markdown(f"""<div style='text-align:center;margin-bottom:2rem;padding:1.5rem;background:linear-gradient(135deg,#1565C0,#1976D2);border-radius:16px;color:white'><div style='font-size:44px'>🏠</div><h1 style='color:white;margin:8px 0 4px 0;font-size:22px'>🇫🇷 Votre avis compte !&nbsp;&nbsp;🇬🇧 Your review matters!</h1><p style='opacity:.9;margin:4px 0 2px 0;font-size:15px'>🇫🇷 Bonjour <b>{nom}</b>, merci pour votre séjour.<br>🇬🇧 Hello <b>{nom}</b>, thank you for your stay.</p>{_sejour_info}</div>""", unsafe_allow_html=True)
    CRITERES_BILINGUES={"note_proprete":"🧹 Propreté / Cleanliness","note_emplacement":"📍 Emplacement / Location","note_personnel":"👤 Personnel / Staff","note_confort":"🛋️ Confort / Comfort","note_equipements":"⚙️ Équipements / Amenities","note_qualite_prix":"💶 Rapport qualité/prix / Value for money"}
    st.markdown("### ⭐ Évaluez votre séjour / Rate your stay")
    notes={}
    for col_key,label in CRITERES_BILINGUES.items():
        c1,c2=st.columns([3,3])
        with c1: st.markdown(f"<div style='padding-top:8px;font-weight:500;font-size:14px'>{label}</div>",unsafe_allow_html=True)
        with c2: notes[col_key]=st.select_slider(label,options=[1,2,3,4,5],value=5,format_func=lambda x:ETOILES[x],key=f"q_{col_key}",label_visibility="collapsed")
    note_globale=round(sum(notes.values())/len(notes))
    couleur="#4CAF50" if note_globale>=4 else "#FF9800" if note_globale==3 else "#F44336"
    st.markdown(f"<div style='background:{couleur}18;border:2px solid {couleur};border-radius:10px;padding:12px;text-align:center;margin:16px 0'><b style='color:{couleur};font-size:18px'>🇫🇷 Note globale / 🇬🇧 Overall score : {ETOILES[note_globale]} {note_globale}/5</b></div>",unsafe_allow_html=True)
    st.divider()
    st.markdown("### 💬 Votre commentaire / Your review")
    commentaire=st.text_area("Décrivez votre séjour",height=120,placeholder="🇫🇷 Excellent séjour...  /  🇬🇧 Excellent stay...",key="q_comment",label_visibility="collapsed")
    c1,c2=st.columns(2)
    with c1: points_forts=st.text_area("👍 Points forts",height=80,placeholder="Vue, literie...",key="q_forts")
    with c2: ameliorations=st.text_area("💡 Suggestions",height=80,placeholder="Ce qui pourrait être amélioré...",key="q_amelio")
    st.markdown("### 🔄 Recommanderiez-vous ce logement ? / Would you recommend this place?")
    recommande=st.radio("",["Oui, absolument !","Oui, probablement","Peut-être","Non"],horizontal=True,key="q_reco",label_visibility="collapsed")
    st.divider()
    if st.button("✅ Envoyer mon avis / Submit my review",type="primary",use_container_width=True):
        comment_final=commentaire or ""
        if points_forts: comment_final+=f"\n\n👍 Points forts : {points_forts}"
        if ameliorations: comment_final+=f"\n\n💡 Suggestions : {ameliorations}"
        comment_final+=f"\n\n🔄 Recommande : {recommande}"
        if submit_questionnaire(_token,{"note":note_globale,"commentaire":comment_final.strip(),**notes}):
            st.balloons()
            st.markdown(f"<div style='text-align:center;padding:2rem;background:#E8F5E9;border-radius:16px;margin-top:1rem'><div style='font-size:56px'>{ETOILES[note_globale]}</div><h2 style='color:#2E7D32'>Merci {nom} !</h2><p>Votre avis a bien été enregistré.</p></div>",unsafe_allow_html=True)
            st.stop()
        else: st.error("Une erreur s'est produite. Veuillez réessayer.")
    st.stop()

# ── MODE NORMAL ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Vacances-Locations PRO", page_icon="🏖️", layout="wide", initial_sidebar_state="expanded")

# ── CSS Dark Mode global ──────────────────────────────────────────────────────
st.markdown("""
<style>
@media (prefers-color-scheme: dark) {
    [style*="background:#E3F2FD"],[style*="background: #E3F2FD"]{background:var(--bg-info,#0D2137)!important}
    [style*="background:#F0F4FF"],[style*="background: #F0F4FF"]{background:#1E2A3A!important}
    [style*="background:#F8FBFF"],[style*="background: #F8FBFF"]{background:#1A2332!important}
    [style*="background:#FAFAFA"],[style*="background: #FAFAFA"]{background:#1A1A2E!important}
    [style*="background:#FFF8E1"],[style*="background: #FFF8E1"]{background:#2A1F00!important}
    [style*="background:#FFEBEE"],[style*="background: #FFEBEE"]{background:#2A0D0D!important}
    [style*="background:#E8F5E9"],[style*="background: #E8F5E9"]{background:#0D2818!important}
    [style*="background:#F5F5F5"],[style*="background: #F5F5F5"]{background:#1E1E1E!important}
    [style*="color:#222"],[style*="color: #222"]{color:#E0E0E0!important}
    [style*="color:#333"],[style*="color: #333"]{color:#CCCCCC!important}
    [style*="color:#555"],[style*="color: #555"]{color:#AAAAAA!important}
    [style*="color:#666"],[style*="color: #666"]{color:#999999!important}
    .bubble-other{background:#1E2D3D!important;color:#E0E0E0!important}
    .cal-cell{background:#1A2332!important;border-color:#2D3748!important}
    .cal-cell.empty{background:#111827!important}
    .cal-cell.today{background:#0D2137!important;border-color:#4A90D9!important}
}
</style>
""", unsafe_allow_html=True)

# ── Page création de mot de passe (invitation + reset) ────────────────────────
import streamlit.components.v1 as _components
_components.html("""
<script>
(function() {
    var hash = window.location.hash || parent.location.hash;
    if (!hash) {
        try {
            var t = localStorage.getItem('_vlp_token');
            if (t) {
                var ty = localStorage.getItem('_vlp_type') || 'recovery';
                localStorage.removeItem('_vlp_token'); localStorage.removeItem('_vlp_type');
                parent.window.location.replace(parent.window.location.origin + parent.window.location.pathname + '?sb_token=' + encodeURIComponent(t) + '&sb_type=' + encodeURIComponent(ty));
            }
        } catch(e) {}
        return;
    }
    var params = new URLSearchParams(hash.replace(/^#/, ''));
    var token = params.get('access_token');
    var type  = params.get('type') || 'recovery';
    if (!token) return;
    try { localStorage.setItem('_vlp_token', token); localStorage.setItem('_vlp_type', type); } catch(e) {}
    parent.window.location.replace(parent.window.location.origin + parent.window.location.pathname + '?sb_token=' + encodeURIComponent(token) + '&sb_type=' + encodeURIComponent(type));
})();
</script>
""", height=0)

_qp = st.query_params
_sb_token = _qp.get("sb_token", "").strip()
_sb_type  = _qp.get("sb_type", "recovery").strip()

if _sb_token:
    st.markdown("""<style>[data-testid="stSidebar"],[data-testid="stSidebarNav"],[data-testid="collapsedControl"],#MainMenu,footer{display:none!important}.main .block-container{max-width:460px;margin:3rem auto;padding:2rem}</style>""", unsafe_allow_html=True)
    titre = "Bienvenue — Créez votre mot de passe" if _sb_type == "invite" else "Réinitialiser votre mot de passe"
    st.markdown(f"<div style='text-align:center;padding:1.5rem 0 1rem'><div style='font-size:56px'>🏖️</div><h2 style='color:#1565C0;margin:0.5rem 0 0.2rem'>{titre}</h2><p style='color:#666;font-size:0.9rem'>Vacances-Locations Pro</p></div>", unsafe_allow_html=True)
    import requests as _req, os as _os
    _surl = st.secrets.get("SUPABASE_URL", _os.environ.get("SUPABASE_URL",""))
    _skey = st.secrets.get("SUPABASE_KEY", _os.environ.get("SUPABASE_KEY",""))
    if _sb_type in ("magiclink", "signup", "email"):
        with st.spinner("Connexion en cours..."):
            try:
                r = _req.get(f"{_surl}/auth/v1/user", headers={"apikey":_skey,"Authorization":f"Bearer {_sb_token}"}, timeout=10)
                if r.status_code == 200:
                    user_data=r.json(); user_id=user_data.get("id",""); user_email=user_data.get("email","")
                    from database.auth_repo import get_profile, get_proprietes_for_user
                    profile=get_profile(user_id) or {}; role=profile.get("role","proprietaire"); is_adm=(role=="admin")
                    props2=get_proprietes_for_user(user_id,role); prop_ids=[p["id"] for p in props2]
                    st.session_state.update({"global_logged_in":True,"is_admin":is_adm,"auth_user_id":user_id,"auth_user_email":user_email,"prop_id":0 if is_adm else (prop_ids[0] if prop_ids else 0)})
                    for pid in prop_ids: st.session_state[f"unlocked_{pid}"]=True
                    st.query_params.clear(); st.rerun()
                else: st.error("❌ Lien expiré ou invalide.")
            except Exception as e: st.error(f"❌ Erreur : {e}")
        st.stop()
    with st.form("form_set_pwd"):
        pwd1=st.text_input("🔑 Nouveau mot de passe",type="password",placeholder="Au moins 8 caractères")
        pwd2=st.text_input("🔑 Confirmer",type="password",placeholder="Répétez le mot de passe")
        ok=st.form_submit_button("✅ Valider",type="primary",use_container_width=True)
    if ok:
        if len(pwd1)<8: st.error("❌ Minimum 8 caractères.")
        elif pwd1!=pwd2: st.error("❌ Les mots de passe ne correspondent pas.")
        else:
            try:
                r=_req.put(f"{_surl}/auth/v1/user",headers={"apikey":_skey,"Authorization":f"Bearer {_sb_token}","Content-Type":"application/json"},json={"password":pwd1},timeout=10)
                if r.status_code==200:
                    st.success("✅ Mot de passe enregistré !"); st.info("Connectez-vous avec votre email et ce mot de passe.")
                    st.query_params.clear(); st.markdown("<meta http-equiv='refresh' content='3;url=/'>",unsafe_allow_html=True)
                else:
                    msg=r.json().get("message","Erreur inconnue"); st.error(f"❌ {msg}")
                    if "expired" in msg.lower(): st.warning("Lien expiré. Demandez un nouveau lien.")
            except Exception as e: st.error(f"❌ Erreur réseau : {e}")
    st.markdown("<div style='text-align:center;margin-top:2rem;color:#AAA;font-size:0.75rem'>Développé par <strong>Charley Trigano</strong> — 2026</div>",unsafe_allow_html=True)
    st.stop()

# ── PWA : balises meta + manifest ─────────────────────────────────────────────
st.markdown("""
<link rel="manifest" href="/app/static/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="VLP">
<meta name="theme-color" content="#1565C0">
<link rel="apple-touch-icon" href="/app/static/apple-touch-icon.png">
""", unsafe_allow_html=True)

from components.sidebar import sidebar
import hashlib as _hashlib

def _hash_mdp(mdp: str) -> str:
    return _hashlib.sha256(mdp.strip().encode()).hexdigest()

def _show_splash_login():
    from database.proprietes_repo import fetch_all as _fetch_props
    import os
    st.markdown("""<style>[data-testid="stSidebar"],[data-testid="stSidebarNav"],[data-testid="collapsedControl"],#MainMenu,footer{display:none!important}.main .block-container{max-width:420px;margin:3rem auto;padding:2rem}</style>""", unsafe_allow_html=True)
    st.markdown("""<div style='text-align:center;padding:1.5rem 0 1.5rem 0'><div style='font-size:64px'>🏖️</div><h1 style='font-size:2rem;margin:0.5rem 0 0.2rem 0;color:#1565C0'>Vacances-Locations Pro</h1><p style='color:#666;font-size:0.9rem;margin:0'>Gestion locative</p></div>""", unsafe_allow_html=True)
    props = [p for p in _fetch_props() if p.get("actif")]
    if not props or all(not p.get("mot_de_passe") for p in props):
        st.session_state["global_logged_in"]=True; st.session_state["is_admin"]=True; st.rerun(); return
    admin_prop_id = int(st.secrets.get("ADMIN_PROP_ID", os.environ.get("ADMIN_PROP_ID", 2)))
    mode = st.radio("Mode de connexion", ["🔑 Code d'accès", "📧 Email / Mot de passe"], horizontal=True, key="login_mode", label_visibility="collapsed", index=0)
    if mode == "📧 Email / Mot de passe":
        st.caption("Connectez-vous avec votre email + le code que vous avez reçu (ou votre mot de passe Supabase).")
        with st.form("form_email_login"):
            email_input = st.text_input("📧 Email", placeholder="votre@email.fr")
            pwd_input   = st.text_input("🔑 Code d'accès personnel", type="password", placeholder="Votre code ou mot de passe...")
            submitted_email = st.form_submit_button("🔓 Se connecter", type="primary", use_container_width=True)
        if submitted_email:
            from database.auth_repo import sign_in_with_code, sign_in_with_email, get_profile, get_proprietes_for_user
            result_code = sign_in_with_code(email_input, pwd_input)
            if result_code:
                user_id=result_code["user_id"]; user_email=result_code["email"]; role=result_code["role"]; is_adm=(role=="admin")
                props_user=get_proprietes_for_user(user_id,role); prop_ids=[p["id"] for p in props_user]
                st.session_state.update({"global_logged_in":True,"is_admin":is_adm,"user_role":role,"auth_user_id":user_id,"auth_user_email":user_email,"prop_id":0 if is_adm else (prop_ids[0] if prop_ids else 0)})
                for pid in prop_ids: st.session_state[f"unlocked_{pid}"]=True
                if is_adm:
                    for p in props: st.session_state[f"unlocked_{p['id']}"]=True
                try:
                    from database.journal_repo import log_connexion as _log_c
                    _log_c(mode="email", statut="succes", user_email=user_email, user_id=user_id, detail=f"code_acces role={role}")
                except: pass
                st.rerun()
            else:
                result_auth = sign_in_with_email(email_input, pwd_input)
                if result_auth and result_auth.get("user"):
                    user=result_auth["user"]; profile=get_profile(str(user.id)); role=profile.get("role","proprietaire") if profile else "proprietaire"
                    is_adm=(role=="admin"); props_user=get_proprietes_for_user(str(user.id),role); prop_ids=[p["id"] for p in props_user]
                    st.session_state.update({"global_logged_in":True,"is_admin":is_adm,"user_role":role,"auth_user_id":str(user.id),"auth_user_email":user.email,"prop_id":0 if is_adm else (prop_ids[0] if prop_ids else 0)})
                    for pid in prop_ids: st.session_state[f"unlocked_{pid}"]=True
                    if is_adm:
                        for p in props: st.session_state[f"unlocked_{p['id']}"]=True
                    st.rerun()
                else:
                    try:
                        from database.journal_repo import log_connexion as _log_c
                        _log_c(mode="email", statut="echec", user_email=email_input, detail="Code ou mot de passe incorrect")
                    except: pass
                    st.error("❌ Email ou code incorrect.")
                    if st.button("🔑 Code oublié ?", key="btn_forgot"):
                        st.session_state["show_reset"] = True
        if st.session_state.get("show_reset"):
            with st.form("form_reset_pwd"):
                reset_email = st.text_input("📧 Votre email", key="reset_email_input")
                send_reset  = st.form_submit_button("📧 Envoyer le lien de réinitialisation", use_container_width=True)
            if send_reset and reset_email:
                import requests as _req, os as _os
                _surl=st.secrets.get("SUPABASE_URL",_os.environ.get("SUPABASE_URL",""))
                _skey=st.secrets.get("SUPABASE_KEY",_os.environ.get("SUPABASE_KEY",""))
                _github_redirect=st.secrets.get("AUTH_REDIRECT_URL",_os.environ.get("AUTH_REDIRECT_URL","https://charleytr.github.io/vlp-auth/"))
                try:
                    r=_req.post(f"{_surl}/auth/v1/recover",headers={"apikey":_skey,"Content-Type":"application/json"},json={"email":reset_email,"redirect_to":_github_redirect},timeout=10)
                    if r.status_code in (200,201): st.success("✅ Email envoyé ! Vérifiez votre boîte de réception.")
                    else: st.error(f"❌ {r.status_code} — {r.json().get('message','Erreur')}")
                    st.session_state.pop("show_reset", None)
                except Exception as e: st.error(f"❌ Erreur réseau : {e}")
    else:
        with st.form("form_pin_login"):
            pin_input = st.text_input("🔑 Code d'accès", type="password", placeholder="Entrez votre code...", max_chars=20)
            submitted = st.form_submit_button("🔓 Accéder", type="primary", use_container_width=True)
        if submitted and pin_input:
            prop_trouvee=None; is_code_gest=False
            for p in props:
                stored = p.get("mot_de_passe","") or ""
                if stored and (_hash_mdp(pin_input)==stored or pin_input==stored):
                    prop_trouvee=p; is_code_gest=False; break
                stored_g = p.get("mot_de_passe_gestionnaire","") or ""
                if stored_g and (_hash_mdp(pin_input)==stored_g or pin_input==stored_g):
                    prop_trouvee=p; is_code_gest=True; break
            if prop_trouvee:
                pid=prop_trouvee["id"]
                is_admin=(pid==admin_prop_id and not is_code_gest)
                user_role="admin" if is_admin else ("gestionnaire" if is_code_gest else "proprietaire")
                st.session_state.update({"global_logged_in":True,"is_admin":is_admin,"user_role":user_role,"prop_id":0 if is_admin else pid})
                if is_admin:
                    for p in props: st.session_state[f"unlocked_{p['id']}"]=True
                else:
                    st.session_state[f"unlocked_{pid}"]=True
                try:
                    from database.journal_repo import log_connexion as _log_pin
                    _log_pin(mode="pin", statut="succes", propriete_id=pid, propriete_nom=prop_trouvee.get("nom",""), detail=user_role)
                except: pass
                st.rerun()
            else:
                try:
                    from database.journal_repo import log_connexion as _log_pin
                    _log_pin(mode="pin", statut="echec", detail="Code PIN incorrect")
                except: pass
                st.error("❌ Code incorrect.")
    st.markdown("""<div style='text-align:center;margin-top:2.5rem;color:#AAAAAA;font-size:0.78rem'>Développé par <strong>Charley Trigano</strong> — 2026<br><span style='font-size:0.72rem'>© Tous droits réservés</span></div>""", unsafe_allow_html=True)
    st.stop()

# ── Gestion session persistante via localStorage (JS) ────────────────────────
import json as _json
import streamlit.components.v1 as _cv

# Lire la session sauvegardée depuis localStorage
_sess_html = _cv.html("""
<script>
(function() {
    var s = localStorage.getItem('vlp_session');
    if (s) {
        // Envoyer via URL query param pour que Python puisse lire
        var current = new URL(window.location.href);
        if (!current.searchParams.get('vlp_restore')) {
            current.searchParams.set('vlp_restore', encodeURIComponent(s));
            window.location.replace(current.toString());
        }
    }
    // Écouter le logout
    window.addEventListener('message', function(e) {
        if (e.data === 'vlp_logout') {
            localStorage.removeItem('vlp_session');
        }
    });
})();
</script>
""", height=0)

# Restaurer depuis query param
_qp2 = st.query_params
_restore = _qp2.get("vlp_restore", "")
if _restore and not st.session_state.get("global_logged_in"):
    try:
        import urllib.parse
        _sess = _json.loads(urllib.parse.unquote(_restore))
        st.session_state["global_logged_in"]  = True
        st.session_state["is_admin"]          = _sess.get("is_admin", False)
        st.session_state["user_role"]         = _sess.get("user_role", "proprietaire")
        st.session_state["prop_id"]           = _sess.get("prop_id", 0)
        st.session_state["auth_user_id"]      = _sess.get("auth_user_id", "")
        st.session_state["auth_user_email"]   = _sess.get("auth_user_email", "")
        for k, v in _sess.get("unlocked", {}).items():
            st.session_state[k] = v
        # Nettoyer l'URL
        _qp2.clear()
        st.rerun()
    except: pass

if not st.session_state.get("global_logged_in", False):
    _show_splash_login()

# ── Sauvegarder la session dans localStorage après connexion ──────────────────
if st.session_state.get("global_logged_in"):
    _unlocked = {k: v for k, v in st.session_state.items() if k.startswith("unlocked_")}
    _sess_data = _json.dumps({
        "is_admin":       st.session_state.get("is_admin", False),
        "user_role":      st.session_state.get("user_role", "proprietaire"),
        "prop_id":        st.session_state.get("prop_id", 0),
        "auth_user_id":   st.session_state.get("auth_user_id", ""),
        "auth_user_email":st.session_state.get("auth_user_email", ""),
        "unlocked":       _unlocked,
    })
    import urllib.parse as _up
    _cv.html(f"""
    <script>
    localStorage.setItem('vlp_session', {_json.dumps(_sess_data)});
    </script>
    """, height=0)

# ── Imports pages ─────────────────────────────────────────────────────────────
from pages import dashboard, reservations, calendar, analytics, gaps
try: from pages import paiements
except: paiements = None
try: from pages import menage
except: menage = None
try: from pages import messages
except: messages = None
try: from pages import ical_sync
except: ical_sync = None
try: from pages import proprietes as _page_proprietes
except: _page_proprietes = None
try: from pages import rapport
except: rapport = None
try: from pages import tarifs
except: tarifs = None
try: from pages import avis
except: avis = None
try: from pages import import_booking
except: import_booking = None
try: from pages import import_airbnb
except: import_airbnb = None
try: from pages import templates
except: templates = None
try: from pages import export_comptable
except: export_comptable = None
try: from pages import fiscal
except: fiscal = None
try: from pages import pricing
except: pricing = None
try: from pages import baremes
except: baremes = None
try: from pages import documentation
except: documentation = None
try: from pages import factures
except: factures = None
try: from pages import journal
except: journal = None
try: from pages import chat
except: chat = None
try: from pages import sauvegarde
except: sauvegarde = None
try: from pages import mon_profil
except: mon_profil = None
try: from pages import utilisateurs
except: utilisateurs = None
try: from pages import questionnaire
except: questionnaire = None

page = sidebar()

# ── Tracker la page courante pour les notifications chat ─────────────────────
st.session_state["current_page"] = page

# ── Navigation auto (depuis badge chat) ──────────────────────────────────────
if st.session_state.get("nav_page"):
    _nav = st.session_state.pop("nav_page")
    if _nav == "Chat":
        page = "Chat"

# ── Vérification propriété ────────────────────────────────────────────────────
_is_admin = st.session_state.get("is_admin", False)
if not _is_admin:
    from database.proprietes_repo import fetch_all as _fetch_props
    _props_unlocked = [p["id"] for p in _fetch_props() if st.session_state.get(f"unlocked_{p['id']}", False)]
    if _props_unlocked:
        _current = st.session_state.get("prop_id", _props_unlocked[0])
        if _current not in _props_unlocked:
            st.session_state["_forced_prop_id"] = _props_unlocked[0]; st.rerun()
        elif st.session_state.get("_forced_prop_id"):
            st.session_state.pop("_forced_prop_id", None)

# ── Routing ───────────────────────────────────────────────────────────────────
if   page == "Dashboard":          dashboard.show()
elif page == "Réservations":       reservations.show()
elif page == "Calendrier":         calendar.show()
elif page == "Analyses":           analytics.show()
elif page == "Créneaux":           gaps.show()
elif page == "Paiements":          paiements.show()       if paiements       else st.error("Uploadez pages/paiements.py")
elif page == "Ménage":             menage.show()          if menage          else st.error("Uploadez pages/menage.py")
elif page == "Messages":           messages.show()        if messages        else st.error("Uploadez pages/messages.py")
elif page == "iCal":               ical_sync.show()       if ical_sync       else st.error("Uploadez pages/ical_sync.py")
elif page == "Propriétés":         _page_proprietes.show() if _page_proprietes else st.error("Uploadez pages/proprietes.py")
elif page == "Rapports":           rapport.show()         if rapport         else st.error("Uploadez pages/rapport.py")
elif page == "Tarifs":             tarifs.show()          if tarifs          else st.error("Uploadez pages/tarifs.py")
elif page == "Livre d'or":         avis.show()            if avis            else st.error("Uploadez pages/avis.py")
elif page == "Import Booking":     import_booking.show()  if import_booking  else st.error("Uploadez pages/import_booking.py")
elif page == "Import Airbnb":      import_airbnb.show()   if import_airbnb   else st.error("Uploadez pages/import_airbnb.py")
elif page == "Modèles msgs":       templates.show()       if templates       else st.error("Uploadez pages/templates.py")
elif page == "Export comptable":   export_comptable.show() if export_comptable else st.error("Uploadez pages/export_comptable.py")
elif page == "Fiscal LMNP":        fiscal.show()          if fiscal          else st.error("Uploadez pages/fiscal.py")
elif page == "Revenus & Pricing":  pricing.show()         if pricing         else st.error("Uploadez pages/pricing.py")
elif page == "Barèmes fiscaux":    baremes.show()         if baremes         else st.error("Uploadez pages/baremes.py")
elif page == "Documentation":      documentation.show()   if documentation   else st.error("Uploadez pages/documentation.py")
elif page == "Factures":           factures.show()        if factures        else st.error("Uploadez pages/factures.py")
elif page == "Utilisateurs":       utilisateurs.show()    if utilisateurs    else st.error("Uploadez pages/utilisateurs.py")
elif page == "Journal":            journal.show()         if journal         else st.error("Uploadez pages/journal.py")
elif page == "Chat":               chat.show()            if chat            else st.error("Uploadez pages/chat.py")
elif page == "Sauvegarde":         sauvegarde.show()      if sauvegarde      else st.error("Uploadez pages/sauvegarde.py")
elif page == "Mon profil":         mon_profil.show()      if mon_profil      else st.error("Uploadez pages/mon_profil.py")
elif page == "Questionnaire":      questionnaire.show()   if questionnaire   else st.error("Uploadez pages/questionnaire.py")
