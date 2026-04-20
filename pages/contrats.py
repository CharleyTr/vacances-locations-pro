"""
Page Contrats — Génération de contrats PDF pour les conciergeries.
"""
import streamlit as st
import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

NAVY  = colors.HexColor("#0B1F3A")
BLUE  = colors.HexColor("#1565C0")
GREY  = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F4F7FF")
WHITE = colors.white

def s(size, color=NAVY, bold=False, align=TA_LEFT, sa=6):
    return ParagraphStyle("_", fontSize=size, textColor=color,
                          fontName="Helvetica-Bold" if bold else "Helvetica",
                          alignment=align, leading=size*1.5, spaceAfter=sa)

def entete_pdf(story, titre, sous_titre, date_str):
    # En-tête
    hd = Table([[
        Paragraph(f"<b>{titre}</b>", s(16, WHITE, bold=True)),
        Paragraph(f"{sous_titre}<br/>Date : {date_str}", s(10, WHITE, align=2)),
    ]], colWidths=[10*cm, 7.8*cm])
    hd.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY),
        ("TOPPADDING",(0,0),(-1,-1),14),("BOTTOMPADDING",(0,0),(-1,-1),14),
        ("LEFTPADDING",(0,0),(0,-1),14),("RIGHTPADDING",(1,0),(1,-1),14),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(hd)
    bande = Table([[""]], colWidths=[17.8*cm], rowHeights=[4])
    bande.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F0B429"))]))
    story.append(bande)
    story.append(Spacer(1, 0.4*cm))

def bloc_parties(story, mandant, mandataire):
    data = [[
        Paragraph(f"<b>LE MANDANT (Propriétaire)</b><br/>{mandant}", s(9, NAVY)),
        Paragraph(f"<b>LE MANDATAIRE (Conciergerie)</b><br/>{mandataire}", s(9, NAVY)),
    ]]
    t = Table(data, colWidths=[8.9*cm, 8.9*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),LIGHT),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),10),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("LINEABOVE",(0,0),(-1,0),2,BLUE),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4*cm))

def signatures(story, partie1="Le Mandant", partie2="Le Mandataire"):
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("SIGNATURES", s(10, NAVY, bold=True)))
    story.append(Spacer(1, 0.2*cm))
    sig = Table([[
        Paragraph(f"{partie1}<br/><br/><br/><br/>___________________________<br/>Date :", s(9, NAVY, align=1)),
        Paragraph(f"{partie2}<br/><br/><br/><br/>___________________________<br/>Date :", s(9, NAVY, align=1)),
    ]], colWidths=[8.9*cm, 8.9*cm])
    sig.setStyle(TableStyle([
        ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
    ]))
    story.append(sig)

def pied_page(story, date_str):
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        f"Document généré le {date_str} par LodgePro — À conserver par chaque partie",
        s(7, GREY, align=1)
    ))

