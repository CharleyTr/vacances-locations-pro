"""
Service de messagerie — Templates emails et SMS pour les réservations.
"""
from integrations.brevo_client import send_email, send_sms
from config import EMAIL_FROM

# ── Templates HTML ─────────────────────────────────────────────────────────

def _html_base(contenu: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto;
                border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;">
      <div style="background: #1565C0; padding: 20px; text-align: center;">
        <h2 style="color: white; margin: 0;">🏖️ Vacances-Locations</h2>
      </div>
      <div style="padding: 24px;">
        {contenu}
      </div>
      <div style="background: #f5f5f5; padding: 12px; text-align: center;
                  font-size: 12px; color: #757575;">
        Vacances-Locations PRO — Gestion locative
      </div>
    </div>
    """


def send_confirmation(reservation: dict) -> dict:
    """Email de confirmation de réservation."""
    nom     = reservation.get("nom_client", "")
    arrivee = reservation.get("date_arrivee", "")
    depart  = reservation.get("date_depart", "")
    nuits   = reservation.get("nuitees", "")
    prix    = reservation.get("prix_net", 0)
    num_res = reservation.get("numero_reservation", "")

    contenu = f"""
    <p>Bonjour <strong>{nom}</strong>,</p>
    <p>Nous avons bien reçu votre réservation et nous sommes ravis de vous accueillir !</p>
    <table style="width:100%; border-collapse:collapse; margin: 16px 0;">
      <tr style="background:#f5f5f5;">
        <td style="padding:8px; font-weight:bold;">📅 Arrivée</td>
        <td style="padding:8px;">{arrivee}</td>
      </tr>
      <tr>
        <td style="padding:8px; font-weight:bold;">📅 Départ</td>
        <td style="padding:8px;">{depart}</td>
      </tr>
      <tr style="background:#f5f5f5;">
        <td style="padding:8px; font-weight:bold;">🌙 Durée</td>
        <td style="padding:8px;">{nuits} nuit(s)</td>
      </tr>
      <tr>
        <td style="padding:8px; font-weight:bold;">💶 Montant</td>
        <td style="padding:8px;">{prix:.2f} €</td>
      </tr>
      {"<tr style='background:#f5f5f5;'><td style='padding:8px; font-weight:bold;'>🔖 N° réservation</td><td style='padding:8px;'>" + str(num_res) + "</td></tr>" if num_res else ""}
    </table>
    <p>N'hésitez pas à nous contacter pour toute question.</p>
    <p>À très bientôt !</p>
    """
    html = _html_base(contenu)
    email = reservation.get("email", "")
    return send_email(email, nom, "✅ Confirmation de votre réservation", html)


def send_checkin_reminder(reservation: dict) -> dict:
    """Email de rappel J-2 avant arrivée."""
    nom     = reservation.get("nom_client", "")
    arrivee = reservation.get("date_arrivee", "")
    email   = reservation.get("email", "")

    contenu = f"""
    <p>Bonjour <strong>{nom}</strong>,</p>
    <p>Votre séjour approche ! Nous sommes ravis de vous accueillir dans <strong>2 jours</strong>.</p>
    <p>📅 <strong>Date d'arrivée :</strong> {arrivee}</p>
    <h3 style="color: #1565C0;">📋 Informations d'arrivée</h3>
    <p>Nous vous contacterons pour vous communiquer les détails pratiques (clés, accès, etc.).</p>
    <p>Si vous avez des questions, n'hésitez pas à nous contacter.</p>
    <p>À très bientôt !</p>
    """
    html = _html_base(contenu)
    return send_email(email, nom, "🏖️ Votre arrivée dans 2 jours !", html)


def send_checkout_followup(reservation: dict) -> dict:
    """Email post-départ avec demande d'avis."""
    nom   = reservation.get("nom_client", "")
    email = reservation.get("email", "")

    contenu = f"""
    <p>Bonjour <strong>{nom}</strong>,</p>
    <p>Nous espérons que votre séjour s'est bien passé et que vous avez profité de votre séjour !</p>
    <p>Votre avis nous est précieux pour améliorer notre accueil.</p>
    <p>Merci encore pour votre confiance et à bientôt peut-être ! 🏖️</p>
    """
    html = _html_base(contenu)
    return send_email(email, nom, "🙏 Merci pour votre séjour !", html)


def send_payment_reminder(reservation: dict) -> dict:
    """Email de rappel de paiement."""
    nom     = reservation.get("nom_client", "")
    email   = reservation.get("email", "")
    montant = reservation.get("prix_net", 0)
    arrivee = reservation.get("date_arrivee", "")

    contenu = f"""
    <p>Bonjour <strong>{nom}</strong>,</p>
    <p>Nous n'avons pas encore reçu le règlement pour votre réservation du <strong>{arrivee}</strong>.</p>
    <p>💶 <strong>Montant dû :</strong> {montant:.2f} €</p>
    <p>Merci de procéder au paiement dans les meilleurs délais.</p>
    <p>N'hésitez pas à nous contacter si vous avez des questions.</p>
    """
    html = _html_base(contenu)
    return send_email(email, nom, "⚠️ Rappel de paiement", html)


# ── SMS ────────────────────────────────────────────────────────────────────

def send_checkin_sms(reservation: dict) -> dict:
    """SMS de rappel J-1 avant arrivée."""
    nom      = reservation.get("nom_client", "").split()[0]  # Prénom uniquement
    arrivee  = reservation.get("date_arrivee", "")
    telephone = reservation.get("telephone", "")

    message = (
        f"Bonjour {nom}, votre arrivée est prévue le {arrivee}. "
        f"Nous vous contacterons pour les détails pratiques. "
        f"A bientot ! - Vacances-Locations"
    )
    return send_sms(telephone, message)


def send_payment_sms(reservation: dict) -> dict:
    """SMS de rappel paiement."""
    nom       = reservation.get("nom_client", "").split()[0]
    montant   = reservation.get("prix_net", 0)
    telephone = reservation.get("telephone", "")

    message = (
        f"Bonjour {nom}, rappel: paiement de {montant:.0f}€ en attente "
        f"pour votre reservation. Merci. - Vacances-Locations"
    )
    return send_sms(telephone, message)
