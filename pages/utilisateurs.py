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

    # ── TAB 2 : Inviter un propriétaire ──────────────────────────────────
    with tab2:
        st.subheader("➕ Inviter un nouveau propriétaire")
        st.markdown("""
Supabase enverra automatiquement un **email d'invitation** avec un lien de connexion.
Le propriétaire choisira son mot de passe à la première connexion.
        """)
        st.info("⚠️ Cette fonctionnalité est disponible dès que la migration Auth est complète (script 015 + 016 exécutés).")

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
                with st.spinner("Envoi de l'invitation..."):
                    ok = invite_user(inv_email, inv_props, inv_role)
                if ok:
                    st.success(f"✅ Invitation envoyée à **{inv_email}** !")
                    st.info(f"Il recevra un email pour créer son mot de passe et accéder à : "
                            f"{', '.join(next((p['nom'] for p in props_list if p['id']==pid), str(pid)) for pid in inv_props)}")
                else:
                    st.error("Erreur lors de l'invitation. Vérifiez que le script SQL 015 a été exécuté.")