# ─────────────────────────────────────────────────────────────────────────────
# CONTRAT 1 — MANDAT DE GESTION LOCATIVE
# ─────────────────────────────────────────────────────────────────────────────
def generer_mandat_gestion(data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []
    date_str = date.today().strftime("%d/%m/%Y")

    entete_pdf(story, "MANDAT DE GESTION LOCATIVE", "Contrat de gestion", date_str)

    mandant = (f"{data['prop_nom']}<br/>"
               f"{data['prop_adresse']}<br/>"
               f"{data['prop_cp']} {data['prop_ville']}<br/>"
               f"Tél : {data['prop_tel']}<br/>"
               f"Email : {data['prop_email']}")
    mandataire = (f"{data['conc_nom']}<br/>"
                  f"{data['conc_forme']} — SIRET : {data['conc_siret']}<br/>"
                  f"{data['conc_adresse']}<br/>"
                  f"{data['conc_cp']} {data['conc_ville']}<br/>"
                  f"Carte pro G : {data['conc_carte_g']}")

    bloc_parties(story, mandant, mandataire)

    articles = [
        ("Article 1 — Objet du mandat",
         f"Le Mandant confie au Mandataire la gestion locative du bien immobilier situé : "
         f"{data['bien_adresse']}, {data['bien_cp']} {data['bien_ville']} "
         f"(Type : {data['bien_type']} — Surface : {data['bien_surface']} m²). "
         f"Le Mandataire est autorisé à accomplir tous les actes de gestion courante "
         f"nécessaires à la location du bien."),
        ("Article 2 — Durée du mandat",
         f"Le présent mandat est conclu pour une durée de {data['duree']} mois à compter "
         f"du {data['date_debut']}, renouvelable par tacite reconduction. "
         f"Il peut être résilié par l'une ou l'autre des parties avec un préavis de "
         f"{data['preavis']} mois par lettre recommandée avec accusé de réception."),
        ("Article 3 — Missions du Mandataire",
         "Le Mandataire s'engage à : rechercher des locataires, diffuser les annonces sur "
         "les plateformes (Airbnb, Booking, Direct), effectuer les états des lieux, "
         "encaisser les loyers et charges, organiser le ménage entre chaque séjour, "
         "assurer le suivi des réservations et la communication avec les voyageurs, "
         "transmettre un rapport mensuel au Mandant."),
        ("Article 4 — Honoraires",
         f"En rémunération de ses services, le Mandataire percevra une commission de "
         f"{data['commission']}% HT sur les loyers encaissés. "
         f"Les frais de ménage sont {'inclus' if data['menage_inclus'] == 'Inclus' else 'en sus'} "
         f"dans cette commission. "
         f"La facturation interviendra mensuellement."),
        ("Article 5 — Obligations du Mandant",
         "Le Mandant s'engage à : laisser le bien disponible aux dates convenues, "
         "informer le Mandataire de toute contrainte ou indisponibilité, "
         "maintenir le bien en bon état et assuré, "
         "régler les honoraires dans les délais convenus."),
        ("Article 6 — Responsabilité",
         "Le Mandataire apporte tous les soins nécessaires à la gestion du bien. "
         "Sa responsabilité ne saurait être engagée en cas de dégradations causées "
         "par les locataires au-delà du dépôt de garantie. "
         "Le Mandant conserve la responsabilité des travaux et de l'entretien du bien."),
        ("Article 7 — Résiliation",
         f"Le présent mandat peut être résilié par l'une ou l'autre des parties "
         f"moyennant un préavis de {data['preavis']} mois par lettre recommandée "
         f"avec accusé de réception. En cas de faute grave, la résiliation peut "
         f"être immédiate."),
        ("Article 8 — Loi applicable",
         "Le présent contrat est soumis au droit français. "
         "En cas de litige, les parties s'engagent à rechercher une solution amiable "
         "avant tout recours judiciaire. À défaut, le Tribunal compétent sera celui "
         f"du ressort de {data['tribunal']}."),
    ]

    for titre_art, texte_art in articles:
        story.append(Paragraph(titre_art, s(10, NAVY, bold=True)))
        story.append(Paragraph(texte_art, ParagraphStyle("j", fontSize=9, textColor=GREY,
                                alignment=TA_JUSTIFY, leading=14, spaceAfter=8)))
        story.append(Spacer(1, 0.1*cm))

    signatures(story, "Le Mandant (Propriétaire)", "Le Mandataire (Conciergerie)")
    pied_page(story, date_str)
    doc.build(story)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# CONTRAT 2 — CONTRAT DE PRESTATION DE SERVICES
# ─────────────────────────────────────────────────────────────────────────────
def generer_prestation_services(data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []
    date_str = date.today().strftime("%d/%m/%Y")

    entete_pdf(story, "CONTRAT DE PRESTATION DE SERVICES", "Services de conciergerie", date_str)

    client = (f"{data['client_nom']}<br/>"
              f"{data['client_adresse']}<br/>"
              f"{data['client_cp']} {data['client_ville']}<br/>"
              f"Tél : {data['client_tel']}<br/>"
              f"Email : {data['client_email']}")
    prestataire = (f"{data['conc_nom']}<br/>"
                   f"{data['conc_forme']} — SIRET : {data['conc_siret']}<br/>"
                   f"{data['conc_adresse']}<br/>"
                   f"{data['conc_cp']} {data['conc_ville']}")

    bloc_parties(story, client, prestataire)

    # Tableau des prestations
    story.append(Paragraph("Prestations commandées", s(10, NAVY, bold=True)))
    story.append(Spacer(1, 0.15*cm))

    prest_rows = [[
        Paragraph("<b>Prestation</b>", s(9, WHITE, bold=True)),
        Paragraph("<b>Fréquence</b>", s(9, WHITE, bold=True, align=1)),
        Paragraph("<b>Prix unitaire</b>", s(9, WHITE, bold=True, align=2)),
    ]]
    total = 0
    for p in data.get("prestations", []):
        prest_rows.append([
            Paragraph(p["nom"], s(9, NAVY)),
            Paragraph(p["freq"], s(9, GREY, align=1)),
            Paragraph(f"{p['prix']:.2f} EUR", s(9, NAVY, align=2)),
        ])
        total += p["prix"]
    prest_rows.append([
        Paragraph("<b>TOTAL</b>", s(10, WHITE, bold=True)),
        Paragraph("", s(9)),
        Paragraph(f"<b>{total:.2f} EUR HT</b>", s(10, WHITE, bold=True, align=2)),
    ])
    last = len(prest_rows)-1
    pt = Table(prest_rows, colWidths=[9*cm, 4*cm, 4.8*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,last-1),[WHITE,LIGHT]),
        ("BACKGROUND",(0,last),(-1,last),BLUE),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),
    ]))
    story.append(pt)
    story.append(Spacer(1, 0.3*cm))

    articles = [
        ("Article 1 — Objet",
         f"Le Prestataire s'engage à fournir les prestations de conciergerie listées "
         f"ci-dessus pour le bien situé : {data['bien_adresse']}, {data['bien_cp']} {data['bien_ville']}."),
        ("Article 2 — Durée",
         f"Le présent contrat prend effet le {data['date_debut']} pour une durée de "
         f"{data['duree']}. Il est renouvelable par tacite reconduction sauf préavis "
         f"de {data['preavis']} mois."),
        ("Article 3 — Conditions de paiement",
         f"Le règlement s'effectue {data['paiement']}. "
         f"Tout retard de paiement entraînera des pénalités de retard au taux légal en vigueur."),
        ("Article 4 — Obligations des parties",
         "Le Prestataire s'engage à exécuter les prestations avec professionnalisme "
         "et dans les délais convenus. Le Client s'engage à faciliter l'accès au bien "
         "et à régler les factures dans les délais."),
        ("Article 5 — Résiliation",
         f"Le contrat peut être résilié par lettre recommandée avec un préavis de "
         f"{data['preavis']} mois. En cas de manquement grave, résiliation immédiate possible."),
    ]

    for titre_art, texte_art in articles:
        story.append(Paragraph(titre_art, s(10, NAVY, bold=True)))
        story.append(Paragraph(texte_art, ParagraphStyle("j", fontSize=9, textColor=GREY,
                                alignment=TA_JUSTIFY, leading=14, spaceAfter=8)))

    signatures(story, "Le Client", "Le Prestataire (Conciergerie)")
    pied_page(story, date_str)
    doc.build(story)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# CONTRAT 3 — CONTRAT D'HÉBERGEMENT VOYAGEUR
