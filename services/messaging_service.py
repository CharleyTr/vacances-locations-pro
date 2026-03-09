from integrations.brevo_client import send_email

def send_checkin_message(reservation):

    subject = "Informations pour votre arrivée"

    html = f"""
    Bonjour {reservation['client_nom']},

    Votre séjour approche.

    Arrivée : {reservation['date_arrivee']}
    Appartement : {reservation['appartement']}

    Nous restons disponibles si besoin.

    """

    send_email(reservation["client_email"], subject, html)
