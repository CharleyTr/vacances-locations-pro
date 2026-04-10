"""
Génération de rapport PDF mensuel pour VLP.
Utilise reportlab (déjà dans requirements.txt).
"""
import io
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                  TableStyle, HRFlowable, PageBreak)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

# Couleurs LodgePro
NAVY  = colors.HexColor("#0B1F3A")
BLUE  = colors.HexColor("#1565C0")
GOLD  = colors.HexColor("#F0B429")
GREY  = colors.HexColor("#6B7280")
LIGHT = colors.HexColor("#F4F7FF")
GREEN = colors.HexColor("#2E7D32")
RED   = colors.HexColor("#C62828")
WHITE = colors.white


def _mois_label(mois: int, annee: int) -> str:
    mois_noms = ["Janvier","Février","Mars","Avril","Mai","Juin",
                 "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
    return f"{mois_noms[mois-1]} {annee}"


def generer_rapport_pdf(
    prop_nom: str,
    mois: int,
    annee: int,
    reservations: list[dict],
    reservations_n1: list[dict] | None = None,
) -> bytes:
    """
    Génère un rapport PDF mensuel.
    Retourne les bytes du PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    story  = []

    # ── Styles personnalisés ──────────────────────────────────────────────
    s_title = ParagraphStyle("title", parent=styles["Normal"],
        fontSize=22, textColor=WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=4)
    s_sub   = ParagraphStyle("sub", parent=styles["Normal"],
        fontSize=12, textColor=GOLD, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=2)
    s_h2    = ParagraphStyle("h2", parent=styles["Normal"],
        fontSize=13, textColor=NAVY, fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=6)
    s_body  = ParagraphStyle("body", parent=styles["Normal"],
        fontSize=10, textColor=GREY, leading=14)
    s_note  = ParagraphStyle("note", parent=styles["Normal"],
        fontSize=8, textColor=GREY, alignment=TA_CENTER)

    # ── En-tête ────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"🏖 {prop_nom}", s_title),
    ]]
    header_table = Table(header_data, colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), NAVY),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING",   (0,0), (-1,-1), 16),
        ("BOTTOMPADDING",(0,0), (-1,-1), 16),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.3*cm))

    sub_data = [[Paragraph(f"Rapport mensuel — {_mois_label(mois, annee)}", s_sub)]]
    sub_table = Table(sub_data, colWidths=[17*cm])
    sub_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), BLUE),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(sub_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Calculs KPIs ──────────────────────────────────────────────────────
    def _date_str(val):
        if val is None: return ""
        try: return str(val)[:10]
        except: return ""

    # Normaliser les dates en string
    resas_norm = []
    for r in reservations:
        r2 = dict(r)
        r2["date_arrivee"] = _date_str(r.get("date_arrivee",""))
        r2["date_depart"]  = _date_str(r.get("date_depart",""))
        resas_norm.append(r2)

    resas = [r for r in resas_norm if r.get("date_arrivee","")[:7] == f"{annee}-{mois:02d}"
             or r.get("date_depart","")[:7] == f"{annee}-{mois:02d}"]

    ca_brut      = sum(float(r.get("prix_brut",0) or 0) for r in resas)
    ca_net       = sum(float(r.get("prix_net",0)  or 0) for r in resas)
    commissions  = sum(float(r.get("commissions",0) or 0) for r in resas)
    nuitees      = sum(int(r.get("nuitees",0) or 0) for r in resas)
    nb_resas     = len(resas)
    rev_nuit     = ca_net / nuitees if nuitees > 0 else 0
    nb_jours     = 30
    taux_occ     = min(100, nuitees / nb_jours * 100)

    # KPIs N-1
    ca_net_n1 = 0
    if reservations_n1:
        mois_n1 = mois
        annee_n1 = annee - 1
        resas_n1 = [r for r in reservations_n1
                    if _date_str(r.get("date_arrivee",""))[:7] == f"{annee_n1}-{mois_n1:02d}"]
        ca_net_n1 = sum(float(r.get("prix_net",0) or 0) for r in resas_n1)

    delta_pct = ((ca_net - ca_net_n1) / ca_net_n1 * 100) if ca_net_n1 > 0 else None

    # ── Tableau KPIs ─────────────────────────────────────────────────────
    story.append(Paragraph("📊 Synthèse financière", s_h2))

    def kpi_cell(label, valeur, couleur=BLUE):
        return [
            Paragraph(f'<font size="9" color="gray">{label}</font>', s_body),
            Paragraph(f'<font size="16" color="{couleur.hexval()}" fontName="Helvetica-Bold">{valeur}</font>', s_body),
        ]

    delta_str = ""
    if delta_pct is not None:
        signe = "+" if delta_pct >= 0 else ""
        delta_str = f" ({signe}{delta_pct:.1f}% vs N-1)"

    kpi_data = [
        [
            Table([[Paragraph("CA Brut", s_body)], [Paragraph(f"{ca_brut:,.0f} €", ParagraphStyle("v", fontSize=16, fontName="Helvetica-Bold", textColor=BLUE))]]),
            Table([[Paragraph("CA Net", s_body)], [Paragraph(f"{ca_net:,.0f} €{delta_str}", ParagraphStyle("v", fontSize=14, fontName="Helvetica-Bold", textColor=GREEN))]]),
            Table([[Paragraph("Commissions", s_body)], [Paragraph(f"{commissions:,.0f} €", ParagraphStyle("v", fontSize=16, fontName="Helvetica-Bold", textColor=RED))]]),
            Table([[Paragraph("Nuitées", s_body)], [Paragraph(f"{nuitees}", ParagraphStyle("v", fontSize=16, fontName="Helvetica-Bold", textColor=NAVY))]]),
        ],
        [
            Table([[Paragraph("Réservations", s_body)], [Paragraph(f"{nb_resas}", ParagraphStyle("v", fontSize=16, fontName="Helvetica-Bold", textColor=NAVY))]]),
            Table([[Paragraph("Revenu/nuit", s_body)], [Paragraph(f"{rev_nuit:,.0f} €", ParagraphStyle("v", fontSize=16, fontName="Helvetica-Bold", textColor=BLUE))]]),
            Table([[Paragraph("Taux occupation", s_body)], [Paragraph(f"{taux_occ:.1f}%", ParagraphStyle("v", fontSize=16, fontName="Helvetica-Bold", textColor=BLUE))]]),
            Table([[Paragraph("Payé", s_body)], [Paragraph(f"{sum(1 for r in resas if r.get('paye'))}/{nb_resas}", ParagraphStyle("v", fontSize=16, fontName="Helvetica-Bold", textColor=NAVY))]]),
        ]
    ]

    kpi_table = Table(kpi_data, colWidths=[4.25*cm]*4)
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), LIGHT),
        ("GRID",          (0,0), (-1,-1), 0.5, WHITE),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("ROUNDEDCORNERS",[6]),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 0.5*cm))

    # ── Liste des réservations ────────────────────────────────────────────
    story.append(Paragraph(f"📋 Réservations du mois ({nb_resas})", s_h2))

    if resas:
        entetes = ["Client", "Plateforme", "Arrivée", "Départ", "Nuits", "CA Net", "Payé"]
        rows = [entetes]
        for r in sorted(resas, key=lambda x: x.get("date_arrivee","") or ""):
            rows.append([
                str(r.get("nom_client","") or "")[:22],
                str(r.get("plateforme","") or ""),
                str(r.get("date_arrivee","") or "")[:10],
                str(r.get("date_depart","")  or "")[:10],
                str(r.get("nuitees","") or ""),
                f"{float(r.get('prix_net',0) or 0):,.0f} €",
                "✓" if r.get("paye") else "○",
            ])

        col_w = [4.5*cm, 2.5*cm, 2.2*cm, 2.2*cm, 1.5*cm, 2.2*cm, 1.5*cm]
        resa_table = Table(rows, colWidths=col_w, repeatRows=1)
        resa_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), NAVY),
            ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ALIGN",         (0,0), (-1,-1), "LEFT"),
            ("ALIGN",         (4,0), (6,-1), "CENTER"),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]))
        story.append(resa_table)
    else:
        story.append(Paragraph("Aucune réservation ce mois.", s_body))

    # ── Répartition plateformes ───────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("🏷️ Répartition par plateforme", s_h2))

    plateformes = {}
    for r in resas:
        plat = r.get("plateforme","Autre") or "Autre"
        if plat not in plateformes:
            plateformes[plat] = {"nb": 0, "ca": 0}
        plateformes[plat]["nb"] += 1
        plateformes[plat]["ca"] += float(r.get("prix_net",0) or 0)

    if plateformes:
        plat_rows = [["Plateforme", "Réservations", "CA Net", "% CA"]]
        for plat, vals in sorted(plateformes.items(), key=lambda x: -x[1]["ca"]):
            pct = vals["ca"] / ca_net * 100 if ca_net > 0 else 0
            plat_rows.append([plat, str(vals["nb"]), f"{vals['ca']:,.0f} €", f"{pct:.1f}%"])

        plat_table = Table(plat_rows, colWidths=[5*cm, 3*cm, 4*cm, 3*cm])
        plat_table.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), BLUE),
            ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
            ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#E0E0E0")),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ]))
        story.append(plat_table)

    # ── Pied de page ─────────────────────────────────────────────────────
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Rapport généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} — LodgePro · Vacances-Locations Pro",
        s_note
    ))

    doc.build(story)
    return buffer.getvalue()
