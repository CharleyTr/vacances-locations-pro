"""
Script d'envois automatiques — exécuté chaque matin via GitHub Actions.
- SMS/Email J-2 avant arrivée
- Email J+1 après départ (questionnaire satisfaction)
- Notification nouvelle réservation (J0)
"""
import os
import sys
import json
import requests
from datetime import date, timedelta, datetime

# ── Configuration ──────────────────────────────────────────────────────────
SUPABASE_URL  = os.environ["SUPABASE_URL"]
SUPABASE_KEY  = os.environ["SUPABASE_SERVICE_KEY"]
BREVO_KEY     = os.environ["BREVO_API_KEY"]
EMAIL_FROM    = os.environ.get("EMAIL_FROM", "")
APP_URL       = os.environ.get("APP_URL", "")

TODAY     = date.today()
DEMAIN    = TODAY + timedelta(days=1)
J_MINUS_2 = TODAY + timedelta(days=2)   # Arrivée dans 2 jours
J_PLUS_1  = TODAY - timedelta(days=1)   # Départ hier

print(f"[VLP Auto] {datetime.now().strftime('%Y-%m-%d %H:%M')} — Démarrage")
print(f"  J-2 arrivée : {J_MINUS_2}")
print(f"  J+1 départ  : {J_PLUS_1}")

# ── Helpers Supabase ────────────────────────────────────────────────────────
HEADERS_SB = {
    "apikey":        SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type":  "application/json",
}

def sb_get(table, params=""):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}?{params}",
                     headers=HEADERS_SB, timeout=15)
    r.raise_for_status()
    return r.json()

def sb_patch(table, record_id, data):
    r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{record_id}",
                       headers=HEADERS_SB, json=data, timeout=15)
    r.raise_for_status()
    return r.json()

# ── Helper Brevo email ──────────────────────────────────────────────────────
def send_email_brevo(to_email: str, to_name: str, subject: str, html: str) -> bool:
    if not to_email or not BREVO_KEY:
        return False
    r = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={"api-key": BREVO_KEY, "Content-Type": "application/json"},
        json={
            "sender":   {"name": "Vacances-Locations Pro", "email": EMAIL_FROM},
            "to":       [{"email": to_email, "name": to_name}],
            "subject":  subject,
            "htmlContent": html,
        },
        timeout=15,
    )
    ok = r.status_code in (200, 201)
    if not ok:
        print(f"  ❌ Brevo email error {r.status_code}: {r.text[:100]}")
    return ok