# ─────────────────────────────────────────────────────────────────────────────
def generer_contrat_hebergement(data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []
    date_str = date.today().strftime("%d/%m/%Y")

    entete_pdf(story, "CONTRAT D'HÉBERGEMENT", "Location meublée de tourisme", date_str)

    voyageur = (f"{data['voy_nom']}<br/>"
                f"{data['voy_adresse']}<br/>"
                f"Tél : {data['voy_tel']} — Email : {data['voy_email']}<br/>"
                f"Pièce d'identité : {data['voy_piece']}")
    loueur = (f"{data['conc_nom']}<br/>"
              f"SIRET : {data['conc_siret']}<br/>"
              f"{data['conc_adresse']}, {data['conc_cp']} {data['conc_ville']}")

    bloc_parties(story, voyageur, loueur)

    # Détails du séjour
    story.append(Paragraph("Détails du séjour", s(10, NAVY, bold=True)))
    story.append(Spacer(1, 0.15*cm))
    sejour_data = [
        ["Bien loué", f"{data['bien_adresse']}, {data['bien_cp']} {data['bien_ville']}"],
        ["Type de bien", f"{data['bien_type']} — {data['bien_surface']} m² — {data['bien_couchages']} couchage(s)"],
        ["Date d'arrivée", f"{data['date_arrivee']} à partir de {data['heure_arrivee']}"],
        ["Date de départ", f"{data['date_depart']} avant {data['heure_depart']}"],
        ["Nombre de nuits", str(data['nb_nuits'])],
        ["Nombre de personnes", str(data['nb_personnes'])],
        ["Prix total", f"{data['prix_total']:.2f} EUR TTC"],
        ["Dont ménage", f"{data['prix_menage']:.2f} EUR"],
        ["Dont taxe de séjour", f"{data['taxe_sejour']:.2f} EUR"],
        ["Dépôt de garantie", f"{data['depot_garantie']:.2f} EUR"],
    ]
    st_data = [[Paragraph(f"<b>{r[0]}</b>", s(9, GREY, bold=True)),
                Paragraph(r[1], s(9, NAVY))] for r in sejour_data]
    st = Table(st_data, colWidths=[5*cm, 12.8*cm])
    st.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHITE,LIGHT]),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
    ]))
    story.append(st)
    story.append(Spacer(1, 0.3*cm))

    articles = [
        ("Article 1 — Objet",
         "Le présent contrat constitue un contrat de location meublée de courte durée "
         "conformément aux articles L. 324-1 et suivants du Code du Tourisme."),
        ("Article 2 — Règlement intérieur",
         f"Le Voyageur s'engage à respecter le règlement intérieur du logement. "
         f"Animaux : {'autorisés' if data['animaux'] == 'Oui' else 'non autorisés'}. "
         f"Fumeurs : {'autorisés' if data['fumeurs'] == 'Oui' else 'non autorisés'}. "
         f"Fêtes et événements : non autorisés. "
         f"Silence à respecter après 22h. Capacité maximale : {data['nb_personnes']} personnes."),
        ("Article 3 — Paiement et annulation",
         f"Le montant total de {data['prix_total']:.2f} EUR est dû à la réservation. "
         f"Politique d'annulation : {data['politique_annulation']}."),
        ("Article 4 — Dépôt de garantie",
         f"Un dépôt de garantie de {data['depot_garantie']:.2f} EUR est requis. "
         "Il sera restitué dans les 7 jours suivant le départ, "
         "sous réserve de l'état du logement."),
        ("Article 5 — État des lieux",
         "Un état des lieux d'entrée et de sortie sera réalisé par le Loueur ou son représentant. "
         "Tout dommage constaté à la sortie sera déduit du dépôt de garantie."),
    ]

    for titre_art, texte_art in articles:
        story.append(Paragraph(titre_art, s(10, NAVY, bold=True)))
        story.append(Paragraph(texte_art, ParagraphStyle("j", fontSize=9, textColor=GREY,
                                alignment=TA_JUSTIFY, leading=14, spaceAfter=8)))

    signatures(story, "Le Voyageur", "Le Loueur (Conciergerie)")
    pied_page(story, date_str)
    doc.build(story)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# CONTRAT 4 — AVENANT AU MANDAT
