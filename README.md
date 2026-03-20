# 🏖️ Vacances-Locations PRO — v5.0

Application Python/Streamlit de gestion locative professionnelle avec Supabase.

**URL** : https://vacances-locations-pro-iqmuq8xq9g3kxgw6n8ogpv.streamlit.app  
**Développé par** : Charley Trigano — 2026

---

## ✨ Fonctionnalités

### 🏠 Gestion locative
- Réservations (import Booking, Airbnb, saisie manuelle)
- Calendrier mensuel/semaine avec liens plateformes cliquables
- Paiements & relances
- Planning ménage
- Créneaux libres & opportunités
- Sync iCal (Airbnb, Booking)

### 👥 Utilisateurs & Sécurité
- **3 niveaux d'accès** : Admin / Propriétaire / Gestionnaire
- Login hybride : Code PIN propriété OU Email + code personnel
- Session persistante via cookie (30 jours)
- Journal des connexions (admin)
- Gestion utilisateurs avec invitation email (Supabase Auth)

### 💬 Communication
- Chat interne temps réel (toutes propriétés)
- Messagerie WhatsApp / SMS / Email (Brevo)
- Modèles de messages personnalisables
- Questionnaire satisfaction client bilingue FR/EN

### 📊 Analyses & Reporting
- Dashboard KPIs (CA brut/net, taux occupation, commissions)
- Analyses par plateforme, mensuelle, pluriannuelle
- Statistiques par pays (auto-détection depuis indicatif téléphonique)
- Export comptable
- Rapports PDF

### 🏛️ Fiscal LMNP
- Suivi seuils Micro-BIC (barèmes 2023-2026)
- Estimation fiscale & cotisations sociales
- Liasse 2033 pré-remplie automatiquement
- Simulation déclaration revenus (multi-propriétés, multi-régimes)
- Export rapport fiscal PDF
- Frais déductibles avec justificatifs (Supabase Storage)

### 🧾 Facturation
- Génération factures PDF (logos distincts par propriété)
- Mention LMNP TVA non applicable

### 💾 Sauvegarde
- Export CSV par table
- Export Excel complet (toutes tables)

---

## 🗄️ Architecture

```
vacances-locations-pro/
├── app.py                          # Routeur principal + login hybride
├── config.py                       # Variables d'environnement
├── requirements.txt
│
├── components/
│   ├── sidebar.py                  # Navigation filtrée par rôle + badges
│   └── kpi_cards.py
│
├── database/
│   ├── supabase_client.py          # Connexion Supabase
│   ├── reservations_repo.py
│   ├── proprietes_repo.py
│   ├── auth_repo.py                # Supabase Auth (invite, sign_in, codes)
│   ├── journal_repo.py             # Journal connexions
│   ├── chat_repo.py                # Messagerie interne
│   ├── frais_repo.py               # Frais déductibles LMNP
│   ├── justificatifs_repo.py       # Supabase Storage
│   ├── baremes_repo.py             # Barèmes fiscaux
│   └── ...
│
├── services/
│   ├── auth_service.py             # Rôles, permissions, can_see/can_edit
│   ├── reservation_service.py
│   ├── facture_service.py          # PDF factures
│   ├── indicatifs_service.py       # Détection pays depuis téléphone
│   ├── template_service.py         # Modèles messages
│   └── ...
│
├── pages/                          # 35 pages
│   ├── dashboard.py
│   ├── reservations.py
│   ├── calendar.py
│   ├── analytics.py                # Stats + onglet pays
│   ├── fiscal.py                   # LMNP complet + liasse 2033
│   ├── chat.py                     # Messagerie interne + pièces jointes
│   ├── utilisateurs.py             # Gestion users (admin)
│   ├── journal.py                  # Journal connexions (admin)
│   ├── sauvegarde.py               # Export données (admin)
│   └── ...
│
├── integrations/
│   ├── brevo_client.py             # Email + SMS
│   ├── whatsapp_client.py
│   └── ical_sync.py
│
└── static/                         # PWA + icônes
    ├── manifest.json
    ├── sw.js                       # Service Worker
    ├── offline.html
    └── icon-*.png
```

---

## ⚙️ Configuration

### Secrets Streamlit Cloud
```toml
SUPABASE_URL         = "https://xxxx.supabase.co"
SUPABASE_KEY         = "eyJ..."           # anon key
SUPABASE_SERVICE_KEY = "eyJ..."           # service_role key
BREVO_API_KEY        = "xkeysib-..."
EMAIL_FROM           = "c.trigano@gmail.com"
APP_URL              = "https://vacances-locations-pro-iqmuq8xq9g3kxgw6n8ogpv.streamlit.app"
AUTH_REDIRECT_URL    = "https://CharleyTr.github.io/vlp-auth/"
ADMIN_PROP_ID        = "2"                # ID propriété administrateur
COOKIE_PASSWORD      = "votre-secret-cookie-long"
TWILIO_ACCOUNT_SID   = "ACxxxxxxxxxx"
TWILIO_AUTH_TOKEN    = "votre_token"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
```

### Scripts SQL (dans l'ordre)
| Script | Contenu |
|--------|---------|
| 001-004 | Tables de base |
| 005 | message_templates |
| 006 | signataire dans proprietes |
| 007 | frais_deductibles |
| 008 | pricing |
| 009 | baremes_fiscaux |
| 010 | mot_de_passe dans proprietes |
| 011 | propriété modèle démo |
| 012 | codes PIN |
| 013 | justificatifs (Storage) |
| 014 | infos facturation proprietes |
| 015 | auth_preparation (profiles, propriete_access) |
| 016 | admin_setup |
| 017b | rls_fix (RLS désactivé) |
| 018 | auth_email_config |
| 019 | journal_connexions |
| 020 | chat_messages + bucket |
| 021 | code_acces dans profiles |
| 022 | roles_propriete + mot_de_passe_gestionnaire |

---

## 🔐 Niveaux d'accès

| Rôle | Accès | Connexion |
|------|-------|-----------|
| **Admin** | Tout — toutes propriétés | Code PIN Villa Tobias |
| **Propriétaire** | Sa propriété — menus complets | Code PIN propriété |
| **Gestionnaire** | Dashboard, Calendrier, Ménage, Messages, Chat | Code gestionnaire |

---

## 🏗️ Déploiement

1. Fork le repo GitHub
2. Connecter à Streamlit Cloud
3. Configurer les Secrets
4. Exécuter les scripts SQL dans Supabase
5. L'app est opérationnelle

---

## 📦 Dépendances principales

```
streamlit >= 1.32
supabase >= 2.3
pandas, plotly, reportlab
streamlit-cookies-manager
icalendar, openpyxl
```
