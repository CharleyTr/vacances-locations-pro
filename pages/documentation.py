"""
Page Documentation — Guide utilisateur intégré à l'application.
"""
import streamlit as st
import base64
import os


def show():
    st.title("📖 Documentation")
    st.caption("Guide utilisateur complet — Vacances-Locations Pro v3.0")

    # ── Bouton téléchargement Word ────────────────────────────────────────
    doc_path = os.path.join(os.path.dirname(__file__), "..", "static", "README_VacancesLocationsPro.docx")
    if os.path.exists(doc_path):
        with open(doc_path, "rb") as f:
            doc_bytes = f.read()
        st.download_button(
            label="⬇️ Télécharger le guide complet (Word)",
            data=doc_bytes,
            file_name="README_VacancesLocationsPro.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary",
        )
        st.divider()

    # ── Sélecteur de section ─────────────────────────────────────────────
    SECTIONS = [
        "1. Introduction",
        "2. Modules",
        "3. Réservations",
        "4. Calendrier",
        "5. Analyses",
        "6. Messages & Modèles",
        "7. Tarifs",
        "8. Fiscal LMNP",
        "9. Revenus & Pricing",
        "10. Sécurité",
        "11. Configuration",
        "12. FAQ",
    ]
    section = st.selectbox("📑 Aller à la section", SECTIONS, key="doc_section")
    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 1. INTRODUCTION
    # ─────────────────────────────────────────────────────────────────────
    if section == "1. Introduction":
        st.subheader("1. Introduction")

    st.markdown("""
**Vacances-Locations Pro** est une application web de gestion locative développée avec Streamlit.
Elle centralise la gestion complète de vos locations saisonnières : réservations, finances, fiscalité,
communication clients et tarification.

| | |
|---|---|
| 🏖️ **Propriétés** | Le Turenne — Bordeaux · Villa Tobias — Nice |
| 🛠️ **Technologies** | Python / Streamlit · Supabase · GitHub · Brevo · Claude API |
| 🌐 **URL** | https://vacances-locations-pro-iqmuq8xq9g3kxgw6n8ogpv.streamlit.app |
| 👤 **Développeur** | Charley Trigano — 2026 |
""")

    st.info("💡 **Accès** : un mot de passe global est demandé à l'ouverture. Chaque propriété peut avoir son propre mot de passe supplémentaire.")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 2. MODULES
    # ─────────────────────────────────────────────────────────────────────
    if section == "2. Modules":
        st.subheader("2. Vue d\'ensemble des modules")

    modules = [
        ("📊", "Dashboard",          "Tableau de bord : KPIs, alertes, activité récente, calendrier mini"),
        ("📋", "Réservations",        "Liste, saisie, modification, suppression. Recherche par nom client"),
        ("📅", "Calendrier",          "Vue mensuelle, semaine, Gantt, blocage dates, tableau du mois + totaux"),
        ("📈", "Analyses",            "Bilan annuel + comparaison 5 ans mois par mois, filtres plateforme"),
        ("💳", "Paiements",           "Suivi des paiements, relances, statuts"),
        ("🧹", "Ménage",              "Planning ménage, checklists par propriété"),
        ("📧", "Messages",            "WhatsApp, email Brevo, SMS avec modèles personnalisés et variables"),
        ("🔄", "Sync iCal",           "Synchronisation calendriers Airbnb et Booking.com"),
        ("🕳️", "Créneaux",           "Détection des trous entre réservations"),
        ("🏠", "Propriétés",          "Fiche propriété, signataire, mot de passe, URL iCal"),
        ("📊", "Rapports",            "Rapports personnalisés"),
        ("💶", "Tarifs",              "Saisons tarifaires, tableau éditable (prix, dates, ménage)"),
        ("⭐", "Livre d'or",          "Questionnaires satisfaction bilingues FR/EN, liens token"),
        ("📥", "Import Booking",      "Import relevés financiers Booking.com (XLS)"),
        ("📥", "Import Airbnb",       "Import historique et en attente Airbnb (CSV)"),
        ("📝", "Modèles msgs",        "Création et gestion des modèles WhatsApp/SMS avec variables"),
        ("📊", "Export comptable",    "Fichier Excel 4 onglets (Réservations, Mensuel, Plateforme, Synthèse)"),
        ("🏛️", "Fiscal LMNP",        "Seuils micro-BIC, IR, cotisations SSI/URSSAF, micro vs réel"),
        ("📈", "Revenus & Pricing",   "Pricing dynamique, analyse IA, benchmark concurrents, prévisions 12 mois"),
        ("📐", "Barèmes fiscaux",     "Mise à jour annuelle des paramètres IR/micro-BIC depuis les textes officiels"),
    ]

    for icon, name, desc in modules:
        st.markdown(
            f"<div style='display:flex;align-items:center;padding:6px 12px;border-left:4px solid #1565C0;"
            f"background:#F8FBFF;margin-bottom:4px;border-radius:0 6px 6px 0'>"
            f"<span style='font-size:20px;width:36px'>{icon}</span>"
            f"<span style='font-weight:bold;width:200px;color:#1565C0'>{name}</span>"
            f"<span style='color:#444;font-size:14px'>{desc}</span></div>",
            unsafe_allow_html=True
        )

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 3. RÉSERVATIONS
    # ─────────────────────────────────────────────────────────────────────
    if section == "3. Réservations":
        st.subheader("3. Réservations")

    with st.expander("📋 Liste & Filtres"):
        st.markdown("""
- **🔎 Recherche par nom** : saisissez quelques lettres — la liste se filtre instantanément
- **Filtres combinables** : Plateforme · Année (dynamique) · Paiement · Propriété
""")

    with st.expander("➕ Ajouter une réservation"):
        st.markdown("""
Champs obligatoires * : Nom client, plateforme, propriété, dates arrivée/départ.

Les nuits sont calculées automatiquement. Renseignez également :
- Prix brut, commissions, frais ménage, taxes de séjour
- Téléphone et email pour les messages automatiques
- Statut paiement
""")

    with st.expander("✏️ Modifier / Supprimer"):
        st.markdown("""
1. Recherchez le client par nom dans le champ de recherche
2. Sélectionnez la réservation dans la liste filtrée
3. Modifiez les champs et enregistrez

⚠️ La suppression est définitive.
""")

    with st.expander("📥 Imports Booking & Airbnb"):
        st.markdown("""
**Booking.com** : relevé financier mensuel XLS (Finance → Relevés dans l'extranet)

**Airbnb** : deux fichiers CSV depuis votre tableau de bord → Activité → Exporter :
- Historique des réservations (payées)
- Réservations en attente (à venir)

Un upsert sur le numéro de réservation évite les doublons.
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 4. CALENDRIER
    # ─────────────────────────────────────────────────────────────────────
    if section == "4. Calendrier":
        st.subheader("4. Calendrier")

    with st.expander("📅 Vues disponibles"):
        st.markdown("""
| Vue | Description |
|-----|-------------|
| **Mensuelle** | Calendrier visuel avec code couleur par plateforme |
| **Semaine** | Affichage semaine par semaine |
| **Gantt** | Vue chronologique de toutes les réservations |
| **Tableau du mois** | Liste + totaux (CA Brut, Commission, Ménage, CA Net) |
""")

    with st.expander("📋 Tableau du mois"):
        st.markdown("""
Sous le calendrier, un tableau récapitule toutes les réservations du mois avec :
- Client, plateforme, dates, nuits du mois
- CA Brut · Commission · Ménage · CA Net · Payé

**⚠️ Important** : chaque réservation est rattachée à son **mois d'arrivée** (même si elle déborde sur le mois suivant).

Ligne de totaux en bas : Réservations · Nuits louées · CA Brut · Commissions · CA Net.
""")

    with st.expander("🔒 Bloquer des dates"):
        st.markdown("""
Section « 🔒 Bloquer des dates » en bas du calendrier.
Saisissez la période et le motif (ménage, travaux, usage personnel...).
Ces blocs apparaissent en gris et sont exclus des calculs de CA.
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 5. ANALYSES
    # ─────────────────────────────────────────────────────────────────────
    if section == "5. Analyses":
        st.subheader("5. Analyses")

    with st.expander("📊 Bilan annuel"):
        st.markdown("""
KPIs : CA Brut, CA Net, Commissions, Ménages, Rev/nuit, Nuits, Taux occupation, Nb réservations

- Graphique CA mensuel (brut vs net)
- Répartition plateformes (camembert)
- Revenu moyen/nuit (courbe mensuelle)
- Tableau détail mensuel
""")

    with st.expander("📅 Comparaison pluriannuelle (5 ans)"):
        st.markdown("""
Compare l'année de référence avec les 4 années précédentes, mois par mois :

| Tableau | Contenu |
|---------|---------|
| 💶 Revenus Bruts | Somme annuelle + ligne TOTAL |
| 💵 Revenus Nets | Somme annuelle + ligne TOTAL |
| 🌙 Nuitées | Somme annuelle + ligne TOTAL |
| 📊 Taux d'occupation | Moyenne annuelle + ligne TOTAL |

**Filtres** : plateforme (multi-sélection) · propriété (foyer fiscal)
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 6. MESSAGES & MODÈLES
    # ─────────────────────────────────────────────────────────────────────
    if section == "6. Messages & Modèles":
        st.subheader("6. Messages & Modèles")

    with st.expander("📱 WhatsApp & SMS"):
        st.markdown("""
1. Recherchez le client par nom
2. Choisissez le modèle (chargé depuis la base de données)
3. L'aperçu du message rempli s'affiche avec toutes les variables remplacées
4. Cliquez « 📱 Ouvrir WhatsApp » (lien wa.me) ou « 💬 Ouvrir SMS »
""")

    with st.expander("📝 Variables disponibles dans les modèles"):
        variables = [
            ("{prenom}", "Prénom du client"),
            ("{nom}", "Nom complet"),
            ("{date_arrivee}", "Date d'arrivée (JJ/MM/AAAA)"),
            ("{date_depart}", "Date de départ"),
            ("{nuitees}", "Nombre de nuits"),
            ("{propriete}", "Nom du logement"),
            ("{ville}", "Ville"),
            ("{plateforme}", "Airbnb, Booking..."),
            ("{numero_reservation}", "Référence réservation"),
            ("{prix_brut}", "Montant total (€)"),
            ("{signataire}", "Signataire configuré dans la fiche propriété"),
            ("{lien_questionnaire}", "Lien vers le questionnaire satisfaction"),
        ]
        for var, desc in variables:
            st.markdown(f"- `{var}` — {desc}")

    with st.expander("➕ Créer un modèle (menu 📝 Modèles msgs)"):
        st.markdown("""
- Saisissez le nom, le moment d'envoi et le contenu
- Utilisez les variables entre accolades : `Bonjour {prenom}, votre séjour à {propriete}...`
- Pour les SMS : compteur de caractères et nombre de SMS affiché en temps réel
- **Signataire** : configurez-le dans la fiche propriété (🏠 Propriétés) puis utilisez `{signataire}` dans vos messages
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 7. TARIFS
    # ─────────────────────────────────────────────────────────────────────
    if section == "7. Tarifs":
        st.subheader("7. Tarifs")

    with st.expander("💶 Configuration des saisons"):
        st.markdown("""
Créez des périodes tarifaires avec : nom, dates début/fin, prix/nuit, frais ménage, couleur.

Dans « 📊 Visualisation tarifaire » :
- Diagramme Gantt des périodes
- **Tableau éditable** : cliquez directement sur une cellule pour modifier le prix ou les dates
  - Dates saisies avec sélecteur calendrier (format JJ/MM/AAAA)
  - Cliquez « 💾 Enregistrer les modifications » pour sauvegarder
- **Calculateur** : saisissez des dates → le prix total est calculé par saison
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 8. FISCAL LMNP
    # ─────────────────────────────────────────────────────────────────────
    if section == "8. Fiscal LMNP":
        st.subheader("8. Fiscal LMNP")

    st.warning("⚠️ Les calculs sont indicatifs — consultez un expert-comptable pour votre situation réelle.")

    with st.expander("📊 Paramètres à configurer en haut de page"):
        st.markdown("""
| Paramètre | Options |
|-----------|---------|
| Année fiscale | 2023 à 2026+ |
| Classement | Classé / Gîte (50% depuis 2025) · Non classé (30% depuis 2025) |
| Situation familiale | Sélecteur : célibataire, marié + enfants, parent isolé... |
| Autres revenus | Salaires, pensions, autres BIC |
| Filtre plateforme | Multi-sélection |
""")

    with st.expander("📐 Changement LFR 2024 (revenus 2025+)"):
        st.markdown("""
| Régime | Avant 2025 | 2025+ |
|--------|-----------|-------|
| Classé / Gîte | 71% — seuil 188 700 € | **50%** — seuil **77 700 €** |
| Non classé | 50% — seuil 77 700 € | **30%** — seuil **15 000 €** |

Mettez à jour le barème dans 📐 Barèmes fiscaux dès parution de la Loi de Finances.
""")

    with st.expander("📑 Onglet Micro-BIC vs Réel — Frais déductibles"):
        st.markdown("""
Sélectionnez la propriété (chaque bien = foyer fiscal distinct), puis :

**Saisie des frais** :
- Ajoutez chaque frais avec catégorie, libellé et montant
- La colonne « Rubrique déclaration IR » s'affiche automatiquement (Ligne 236, 240, 250...)
- Tableau de synthèse par ligne 2033-B pour remplir votre déclaration

**Comparaison automatique** : le tableau affiche micro-BIC vs réel avec net après impôt pour chaque régime.
""")

    with st.expander("📐 Mise à jour annuelle des barèmes"):
        st.markdown("""
Menu 📐 Barèmes fiscaux → onglet « Ajouter / Modifier » :

1. Sélectionnez l'année
2. Saisissez seuils micro-BIC, taux d'abattement, tranches IR
3. Notez la source dans le champ dédié (ex : *LFI 2027 — JO du 30/12/2026*)
4. Enregistrez — le tableau de bord fiscal utilise immédiatement les nouvelles valeurs

**Sources** : impots.gouv.fr · legifrance.gouv.fr · bofip.impots.gouv.fr
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 9. REVENUS & PRICING
    # ─────────────────────────────────────────────────────────────────────
    if section == "9. Revenus & Pricing":
        st.subheader("9. Revenus & Pricing")

    with st.expander("💡 Pricing dynamique"):
        st.markdown("""
Saisissez votre prix de base → l'application calcule un prix suggéré pour chaque mois :

| Taux occupation historique | Ajustement |
|---------------------------|-----------|
| > 85% | +15% |
| > 70% | +8% |
| 40–70% | 0% |
| < 40% | -10% |
| < 25% | -20% |

Les **événements locaux** (festivals, congrès, vacances...) ajoutent un % supplémentaire.

Le tableau affiche : Taux occ. hist. · Rev. moy./nuit · **CA moy. mensuel** · Prix suggéré · **CA suggéré** · Variation — avec ligne TOTAL annuel.
""")

    with st.expander("🤖 Analyse IA (Claude)"):
        st.markdown("""
Bouton « 🤖 Générer l'analyse IA » : Claude analyse votre historique, vos événements et vos concurrents pour produire :
- Diagnostic de vos performances
- Opportunités de hausse de prix
- Points d'attention
- 3 recommandations concrètes avec chiffres
""")

    with st.expander("🔮 Prévisions de revenus"):
        st.markdown("""
Pour l'année sélectionnée (12 mois complets) :
- **CA confirmé** : réservations déjà enregistrées
- **Projection** : moyenne des 3 dernières années pour les mois restants
- Graphique barres + taux d'occupation + 3 lignes de seuils fiscaux
- Tableau détail mensuel avec **ligne TOTAL**
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 10. SÉCURITÉ
    # ─────────────────────────────────────────────────────────────────────
    if section == "10. Sécurité":
        st.subheader("10. Sécurité & Mots de passe")

    with st.expander("🔐 Deux niveaux de protection"):
        st.markdown("""
**Niveau 1 — Mot de passe global** (`APP_PASSWORD` dans les Secrets Streamlit)
Protège l'accès à toute l'application. Configurez-le dans Streamlit Cloud → Settings → Secrets.

**Niveau 2 — Mot de passe par propriété**
Protège l'accès aux données d'un bien spécifique.
- Configuration : 🏠 Propriétés → section « 🔐 Mots de passe »
- Saisissez le mot de passe et cliquez « 💾 Appliquer »
- Pour supprimer : laissez vide et cliquez Appliquer
- Pour verrouiller manuellement : cliquez 🔒 dans la barre latérale

🔒 Les mots de passe sont stockés **hashés SHA-256** — jamais en clair.
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 11. CONFIGURATION
    # ─────────────────────────────────────────────────────────────────────
    if section == "11. Configuration":
        st.subheader("11. Configuration Technique")

    with st.expander("🔑 Secrets Streamlit Cloud"):
        secrets = [
            ("SUPABASE_URL",         "URL de votre projet Supabase"),
            ("SUPABASE_KEY",         "Clé anonyme Supabase"),
            ("BREVO_API_KEY",        "Clé API Brevo (email/SMS)"),
            ("EMAIL_FROM",           "Adresse expéditeur emails"),
            ("APP_URL",              "URL de l'application (sans / final)"),
            ("APP_PASSWORD",         "Mot de passe global d'accès"),
            ("TWILIO_ACCOUNT_SID",   "SID Twilio (optionnel, WhatsApp API)"),
            ("TWILIO_AUTH_TOKEN",    "Token Twilio (optionnel)"),
            ("TWILIO_WHATSAPP_FROM", "Numéro Twilio WhatsApp (optionnel)"),
        ]
        for key, desc in secrets:
            st.markdown(f"- `{key}` — {desc}")

    with st.expander("📁 Structure des fichiers"):
        st.markdown("""
```
vacances-locations-pro/
├── app.py                    # Routing principal + login global
├── config.py                 # Lecture des Secrets
├── requirements.txt
├── .streamlit/config.toml
├── pages/                    # Un fichier par module
├── services/                 # Logique métier
├── database/                 # Accès Supabase
├── components/               # Sidebar, KPI cards
├── integrations/             # Brevo, WhatsApp, iCal
└── static/                   # README.docx
```
""")

    with st.expander("🗄️ Migrations SQL"):
        st.markdown("""
Exécutez ces scripts dans l'ordre dans l'éditeur SQL Supabase :

| Script | Contenu |
|--------|---------|
| 001 → 004 | Tables de base (réservations, propriétés, avis...) |
| 005 | message_templates |
| 006 | Colonne signataire dans propriétés |
| 007 | frais_deductibles |
| 008 | evenements_locaux + prix_concurrents |
| 009 | baremes_fiscaux |
| 010 | Colonne mot_de_passe dans propriétés |
""")

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # 12. FAQ
    # ─────────────────────────────────────────────────────────────────────
    if section == "12. FAQ":
        st.subheader("12. Questions Fréquentes")

    faqs = [
        ("L'application est lente au premier chargement",
         "Normal — Streamlit Cloud met l'app en veille après inactivité. Le premier chargement prend 15-30 secondes. Ensuite c'est fluide."),
        ("Les données ne s'affichent pas",
         "Vérifiez que les Secrets SUPABASE_URL et SUPABASE_KEY sont corrects. Le bandeau vert « 🟢 Supabase connecté » doit apparaître dans la sidebar."),
        ("Comment ajouter une nouvelle propriété ?",
         "Menu 🏠 Propriétés → « ➕ Ajouter une propriété ». Elle apparaît immédiatement dans le sélecteur."),
        ("Comment exporter pour mon comptable ?",
         "Menu 📊 Export comptable → propriété + année → « 🔄 Générer » → « ⬇️ Télécharger »"),
        ("Les barèmes fiscaux sont-ils à jour ?",
         "2023 à 2026 sont pré-chargés. Pour les années suivantes, utilisez 📐 Barèmes fiscaux dès parution de la Loi de Finances."),
        ("Comment le questionnaire satisfaction est-il envoyé ?",
         "Générez un lien depuis ⭐ Livre d'or, envoyez-le au client par WhatsApp/email. Pas de connexion requise. Lien valable 30 jours."),
        ("Comment modifier un prix dans le tableau des tarifs ?",
         "Menu 💶 Tarifs → 📊 Visualisation tarifaire → cliquez directement dans la cellule Prix/nuit ou Date → 💾 Enregistrer."),
        ("Comment mettre à jour les barèmes fiscaux chaque année ?",
         "Menu 📐 Barèmes fiscaux → onglet Ajouter/Modifier → saisissez les nouvelles tranches IR et seuils dès publication de la LFI → Enregistrer."),
    ]

    for question, reponse in faqs:
        with st.expander(f"❓ {question}"):
            st.markdown(reponse)

    st.divider()

    # ─────────────────────────────────────────────────────────────────────
    # Crédits
    # ─────────────────────────────────────────────────────────────────────
    st.markdown("""
<div style='text-align:center;padding:2rem;background:#F8FBFF;border-radius:12px;margin-top:1rem'>
    <div style='font-size:36px'>🏖️</div>
    <h3 style='color:#1565C0;margin:0.5rem 0'>Vacances-Locations Pro</h3>
    <p style='color:#555;margin:0.3rem 0'>Développé par <strong>Charley Trigano</strong></p>
    <p style='color:#888;font-size:13px;margin:0'>Version 3.0 — 2026 · © Tous droits réservés</p>
</div>
""", unsafe_allow_html=True)