# ─────────────────────────────────────────────────────────────────────────────
def generer_avenant(data):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []
    date_str = date.today().strftime("%d/%m/%Y")

    entete_pdf(story, "AVENANT AU MANDAT DE GESTION", f"Avenant N° {data['num_avenant']}", date_str)

    mandant = (f"{data['prop_nom']}<br/>{data['prop_adresse']}<br/>"
               f"{data['prop_cp']} {data['prop_ville']}")
    mandataire = (f"{data['conc_nom']}<br/>SIRET : {data['conc_siret']}<br/>"
                  f"{data['conc_adresse']}, {data['conc_cp']} {data['conc_ville']}")

    bloc_parties(story, mandant, mandataire)

    story.append(Paragraph("Références du mandat initial", s(10, NAVY, bold=True)))
    story.append(Paragraph(
        f"Le présent avenant modifie le mandat de gestion locative signé le "
        f"{data['date_mandat_initial']} concernant le bien situé : "
        f"{data['bien_adresse']}, {data['bien_cp']} {data['bien_ville']}.",
        ParagraphStyle("j", fontSize=9, textColor=GREY, alignment=TA_JUSTIFY, leading=14, spaceAfter=12)
    ))

    story.append(Paragraph("Modifications apportées", s(10, NAVY, bold=True)))
    story.append(Spacer(1, 0.15*cm))

    modifs = data.get("modifications", [])
    if modifs:
        mod_rows = [[
            Paragraph("<b>Clause modifiée</b>", s(9, WHITE, bold=True)),
            Paragraph("<b>Ancienne valeur</b>", s(9, WHITE, bold=True)),
            Paragraph("<b>Nouvelle valeur</b>", s(9, WHITE, bold=True)),
        ]]
        for m in modifs:
            mod_rows.append([
                Paragraph(m["clause"], s(9, NAVY)),
                Paragraph(m["ancienne"], s(9, GREY)),
                Paragraph(m["nouvelle"], s(9, BLUE, bold=True)),
            ])
        mt = Table(mod_rows, colWidths=[5*cm, 6*cm, 6.8*cm])
        mt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),NAVY),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT]),
            ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
            ("LEFTPADDING",(0,0),(-1,-1),8),
        ]))
        story.append(mt)
    else:
        story.append(Paragraph(data.get("texte_modifications",""), 
                               ParagraphStyle("j", fontSize=9, textColor=GREY,
                               alignment=TA_JUSTIFY, leading=14, spaceAfter=8)))

    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Toutes les autres clauses du mandat initial restent inchangées. "
        f"Le présent avenant prend effet à compter du {data['date_effet']}.",
        ParagraphStyle("j", fontSize=9, textColor=GREY, alignment=TA_JUSTIFY, leading=14, spaceAfter=8)
    ))

    signatures(story, "Le Mandant (Propriétaire)", "Le Mandataire (Conciergerie)")
    pied_page(story, date_str)
    doc.build(story)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────
