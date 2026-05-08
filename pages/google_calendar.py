"""
Page Google Calendar - VERSION DEBUG
"""
import streamlit as st
from datetime import datetime, timedelta
import requests
from services.auth_service import is_admin, get_accessible_prop_ids
from database.proprietes_repo import fetch_all as fetch_proprietes

def show():
    st.title("📅 Mon Calendrier Google - DEBUG")
    
    # Récupérer l'utilisateur et ses permissions
    admin = is_admin()
    accessible_ids = get_accessible_prop_ids()
    
    # Charger toutes les propriétés
    all_props = fetch_proprietes()
    
    # Filtrer selon les permissions
    if accessible_ids is None:
        my_props = all_props
        st.info("👑 Mode Administrateur")
    else:
        my_props = [p for p in all_props if p["id"] in accessible_ids]
    
    if not my_props:
        st.warning("⚠️ Aucune propriété accessible")
        return
    
    # Filtres
    if admin and len(my_props) > 1:
        choix = st.multiselect(
            "Propriétés à afficher",
            options=[p["id"] for p in my_props],
            default=[p["id"] for p in my_props][:2],
            format_func=lambda pid: next((p["nom"] for p in my_props if p["id"] == pid), f"Propriété {pid}"),
        )
        selected_props = [p for p in my_props if p["id"] in choix]
    else:
        selected_props = my_props
    
    # Vérifier les URLs iCal
    props_with_ical = [p for p in selected_props if p.get("ical_secret_url")]
    
    if not props_with_ical:
        st.error("❌ Aucune URL iCal configurée")
        return
    
    st.markdown("---")
    st.subheader("🔍 TEST DES URLs iCal")
    
    # Tester chaque URL
    for prop in props_with_ical:
        ical_url = prop.get("ical_secret_url")
        prop_name = prop['nom']
        
        with st.expander(f"📊 {prop_name}", expanded=True):
            st.code(ical_url, language="text")
            
            if st.button(f"🧪 Tester {prop_name}", key=f"test_{prop['id']}"):
                with st.spinner(f"Téléchargement {prop_name}..."):
                    try:
                        # Tenter de télécharger
                        st.info("📡 Envoi de la requête HTTP...")
                        response = requests.get(ical_url, timeout=15)
                        
                        # Afficher le statut
                        st.success(f"✅ Code HTTP: {response.status_code}")
                        
                        # Afficher la taille
                        content_length = len(response.content)
                        st.info(f"📦 Taille des données: {content_length} octets")
                        
                        # Afficher les en-têtes
                        st.write("**Headers reçus:**")
                        st.json(dict(response.headers))
                        
                        # Afficher le début du contenu
                        if content_length > 0:
                            content_preview = response.text[:500]
                            st.write("**Aperçu du contenu (500 premiers caractères):**")
                            st.code(content_preview, language="text")
                            
                            # Vérifier si c'est bien du iCal
                            if "BEGIN:VCALENDAR" in response.text:
                                st.success("✅ Format iCal valide détecté!")
                                
                                # Compter les événements
                                event_count = response.text.count("BEGIN:VEVENT")
                                st.info(f"📅 Nombre d'événements: {event_count}")
                                
                                if event_count > 0:
                                    # Essayer de parser avec icalendar
                                    st.write("---")
                                    st.write("**Tentative de parsing avec icalendar...**")
                                    
                                    try:
                                        from icalendar import Calendar
                                        cal = Calendar.from_ical(response.content)
                                        st.success("✅ Parsing réussi!")
                                        
                                        # Extraire les événements
                                        events = []
                                        for component in cal.walk():
                                            if component.name == "VEVENT":
                                                try:
                                                    summary = str(component.get('summary', 'Sans titre'))
                                                    start = component.get('dtstart')
                                                    end = component.get('dtend')
                                                    
                                                    events.append({
                                                        'summary': summary,
                                                        'start': str(start.dt) if start else 'N/A',
                                                        'end': str(end.dt) if end else 'N/A'
                                                    })
                                                except Exception as e:
                                                    st.warning(f"⚠️ Erreur parsing événement: {e}")
                                        
                                        if events:
                                            st.success(f"✅ {len(events)} événements extraits!")
                                            st.dataframe(events)
                                        else:
                                            st.warning("⚠️ Aucun événement extrait")
                                            
                                    except ImportError:
                                        st.error("❌ Librairie 'icalendar' non installée!")
                                        st.info("Ajoutez `icalendar==5.0.11` dans requirements.txt")
                                    except Exception as e:
                                        st.error(f"❌ Erreur parsing: {e}")
                                        st.code(str(e))
                                else:
                                    st.warning("⚠️ Calendrier vide (0 événements)")
                            else:
                                st.error("❌ Ce n'est pas un fichier iCal valide")
                                st.write("Le contenu ne commence pas par BEGIN:VCALENDAR")
                        else:
                            st.warning("⚠️ Réponse vide (0 octets)")
                            
                    except requests.exceptions.Timeout:
                        st.error("❌ Timeout - La requête a pris trop de temps")
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Erreur réseau: {e}")
                    except Exception as e:
                        st.error(f"❌ Erreur inattendue: {e}")
                        st.code(str(e))
    
    st.markdown("---")
    st.info("""
    **Instructions :**
    
    1. Cliquez sur les boutons "🧪 Tester" ci-dessus
    2. Vérifiez les résultats affichés
    3. Faites une capture d'écran des résultats
    4. Envoyez-la moi pour diagnostic
    """)


if __name__ == "__main__":
    show()
