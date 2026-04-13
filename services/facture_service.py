"""
Service de génération de factures PDF professionnelles.
Utilise reportlab (déjà dans requirements.txt).
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

NAVY  = colors.HexColor("#0B1F3A")
BLUE  = colors.HexColor("#1565C0")
GOLD  = colors.HexColor("#F0B429")
GREY  = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F4F7FF")
WHITE = colors.white


def _fv(d, key, default=0.0):
    try:
        v = d.get(key, default)
        return float(v) if v else default
    except:
        return default


def _ds(d, key, default=""):
    v = d.get(key, default)
    return str(v) if v else default


def generate_facture(reservation: dict, propriete_id: int, signataire: str,
                     prop_nom: str, numero_facture: str,
                     prop_data: dict = None) -> bytes:
    """
    Génère une facture PDF professionnelle.
    Retourne les bytes du PDF.
    """
    prop_data = prop_data or {}
    buffer    = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    s_title  = ParagraphStyle("t",  fontSize=22, textColor=WHITE,
                               fontName="Helvetica-Bold", alignment=TA_CENTER)
    s_sub    = ParagraphStyle("s",  fontSize=11, textColor=GOLD,
                               fontName="Helvetica", alignment=TA_CENTER)
    s_h2     = ParagraphStyle("h2", fontSize=12, textColor=NAVY,
                               fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4)
    s_body   = ParagraphStyle("b",  fontSize=10, textColor=GREY, leading=14)
    s_right  = ParagraphStyle("r",  fontSize=10, textColor=NAVY,
                               alignment=TA_RIGHT, fontName="Helvetica-Bold")
    s_note   = ParagraphStyle("n",  fontSize=8,  textColor=GREY, alignment=TA_CENTER)
    s_total  = ParagraphStyle("tot",fontSize=13, textColor=WHITE,
                               fontName="Helvetica-Bold", alignment=TA_CENTER)

    story = []

    # ── En-tête ───────────────────────────────────────────────────────────
    header = Table([[Paragraph(f"🏖 {prop_nom}", s_title)]], colWidths=[17*cm])
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("ROUNDEDCORNERS",[8]),
    ]))
    story.append(header)

    sub = Table([[Paragraph(f"FACTURE  N° {numero_facture}", s_sub)]], colWidths=[17*cm])
    sub.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), BLUE),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
    ]))
    story.append(sub)
    story.append(Spacer(1, 0.5*cm))

    # ── Date émission ─────────────────────────────────────────────────────
    date_emission = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph(f"Date d'émission : {date_emission}", s_right))
    story.append(Spacer(1, 0.3*cm))

    # ── Parties ───────────────────────────────────────────────────────────
    adresse_prop = " — ".join(filter(None, [
        prop_data.get("rue",""),
        prop_data.get("code_postal",""),
        prop_data.get("ville",""),
    ])) or ""
    siret = prop_data.get("siret","") or ""

    nom_client = _ds(reservation, "nom_client")
    email_client = _ds(reservation, "email")
    tel_client = _ds(reservation, "telephone")
    pays_client = _ds(reservation, "pays")

    parties_data = [
        [
            Paragraph("<b>ÉMETTEUR</b>", s_h2),
            Paragraph("<b>CLIENT</b>", s_h2),
        ],
        [
            Paragraph(f"{signataire or prop_nom}<br/>"
                      f"{adresse_prop}<br/>"
                      f"{'SIRET : ' + siret if siret else ''}", s_body),
            Paragraph(f"{nom_client}<br/>"
                      f"{'📧 ' + email_client if email_client else ''}<br/>"
                      f"{'📱 ' + tel_client if tel_client else ''}<br/>"
                      f"{pays_client}", s_body),
        ]
    ]
    parties_table = Table(parties_data, colWidths=[8.5*cm, 8.5*cm])
    parties_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,1),(0,1), LIGHT),
        ("BACKGROUND",    (1,1),(1,1), LIGHT),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#E0E0E0")),
        ("ROUNDEDCORNERS",[4]),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Détail séjour ─────────────────────────────────────────────────────
    story.append(Paragraph("📋 Détail de la prestation", s_h2))

    date_arr = _ds(reservation, "date_arrivee")[:10]
    date_dep = _ds(reservation, "date_depart")[:10]
    nuitees  = int(_fv(reservation, "nuitees"))
    plateforme = _ds(reservation, "plateforme")
    num_resa   = _ds(reservation, "numero_reservation")

    prix_brut  = _fv(reservation, "prix_brut")
    menage     = _fv(reservation, "prix_menage") or _fv(reservation, "menage")
    taxes      = _fv(reservation, "taxes_sejour")
    prix_nuit  = round(prix_brut / nuitees, 2) if nuitees > 0 else 0

    lignes = [
        ["Description", "Qté", "P.U.", "Total"],
        [f"Location — {prop_nom}\n{date_arr} → {date_dep}\n{plateforme}{' — N° ' + num_resa if num_resa else ''}",
         f"{nuitees} nuits", f"{prix_nuit:,.2f} €", f"{prix_brut:,.2f} €"],
    ]
    if menage > 0:
        lignes.append(["Frais de ménage", "1", f"{menage:,.2f} €", f"{menage:,.2f} €"])
    if taxes > 0:
        lignes.append(["Taxes de séjour", f"{nuitees} nuits", "—", f"{taxes:,.2f} €"])

    total = prix_brut + menage + taxes

    detail_table = Table(lignes, colWidths=[9*cm, 2.5*cm, 2.5*cm, 3*cm])
    detail_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("TEXTCOLOR",     (0,0),(-1,0), WHITE),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 9),
        ("ALIGN",         (1,0),(-1,-1), "CENTER"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#E0E0E0")),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 0.3*cm))

    # ── Total ─────────────────────────────────────────────────────────────
    total_table = Table([[Paragraph(f"TOTAL TTC : {total:,.2f} €", s_total)]],
                         colWidths=[17*cm])
    total_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("ROUNDEDCORNERS",[6]),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Paiement ──────────────────────────────────────────────────────────
    paye = reservation.get("paye", False)
    statut_paiement = "✅ PAYÉE" if paye else "⏳ EN ATTENTE DE PAIEMENT"
    couleur_statut  = colors.HexColor("#2E7D32") if paye else colors.HexColor("#E65100")

    story.append(Paragraph(f"Statut : {statut_paiement}", ParagraphStyle(
        "paye", fontSize=11, textColor=couleur_statut,
        fontName="Helvetica-Bold", alignment=TA_CENTER
    )))
    story.append(Spacer(1, 0.8*cm))

    # ── Mentions légales ──────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "TVA non applicable — art. 293B du CGI · "
        "Location meublée non professionnelle (LMNP) · "
        f"Document émis le {date_emission} par {signataire or prop_nom}",
        s_note
    ))

    doc.build(story)
    return buffer.getvalue()
