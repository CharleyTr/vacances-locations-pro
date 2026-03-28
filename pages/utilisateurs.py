"""
Page Gestion des utilisateurs — admin uniquement.
Permet d'inviter des propriétaires et gérer leurs accès.
"""
import streamlit as st
from database.auth_repo import (
    get_all_profiles, get_proprietes_for_user,
    invite_user, revoke_access
)
from database.proprietes_repo import fetch_all
from database.supabase_client import is_connected


def show():
    st.title("👥 Gestion des utilisateurs")
    st.caption("Invitez des propriétaires et gérez leurs accès — Admin uniquement.")

    if not st.session_state.get("is_admin", False):
        st.error("⛔ Accès réservé à l'administrateur.")
        return

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise.")
        return

    tab1, tab2 = st.tabs(["👥 Utilisateurs actifs", "➕ Inviter un propriétaire"])

    # ── TAB 1 : Liste des utilisateurs ───────────────────────────────────
    with tab1:
        profiles = get_all_profiles()
        # Enrichir avec code_acces
        try:
            from database.supabase_client import get_supabase as _gsb
            _sb2 = _gsb()
            if _sb2:
                _codes = {r["id"]: r.get("code_acces") 
                          for r in (_sb2.table("profiles").select("id,code_acces").execute().data or [])}
                for p in profiles:
                    p["code_acces"] = _codes.get(p["id"])
        except: pass
        props_all = {p["id"]: p["nom"] for p in fetch_all()}

        if not profiles:
            st.info("Aucun utilisateur encore. Invitez votre premier propriétaire →")
        else:
            st.markdown(f"**{len(profiles)} utilisateur(s) enregistré(s)**")
            for p in profiles:
                role_badge = "🔑 Admin" if p["role"] == "admin" else "🏠 Propriétaire" if p["role"] == "proprietaire" else "👁️ Lecteur"
                with st.expander(f"{role_badge} — {p.get('email','?')}  |  {p.get('nom','') or ''}"):
                    col1, col2 = st.columns([3,1])
                    with col1:
                        st.markdown(f"**Email :** {p.get('email','?')}")
                        st.markdown(f"**Rôle :** {p.get('role','?')}")
                        st.markdown(f"**Depuis :** {str(p.get('created_at',''))[:10]}")
                        st.markdown(f"**Statut :** {'✅ Actif' if p.get('actif') else '❌ Inactif'}")

                    with col2:
                        if p["role"] != "admin":
                            # Afficher les propriétés accessibles
                            from database.supabase_client import get_supabase
                            sb = get_supabase()
                            if sb:
                                try:
                                    access = sb.table("propriete_access")\
                                               .select("propriete_id, role")\
                                               .eq("user_id", p["id"]).execute().data or []
                                    if access:
                                        st.markdown("**Propriétés :**")
                                        for a in access:
                                            pnom = props_all.get(a["propriete_id"], f"#{a['propriete_id']}")
                                            st.markdown(f"- {pnom} ({a['role']})")
                                    else:
                                        st.caption("Aucune propriété assignée")
                                except: pass

            # ── Définir / modifier le code d'accès ───────────────────────
            if p["role"] != "admin":
                st.markdown("**🔑 Code d'accès**")
                has_code = bool(p.get("code_acces"))
                st.caption(
                    "✅ Code configuré — l'utilisateur peut le modifier dans Mon profil"
                    if has_code else
                    "❌ Aucun code — définissez-en un pour que l'utilisateur puisse se connecter"
                )
                with st.form(f"form_code_{p['id']}", clear_on_submit=True):
                    new_code = st.text_input(
                        "Nouveau code",
                        type="password",
                        placeholder="Ex: 1234, prénom2026...",
                        key=f"code_input_{p['id']}"
                    )
                    set_btn = st.form_submit_button(
                        "💾 Définir ce code",
                        type="primary",
                        use_container_width=True
                    )
                if set_btn:
                    if not new_code or len(new_code) < 4:
                        st.error("❌ Le code doit contenir au moins 4 caractères.")
                    else:
                        from database.auth_repo import set_code_acces
                        if set_code_acces(p["id"], new_code.strip()):
                            st.success(f"✅ Code défini pour {p.get('email','')} — communiquez-le lui.")
                            st.rerun()
                        else:
                            st.error("❌ Erreur lors de la sauvegarde.")

    # ── TAB 2 : Ajouter un propriétaire ──────────────────────────────────
    with tab2:
        st.subheader("➕ Ajouter un propriétaire / gestionnaire")
        st.info("""
**Comment ajouter un utilisateur :**
1. Va dans **Supabase → Authentication → Users → Add user**
2. Saisis l'email + mot de passe → coche **Auto Confirm User** → **Create user**
3. Reviens ici et clique **🔄 Synchroniser les profils** ci-dessous
        """)

        # ── Synchronisation des profils manquants ────────────────────────
        st.divider()
        st.markdown("### 🔄 Synchroniser les profils")
        st.caption("Crée automatiquement les profils pour les utilisateurs Auth sans profil.")

        if st.button("🔄 Synchroniser les profils depuis Supabase Auth", 
                     type="primary", use_container_width=True, key="btn_sync_profiles"):
            import os, requests as _req
            _surl = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL",""))
            _skey = st.secrets.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_KEY",""))
            from database.supabase_client import get_supabase
            _sb2 = get_supabase()
            try:
                # Récupérer tous les users Auth
                r = _req.get(f"{_surl}/auth/v1/admin/users",
                             headers={"apikey": _skey, "Authorization": f"Bearer {_skey}"},
                             timeout=15)
                if r.status_code == 200:
                    auth_users = r.json().get("users", [])
                    # Récupérer les profils existants
                    existing_ids = {p["id"] for p in (_sb2.table("profiles").select("id").execute().data or [])}
                    created = 0
                    for u in auth_users:
                        if u["id"] not in existing_ids:
                            _sb2.table("profiles").insert({
                                "id":    u["id"],
                                "email": u["email"],
                                "role":  "proprietaire",
                                "nom":   u["email"].split("@")[0],
                            }).execute()
                            created += 1
                    if created:
                        st.success(f"✅ {created} profil(s) créé(s) !")
                    else:
                        st.success("✅ Tous les utilisateurs ont déjà un profil.")
                    st.rerun()
                else:
                    st.error(f"❌ Erreur Auth : {r.status_code}")
            except Exception as e:
                st.error(f"❌ {e}")

        st.divider()
        st.markdown("### ✏️ Configurer un profil existant")
        st.caption("Modifie le rôle et les propriétés d'un utilisateur déjà créé dans Supabase.")
        # Vérifier si la migration est complète
    from database.supabase_client import get_supabase
    _sb = get_supabase()
    _migration_ok = False
    if _sb:
        try:
            r = _sb.table("profiles").select("id").limit(1).execute()
            _migration_ok = True
        except: pass

    if _migration_ok:
        st.success("✅ Migration Auth complète — l'invitation par email est opérationnelle.")
    else:
        st.warning("⚠️ Scripts SQL 015 + 016 à exécuter dans Supabase pour activer les invitations.")

    props_list = fetch_all()
    with st.form("form_config_profil", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            cfg_email = st.text_input("Email de l'utilisateur *", placeholder="user@email.fr")
            cfg_nom   = st.text_input("Nom (optionnel)", placeholder="Jean Dupont")
        with col2:
            cfg_role  = st.selectbox("Rôle", ["proprietaire", "gestionnaire", "lecteur"],
                                      format_func=lambda x: {
                                          "proprietaire": "🏠 Propriétaire",
                                          "gestionnaire": "🔧 Gestionnaire",
                                          "lecteur":      "👁️ Lecteur",
                                      }[x])
            cfg_props = st.multiselect(
                "Propriétés accessibles *",
                options=[p["id"] for p in props_list],
                format_func=lambda x: next((p["nom"] for p in props_list if p["id"]==x), str(x))
            )
        submitted_cfg = st.form_submit_button("💾 Enregistrer la configuration",
                                               type="primary", use_container_width=True)
        if submitted_cfg:
            if not cfg_email or not cfg_props:
                st.error("Email et au moins une propriété sont obligatoires.")
            else:
                import os, requests as _req
                _surl = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL",""))
                _skey = st.secrets.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_KEY",""))
                from database.supabase_client import get_supabase
                _sb3 = get_supabase()
                # Trouver l'UUID de l'email
                try:
                    r = _req.get(f"{_surl}/auth/v1/admin/users",
                                 headers={"apikey": _skey, "Authorization": f"Bearer {_skey}"},
                                 timeout=10)
                    users = r.json().get("users", []) if r.status_code == 200 else []
                    user = next((u for u in users if u.get("email","").lower() == cfg_email.lower()), None)
                    if not user:
                        st.error(f"❌ Utilisateur {cfg_email} non trouvé dans Supabase Auth. Créez-le d'abord.")
                    else:
                        uid = user["id"]
                        _sb3.table("profiles").upsert({
                            "id": uid, "email": cfg_email,
                            "role": cfg_role, "nom": cfg_nom or cfg_email.split("@")[0],
                        }, on_conflict="id").execute()
                        for pid in cfg_props:
                            _sb3.table("propriete_access").upsert({
                                "user_id": uid, "propriete_id": pid, "role": cfg_role
                            }, on_conflict="user_id,propriete_id").execute()
                        st.success(f"✅ Profil configuré pour **{cfg_email}** !")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ {e}")
