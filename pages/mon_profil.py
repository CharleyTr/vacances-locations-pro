"""
Page Mon Profil — chaque utilisateur peut modifier son code d'accès.
"""
import streamlit as st
import hashlib
from database.auth_repo import set_code_acces, get_profile


def show():
    st.title("👤 Mon profil")

    user_id    = st.session_state.get("auth_user_id", "")
    user_email = st.session_state.get("auth_user_email", "")

    if not user_id or not user_email:
        st.warning("Cette page est réservée aux utilisateurs connectés via email.")
        return

    profile = get_profile(user_id) or {}
    has_code = bool(profile.get("code_acces"))

    st.markdown(f"""
    <div style='background:#E3F2FD;border-radius:10px;padding:14px 20px;margin-bottom:1.5rem'>
        <strong>📧 {user_email}</strong><br>
        <span style='color:#666;font-size:13px'>
            Rôle : {profile.get('role','proprietaire').capitalize()} · 
            Code d'accès : {'✅ Configuré' if has_code else '❌ Non configuré'}
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("🔑 Définir / Modifier mon code d'accès")
    st.caption("Ce code vous permet de vous connecter avec votre email + ce code. "
               "Choisissez un code facile à retenir (chiffres, lettres, ou les deux).")

    with st.form("form_code_acces"):
        if has_code:
            ancien = st.text_input("Code actuel (vérification)", type="password",
                                    placeholder="Entrez votre code actuel")
        else:
            ancien = None
            st.info("Vous n'avez pas encore de code — définissez-en un maintenant.")

        nouveau    = st.text_input("Nouveau code *", type="password",
                                    placeholder="Ex: 1234, moncode2026...")
        confirmer  = st.text_input("Confirmer le nouveau code *", type="password",
                                    placeholder="Répétez le code")
        hint       = st.text_input("Indice mémo (optionnel)",
                                    placeholder="Ex: année de naissance, prénom chat...")

        ok = st.form_submit_button("💾 Enregistrer le code", type="primary",
                                    use_container_width=True)

    if ok:
        if not nouveau:
            st.error("❌ Le nouveau code est obligatoire.")
        elif len(nouveau) < 4:
            st.error("❌ Le code doit contenir au moins 4 caractères.")
        elif nouveau != confirmer:
            st.error("❌ Les codes ne correspondent pas.")
        elif has_code and ancien:
            # Vérifier l'ancien code
            stored = profile.get("code_acces","")
            ancien_hash = hashlib.sha256(ancien.strip().encode()).hexdigest()
            if ancien.strip() != stored and ancien_hash != stored:
                st.error("❌ Code actuel incorrect.")
            else:
                if set_code_acces(user_id, nouveau.strip(), hint.strip()):
                    st.success("✅ Code d'accès mis à jour !")
                else:
                    st.error("❌ Erreur lors de la sauvegarde.")
        elif not has_code:
            if set_code_acces(user_id, nouveau.strip(), hint.strip()):
                st.success("✅ Code d'accès créé ! Vous pouvez maintenant vous connecter "
                           f"avec **{user_email}** + votre code.")
                st.rerun()
            else:
                st.error("❌ Erreur lors de la sauvegarde.")
        else:
            # has_code mais ancien non fourni
            st.error("❌ Entrez votre code actuel pour le modifier.")
