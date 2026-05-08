"""
Page Google Calendar - Lecture depuis URLs iCal secrètes
Affiche les événements depuis Google Calendar via parsing iCal
"""
import streamlit as st
from datetime import datetime, timedelta
import requests
from icalendar import Calendar
from services.auth_service import is_admin, get_accessible_prop_ids
from database.proprietes_repo import fetch_all as fetch_proprietes

def parse_ical_events(ical_url, calendar_name, max_days=90):
    """Parse les événements depuis une URL iCal Google Calendar"""
    try:
        # Télécharger le fichier iCal
        response = requests.get(ical_url, timeout=10)
        response.raise_for_status()
        
        # Parser le calendrier
        cal = Calendar.from_ical(response.content)
        
        events = []
        now = datetime.now()
        max_date = now + timedelta(days=max_days)
        
        for component in cal.walk():
            if component.name == "VEVENT":
                try:
                    # Extraire les informations de l'événement
                    summary = str(component.get('summary', 'Sans titre'))
                    start = component.get('dtstart').dt
                    end = component.get('dtend').dt
                    
                    # Convertir en datetime si c'est une date
                    if isinstance(start, datetime):
                        start_dt = start
                    else:
                        start_dt = datetime.combine(start, datetime.min.time())
                    
                    if isinstance(end, datetime):
                        end_dt = end
                    else:
                        end_dt = datetime.combine(end, datetime.min.time())
                    
                    # Filtrer : uniquement les événements futurs ou récents (90 jours)
                    if start_dt <= max_date and end_dt >= now - timedelta(days=30):
                        events.append({
                            'summary': summary,
                            'start': start_dt,
                            'end': end_dt,
                            'calendar': calendar_name,
                            'description': str(component.get('description', ''))
                        })
                except Exception as e:
                    continue  # Ignorer les événements malformés
        
        return events
    
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement de {calendar_name}: {str(e)}")
        return []


def render_calendar_view(events, selected_props):
    """Affiche les événements dans une vue calendrier"""
    
    if not events:
        st.info("📅 Aucun événement à afficher pour la période sélectionnée.")
        return
    
    # Trier les événements par date de début
    events_sorted = sorted(events, key=lambda x: x['start'])
    
    # Vue par mois
    st.subheader(f"📅 {len(events_sorted)} événement(s) trouvé(s)")
    
    # Grouper par propriété
    events_by_prop = {}
    for event in events_sorted:
        prop = event['calendar']
        if prop not in events_by_prop:
            events_by_prop[prop] = []
        events_by_prop[prop].append(event)
    
    # Couleurs par propriété
    colors = {
        selected_props[i]['nom']: ['#7986cb', '#d81b60', '#e67c73', '#616161', '#33b679', '#f4511e'][i % 6]
        if i < len(selected_props) else '#999999'
        for i in range(len(selected_props))
    }
    
    # Afficher les événements groupés par mois
    current_month = None
    
    for event in events_sorted:
        event_month = event['start'].strftime("%B %Y")
        
        # Nouveau mois
        if event_month != current_month:
            current_month = event_month
            st.markdown(f"### 📆 {event_month.capitalize()}")
            st.markdown("---")
        
        # Afficher l'événement
        prop_name = event['calendar']
        color = colors.get(prop_name, '#999999')
        
        start_str = event['start'].strftime("%d/%m/%Y")
        end_str = event['end'].strftime("%d/%m/%Y")
        
        # Calculer la durée
        duration = (event['end'] - event['start']).days
        duration_str = f"{duration} nuit{'s' if duration > 1 else ''}" if duration > 0 else "Journée"
        
        # Carte événement
        st.markdown(f"""
        <div style='background: {color}20; border-left: 4px solid {color}; 
                    padding: 12px; margin-bottom: 10px; border-radius: 4px'>
            <div style='font-weight: 600; font-size: 15px; color: {color}'>
                🏠 {prop_name}
            </div>
            <div style='margin-top: 6px; font-size: 14px'>
                <strong>{event['summary']}</strong>
            </div>
            <div style='margin-top: 4px; font-size: 13px; opacity: 0.8'>
                📅 {start_str} → {end_str} ({duration_str})
            </div>
        </div>
        """, unsafe_allow_html=True)


