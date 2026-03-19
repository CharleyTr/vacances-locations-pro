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

    # ── TAB 2 : Inviter un propriétaire ──────────────────────────────────
    with tab2:
        st.subheader("➕ Inviter un nouveau propriétaire")
        st.markdown("""
Supabase enverra automatiquement un **email d'invitation** avec un lien de connexion.
Le propriétaire choisira son mot de passe à la première connexion.
        """)
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
    with st.form("form_invite", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            inv_email = st.text_input("Email *", placeholder="proprietaire@email.fr")
            inv_nom   = st.text_input("Nom (optionnel)", placeholder="Jean Dupont")
        with col2:
            inv_role  = st.selectbox("Rôle", ["proprietaire", "gestionnaire", "lecteur"],
                                      format_func=lambda x: {
                                          "proprietaire": "🏠 Propriétaire (lecture + écriture)",
                                          "gestionnaire": "🔧 Gestionnaire (tout sauf admin)",
                                          "lecteur":      "👁️ Lecteur (consultation uniquement)",
                                      }[x])
            inv_props = st.multiselect(
                "Propriétés accessibles *",
                options=[p["id"] for p in props_list],
                format_func=lambda x: next((p["nom"] for p in props_list if p["id"]==x), str(x))
            )

        submitted = st.form_submit_button("📧 Envoyer l'invitation", type="primary",
                                           use_container_width=True)

        if submitted:
            if not inv_email or not inv_props:
                st.error("Email et au moins une propriété sont obligatoires.")
            else:
                import os, requests as _req
                _surl = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL",""))
                _skey = st.secrets.get("SUPABASE_SERVICE_KEY", os.environ.get("SUPABASE_SERVICE_KEY",""))
                _anon = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY",""))
                from database.supabase_client import get_supabase
                _sb = get_supabase()

                with st.spinner("Traitement en cours..."):
                    user_id = None

                    # Étape 1 : Essayer d'inviter
                    r = _req.post(
                        f"{_surl}/auth/v1/invite",
                        headers={"apikey": _skey, "Authorization": f"Bearer {_skey}",
                                 "Content-Type": "application/json"},
                        json={"email": inv_email}, timeout=15,
                    )

                    if r.status_code in (200, 201):
                        user_id = r.json().get("id")
                        st.success(f"✅ Invitation envoyée à **{inv_email}** !")
                    elif "email_exists" in r.text:
                        # Utilisateur déjà existant — récupérer son UUID
                        r2 = _req.get(
                            f"{_surl}/auth/v1/admin/users",
                            headers={"apikey": _skey, "Authorization": f"Bearer {_skey}"},
                            timeout=10,
                        )
                        if r2.status_code == 200:
                            users = r2.json().get("users", [])
                            existing = next((u for u in users
                                             if u.get("email","").lower() == inv_email.lower()), None)
                            if existing:
                                user_id = existing["id"]
                                st.success(f"✅ Accès configuré pour **{inv_email}** (compte existant).")
                            else:
                                st.error("Utilisateur introuvable dans la liste Auth.")
                        else:
                            st.error(f"Erreur récupération users: {r2.status_code}")
                    else:
                        st.error(f"❌ Erreur invitation: {r.status_code} — {r.text[:150]}")

                    # Étape 2 : Créer profil + accès si user_id trouvé
                    if user_id and _sb:
                        _sb.table("profiles").upsert({
                            "id": user_id, "email": inv_email, "role": inv_role,
                            "nom": inv_nom or inv_email.split("@")[0]
                        }).execute()
                        for pid in inv_props:
                            _sb.table("propriete_access").upsert({
                                "user_id": user_id, "propriete_id": pid, "role": inv_role
                            }, on_conflict="user_id,propriete_id").execute()
                        prop_noms = ', '.join(
                            next((p['nom'] for p in props_list if p['id']==pid), str(pid))
                            for pid in inv_props
                        )
                        st.info(f"Propriétés assignées : {prop_noms}")
