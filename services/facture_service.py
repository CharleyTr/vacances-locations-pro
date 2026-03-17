"""
Service de génération de factures PDF avec logos distincts par propriété.
"""
import io
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.platypus import Table, TableStyle

W, H = A4  # 210 x 297 mm

# ── Identités visuelles par propriété ─────────────────────────────────────────
IDENTITES = {
    1: {
        "nom":       "Le Turenne",
        "sous_titre":"Studio & appartement — Bordeaux",
        "adresse":   "Bordeaux, France",
        "siret":     "",
        "couleur1":  HexColor("#722F37"),   # bordeaux
        "couleur2":  HexColor("#F5E6D3"),   # crème
        "couleur3":  HexColor("#A0522D"),   # sienna
        "emoji":     "🍷",
        "slogan":    "Au cœur de Bordeaux",
    },
    2: {
        "nom":       "Villa Tobias",
        "sous_titre":"Villa & studios — Nice, Côte d'Azur",
        "adresse":   "Nice, Alpes-Maritimes, France",
        "siret":     "",
        "couleur1":  HexColor("#006994"),   # bleu méditerranée
        "couleur2":  HexColor("#E8F4F8"),   # bleu ciel clair
        "couleur3":  HexColor("#00A693"),   # turquoise
        "emoji":     "🌊",
        "slogan":    "La Méditerranée à vos pieds",
    },
    99: {
        "nom":       "Appartement Demo",
        "sous_titre":"Location saisonnière — Paris",
        "adresse":   "Paris, France",
        "siret":     "",
        "couleur1":  HexColor("#1A1A2E"),   # bleu nuit parisien
        "couleur2":  HexColor("#F0F4FF"),   # bleu pâle
        "couleur3":  HexColor("#C0A060"),   # or parisien
        "emoji":     "🗼",
        "slogan":    "Paris au quotidien",
    },
}

DEFAULT_IDENTITE = {
    "nom": "Location Saisonnière", "sous_titre": "", "adresse": "France",
    "siret": "", "couleur1": HexColor("#1565C0"), "couleur2": HexColor("#E3F2FD"),
    "couleur3": HexColor("#0D47A1"), "emoji": "🏠", "slogan": "",
}


def _logo_turenne(c, x, y, couleur1, couleur3):
    """Logo Le Turenne : arche gothique stylisée + vigne."""
    c.setFillColor(couleur1)
    # Arche principale
    c.arc(x+2*mm, y+2*mm, x+22*mm, y+28*mm, 0, 180)
    c.rect(x+2*mm, y+2*mm, 5*mm, 14*mm, fill=1, stroke=0)
    c.rect(x+15*mm, y+2*mm, 5*mm, 14*mm, fill=1, stroke=0)
    c.ellipse(x+4.5*mm, y+16*mm, x+19.5*mm, y+28*mm, fill=1, stroke=0)
    # Fenêtre intérieure
    c.setFillColor(HexColor("#FFFFFF"))
    c.ellipse(x+7*mm, y+14*mm, x+17*mm, y+26*mm, fill=1, stroke=0)
    # Détail vigne
    c.setFillColor(couleur3)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x+6*mm, y+16*mm, "T")
    # Nom sous le logo
    c.setFillColor(couleur1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y-2*mm, "LE TURENNE")


def _logo_tobias(c, x, y, couleur1, couleur3):
    """Logo Villa Tobias : vague + soleil."""
    # Soleil
    c.setFillColor(HexColor("#F4A820"))
    c.circle(x+15*mm, y+22*mm, 7*mm, fill=1, stroke=0)
    # Rayons
    c.setStrokeColor(HexColor("#F4A820"))
    c.setLineWidth(1.5)
    for angle in range(0, 360, 45):
        import math
        rad = math.radians(angle)
        x1 = x+15*mm + 8*mm*math.cos(rad)
        y1 = y+22*mm + 8*mm*math.sin(rad)
        x2 = x+15*mm + 10.5*mm*math.cos(rad)
        y2 = y+22*mm + 10.5*mm*math.sin(rad)
        c.line(x1, y1, x2, y2)
    # Vagues
    c.setFillColor(couleur1)
    c.setStrokeColor(couleur1)
    c.setLineWidth(2.5)
    for i, (oy, alpha) in enumerate([(8,1),(5,0.6),(2,0.35)]):
        c.setFillAlpha(alpha)
        path = c.beginPath()
        path.moveTo(x, y+oy*mm)
        for xi in range(0, 30, 6):
            path.curveTo(x+xi*mm, y+(oy+3)*mm, x+(xi+3)*mm, y+(oy-3)*mm, x+(xi+6)*mm, y+oy*mm)
        path.lineTo(x+30*mm, y)
        path.lineTo(x, y)
        path.close()
        c.drawPath(path, fill=1, stroke=0)
    c.setFillAlpha(1)
    c.setFillColor(couleur1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x, y-2*mm, "VILLA TOBIAS")


