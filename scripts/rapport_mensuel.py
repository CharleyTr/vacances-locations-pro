"""
Script de rapport mensuel automatique.
Exécuté le 1er de chaque mois par GitHub Actions.
Envoie un email récapitulatif à chaque propriétaire.
"""
import os
import io
import requests
import json
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
BREVO_KEY    = os.environ.get("BREVO_API_KEY", "")
EMAIL_FROM   = os.environ.get("EMAIL_FROM", "c.trigano@gmail.com")
APP_URL      = os.environ.get("APP_URL", "https://vacances-locations-pro-iqmuq8xq9g3kxgw6n8ogpv.streamlit.app")

HEADERS_SB = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
}

MOIS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
           "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]


def sb_get(table, params=""):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}",
                     headers=HEADERS_SB, timeout=15)
    return r.json() if r.status_code == 200 else []


def send_email(to_email, to_name, subject, html):
    if not BREVO_KEY:
        print(f"BREVO_KEY manquant — email non envoyé à {to_email}")
        return False
    r = requests.post("https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_KEY, "Content-Type": "application/json"},
        json={
            "sender":      {"name": "LodgePro", "email": EMAIL_FROM},
            "to":          [{"email": to_email, "name": to_name}],
            "subject":     subject,
            "htmlContent": html,
        }, timeout=15)
    ok = r.status_code in (200, 201)
    print(f"Email {'OK' if ok else 'ERREUR'} → {to_email}")
    return ok


