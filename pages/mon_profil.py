"""
Page Mon Profil — fonctionne avec connexion PIN et email.
"""
import streamlit as st
import hashlib
from database.supabase_client import get_supabase


def _hash(val: str) -> str:
    return hashlib.sha256(val.strip().encode()).hexdigest()


def show():
    st.title("👤 Mon profil")

    user_id    = st.session_state.get("auth_user_id", "")
    user_email = st.session_state.get("auth_user_email", "")
    prop_id    = st.session_state.get("prop_id", 0) or 0
    is_admin   = st.session_state.get("is_admin", False)

    # ── Mode connexion PIN ────────────────────────────────────────────────
    if not user_id and prop_id:
        _show_profil_pin(prop_id, is_admin)
        return

    # ── Mode connexion email ──────────────────────────────────────────────
    if user_id and user_email:
        _show_profil_email(user_id, user_email)
        return

    st.warning("Vous devez être connecté pour accéder à cette page.")


# ─────────────────────────────────────────────────────────────────────────────
# PROFIL MODE PIN
# ─────────────────────────────────────────────────────────────────────────────
def _show_profil_pin(prop_id: int, is_admin: bool):
    from database.proprietes_repo import fetch_all

    # Charger la propriété
    props = {p["id"]: p for p in fetch_all(force_refresh=True)}
    prop  = props.get(prop_id, {})

    if not prop:
        st.error("Propriété introuvable.")
        return

    st.markdown(f"""
    <div style='background:var(--bg-info,#E3F2FD);border-radius:10px;
                padding:14px 20px;margin-bottom:1.5rem'>
        <strong>🏠 {prop.get('nom','')}</strong><br>
        <span style='color:#666;font-size:13px'>
            Connexion par code PIN · {'Admin' if is_admin else 'Propriétaire'}
        </span>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔑 Code d'accès", "✍️ Informations"])

    # ── Onglet 1 : Changer le code PIN ────────────────────────────────────
    with tab1:
        st.subheader("Modifier le code d'accès")
        st.caption("Ce code est utilisé pour se connecter à l'application.")

        with st.form("form_pin_profil"):
            ancien  = st.text_input("Code actuel", type="password",
                                     placeholder="Votre code actuel")
            nouveau = st.text_input("Nouveau code *", type="password",
                                     placeholder="Au moins 4 caractères")
            confirmer = st.text_input("Confirmer *", type="password",
                                       placeholder="Répétez le nouveau code")
            ok = st.form_submit_button("💾 Enregistrer", type="primary",
                                        use_container_width=True)

        if ok:
            if not ancien or not nouveau:
                st.error("Tous les champs sont obligatoires.")
            elif len(nouveau) < 4:
                st.error("Le code doit contenir au moins 4 caractères.")
            elif nouveau != confirmer:
                st.error("Les codes ne correspondent pas.")
            else:
                stored = prop.get("mot_de_passe", "") or ""
                if ancien.strip() != stored and _hash(ancien.strip()) != stored:
                    st.error("❌ Code actuel incorrect.")
                else:
                    try:
                        sb = get_supabase()
                        sb.table("proprietes").update(
                            {"mot_de_passe": nouveau.strip()}
                        ).eq("id", prop_id).execute()
                        st.success("✅ Code d'accès mis à jour !")
                        st.info("Utilisez ce nouveau code à votre prochaine connexion.")
                    except Exception as e:
                        st.error(f"❌ Erreur : {e}")

    # ── Onglet 2 : Informations propriété ────────────────────────────────
    with tab2:
        st.subheader("Informations de la propriété")

        with st.form("form_info_profil"):
            signataire = st.text_input("Signataire (messages)",
                                        value=prop.get("signataire", "") or "",
                                        placeholder="Ex: Annick & Charley")
            tel_whatsapp = st.text_input("Téléphone WhatsApp",
                                          value=prop.get("tel_whatsapp", "") or "",
                                          placeholder="+33612345678")
            tel_sms = st.text_input("Téléphone SMS",
                                     value=prop.get("tel_sms", "") or "",
                                     placeholder="+33612345678")
            nom_exp = st.text_input("Nom expéditeur SMS",
                                     value=prop.get("nom_expediteur", "") or "",
                                     placeholder="VLPro")

            save = st.form_submit_button("💾 Enregistrer", type="primary",
                                          use_container_width=True)

        if save:
            try:
                sb = get_supabase()
                sb.table("proprietes").update({
                    "signataire":     signataire.strip(),
                    "tel_whatsapp":   tel_whatsapp.strip(),
                    "tel_sms":        tel_sms.strip(),
                    "nom_expediteur": nom_exp.strip(),
                }).eq("id", prop_id).execute()
                st.success("✅ Informations mises à jour !")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")


# ─────────────────────────────────────────────────────────────────────────────
# PROFIL MODE EMAIL
# ─────────────────────────────────────────────────────────────────────────────
def _show_profil_email(user_id: str, user_email: str):
    try:
        from database.auth_repo import set_code_acces, get_profile
        profile  = get_profile(user_id) or {}
        has_code = bool(profile.get("code_acces"))
    except:
        profile  = {}
        has_code = False

    st.markdown(f"""
    <div style='background:var(--bg-info,#E3F2FD);border-radius:10px;
                padding:14px 20px;margin-bottom:1.5rem'>
        <strong>📧 {user_email}</strong><br>
        <span style='color:#666;font-size:13px'>
            Rôle : {profile.get('role','proprietaire').capitalize()} ·
            Code d'accès : {'✅ Configuré' if has_code else '❌ Non configuré'}
        </span>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔑 Code d'accès", "🔒 Mot de passe"])

    with tab1:
        st.subheader("Code d'accès rapide")
        st.caption("Permet de vous connecter avec email + ce code (sans mot de passe Supabase).")

        with st.form("form_code_email"):
            if has_code:
                ancien = st.text_input("Code actuel", type="password")
            else:
                ancien = None
                st.info("Pas encore de code — définissez-en un.")
            nouveau   = st.text_input("Nouveau code *", type="password",
                                       placeholder="Au moins 4 caractères")
            confirmer = st.text_input("Confirmer *", type="password")
            ok = st.form_submit_button("💾 Enregistrer", type="primary",
                                        use_container_width=True)

        if ok:
            if not nouveau or len(nouveau) < 4:
                st.error("Code trop court (minimum 4 caractères).")
            elif nouveau != confirmer:
                st.error("Les codes ne correspondent pas.")
            elif has_code:
                stored = profile.get("code_acces", "")
                if (ancien or "").strip() != stored and _hash((ancien or "").strip()) != stored:
                    st.error("❌ Code actuel incorrect.")
                else:
                    try:
                        set_code_acces(user_id, nouveau.strip(), "")
                        st.success("✅ Code mis à jour !")
                    except Exception as e:
                        st.error(f"❌ {e}")
            else:
                try:
                    set_code_acces(user_id, nouveau.strip(), "")
                    st.success(f"✅ Code créé ! Connectez-vous avec **{user_email}** + ce code.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")

    with tab2:
        st.subheader("Changer le mot de passe Supabase")
        st.caption("Envoi d'un lien de réinitialisation par email.")
        if st.button("📧 Envoyer un lien de réinitialisation", use_container_width=True):
            try:
                import os, requests as _req
                _surl = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL",""))
                _skey = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY",""))
                _redir = st.secrets.get("AUTH_REDIRECT_URL",
                                         os.environ.get("AUTH_REDIRECT_URL",""))
                r = _req.post(f"{_surl}/auth/v1/recover",
                              headers={"apikey": _skey, "Content-Type": "application/json"},
                              json={"email": user_email, "redirect_to": _redir},
                              timeout=10)
                if r.status_code in (200, 201):
                    st.success(f"✅ Email envoyé à {user_email} !")
                else:
                    st.error(f"❌ Erreur : {r.json().get('message','')}")
            except Exception as e:
                st.error(f"❌ {e}")