def _html(contenu: str, prop_nom: str = "") -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto;
                border:1px solid #e0e0e0;border-radius:8px;overflow:hidden">
      <div style="background:#1565C0;padding:20px;text-align:center">
        <h2 style="color:white;margin:0">🏖️ {prop_nom or 'Vacances-Locations Pro'}</h2>
      </div>
      <div style="padding:24px;line-height:1.7">
        {"<br>".join(contenu.split(chr(10)))}
      </div>
      <div style="background:#f5f5f5;padding:12px;text-align:center;
                  font-size:12px;color:#757575">
        Vacances-Locations PRO — Message automatique
      </div>
    </div>"""

# ── Charger les propriétés ──────────────────────────────────────────────────
props_list = sb_get("proprietes", "actif=eq.true&select=id,nom,ville,signataire")
props = {p["id"]: p for p in props_list}

# ── Charger les templates WhatsApp ─────────────────────────────────────────
templates_list = sb_get("message_templates", "actif=eq.true&canal=eq.whatsapp&select=*")
tpl_by_moment = {t["moment"]: t for t in templates_list}

def get_template(moment: str, res: dict, prop: dict) -> str:
    """Applique le template si disponible, sinon message par défaut."""
    tpl = tpl_by_moment.get(moment)
    if not tpl:
        return None
    from dateutil import parser as _dp
    def fmt_date(val):
        if not val: return ""
        try: return _dp.parse(str(val)).strftime("%d/%m/%Y")
        except: return str(val)[:10]
    nom = str(res.get("nom_client","") or "")
    prenom = nom.split()[0] if nom else ""
    contenu = tpl["contenu"]
    replacements = {
        "{prenom}":      prenom,
        "{nom}":         nom,
        "{propriete}":   prop.get("nom",""),
        "{ville}":       prop.get("ville",""),
        "{signataire}":  prop.get("signataire",""),
        "{date_arrivee}": fmt_date(res.get("date_arrivee")),
        "{date_depart}":  fmt_date(res.get("date_depart")),
        "{nuitees}":     str(int(res.get("nuitees",0) or 0)),
        "{plateforme}":  str(res.get("plateforme","") or ""),
        "{email}":       str(res.get("email","") or ""),
        "{telephone}":   str(res.get("telephone","") or ""),
        "{pays}":        str(res.get("pays","") or ""),
    }
    for k, v in replacements.items():
        contenu = contenu.replace(k, v)
    return contenu

# ══════════════════════════════════════════════════════════════════════════════
# 1. SMS/EMAIL J-2 AVANT ARRIVÉE
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n📅 J-2 Arrivées le {J_MINUS_2}...")
rappels = sb_get("reservations",
    f"date_arrivee=eq.{J_MINUS_2.isoformat()}"
    f"&sms_envoye=eq.false"
    f"&plateforme=neq.Fermeture"
    f"&select=*")

print(f"  {len(rappels)} réservation(s) à rappeler")
ok_j2 = 0

for res in rappels:
    prop = props.get(res.get("propriete_id"), {})
    nom  = res.get("nom_client","")
    email = res.get("email","")
    prenom = nom.split()[0] if nom else "cher client"

    # Essayer le template J-3 ou arrivee
    msg = (get_template("j-3", res, prop) or
           get_template("arrivee", res, prop))

    if not msg:
        msg = (f"Bonjour {prenom},\n\n"
               f"Votre arrivée à {prop.get('nom','')} est dans 2 jours "
               f"({J_MINUS_2.strftime('%d/%m/%Y')}).\n\n"
               f"N'hésitez pas à nous contacter pour toute question.\n\n"
               f"{prop.get('signataire','Vacances-Locations Pro')}")

    sujet = f"🏖️ Votre arrivée dans 2 jours — {prop.get('nom','')}"

    sent = False
    if email:
        sent = send_email_brevo(email, nom, sujet, _html(msg, prop.get("nom","")))
        if sent:
            print(f"  ✅ Email J-2 → {nom} ({email})")

    if sent:
        sb_patch("reservations", res["id"], {"sms_envoye": True})
        ok_j2 += 1
    else:
        print(f"  ⚠️  Pas d'email pour {nom}")

print(f"  → {ok_j2}/{len(rappels)} envoyés")

# ══════════════════════════════════════════════════════════════════════════════
# 2. EMAIL J+1 APRÈS DÉPART (questionnaire satisfaction)
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n🙏 J+1 Départs le {J_PLUS_1}...")
post_dep = sb_get("reservations",
    f"date_depart=eq.{J_PLUS_1.isoformat()}"
    f"&post_depart_envoye=eq.false"
    f"&plateforme=neq.Fermeture"
    f"&select=*")

print(f"  {len(post_dep)} réservation(s) post-départ")
ok_postdep = 0

for res in post_dep:
    prop  = props.get(res.get("propriete_id"), {})
    nom   = res.get("nom_client","")
    email = res.get("email","")
    prenom = nom.split()[0] if nom else "cher client"

    # Générer lien questionnaire
    import hashlib
    res_id = str(res.get("id",""))
    token  = hashlib.md5(f"{res_id}{APP_URL}".encode()).hexdigest()[:16]
    lien_q = f"{APP_URL}/?token={token}" if APP_URL else ""

    msg = get_template("post_depart", res, prop)
    if not msg:
        msg = (f"Bonjour {prenom},\n\n"
               f"Merci pour votre séjour à {prop.get('nom','')} !\n\n"
               f"Votre avis nous est précieux. Partagez votre expérience en 2 minutes :\n"
               f"{lien_q}\n\n"
               f"À très bientôt !\n"
               f"{prop.get('signataire','Vacances-Locations Pro')}")
    elif lien_q:
        msg = msg.replace("{lien_questionnaire}", lien_q)

    sujet = f"🙏 Merci pour votre séjour — {prop.get('nom','')}"

    if email:
        sent = send_email_brevo(email, nom, sujet, _html(msg, prop.get("nom","")))
        if sent:
            print(f"  ✅ Email J+1 → {nom} ({email})")
            sb_patch("reservations", res["id"], {"post_depart_envoye": True})
            ok_postdep += 1
        else:
            print(f"  ⚠️  Échec email pour {nom}")
    else:
        print(f"  ⚠️  Pas d'email pour {nom}")

print(f"  → {ok_postdep}/{len(post_dep)} envoyés")

# ══════════════════════════════════════════════════════════════════════════════
# 3. NOTIFICATION NOUVELLE RÉSERVATION (créées aujourd'hui)
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n🔔 Nouvelles réservations du {TODAY}...")
nouvelles = sb_get("reservations",
    f"created_at=gte.{TODAY.isoformat()}T00:00:00"
    f"&created_at=lte.{TODAY.isoformat()}T23:59:59"
    f"&plateforme=neq.Fermeture"
    f"&select=*")

print(f"  {len(nouvelles)} nouvelle(s) réservation(s)")

if nouvelles:
    # Email récap à l'admin
    admin_email = EMAIL_FROM
    lignes = []
    for res in nouvelles:
        prop = props.get(res.get("propriete_id"), {})
        lignes.append(
            f"• <b>{res.get('nom_client','?')}</b> — "
            f"{prop.get('nom','?')} — "
            f"{res.get('date_arrivee','?')} → {res.get('date_depart','?')} "
            f"({res.get('nuitees','?')} nuits) — "
            f"{res.get('plateforme','?')} — "
            f"{float(res.get('prix_net',0) or 0):,.0f} € net"
        )
    html_recap = _html(
        f"<b>🎉 {len(nouvelles)} nouvelle(s) réservation(s) aujourd'hui :</b><br><br>" +
        "<br>".join(lignes),
        "Vacances-Locations Pro"
    )
    sent = send_email_brevo(
        admin_email, "Admin",
        f"🔔 VLP — {len(nouvelles)} nouvelle(s) réservation(s) le {TODAY.strftime('%d/%m/%Y')}",
        html_recap
    )
    if sent:
        print(f"  ✅ Récap envoyé à {admin_email}")

# ── Résumé final ───────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"✅ Terminé — J-2: {ok_j2} | J+1: {ok_postdep} | Nouvelles: {len(nouvelles)}")