def show():
    st.title("📅 Mon Calendrier Google")
    
    # Récupérer l'utilisateur et ses permissions
    admin = is_admin()
    accessible_ids = get_accessible_prop_ids()
    
    # Charger toutes les propriétés
    all_props = fetch_proprietes()
    
    # Filtrer selon les permissions
    if accessible_ids is None:
        my_props = all_props
        st.info("👑 **Mode Administrateur** : Vous voyez toutes les propriétés")
    else:
        my_props = [p for p in all_props if p["id"] in accessible_ids]
        if len(my_props) == 1:
            st.success(f"🏠 **Vos réservations** : {my_props[0]['nom']}")
        else:
            st.success(f"🏠 **Vos {len(my_props)} propriétés**")
    
    if not my_props:
        st.warning("⚠️ Aucune propriété accessible. Contactez l'administrateur.")
        return
    
    # Filtres pour l'admin
    if admin:
        st.markdown("---")
        st.subheader("🎯 Filtrer les propriétés")
        
        if len(my_props) > 1:
            choix = st.multiselect(
                "Propriétés à afficher",
                options=[p["id"] for p in my_props],
                default=[p["id"] for p in my_props][:5],  # Max 5 par défaut
                format_func=lambda pid: next((p["nom"] for p in my_props if p["id"] == pid), f"Propriété {pid}"),
                key="admin_prop_filter"
            )
            selected_props = [p for p in my_props if p["id"] in choix]
        else:
            selected_props = my_props
    else:
        selected_props = my_props
    
    # Vérifier quelles propriétés ont des URLs iCal configurées
    props_with_ical = [p for p in selected_props if p.get("ical_secret_url")]
    
    if not props_with_ical:
        st.warning("⚠️ Aucune URL iCal secrète configurée pour vos propriétés.")
        st.info("""
        **Pour l'administrateur :**
        
        Configurez les URLs iCal secrètes dans la base de données :
        
        ```sql
        UPDATE proprietes 
        SET ical_secret_url = 'https://calendar.google.com/calendar/ical/...'
        WHERE id = 1;
        ```
        """)
        return
    
    st.markdown("---")
    
    # Période à afficher
    col1, col2 = st.columns([3, 1])
    with col1:
        periode = st.radio(
            "Période",
            ["30 jours", "60 jours", "90 jours"],
            horizontal=True,
            index=1
        )
    
    max_days = int(periode.split()[0])
    
    # Charger les événements de tous les calendriers sélectionnés
    with st.spinner("🔄 Chargement des événements depuis Google Calendar..."):
        all_events = []
        
        for prop in props_with_ical:
            ical_url = prop.get("ical_secret_url")
            if ical_url:
                events = parse_ical_events(ical_url, prop['nom'], max_days=max_days)
                all_events.extend(events)
                if events:
                    st.success(f"✅ {prop['nom']}: {len(events)} événement(s)")
    
    st.markdown("---")
    
    # Afficher les événements
    if all_events:
        render_calendar_view(all_events, props_with_ical)
    else:
        st.info("📅 Aucun événement trouvé pour la période sélectionnée.")
    
    # Informations
    with st.expander("ℹ️ À propos de cette vue"):
        st.markdown("""
        ### Comment ça fonctionne ?
        
        Cette page récupère les événements **directement depuis vos calendriers Google** 
        en utilisant les adresses iCal secrètes.
        
        ✅ **Avantages :**
        - Pas de problème de permissions publiques
        - Mise à jour en temps réel
        - Fonctionne avec des calendriers privés
        
        🔄 **Synchronisation :**
        Les événements sont rechargés à chaque visite de la page.
        
        🔒 **Sécurité :**
        Les URLs secrètes sont stockées dans votre base de données Supabase 
        et ne sont jamais exposées publiquement.
        """)
    
    # Liens rapides
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🔗 [Ouvrir dans Google Calendar](https://calendar.google.com)")
    with col2:
        st.markdown("📱 [App mobile Google Calendar](https://support.google.com/calendar/answer/6084659)")
    with col3:
        if admin:
            st.markdown("⚙️ [Configurer les URLs iCal](#)")


if __name__ == "__main__":
    show()
