"""
Page Mon Profil - Configuration propriétaire
Permet à chaque propriétaire de configurer son calendrier Google
"""
import streamlit as st
from services.auth_service import is_admin, get_accessible_prop_ids
from database.proprietes_repo import fetch_all as fetch_proprietes
from database.supabase_client import get_supabase
import requests

def test_ical_url(url):
    """Teste si une URL iCal est valide"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200 and "BEGIN:VCALENDAR" in response.text:
            event_count = response.text.count("BEGIN:VEVENT")
            return True, f"✅ URL valide - {event_count} événement(s) trouvé(s)"
        else:
            return False, "❌ URL invalide - Aucun calendrier trouvé"
    except Exception as e:
        return False, f"❌ Erreur : {str(e)}"

def show():
    st.title("👤 Mon Profil")
    
    # Récupérer les informations utilisateur
    admin = is_admin()
    accessible_ids = get_accessible_prop_ids()
    user_email = st.session_state.get("auth_user_email", "")
    user_role = st.session_state.get("user_role", "proprietaire")
    
    # Charger les propriétés
    all_props = fetch_proprietes()
    
    # Filtrer selon les permissions
    if accessible_ids is None:
        my_props = all_props
    else:
        my_props = [p for p in all_props if p["id"] in accessible_ids]
    
    if not my_props:
        st.warning("⚠️ Aucune propriété accessible")
        return
    
    # Afficher les informations utilisateur
    st.markdown("---")
    st.subheader("📋 Mes informations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if admin:
            st.info("👑 **Rôle** : Administrateur")
        elif user_role == "gestionnaire":
            st.info("🔑 **Rôle** : Gestionnaire")
        else:
            st.info("🏠 **Rôle** : Propriétaire")
    
    with col2:
        if user_email:
            st.info(f"📧 **Email** : {user_email}")
        else:
            st.info("🔐 **Connexion** : Code PIN")
    
    # Liste des propriétés
    st.markdown("---")
    st.subheader("🏠 Mes propriétés")
    
    if len(my_props) == 1:
        st.success(f"**{my_props[0]['nom']}**")
    else:
        for prop in my_props:
            st.write(f"• {prop['nom']}")
    
    # Configuration Google Calendar
    st.markdown("---")
    st.subheader("📅 Configuration Google Calendar")
    
    st.info("""
    **Synchronisez vos réservations avec Google Calendar !**
    
    En ajoutant votre calendrier Google, vos réservations Airbnb, Booking, etc. 
    seront automatiquement visibles dans Lodgepro.
    """)
    
    # Sélection de la propriété (si plusieurs)
    if len(my_props) > 1:
        selected_prop = st.selectbox(
            "Propriété à configurer",
            options=my_props,
            format_func=lambda p: p['nom'],
            key="profile_prop_select"
        )
    else:
        selected_prop = my_props[0]
    
    prop_id = selected_prop['id']
    current_url = selected_prop.get('ical_secret_url', '')
    
    # Formulaire de configuration
    with st.form("form_ical_config"):
        st.markdown(f"### Configuration : {selected_prop['nom']}")
        
        # Afficher l'URL actuelle si elle existe
        if current_url:
            st.success("✅ Calendrier Google déjà configuré")
            with st.expander("🔍 Voir l'URL actuelle"):
                st.code(current_url, language="text")
        
        # Instructions
        with st.expander("📖 Comment obtenir l'URL secrète ?"):
            st.markdown("""
            ### Étapes pour récupérer votre URL iCal secrète :
            
            1. **Ouvrez** [Google Calendar](https://calendar.google.com)
            2. **Cliquez** sur votre calendrier dans la liste de gauche
            3. **Cliquez** sur les **3 points** → **"Paramètres et partage"**
            4. **Scrollez** jusqu'à **"Intégrer l'agenda"**
            5. **Copiez** l'**"Adresse secrète au format iCal"**
            
            L'URL doit ressembler à :
            ```
            https://calendar.google.com/calendar/ical/XXXX@group.calendar.google.com/private-YYYY/basic.ics
            ```
            
            ⚠️ **Important** : Ne partagez jamais cette URL publiquement !
            """)
        
        # Champ de saisie
        new_url = st.text_input(
            "URL iCal secrète",
            value=current_url,
            placeholder="https://calendar.google.com/calendar/ical/...",
            help="Collez l'adresse secrète de votre calendrier Google"
        )
        
        # Boutons
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            submit = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)
        
        with col2:
            test = st.form_submit_button("🧪 Tester", use_container_width=True)
        
        with col3:
            remove = st.form_submit_button("🗑️ Supprimer", use_container_width=True)
    
    # Traitement du formulaire
    if test and new_url:
        with st.spinner("🔄 Test de l'URL..."):
            valid, message = test_ical_url(new_url)
            if valid:
                st.success(message)
            else:
                st.error(message)
    
    if submit:
        if not new_url:
            st.error("❌ Veuillez saisir une URL")
        elif not new_url.startswith("https://calendar.google.com/calendar/ical/"):
            st.error("❌ L'URL doit commencer par : https://calendar.google.com/calendar/ical/")
        else:
            # Sauvegarder dans la base de données
            try:
                sb = get_supabase()
                if sb:
                    result = sb.table("proprietes").update({
                        "ical_secret_url": new_url
                    }).eq("id", prop_id).execute()
                    
                    if result.data:
                        st.success("✅ Calendrier Google configuré avec succès !")
                        st.balloons()
                        
                        # Proposer de tester
                        if st.button("🧪 Tester maintenant"):
                            valid, message = test_ical_url(new_url)
                            if valid:
                                st.success(message)
                            else:
                                st.error(message)
                        
                        # Attendre 2 secondes et recharger
                        import time
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de l'enregistrement")
                else:
                    st.error("❌ Connexion Supabase indisponible")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
    
    if remove:
        if current_url:
            try:
                sb = get_supabase()
                if sb:
                    result = sb.table("proprietes").update({
                        "ical_secret_url": None
                    }).eq("id", prop_id).execute()
                    
                    if result.data:
                        st.success("✅ Calendrier Google supprimé")
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Erreur lors de la suppression")
                else:
                    st.error("❌ Connexion Supabase indisponible")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
        else:
            st.warning("⚠️ Aucun calendrier à supprimer")
    
    # Liens utiles
    st.markdown("---")
    st.subheader("🔗 Liens utiles")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("[📅 Google Calendar](https://calendar.google.com)")
    
    with col2:
        st.markdown("[📖 Documentation](https://support.google.com/calendar)")
    
    with col3:
        if admin:
            st.markdown("[⚙️ Gérer les utilisateurs](utilisateurs)")


if __name__ == "__main__":
    show()