def _logo_paris(c, x, y, couleur1, couleur3):
    """Logo Appartement Demo Paris : Tour Eiffel stylisée."""
    c.setFillColor(couleur1)
    c.setStrokeColor(couleur1)
    c.setLineWidth(1)
    # Base
    c.rect(x+2*mm, y+1*mm, 20*mm, 3*mm, fill=1, stroke=0)
    # Corps
    c.rect(x+5*mm, y+4*mm, 14*mm, 6*mm, fill=1, stroke=0)
    # Étage
    c.rect(x+8*mm, y+10*mm, 8*mm, 5*mm, fill=1, stroke=0)
    # Sommet
    path = c.beginPath()
    path.moveTo(x+9*mm, y+15*mm)
    path.lineTo(x+15*mm, y+15*mm)
    path.lineTo(x+12*mm, y+26*mm)
    path.close()
    c.drawPath(path, fill=1, stroke=0)
    # Détail fenêtre
    c.setFillColor(HexColor("#FFFFFF"))
    c.rect(x+11*mm, y+11*mm, 2*mm, 2.5*mm, fill=1, stroke=0)
    c.setFillColor(couleur3)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x+1*mm, y-2*mm, "PARIS DEMO")


def _draw_logo(c, prop_id, ident, x, y):
    if prop_id == 1:
        _logo_turenne(c, x, y, ident["couleur1"], ident["couleur3"])
    elif prop_id == 2:
        _logo_tobias(c, x, y, ident["couleur1"], ident["couleur3"])
    else:
        _logo_paris(c, x, y, ident["couleur1"], ident["couleur3"])


