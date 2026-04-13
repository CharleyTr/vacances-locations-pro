"""
Service de génération de factures PDF professionnelles.
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
GREEN = colors.HexColor("#2E7D32")
ORANGE= colors.HexColor("#E65100")


def _fv(d, key, default=0.0):
    try:
        v = d.get(key, default)
        return float(v) if v else default
    except:
        return default


def _ds(d, key, default=""):
    v = d.get(key, default)
    return str(v).strip() if v else default


def generate_facture(reservation: dict, propriete_id: int, signataire: str,
                     prop_nom: str, numero_facture: str,
                     prop_data: dict = None) -> bytes:
    prop_data = prop_data or {}
    buffer    = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()

    def s(size, color=NAVY, bold=False, align=TA_LEFT, space_before=0, space_after=4):
        return ParagraphStyle("_", fontSize=size, textColor=color,
                              fontName="Helvetica-Bold" if bold else "Helvetica",
                              alignment=align, spaceBefore=space_before,
                              spaceAfter=space_after, leading=size*1.4)

    story = []

    # ── En-tête : logo + titre FACTURE côte à côte ────────────────────────
    date_emission = datetime.now().strftime("%d/%m/%Y")

    header_data = [[
        Paragraph(f"<b>{prop_nom}</b>", s(18, WHITE, bold=True)),
        Paragraph(f"FACTURE<br/><font size='10'>N° {numero_facture}</font><br/>"
                  f"<font size='9'>Date : {date_emission}</font>",
                  s(16, WHITE, bold=True, align=TA_RIGHT)),
    ]]
    header_table = Table(header_data, colWidths=[10*cm, 7*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), NAVY),
        ("TOPPADDING",    (0,0),(-1,-1), 16),
        ("BOTTOMPADDING", (0,0),(-1,-1), 16),
        ("LEFTPADDING",   (0,0),(0,-1),  16),
        ("RIGHTPADDING",  (1,0),(1,-1),  16),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(header_table)

    # Bande dorée
    bande = Table([[""]], colWidths=[17*cm], rowHeights=[4])
    bande.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1), GOLD)]))
    story.append(bande)
    story.append(Spacer(1, 0.5*cm))

    # ── Émetteur & Client ─────────────────────────────────────────────────
    # Construire adresse propriété
    adresse_lignes = []
    if prop_data.get("rue"):        adresse_lignes.append(_ds(prop_data, "rue"))
    cp_ville = " ".join(filter(None, [
        _ds(prop_data, "code_postal"), _ds(prop_data, "ville")
    ]))
    if cp_ville:                    adresse_lignes.append(cp_ville)
    if prop_data.get("telephone"):  adresse_lignes.append(f"Tel : {_ds(prop_data,'telephone')}")
    if prop_data.get("email") or prop_data.get("EMAIL_FROM"):
        email = _ds(prop_data,"email") or _ds(prop_data,"EMAIL_FROM")
        if email: adresse_lignes.append(f"Email : {email}")
    if prop_data.get("siret"):      adresse_lignes.append(f"SIRET : {_ds(prop_data,'siret')}")

    emetteur_txt = f"<b>{signataire or prop_nom}</b><br/>" + \
                   "<br/>".join(adresse_lignes) if adresse_lignes else \
                   f"<b>{signataire or prop_nom}</b>"

    # Construire infos client
    nom_client   = _ds(reservation, "nom_client")
    email_client = _ds(reservation, "email")
    tel_client   = _ds(reservation, "telephone")
    pays_client  = _ds(reservation, "pays")
    num_resa     = _ds(reservation, "numero_reservation")

    client_lignes = [f"<b>{nom_client}</b>"]
    if email_client: client_lignes.append(f"Email : {email_client}")
    if tel_client:   client_lignes.append(f"Tel : {tel_client}")
    if pays_client:  client_lignes.append(f"Pays : {pays_client}")
    if num_resa:     client_lignes.append(f"N° reservation : {num_resa}")

    client_txt = "<br/>".join(client_lignes)

    parties_header = [
        [Paragraph("EMETTEUR", s(9, WHITE, bold=True, align=TA_CENTER)),
         Paragraph("CLIENT",   s(9, WHITE, bold=True, align=TA_CENTER))],
        [Paragraph(emetteur_txt, s(9, NAVY)),
         Paragraph(client_txt,   s(9, NAVY))],
    ]
    parties_table = Table(parties_header, colWidths=[8.5*cm, 8.5*cm])
    parties_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(0,0), BLUE),
        ("BACKGROUND",    (1,0),(1,0), NAVY),
        ("BACKGROUND",    (0,1),(0,1), LIGHT),
        ("BACKGROUND",    (1,1),(1,1), colors.HexColor("#F8FBFF")),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#D0D5DD")),
        ("LINEBELOW",     (0,0),(-1,0), 2, GOLD),
    ]))
    story.append(parties_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Detail sejour ─────────────────────────────────────────────────────
    story.append(Paragraph("DETAIL DE LA PRESTATION", s(10, NAVY, bold=True)))
    story.append(Spacer(1, 0.2*cm))

    date_arr  = _ds(reservation, "date_arrivee")[:10]
    date_dep  = _ds(reservation, "date_depart")[:10]
    nuitees   = int(_fv(reservation, "nuitees"))
    plateforme= _ds(reservation, "plateforme")
    prix_brut = _fv(reservation, "prix_brut")
    menage    = _fv(reservation, "prix_menage") or _fv(reservation, "menage")
    taxes     = _fv(reservation, "taxes_sejour")
    prix_nuit = round(prix_brut / nuitees, 2) if nuitees > 0 else 0
    total     = prix_brut + menage + taxes

    desc_loc = (f"Location meublée - {prop_nom}<br/>"
                f"Du {date_arr} au {date_dep} ({nuitees} nuit{'s' if nuitees > 1 else ''})<br/>"
                f"Plateforme : {plateforme}")

    lignes = [
        [Paragraph("<b>Description</b>", s(9, WHITE, bold=True)),
         Paragraph("<b>Qte</b>",  s(9, WHITE, bold=True, align=TA_CENTER)),
         Paragraph("<b>P.U.</b>", s(9, WHITE, bold=True, align=TA_RIGHT)),
         Paragraph("<b>Total</b>",s(9, WHITE, bold=True, align=TA_RIGHT))],
        [Paragraph(desc_loc, s(9, NAVY)),
         Paragraph(f"{nuitees} nuits", s(9, GREY, align=TA_CENTER)),
         Paragraph(f"{prix_nuit:,.2f} EUR", s(9, GREY, align=TA_RIGHT)),
         Paragraph(f"{prix_brut:,.2f} EUR", s(9, NAVY, bold=True, align=TA_RIGHT))],
    ]
    if menage > 0:
        lignes.append([
            Paragraph("Frais de menage", s(9, NAVY)),
            Paragraph("1 forfait", s(9, GREY, align=TA_CENTER)),
            Paragraph(f"{menage:,.2f} EUR", s(9, GREY, align=TA_RIGHT)),
            Paragraph(f"{menage:,.2f} EUR", s(9, NAVY, bold=True, align=TA_RIGHT)),
        ])
    if taxes > 0:
        lignes.append([
            Paragraph("Taxe de sejour", s(9, NAVY)),
            Paragraph(f"{nuitees} nuits", s(9, GREY, align=TA_CENTER)),
            Paragraph("—", s(9, GREY, align=TA_RIGHT)),
            Paragraph(f"{taxes:,.2f} EUR", s(9, NAVY, bold=True, align=TA_RIGHT)),
        ])

    col_w = [9*cm, 2.5*cm, 2.5*cm, 3*cm]
    detail_table = Table(lignes, colWidths=col_w)
    row_bgs = [WHITE, LIGHT] * 10
    detail_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,0), NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, LIGHT]),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#D0D5DD")),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(detail_table)
    story.append(Spacer(1, 0.3*cm))

    # ── Sous-total / Total ────────────────────────────────────────────────
    sous_total_data = [
        ["", Paragraph("Sous-total HT :", s(9, GREY, align=TA_RIGHT)),
         Paragraph(f"{(prix_brut+menage):,.2f} EUR", s(9, NAVY, align=TA_RIGHT))],
    ]
    if taxes > 0:
        sous_total_data.append(
            ["", Paragraph("Taxes de sejour :", s(9, GREY, align=TA_RIGHT)),
             Paragraph(f"{taxes:,.2f} EUR", s(9, NAVY, align=TA_RIGHT))]
        )
    sous_total_data.append(
        ["", Paragraph("<b>TOTAL TTC :</b>", s(12, WHITE, bold=True, align=TA_RIGHT)),
         Paragraph(f"<b>{total:,.2f} EUR</b>", s(12, WHITE, bold=True, align=TA_RIGHT))]
    )

    st_table = Table(sous_total_data, colWidths=[9.5*cm, 4*cm, 3.5*cm])
    st_styles = [
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 8),
    ]
    # Fond bleu sur la dernière ligne (total)
    last = len(sous_total_data) - 1
    st_styles += [
        ("BACKGROUND", (1,last),(-1,last), NAVY),
        ("ROUNDEDCORNERS", [4]),
    ]
    st_table.setStyle(TableStyle(st_styles))
    story.append(st_table)
    story.append(Spacer(1, 0.4*cm))

    # ── Statut paiement ───────────────────────────────────────────────────
    paye = reservation.get("paye", False)
    statut_txt    = "REGLEE" if paye else "EN ATTENTE DE REGLEMENT"
    statut_color  = GREEN if paye else ORANGE
    statut_bg     = colors.HexColor("#E8F5E9") if paye else colors.HexColor("#FFF3E0")

    statut_table = Table(
        [[Paragraph(f"<b>Statut : {statut_txt}</b>",
                    s(11, statut_color, bold=True, align=TA_CENTER))]],
        colWidths=[17*cm]
    )
    statut_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), statut_bg),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("ROUNDEDCORNERS",[6]),
        ("BOX",           (0,0),(-1,-1), 1, statut_color),
    ]))
    story.append(statut_table)
    story.append(Spacer(1, 0.8*cm))

    # ── Mentions légales ──────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "TVA non applicable - art. 293B du CGI  |  "
        "Location meublee non professionnelle (LMNP)  |  "
        f"Document emis le {date_emission}",
        s(8, GREY, align=TA_CENTER)
    ))

    doc.build(story)
    return buffer.getvalue()
