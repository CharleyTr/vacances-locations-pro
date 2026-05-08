"""
Page Google Calendar - VERSION DEBUG
"""
import streamlit as st
import streamlit.components.v1 as components
from services.auth_service import is_admin, get_accessible_prop_ids
from database.proprietes_repo import fetch_all as fetch_proprietes

def show():
    st.title("📅 Mon Calendrier Google - DEBUG")
    
    admin = is_admin()
    accessible_ids = get_accessible_prop_ids()
    all_props = fetch_proprietes()
    
    if accessible_ids is None:
        my_props = all_props
        st.info("👑 Mode Administrateur")
    else:
        my_props = [p for p in all_props if p["id"] in accessible_ids]
    
    if not my_props:
        st.warning("⚠️ Aucune propriété accessible")
        return
    
    # Filtres
    calendriers_actifs = []
    
    if admin:
        st.markdown("---")
        if len(my_props) > 1:
            choix = st.multiselect(
                "Propriétés à afficher",
                options=[p["id"] for p in my_props],
                default=[p["id"] for p in my_props][:2],  # Seulement les 2 premières par défaut
                format_func=lambda pid: next((p["nom"] for p in my_props if p["id"] == pid), f"Propriété {pid}"),
            )
            selected_props = [p for p in my_props if p["id"] in choix]
        else:
            selected_props = my_props
    else:
        selected_props = my_props
    
    # Construire la liste des calendriers
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
        st.warning("⚠️ Aucun calendrier configuré")
        return
    
    st.markdown("---")
    
    # 🔍 DEBUG : Afficher les IDs
    with st.expander("🔍 DEBUG - IDs des calendriers", expanded=True):
        for cal in calendriers_actifs:
            st.code(f"{cal['nom']}: {cal['id']}")
    
    # Construire l'URL
    calendar_base = "https://calendar.google.com/calendar/embed"
    
    params = [
        "height=600",
        "wkst=1",
        "ctz=Europe%2FParis",
        "showPrint=0",
        "showTabs=0",
        "showCalendars=0",
        "showTz=0",
        "mode=MONTH",
    ]
    
    for cal in calendriers_actifs:
        params.append(f"src={cal['id']}")
        params.append(f"color={cal['color']}")
    
    calendar_url = f"{calendar_base}?{'&'.join(params)}"
    
    # 🔍 DEBUG : Afficher l'URL complète
    with st.expander("🔍 DEBUG - URL générée", expanded=True):
        st.text_area("URL complète", calendar_url, height=150)
        st.markdown(f"[🔗 Tester l'URL dans un nouvel onglet]({calendar_url})")
        st.caption("👆 Cliquez pour ouvrir l'URL directement et voir l'erreur exacte de Google")
    
    # Afficher le calendrier
    st.caption(f"📊 Affichage de {len(calendriers_actifs)} calendrier(s)")
    
    components.iframe(
        calendar_url,
        height=650,
        scrolling=False
    )

if __name__ == "__main__":
    show()
