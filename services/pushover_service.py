"""
Service de notifications push via Pushover.
"""
import requests
import os

def _get_keys():
    try:
        import streamlit as st
        user_key  = st.secrets.get("PUSHOVER_USER_KEY",  os.environ.get("PUSHOVER_USER_KEY", ""))
        api_token = st.secrets.get("PUSHOVER_API_TOKEN", os.environ.get("PUSHOVER_API_TOKEN", ""))
    except Exception:
        user_key  = os.environ.get("PUSHOVER_USER_KEY", "")
        api_token = os.environ.get("PUSHOVER_API_TOKEN", "")
    return user_key, api_token

def send_notification(title: str, message: str, priority: int = 0) -> bool:
    user_key, api_token = _get_keys()
    if not user_key or not api_token:
        return False
    try:
        r = requests.post("https://api.pushover.net/1/messages.json", data={
            "token":    api_token,
            "user":     user_key,
            "title":    title[:250],
            "message":  message[:1024],
            "priority": priority,
        }, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Pushover error: {e}")
        return False

def notify_nouvelle_reservation(nom_client, plateforme, date_arrivee,
                                 date_depart, prix_net, prop_nom=""):
    title = f"🏖️ Nouvelle résa — {prop_nom}" if prop_nom else "🏖️ Nouvelle réservation"
    message = (f"👤 {nom_client}\n"
               f"📋 {plateforme}\n"
               f"📅 {date_arrivee} → {date_depart}\n"
               f"💶 {float(prix_net or 0):,.0f} € net")
    return send_notification(title, message, priority=1)

def notify_arrivee_demain(nom_client, telephone, prop_nom=""):
    title = f"🏠 Arrivée demain — {prop_nom}" if prop_nom else "🏠 Arrivée demain"
    message = f"👤 {nom_client}\n📱 {telephone or 'pas de tél'}"
    return send_notification(title, message, priority=0)

def notify_paiement_manquant(nom_client, prix_net, date_arrivee, prop_nom=""):
    title = f"💳 Paiement manquant — {prop_nom}" if prop_nom else "💳 Paiement manquant"
    message = (f"👤 {nom_client}\n"
               f"💶 {float(prix_net or 0):,.0f} € en attente\n"
               f"📅 Arrivée : {date_arrivee}")
    return send_notification(title, message, priority=1)
