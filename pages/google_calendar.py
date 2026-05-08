"""
Page Google Calendar - Vue par propriétaire avec permissions
Chaque utilisateur ne voit que SES propriétés
"""
import streamlit as st
import streamlit.components.v1 as components
from services.auth_service import require_auth, is_admin, get_accessible_prop_ids
from database.proprietes_repo import fetch_all as fetch_proprietes

def show():
    require_auth()
    
    st.title("📅 Mon Calendrier Google")
    
    # Récupérer l'utilisateur et ses permissions
    admin = is_admin()
    accessible_ids = get_accessible_prop_ids()  # None = admin (tout), sinon liste d'IDs
    
    # Charger toutes les propriétés
    all_props = fetch_proprietes()
    
    # Filtrer selon les permissions
    if accessible_ids is None:
        # Admin : toutes les propriétés
        my_props = all_props
        st.info("👑 **Mode Administrateur** : Vous voyez toutes les propriétés")
    else:
        # Propriétaire : uniquement ses propriétés
        my_props = [p for p in all_props if p["id"] in accessible_ids]
        if len(my_props) == 1:
            st.success(f"🏠 **Vos réservations** : {my_props[0]['nom']}")
        else:
            st.success(f"🏠 **Vos {len(my_props)} propriétés**")
    
    if not my_props:
        st.warning("⚠️ Aucune propriété accessible. Contactez l'administrateur.")
        return
    
    # Configuration de la vue
    col1, col2 = st.columns([3, 1])
    
    with col1:
        vue_type = st.radio(
            "Type de vue",
            ["Mois", "Semaine", "Agenda"],
            horizontal=True
        )
    
    vue_params = {
        "Mois": "mode=MONTH",
        "Semaine": "mode=WEEK",
        "Agenda": "mode=AGENDA"
    }
    
    # Filtres pour l'admin
    calendriers_actifs = []
    
    if admin:
        st.markdown("---")
        st.subheader("🎯 Filtrer les propriétés (Admin)")
        
        # Option pour afficher le calendrier personnel
        show_personal = st.checkbox("📧 Afficher mon calendrier personnel", value=False, key="show_personal_admin")
        
        # Sélection des propriétés
        if len(my_props) > 1:
            choix = st.multiselect(
                "Propriétés à afficher",
                options=[p["id"] for p in my_props],
                default=[p["id"] for p in my_props],
                format_func=lambda pid: next((p["nom"] for p in my_props if p["id"] == pid), f"Propriété {pid}"),
                key="admin_prop_filter"
            )
            selected_props = [p for p in my_props if p["id"] in choix]
        else:
            selected_props = my_props
            
        # Ajouter le calendrier personnel si demandé
        if show_personal:
            calendriers_actifs.append({
                "nom": "Calendrier personnel",
                "id": "charley@trigano.org",
                "color": "%23b39ddb"
            })
    else:
        # Propriétaire : afficher uniquement ses propriétés
        selected_props = my_props
    
    # Construire la liste des calendriers à afficher
    couleurs = ["%237986cb", "%23d81b60", "%23e67c73", "%23616161", "%2333b679", "%23f4511e"]
    
    for i, prop in enumerate(selected_props):
        gcal_id = prop.get("google_calendar_id")
        if gcal_id:
            calendriers_actifs.append({
                "nom": prop["nom"],
                "id": gcal_id,
                "color": couleurs[i % len(couleurs)]
            })
    
    if not calendriers_actifs:
        st.warning("⚠️ Aucun calendrier Google configuré pour vos propriétés.")
        st.info("""
        **Pour l'administrateur :**
        
        Configurez les IDs de calendrier Google dans la base de données :
        
```sql
        UPDATE proprietes 
        SET google_calendar_id = 'votre_calendar_id@group.calendar.google.com'
        WHERE id = 1;
```
        """)
        return
    
    st.markdown("---")
    
    # Construire l'URL du calendrier
    calendar_base = "https://calendar.google.com/calendar/embed"
    
    params = [
        "height=600",
        "wkst=1",
        "ctz=Europe%2FParis",
        "showPrint=0",
        "showTabs=0",
        "showCalendars=0",
        "showTz=0",
        vue_params[vue_type],
    ]
    
    # Ajouter les calendriers
    for cal in calendriers_actifs:
        params.append(f"src={cal['id']}")
        params.append(f"color={cal['color']}")
    
    calendar_url = f"{calendar_base}?{'&'.join(params)}"
    
    # Afficher les calendriers actifs
    cal_names = ", ".join([cal['nom'] for cal in calendriers_actifs])
    st.caption(f"📊 Affichage de {len(calendriers_actifs)} calendrier(s) : {cal_names}")
    
    # Afficher le calendrier
    components.iframe(
        calendar_url,
        height=650,
        scrolling=False
    )
    
    # Informations
    with st.expander("ℹ️ À propos de cette vue"):
        if admin:
            st.markdown("""
            ### Mode Administrateur
            
            ✅ Vous avez accès à toutes les propriétés  
            ✅ Vous pouvez filtrer les calendriers à afficher  
            ✅ Vous pouvez afficher votre calendrier personnel  
            
            **Les propriétaires** voient uniquement leurs propres propriétés et ne peuvent pas voir votre calendrier personnel.
            """)
        else:
            st.markdown(f"""
            ### Vos réservations
            
            Vous voyez ici les réservations de : **{', '.join([p['nom'] for p in my_props])}**
            
            Les réservations sont automatiquement synchronisées depuis :
            - 📥 Airbnb
            - 📥 Booking  
            - 📥 Abritel
            - ✏️ Saisies manuelles dans Lodgepro
            
            **Cette vue est en lecture seule.** Pour modifier une réservation, utilisez la page "Réservations".
            """)
    
    # Liens rapides
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🔗 [Ouvrir dans Google Calendar](https://calendar.google.com)")
    with col2:
        st.markdown("📱 [App mobile](https://support.google.com/calendar/answer/6084659)")
    with col3:
        if admin:
            st.markdown("⚙️ [Gérer les utilisateurs](utilisateurs)")


if __name__ == "__main__":
    show()