def generer_rapport_html(prop, reservations_mois, reservations_mois_prec,
                          heures_mois, mois, annee):
    """Génère le HTML du rapport mensuel."""
    mois_label = f"{MOIS_FR[mois-1]} {annee}"
    prop_nom   = prop.get("nom", "")

    # KPIs mois
    ca_net    = sum(float(r.get("prix_net",0) or 0) for r in reservations_mois)
    ca_brut   = sum(float(r.get("prix_brut",0) or 0) for r in reservations_mois)
    nuitees   = sum(int(r.get("nuitees",0) or 0) for r in reservations_mois)
    nb_resas  = len(reservations_mois)
    rev_nuit  = ca_net / nuitees if nuitees > 0 else 0

    # KPIs mois précédent
    ca_net_prec = sum(float(r.get("prix_net",0) or 0) for r in reservations_mois_prec)
    delta = ca_net - ca_net_prec
    delta_pct = (delta / ca_net_prec * 100) if ca_net_prec > 0 else 0
    delta_str = f"+{delta_pct:.1f}%" if delta >= 0 else f"{delta_pct:.1f}%"
    delta_color = "#2E7D32" if delta >= 0 else "#C62828"

    # Heures ménage
    total_min = sum(int(p.get("duree_minutes",0) or 0) for p in heures_mois)
    h, m = divmod(total_min, 60)
    heures_str = f"{h}h{m:02d}" if total_min > 0 else "—"

    # Réservations à venir (30 prochains jours)
    today = date.today()
    resas_futures = sorted([
        r for r in sb_get("reservations",
            f"propriete_id=eq.{prop['id']}"
            f"&date_arrivee=gte.{today}"
            f"&plateforme=neq.Fermeture"
            f"&order=date_arrivee"
        )
    ], key=lambda x: x.get("date_arrivee",""))[:5]

    # HTML email
    resas_html = ""
    for r in resas_futures:
        resas_html += f"""
        <tr>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0">{r.get('nom_client','?')}</td>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0">{str(r.get('date_arrivee',''))[:10]}</td>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0">{str(r.get('date_depart',''))[:10]}</td>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0">{r.get('plateforme','?')}</td>
          <td style="padding:8px;border-bottom:1px solid #E0E0E0;font-weight:bold">
            {float(r.get('prix_net',0) or 0):,.0f} €
          </td>
        </tr>"""

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:650px;margin:auto">

      <!-- Header -->
      <div style="background:#0B1F3A;padding:24px;border-radius:8px 8px 0 0;text-align:center">
        <h1 style="color:white;margin:0;font-size:22px">🏖️ LodgePro</h1>
        <p style="color:#F0B429;margin:6px 0 0;font-size:14px">Rapport mensuel — {mois_label}</p>
      </div>

      <div style="background:#F4F7FF;padding:20px">
        <h2 style="color:#0B1F3A;margin:0 0 16px">{prop_nom}</h2>

        <!-- KPIs -->
        <table width="100%" cellpadding="0" cellspacing="8" style="margin-bottom:20px">
          <tr>
            <td style="background:white;border-radius:8px;padding:16px;text-align:center;width:25%">
              <div style="font-size:11px;color:#666">CA Net</div>
              <div style="font-size:22px;font-weight:bold;color:#1565C0">{ca_net:,.0f} €</div>
              <div style="font-size:11px;color:{delta_color}">{delta_str} vs mois préc.</div>
            </td>
            <td style="background:white;border-radius:8px;padding:16px;text-align:center;width:25%">
              <div style="font-size:11px;color:#666">Réservations</div>
              <div style="font-size:22px;font-weight:bold;color:#1565C0">{nb_resas}</div>
            </td>
            <td style="background:white;border-radius:8px;padding:16px;text-align:center;width:25%">
              <div style="font-size:11px;color:#666">Nuitées</div>
              <div style="font-size:22px;font-weight:bold;color:#1565C0">{nuitees}</div>
            </td>
            <td style="background:white;border-radius:8px;padding:16px;text-align:center;width:25%">
              <div style="font-size:11px;color:#666">Rev/nuit</div>
              <div style="font-size:22px;font-weight:bold;color:#1565C0">{rev_nuit:,.0f} €</div>
            </td>
          </tr>
        </table>

        <!-- Heures ménage -->
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:20px">
          <h3 style="color:#0B1F3A;margin:0 0 8px">🧹 Ménage</h3>
          <p style="margin:0;color:#666">Heures travaillées ce mois : <strong>{heures_str}</strong></p>
        </div>

        <!-- Prochaines réservations -->
        {"" if not resas_futures else f"""
        <div style="background:white;border-radius:8px;padding:16px;margin-bottom:20px">
          <h3 style="color:#0B1F3A;margin:0 0 12px">📅 Prochaines réservations</h3>
          <table width="100%" style="border-collapse:collapse;font-size:13px">
            <tr style="background:#F4F7FF">
              <th style="padding:8px;text-align:left">Client</th>
              <th style="padding:8px;text-align:left">Arrivée</th>
              <th style="padding:8px;text-align:left">Départ</th>
              <th style="padding:8px;text-align:left">Plateforme</th>
              <th style="padding:8px;text-align:left">CA Net</th>
            </tr>
            {resas_html}
          </table>
        </div>
        """}

        <!-- CTA -->
        <div style="text-align:center;margin-top:20px">
          <a href="{APP_URL}" style="background:#1565C0;color:white;padding:14px 28px;
             border-radius:8px;text-decoration:none;font-weight:bold;font-size:14px">
            Accéder à mon espace LodgePro →
          </a>
        </div>
      </div>

      <!-- Footer -->
      <div style="background:#0B1F3A;padding:16px;border-radius:0 0 8px 8px;text-align:center">
        <p style="color:#666;font-size:11px;margin:0">
          LodgePro · Rapport généré automatiquement le {datetime.now().strftime('%d/%m/%Y')}
        </p>
      </div>
    </div>"""

    return html


def main():
    print(f"=== Rapport mensuel — {datetime.now().strftime('%d/%m/%Y %H:%M')} ===")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Variables SUPABASE_URL et SUPABASE_KEY manquantes")
        return

    # Mois précédent
    today      = date.today()
    mois_prec  = today - relativedelta(months=1)
    mois       = mois_prec.month
    annee      = mois_prec.year
    debut_mois = f"{annee}-{mois:02d}-01"
    from calendar import monthrange
    fin_mois   = f"{annee}-{mois:02d}-{monthrange(annee, mois)[1]:02d}"

    # Mois encore précédent (pour comparaison)
    mois_2     = mois_prec - relativedelta(months=1)
    debut_2    = f"{mois_2.year}-{mois_2.month:02d}-01"
    fin_2      = f"{mois_2.year}-{mois_2.month:02d}-{monthrange(mois_2.year, mois_2.month)[1]:02d}"

    print(f"Période : {debut_mois} → {fin_mois}")

    # Récupérer les propriétés actives
    props = sb_get("proprietes", "actif=eq.true&select=*")
    print(f"{len(props)} propriété(s) trouvée(s)")

    for prop in props:
        pid     = prop["id"]
        email   = prop.get("email") or prop.get("contact_email")
        signat  = prop.get("signataire") or prop.get("nom","")

        if not email:
            print(f"⚠️ Propriété {prop['nom']} — pas d'email, ignorée")
            continue

        print(f"📧 Traitement {prop['nom']} → {email}")

        # Réservations du mois précédent
        resas_mois = sb_get("reservations",
            f"propriete_id=eq.{pid}"
            f"&date_arrivee=gte.{debut_mois}"
            f"&date_arrivee=lte.{fin_mois}"
            f"&plateforme=neq.Fermeture"
        )

        # Réservations du mois encore précédent (comparaison)
        resas_prec = sb_get("reservations",
            f"propriete_id=eq.{pid}"
            f"&date_arrivee=gte.{debut_2}"
            f"&date_arrivee=lte.{fin_2}"
            f"&plateforme=neq.Fermeture"
        )

        # Heures ménage du mois précédent
        heures = sb_get("pointages_menage",
            f"propriete_id=eq.{pid}"
            f"&date_menage=gte.{debut_mois}"
            f"&date_menage=lte.{fin_mois}"
        )

        html = generer_rapport_html(prop, resas_mois, resas_prec,
                                     heures, mois, annee)

        sujet = f"📊 Rapport {MOIS_FR[mois-1]} {annee} — {prop['nom']}"
        send_email(email, signat, sujet, html)

    print("=== Rapports envoyés ===")


if __name__ == "__main__":
    main()