def show():
    st.title("📄 Contrats")
    st.caption("Générez vos contrats professionnels en PDF — prêts à signer.")

    prop_id  = st.session_state.get("prop_id", 0) or 0
    from database.proprietes_repo import fetch_all as _fa
    props    = {p["id"]: p for p in _fa()}
    prop     = props.get(prop_id, {})

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Mandat de gestion",
        "🛠️ Prestation de services",
        "🏠 Hébergement voyageur",
        "📝 Avenant"
    ])

    # ── Infos conciergerie communes ───────────────────────────────────────
    with st.sidebar.expander("⚙️ Infos conciergerie", expanded=False):
        conc_nom    = st.text_input("Raison sociale", value=prop.get("signataire","") or "", key="conc_nom")
        conc_forme  = st.text_input("Forme juridique", value="SAS", key="conc_forme")
        conc_siret  = st.text_input("SIRET", value=prop.get("siret","") or "", key="conc_siret")
        conc_carte  = st.text_input("Carte pro G", value="", key="conc_carte")
        conc_adr    = st.text_input("Adresse", value=prop.get("rue","") or "", key="conc_adr")
        conc_cp     = st.text_input("Code postal", value=prop.get("code_postal","") or "", key="conc_cp")
        conc_ville  = st.text_input("Ville", value=prop.get("ville","") or "", key="conc_ville")

    conc = {
        "conc_nom":    st.session_state.get("conc_nom",""),
        "conc_forme":  st.session_state.get("conc_forme","SAS"),
        "conc_siret":  st.session_state.get("conc_siret",""),
        "conc_carte_g":st.session_state.get("conc_carte",""),
        "conc_adresse":st.session_state.get("conc_adr",""),
        "conc_cp":     st.session_state.get("conc_cp",""),
        "conc_ville":  st.session_state.get("conc_ville",""),
    }

    # ── ONGLET 1 — MANDAT DE GESTION ─────────────────────────────────────
    with tab1:
        st.subheader("Mandat de gestion locative")
        st.caption("Contrat entre la conciergerie et le propriétaire du bien.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Propriétaire (Mandant)**")
            prop_nom    = st.text_input("Nom complet *", key="mg_prop_nom")
            prop_adr    = st.text_input("Adresse", key="mg_prop_adr")
            prop_cp2    = st.text_input("Code postal", key="mg_prop_cp")
            prop_ville2 = st.text_input("Ville", key="mg_prop_ville")
            prop_tel    = st.text_input("Téléphone", key="mg_prop_tel")
            prop_email  = st.text_input("Email", key="mg_prop_email")

        with c2:
            st.markdown("**Bien immobilier**")
            bien_adr    = st.text_input("Adresse du bien *", key="mg_bien_adr")
            bien_cp3    = st.text_input("Code postal", key="mg_bien_cp")
            bien_ville3 = st.text_input("Ville", key="mg_bien_ville")
            bien_type   = st.selectbox("Type", ["Appartement","Maison","Studio","Villa","Chalet"], key="mg_bien_type")
            bien_surf   = st.number_input("Surface (m²)", min_value=0, value=50, key="mg_bien_surf")

        st.markdown("**Conditions du mandat**")
        c3, c4, c5 = st.columns(3)
        with c3:
            duree       = st.number_input("Durée (mois)", min_value=1, value=12, key="mg_duree")
            date_debut  = st.date_input("Date de début", key="mg_date_debut")
        with c4:
            commission  = st.number_input("Commission (%)", min_value=0.0, max_value=50.0, value=20.0, step=0.5, key="mg_comm")
            menage_inc  = st.selectbox("Frais ménage", ["Inclus","En sus"], key="mg_menage")
        with c5:
            preavis     = st.number_input("Préavis résiliation (mois)", min_value=1, value=3, key="mg_preavis")
            tribunal    = st.text_input("Tribunal compétent (ville)", value="Nice", key="mg_tribunal")

        if st.button("📄 Générer le mandat PDF", type="primary", use_container_width=True, key="btn_mandat"):
            if not prop_nom or not bien_adr:
                st.error("Nom du propriétaire et adresse du bien obligatoires.")
            else:
                data_m = {**conc,
                    "prop_nom": prop_nom, "prop_adresse": prop_adr,
                    "prop_cp": prop_cp2, "prop_ville": prop_ville2,
                    "prop_tel": prop_tel, "prop_email": prop_email,
                    "bien_adresse": bien_adr, "bien_cp": bien_cp3,
                    "bien_ville": bien_ville3, "bien_type": bien_type,
                    "bien_surface": bien_surf, "duree": duree,
                    "date_debut": date_debut.strftime("%d/%m/%Y"),
                    "commission": commission, "menage_inclus": menage_inc,
                    "preavis": preavis, "tribunal": tribunal,
                }
                with st.spinner("Génération..."):
                    pdf = generer_mandat_gestion(data_m)
                st.download_button("⬇️ Télécharger le mandat PDF", pdf,
                    f"Mandat_gestion_{prop_nom.replace(' ','_')}.pdf",
                    "application/pdf", type="primary", use_container_width=True)

    # ── ONGLET 2 — PRESTATION DE SERVICES ────────────────────────────────
    with tab2:
        st.subheader("Contrat de prestation de services")
        st.caption("Pour les prestations ponctuelles ou forfaitaires.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Client**")
            cl_nom    = st.text_input("Nom complet *", key="ps_cl_nom")
            cl_adr    = st.text_input("Adresse", key="ps_cl_adr")
            cl_cp     = st.text_input("Code postal", key="ps_cl_cp")
            cl_ville  = st.text_input("Ville", key="ps_cl_ville")
            cl_tel    = st.text_input("Téléphone", key="ps_cl_tel")
            cl_email  = st.text_input("Email", key="ps_cl_email")
        with c2:
            st.markdown("**Bien**")
            ps_bien_adr   = st.text_input("Adresse du bien *", key="ps_bien_adr")
            ps_bien_cp    = st.text_input("Code postal", key="ps_bien_cp")
            ps_bien_ville = st.text_input("Ville", key="ps_bien_ville")
            ps_date_debut = st.date_input("Date de début", key="ps_date_debut")
            ps_duree      = st.text_input("Durée", value="12 mois", key="ps_duree")
            ps_preavis    = st.number_input("Préavis (mois)", min_value=1, value=1, key="ps_preavis")

        st.markdown("**Prestations**")
        ps_paiement = st.selectbox("Modalités de paiement",
            ["mensuellement", "à la prestation", "trimestriellement"], key="ps_paiement")

        prestations = []
        nb_prest = st.number_input("Nombre de prestations", min_value=1, max_value=10, value=3, key="ps_nb")
        for i in range(int(nb_prest)):
            col_a, col_b, col_c = st.columns([3,2,2])
            with col_a: nom_p = st.text_input(f"Prestation {i+1}", key=f"ps_nom_{i}", placeholder="Ex: Ménage entre séjours")
            with col_b: freq_p = st.text_input("Fréquence", key=f"ps_freq_{i}", placeholder="Ex: Par séjour")
            with col_c: prix_p = st.number_input("Prix (€ HT)", min_value=0.0, step=5.0, key=f"ps_prix_{i}")
            if nom_p:
                prestations.append({"nom": nom_p, "freq": freq_p, "prix": prix_p})

        if st.button("📄 Générer le contrat PDF", type="primary", use_container_width=True, key="btn_prest"):
            if not cl_nom or not ps_bien_adr:
                st.error("Nom du client et adresse du bien obligatoires.")
            else:
                data_p = {**conc,
                    "client_nom": cl_nom, "client_adresse": cl_adr,
                    "client_cp": cl_cp, "client_ville": cl_ville,
                    "client_tel": cl_tel, "client_email": cl_email,
                    "bien_adresse": ps_bien_adr, "bien_cp": ps_bien_cp,
                    "bien_ville": ps_bien_ville,
                    "date_debut": ps_date_debut.strftime("%d/%m/%Y"),
                    "duree": ps_duree, "preavis": ps_preavis,
                    "paiement": ps_paiement, "prestations": prestations,
                }
                with st.spinner("Génération..."):
                    pdf = generer_prestation_services(data_p)
                st.download_button("⬇️ Télécharger le contrat PDF", pdf,
                    f"Contrat_prestation_{cl_nom.replace(' ','_')}.pdf",
                    "application/pdf", type="primary", use_container_width=True)

    # ── ONGLET 3 — HÉBERGEMENT VOYAGEUR ──────────────────────────────────
    with tab3:
        st.subheader("Contrat d'hébergement voyageur")
        st.caption("Location meublée de tourisme — entre la conciergerie et le voyageur.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Voyageur**")
            voy_nom   = st.text_input("Nom complet *", key="heb_voy_nom")
            voy_adr   = st.text_input("Adresse", key="heb_voy_adr")
            voy_cp    = st.text_input("Code postal", key="heb_voy_cp")
            voy_ville = st.text_input("Ville", key="heb_voy_ville")
            voy_tel   = st.text_input("Téléphone", key="heb_voy_tel")
            voy_email = st.text_input("Email", key="heb_voy_email")
            voy_piece = st.text_input("Pièce d'identité (type + n°)", key="heb_voy_piece")
        with c2:
            st.markdown("**Séjour**")
            heb_bien_adr   = st.text_input("Adresse du bien *", key="heb_bien_adr")
            heb_bien_cp    = st.text_input("Code postal", key="heb_bien_cp")
            heb_bien_ville = st.text_input("Ville", key="heb_bien_ville")
            heb_bien_type  = st.selectbox("Type", ["Appartement","Maison","Studio","Villa","Chalet"], key="heb_bien_type")
            heb_surf       = st.number_input("Surface (m²)", min_value=0, value=50, key="heb_surf")
            heb_couchages  = st.number_input("Couchages", min_value=1, value=2, key="heb_couchages")

        c3, c4 = st.columns(2)
        with c3:
            heb_arr     = st.date_input("Date d'arrivée", key="heb_arr")
            heb_h_arr   = st.text_input("Heure d'arrivée", value="16:00", key="heb_h_arr")
            heb_dep     = st.date_input("Date de départ", key="heb_dep")
            heb_h_dep   = st.text_input("Heure de départ", value="11:00", key="heb_h_dep")
            heb_nb_pers = st.number_input("Nb personnes", min_value=1, value=2, key="heb_nb_pers")
        with c4:
            heb_prix    = st.number_input("Prix total TTC (€)", min_value=0.0, step=10.0, key="heb_prix")
            heb_menage  = st.number_input("Dont ménage (€)", min_value=0.0, step=5.0, key="heb_menage")
            heb_taxe    = st.number_input("Dont taxe séjour (€)", min_value=0.0, step=0.5, key="heb_taxe")
            heb_depot   = st.number_input("Dépôt de garantie (€)", min_value=0.0, step=50.0, key="heb_depot")
            heb_annul   = st.text_input("Politique d'annulation", value="Non remboursable", key="heb_annul")

        c5, c6 = st.columns(2)
        with c5: heb_animaux  = st.selectbox("Animaux", ["Non","Oui"], key="heb_animaux")
        with c6: heb_fumeurs  = st.selectbox("Fumeurs", ["Non","Oui"], key="heb_fumeurs")

        if st.button("📄 Générer le contrat PDF", type="primary", use_container_width=True, key="btn_heb"):
            if not voy_nom or not heb_bien_adr:
                st.error("Nom du voyageur et adresse du bien obligatoires.")
            else:
                nb_nuits = (heb_dep - heb_arr).days
                data_h = {**conc,
                    "voy_nom": voy_nom, "voy_adresse": heb_adr if False else f"{voy_adr}, {voy_cp} {voy_ville}",
                    "voy_tel": voy_tel, "voy_email": voy_email, "voy_piece": voy_piece,
                    "bien_adresse": heb_bien_adr, "bien_cp": heb_bien_cp, "bien_ville": heb_bien_ville,
                    "bien_type": heb_bien_type, "bien_surface": heb_surf, "bien_couchages": heb_couchages,
                    "date_arrivee": heb_arr.strftime("%d/%m/%Y"), "heure_arrivee": heb_h_arr,
                    "date_depart": heb_dep.strftime("%d/%m/%Y"), "heure_depart": heb_h_dep,
                    "nb_nuits": nb_nuits, "nb_personnes": heb_nb_pers,
                    "prix_total": heb_prix, "prix_menage": heb_menage,
                    "taxe_sejour": heb_taxe, "depot_garantie": heb_depot,
                    "politique_annulation": heb_annul,
                    "animaux": "Oui" if heb_animaux == "Oui" else "Non",
                    "fumeurs": "Oui" if heb_fumeurs == "Oui" else "Non",
                }
                with st.spinner("Génération..."):
                    pdf = generer_contrat_hebergement(data_h)
                st.download_button("⬇️ Télécharger le contrat PDF", pdf,
                    f"Contrat_hebergement_{voy_nom.replace(' ','_')}.pdf",
                    "application/pdf", type="primary", use_container_width=True)

    # ── ONGLET 4 — AVENANT ────────────────────────────────────────────────
    with tab4:
        st.subheader("Avenant au mandat de gestion")
        st.caption("Modification d'un mandat existant.")

        c1, c2 = st.columns(2)
        with c1:
            av_prop_nom    = st.text_input("Nom propriétaire *", key="av_prop_nom")
            av_prop_adr    = st.text_input("Adresse propriétaire", key="av_prop_adr")
            av_prop_cp     = st.text_input("Code postal", key="av_prop_cp")
            av_prop_ville  = st.text_input("Ville", key="av_prop_ville")
        with c2:
            av_bien_adr    = st.text_input("Adresse du bien *", key="av_bien_adr")
            av_bien_cp     = st.text_input("Code postal", key="av_bien_cp")
            av_bien_ville  = st.text_input("Ville", key="av_bien_ville")
            av_date_mandat = st.date_input("Date du mandat initial", key="av_date_mandat")

        av_num     = st.text_input("Numéro d'avenant", value="001", key="av_num")
        av_effet   = st.date_input("Date d'effet de l'avenant", key="av_effet")

        st.markdown("**Modifications**")
        nb_modifs = st.number_input("Nombre de modifications", min_value=1, max_value=10, value=1, key="av_nb")
        modifications = []
        for i in range(int(nb_modifs)):
            col_a, col_b, col_c = st.columns(3)
            with col_a: clause = st.text_input(f"Clause modifiée {i+1}", key=f"av_clause_{i}", placeholder="Ex: Commission")
            with col_b: ancienne = st.text_input("Ancienne valeur", key=f"av_anc_{i}", placeholder="Ex: 20%")
            with col_c: nouvelle = st.text_input("Nouvelle valeur", key=f"av_nouv_{i}", placeholder="Ex: 22%")
            if clause:
                modifications.append({"clause": clause, "ancienne": ancienne, "nouvelle": nouvelle})

        if st.button("📄 Générer l'avenant PDF", type="primary", use_container_width=True, key="btn_avenant"):
            if not av_prop_nom or not av_bien_adr:
                st.error("Nom du propriétaire et adresse du bien obligatoires.")
            else:
                data_av = {**conc,
                    "num_avenant": av_num,
                    "prop_nom": av_prop_nom, "prop_adresse": av_prop_adr,
                    "prop_cp": av_prop_cp, "prop_ville": av_prop_ville,
                    "bien_adresse": av_bien_adr, "bien_cp": av_bien_cp, "bien_ville": av_bien_ville,
                    "date_mandat_initial": av_date_mandat.strftime("%d/%m/%Y"),
                    "date_effet": av_effet.strftime("%d/%m/%Y"),
                    "modifications": modifications,
                }
                with st.spinner("Génération..."):
                    pdf = generer_avenant(data_av)
                st.download_button("⬇️ Télécharger l'avenant PDF", pdf,
                    f"Avenant_{av_num}_{av_prop_nom.replace(' ','_')}.pdf",
                    "application/pdf", type="primary", use_container_width=True)
