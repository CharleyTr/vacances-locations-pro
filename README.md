# 🏖️ Vacances-Locations PRO — v2.0

Application Streamlit de gestion locative avec synchronisation Supabase.

## 🚀 Démarrage rapide

### 1. Configurer l'environnement
```bash
cp .env.example .env
# Remplir SUPABASE_URL et SUPABASE_KEY dans .env
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Créer la table Supabase
Exécuter le fichier `database/migrations/001_create_reservations.sql`
dans l'éditeur SQL de votre dashboard Supabase.

### 4. Importer les données
Lancer l'app puis aller dans **Réservations → Import CSV**
et uploader votre fichier `reservations.csv`.

### 5. Lancer l'application
```bash
streamlit run app.py
```

---

## 📂 Structure

```
vacances-locations-pro/
├── app.py                          # Point d'entrée
├── config.py                       # Variables d'env
├── .env.example                    # Template config
├── requirements.txt
│
├── database/
│   ├── supabase_client.py          # Connexion Supabase (avec fallback)
│   ├── reservations_repo.py        # CRUD réservations
│   └── migrations/
│       └── 001_create_reservations.sql
│
├── models/
│   └── reservation.py              # Dataclass Reservation
│
├── services/
│   ├── reservation_service.py      # Chargement (Supabase ou CSV)
│   ├── import_service.py           # Import CSV → Supabase
│   ├── analytics_service.py        # KPIs et métriques
│   ├── finance_service.py          # Rapport financier
│   ├── gap_service.py              # Détection créneaux libres
│   ├── opportunity_service.py      # Opportunités réservation
│   ├── calendar_service.py         # Événements calendrier
│   ├── cleaning_service.py         # Planning ménage
│   ├── alert_service.py            # Alertes arrivées / paiements
│   ├── messaging_service.py        # Envoi emails Brevo
│   └── automation_service.py       # Automatisations
│
├── pages/
│   ├── dashboard.py                # Vue principale + KPIs
│   ├── reservations.py             # Liste + filtres + import
│   ├── calendar.py                 # Vue calendrier
│   ├── analytics.py                # Analyses financières
│   └── gaps.py                     # Créneaux libres
│
├── components/
│   └── sidebar.py                  # Navigation + statut connexion
│
└── data/
    └── reservations.csv            # Données locales (fallback)
```

## 🔌 Mode hors ligne

Sans `.env` configuré, l'app fonctionne en **mode CSV local** :
le fichier `data/reservations.csv` est utilisé automatiquement.

## 📊 Colonnes CSV supportées

| Colonne | Type | Description |
|---|---|---|
| `nom_client` | text | Nom du voyageur |
| `date_arrivee` | date | Date d'arrivée |
| `date_depart` | date | Date de départ |
| `plateforme` | text | Booking / Airbnb / Direct / Abritel |
| `prix_brut` | float | Prix total encaissé |
| `commissions` | float | Commissions plateforme |
| `prix_net` | float | Revenu après commissions |
| `menage` | float | Frais ménage |
| `paye` | bool | Statut paiement |
| `propriete_id` | int | ID de la propriété (1 ou 2) |