def generate_facture(
    reservation: dict,
    propriete_id: int,
    signataire: str = "",
    prop_nom: str = "",
    numero_facture: str = "",
    lignes_supplementaires: list = None,
    prop_data: dict = None,  # fiche propriété complète (rue, cp, ville, tel, siret)
) -> bytes:
    """
    Génère une facture PDF et retourne les bytes.
    reservation: dict avec nom_client, date_arrivee, date_depart, nuitees,
                 prix_brut, menage, taxes_sejour, numero_reservation, email
    prop_data: dict optionnel avec rue, code_postal, ville, telephone, siret
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    ident = IDENTITES.get(propriete_id, DEFAULT_IDENTITE)
    col1  = ident["couleur1"]
    col2  = ident["couleur2"]
    col3  = ident["couleur3"]

    # Champs adresse depuis prop_data ou fallback ident
    p = prop_data or {}
    _rue    = p.get("rue","") or ""
    _cp     = p.get("code_postal","") or ""
    _ville  = p.get("ville","") or ident.get("adresse","")
    _tel    = p.get("telephone","") or ""
    _siret  = (p.get("siret","") or "").strip()  # SIRET uniquement si renseigné en DB
    _prop_nom = p.get("nom","") or prop_nom or ident["nom"]
    # Adresse formatée
    _adresse_ligne1 = _rue if _rue else ""
    _adresse_ligne2 = f"{_cp} {_ville}".strip() if (_cp or _ville) else ident.get("adresse","")

    def _fmt_date(v):
        if not v: return ""
        try:
            from datetime import datetime
            if hasattr(v, "strftime"): return v.strftime("%d/%m/%Y")
            return datetime.strptime(str(v)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except: return str(v)[:10]

    def _fv(key, default=0):
        v = reservation.get(key, default)
        try: return float(v) if v else default
        except: return default

    # ── Bandeau header ────────────────────────────────────────────────────
    c.setFillColor(col1)
    c.rect(0, H-42*mm, W, 42*mm, fill=1, stroke=0)

    # Logo
    _draw_logo(c, propriete_id, ident, 15*mm, H-38*mm)

    # Nom propriété
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(55*mm, H-18*mm, ident["nom"].upper())
    c.setFont("Helvetica", 11)
    c.drawString(55*mm, H-26*mm, ident["sous_titre"])
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(55*mm, H-33*mm, ident["slogan"])

    # Adresse + coordonnées (droite) — uniquement si renseignés
    c.setFont("Helvetica", 8)
    y_info = H - 14*mm
    if _adresse_ligne1:
        c.drawRightString(W-15*mm, y_info, _adresse_ligne1)
        y_info -= 7*mm
    if _adresse_ligne2:
        c.drawRightString(W-15*mm, y_info, _adresse_ligne2)
        y_info -= 7*mm
    if _tel:
        c.drawRightString(W-15*mm, y_info, f"Tél : {_tel}")
        y_info -= 7*mm
    if signataire:
        c.drawRightString(W-15*mm, y_info, signataire)

    # ── Titre FACTURE ─────────────────────────────────────────────────────
    c.setFillColor(col3)
    c.rect(0, H-55*mm, W, 13*mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(15*mm, H-49*mm, "FACTURE")

    # Numéro et date
    num = numero_facture or f"FAC-{date.today().strftime('%Y%m%d')}-{reservation.get('id','')}"
    c.setFont("Helvetica", 10)
    c.drawRightString(W-15*mm, H-49*mm, f"N° {num}  |  {date.today().strftime('%d/%m/%Y')}")

    # ── Bloc client ───────────────────────────────────────────────────────
    y_client = H - 75*mm
    c.setFillColor(col2)
    c.rect(15*mm, y_client-18*mm, 85*mm, 25*mm, fill=1, stroke=0)
    c.setFillColor(col1)
    c.rect(15*mm, y_client+2*mm, 85*mm, 5*mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(18*mm, y_client+3.5*mm, "FACTURÉ À")
    c.setFillColor(HexColor("#222222"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(18*mm, y_client-5*mm, reservation.get("nom_client", ""))
    c.setFont("Helvetica", 9)
    if reservation.get("email"):
        c.drawString(18*mm, y_client-11*mm, reservation.get("email",""))
    if reservation.get("telephone"):
        c.drawString(18*mm, y_client-16*mm, reservation.get("telephone",""))

    # ── Bloc réservation ──────────────────────────────────────────────────
    c.setFillColor(col2)
    c.rect(110*mm, y_client-18*mm, 85*mm, 25*mm, fill=1, stroke=0)
    c.setFillColor(col1)
    c.rect(110*mm, y_client+2*mm, 85*mm, 5*mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(113*mm, y_client+3.5*mm, "DÉTAILS DU SÉJOUR")
    c.setFillColor(HexColor("#222222"))
    c.setFont("Helvetica", 9)
    c.drawString(113*mm, y_client-3*mm, f"Arrivée  :  {_fmt_date(reservation.get('date_arrivee'))}")
    c.drawString(113*mm, y_client-9*mm, f"Départ   :  {_fmt_date(reservation.get('date_depart'))}")
    nuits = int(_fv("nuitees"))
    c.drawString(113*mm, y_client-15*mm, f"Durée    :  {nuits} nuit(s)")
    num_res = reservation.get("numero_reservation","")
    if num_res:
        c.setFont("Helvetica", 8)
        c.drawString(113*mm, y_client-21*mm, f"Réf. : {num_res}")

    # ── Tableau des prestations ───────────────────────────────────────────
    y_table = y_client - 35*mm
    prix_brut = _fv("prix_brut")
    menage    = _fv("menage") or _fv("prix_menage")
    taxes     = _fv("taxes_sejour")
    prix_nuit = round(prix_brut / nuits, 2) if nuits > 0 else prix_brut

    lignes = [
        ["Désignation", "Qté", "P.U.", "Montant"],
        [f"Location {ident['nom']} — {_fmt_date(reservation.get('date_arrivee'))} au {_fmt_date(reservation.get('date_depart'))}", f"{nuits} nuit(s)", f"{prix_nuit:.2f} €", f"{prix_brut:.2f} €"],
    ]
    if menage > 0:
        lignes.append(["Frais de ménage", "1", f"{menage:.2f} €", f"{menage:.2f} €"])
    if taxes > 0:
        lignes.append(["Taxe de séjour", "1", f"{taxes:.2f} €", f"{taxes:.2f} €"])
    if lignes_supplementaires:
        lignes.extend(lignes_supplementaires)

    total_ht  = prix_brut + menage + taxes
    total_ttc = total_ht  # LMNP non assujetti TVA

    lignes.append(["", "", "", ""])
    lignes.append(["", "", "TOTAL TTC", f"{total_ttc:.2f} €"])

    # Dessiner le tableau manuellement
    col_widths = [100*mm, 20*mm, 25*mm, 30*mm]
    row_h = 9*mm
    header_h = 10*mm
    x_start = 15*mm
    y_cur = y_table

    # En-tête tableau
    c.setFillColor(col1)
    c.rect(x_start, y_cur-header_h, sum(col_widths), header_h, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica-Bold", 9)
    x_pos = x_start
    for i, (header, cw) in enumerate(zip(lignes[0], col_widths)):
        if i == 0:
            c.drawString(x_pos+3*mm, y_cur-6.5*mm, header)
        else:
            c.drawRightString(x_pos+cw-2*mm, y_cur-6.5*mm, header)
        x_pos += cw
    y_cur -= header_h

    # Lignes données
    for row_idx, row in enumerate(lignes[1:]):
        is_total = row[2] == "TOTAL TTC"
        if is_total:
            c.setFillColor(col3)
            c.rect(x_start, y_cur-row_h, sum(col_widths), row_h, fill=1, stroke=0)
            c.setFillColor(HexColor("#FFFFFF"))
            c.setFont("Helvetica-Bold", 11)
        elif row[0] == "":
            y_cur -= 4*mm
            continue
        else:
            bg = col2 if row_idx % 2 == 0 else HexColor("#FFFFFF")
            c.setFillColor(bg)
            c.rect(x_start, y_cur-row_h, sum(col_widths), row_h, fill=1, stroke=0)
            c.setFillColor(HexColor("#333333"))
            c.setFont("Helvetica", 9)

        x_pos = x_start
        for i, (cell, cw) in enumerate(zip(row, col_widths)):
            if i == 0:
                c.drawString(x_pos+3*mm, y_cur-6*mm, str(cell))
            else:
                c.drawRightString(x_pos+cw-2*mm, y_cur-6*mm, str(cell))
            x_pos += cw

        # Bordure basse
        c.setStrokeColor(HexColor("#DDDDDD"))
        c.setLineWidth(0.3)
        c.line(x_start, y_cur-row_h, x_start+sum(col_widths), y_cur-row_h)
        y_cur -= row_h

    # ── Mentions légales ──────────────────────────────────────────────────
    y_mentions = y_cur - 15*mm
    c.setFillColor(col2)
    c.rect(15*mm, y_mentions-20*mm, W-30*mm, 20*mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#555555"))
    c.setFont("Helvetica", 8)
    c.drawString(18*mm, y_mentions-6*mm, "Loueur Meublé Non Professionnel (LMNP) — TVA non applicable, art. 293B du CGI")
    _adresse_complete = ", ".join(filter(None, [_adresse_ligne1, _adresse_ligne2]))
    c.drawString(18*mm, y_mentions-12*mm, f"Location meublée de courte durée — {_adresse_complete or 'France'}")
    if _siret:
        c.drawString(18*mm, y_mentions-18*mm, f"SIRET : {_siret} — Régime micro-BIC")

    # ── Pied de page ──────────────────────────────────────────────────────
    c.setFillColor(col1)
    c.rect(0, 0, W, 12*mm, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(W/2, 5*mm, f"{ident['nom']}  ·  {ident['slogan']}  ·  Document généré le {date.today().strftime('%d/%m/%Y')}")

    c.save()
    buf.seek(0)
    return buf.getvalue()


# ── Test local ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    res_test = {
        "id": 42, "nom_client": "DUPONT Jean",
        "email": "jean.dupont@email.fr", "telephone": "+33 6 12 34 56 78",
        "date_arrivee": "2026-07-15", "date_depart": "2026-07-22",
        "nuitees": 7, "prix_brut": 980.0, "menage": 80.0,
        "taxes_sejour": 14.0, "numero_reservation": "HM1A2B3C",
    }
    for pid in [1, 2, 99]:
        pdf = generate_facture(res_test, pid, "Charley Trigano", signataire="Charley Trigano", numero_facture=f"FAC-2026-{pid:03d}")
        with open(f"/home/claude/test_facture_prop{pid}.pdf", "wb") as f:
            f.write(pdf)
        print(f"✅ Facture propriété {pid} générée")
