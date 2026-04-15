"""
Page Ménage — Suivi RH, pointages et ventilation des heures.
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, time
from database.supabase_client import get_supabase
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_autorises


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DB
# ─────────────────────────────────────────────────────────────────────────────

def _sb():
    return get_supabase()

def get_employes(prop_id):
    try:
        return _sb().table("employes_menage").select("*")\
            .eq("propriete_id", prop_id).eq("actif", True)\
            .order("nom").execute().data or []
    except: return []

def get_taches(prop_id):
    try:
        r = _sb().table("taches_menage").select("*")\
            .eq("propriete_id", prop_id).eq("actif", True)\
            .order("ordre").execute().data or []
        if not r:
            # Copier les tâches par défaut
            defaut = _sb().table("taches_defaut").select("*").order("ordre").execute().data or []
            for t in defaut:
                _sb().table("taches_menage").insert({
                    "propriete_id":  prop_id,
                    "nom":           t["nom"],
                    "ordre":         t["ordre"],
                    "duree_estimee": t["duree_estimee"],
                }).execute()
            r = _sb().table("taches_menage").select("*")\
                .eq("propriete_id", prop_id).eq("actif", True)\
                .order("ordre").execute().data or []
        return r
    except: return []

def get_pointages(prop_id, mois=None, annee=None):
    try:
        import calendar as _cal
        q = _sb().table("pointages_menage").select(
            "*, employes_menage(prenom, nom)"
        ).eq("propriete_id", prop_id).order("date_menage", desc=True)
        if mois and annee:
            debut = f"{annee}-{mois:02d}-01"
            dernier_jour = _cal.monthrange(annee, mois)[1]
            fin = f"{annee}-{mois:02d}-{dernier_jour:02d}"
            q = q.gte("date_menage", debut).lte("date_menage", fin)
        return q.execute().data or []
    except Exception as e:
        print(f"get_pointages error: {e}")
        return []

def get_ventilation(pointage_id):
    try:
        return _sb().table("ventilation_taches").select(
            "*, taches_menage(nom)"
        ).eq("pointage_id", pointage_id).execute().data or []
    except: return []

def save_employe(data):
    try:
        r = _sb().table("employes_menage").insert(data).execute()
        if r.data:
            emp_id   = r.data[0]["id"]
            prop_id  = data.get("propriete_id")
            if prop_id:
                _sb().table("employe_proprietes").insert({
                    "employe_id": emp_id, "propriete_id": prop_id
                }).execute()
        return True
    except: return False

def update_employe(emp_id, data):
    try: _sb().table("employes_menage").update(data).eq("id", emp_id).execute(); return True
    except: return False

def save_pointage(data):
    try:
        r = _sb().table("pointages_menage").insert(data).execute()
        return r.data[0]["id"] if r.data else None
    except: return None

def update_pointage(pid, data):
    try: _sb().table("pointages_menage").update(data).eq("id", pid).execute(); return True
    except: return False

def save_ventilation(pointage_id, tache_id, duree, notes=""):
    try:
        _sb().table("ventilation_taches").insert({
            "pointage_id":  pointage_id,
            "tache_id":     tache_id,
            "duree_minutes":duree,
            "notes":        notes,
        }).execute()
        return True
    except: return False

def delete_ventilation(pointage_id):
    try: _sb().table("ventilation_taches").delete().eq("pointage_id", pointage_id).execute()
    except: pass

def get_employes_all(prop_ids: list):
    """Retourne tous les employés pour une liste de propriétés."""
    try:
        if not prop_ids:
            return []
        liens = _sb().table("employe_proprietes").select("employe_id, propriete_id")            .in_("propriete_id", [int(p) for p in prop_ids]).execute().data or []
        ids = list({l["employe_id"] for l in liens})
        if not ids:
            return []
        emps = _sb().table("employes_menage").select("*")            .in_("id", ids).eq("actif", True).order("nom").execute().data or []
        emp_props = {}
        for l in liens:
            emp_props.setdefault(l["employe_id"], []).append(l["propriete_id"])
        for e in emps:
            e["proprietes_rattachees"] = emp_props.get(e["id"], [])
        return emps
    except Exception as e:
        print(f"get_employes_all error: {e}")
        return []

def rattacher_employe(employe_id, prop_id):
    try:
        _sb().table("employe_proprietes").insert({
            "employe_id": employe_id, "propriete_id": prop_id
        }).execute()
        return True
    except: return False


# ─────────────────────────────────────────────────────────────────────────────
# GENERATION PDF BULLETIN
# ─────────────────────────────────────────────────────────────────────────────

# Taux de cotisations 2026 (approximatifs)
TAUX_2026 = {
    "Sécurité sociale maladie salarié":   0.0075,
    "Sécurité sociale vieillesse salarié":0.0690,
    "Chômage salarié":                    0.0000,  # à charge employeur uniquement
    "Retraite complémentaire salarié":    0.0315,
    "CSG non déductible":                 0.0240,
    "CSG/CRDS déductible":                0.0680,
    # Patronales
    "Sécurité sociale maladie patronal":  0.1300,
    "Sécurité sociale vieillesse patronal":0.0845,
    "Chômage patronal":                   0.0405,
    "Retraite complémentaire patronal":   0.0460,
    "Accidents du travail (moyen)":       0.0220,
    "Formation professionnelle":          0.0055,
    "Allocations familiales":             0.0525,
}


def _generer_bulletin(employe, pointages, prop_nom, mois, annee, taux_custom=None, extra=None):
    """Génère un document préparatoire de paie complet en PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    import io

    NAVY  = colors.HexColor("#0B1F3A")
    BLUE  = colors.HexColor("#1565C0")
    GREY  = colors.HexColor("#6B7280")
    LIGHT = colors.HexColor("#F4F7FF")
    WHITE = colors.white
    GOLD  = colors.HexColor("#F0B429")
    GREEN = colors.HexColor("#1B5E20")
    LGREEN= colors.HexColor("#E8F5E9")
    RED   = colors.HexColor("#B71C1C")
    LRED  = colors.HexColor("#FFEBEE")
    LBLUE = colors.HexColor("#E3F2FD")

    mois_noms = ["Janvier","Fevrier","Mars","Avril","Mai","Juin",
                 "Juillet","Aout","Septembre","Octobre","Novembre","Decembre"]

    def s(size, color=NAVY, bold=False, align=0):
        return ParagraphStyle("_", fontSize=size, textColor=color,
                              fontName="Helvetica-Bold" if bold else "Helvetica",
                              alignment=align, leading=size*1.45, spaceAfter=2)

    # ── Paramètres ────────────────────────────────────────────────────────
    tc    = taux_custom or {}
    ex    = extra or {}
    mut_mensuel  = float(ex.get("mutuelle_mensuel", 0.0) or 0.0)
    mut_sal_pct  = float(ex.get("mutuelle_sal_pct", 50.0) or 50.0)
    mut_pat_pct  = float(ex.get("mutuelle_pat_pct", 50.0) or 50.0)
    mut_sal_mnt  = round(mut_mensuel * mut_sal_pct / 100, 2)
    mut_pat_mnt  = round(mut_mensuel * mut_pat_pct / 100, 2)
    cp_taux      = float(ex.get("cp_taux", 0.10) or 0.10)
    pas_taux     = float(ex.get("pas_taux", 0.0) or 0.0)
    convention   = ex.get("convention", "Non precisee")

    nom_emp     = f"{employe.get('prenom','')} {employe.get('nom','')}".strip()
    taux_h      = float(employe.get("taux_horaire", 12) or 12)
    contrat     = employe.get("contrat", "CDI") or "CDI"
    num_ss      = employe.get("numero_ss", "") or "Non renseigne"
    adresse_sal = " ".join(filter(None, [
        employe.get("adresse","") or "",
        employe.get("code_postal","") or "",
        employe.get("ville","") or "",
    ])) or "Non renseignee"
    date_naiss  = str(employe.get("date_naissance","") or "Non renseignee")[:10]

    # ── Calculs heures ─────────────────────────────────────────────────────
    total_minutes = sum(p.get("duree_minutes") or 0 for p in pointages)
    total_heures  = total_minutes / 60
    salaire_brut  = round(total_heures * taux_h, 2)

    # ── Cotisations salariales ────────────────────────────────────────────
    cs = [
        ("Securite sociale maladie", tc.get("Securite sociale maladie salarie", 0.0075), "pct"),
        ("Vieillesse plafonnee", tc.get("Vieillesse plafonnee salarie", 0.0690), "pct"),
        ("Retraite complementaire AGIRC-ARRCO", tc.get("Retraite complementaire salarie", 0.0315), "pct"),
        ("CSG non deductible", tc.get("CSG non deductible", 0.0240), "pct"),
        ("CSG/CRDS deductible", tc.get("CSG/CRDS deductible", 0.0680), "pct"),
    ]
    if mut_sal_mnt > 0:
        cs.append(("Mutuelle - part salariale", mut_sal_mnt, "fixe"))

    total_cotis_sal = sum(
        round(salaire_brut * v, 2) if t == "pct" else v
        for _, v, t in cs
    )
    indemnite_cp   = round(salaire_brut * cp_taux, 2)
    net_avant_pas  = round(salaire_brut - total_cotis_sal + indemnite_cp, 2)
    pas_montant    = round(net_avant_pas * pas_taux, 2) if pas_taux > 0 else 0.0
    net_a_payer    = round(net_avant_pas - pas_montant, 2)

    # ── Cotisations patronales ────────────────────────────────────────────
    cp_list = [
        ("Securite sociale maladie", tc.get("Securite sociale maladie patronal", 0.1300), "pct"),
        ("Vieillesse plafonnee", tc.get("Vieillesse plafonnee patronal", 0.0845), "pct"),
        ("Allocations familiales", tc.get("Allocations familiales", 0.0525), "pct"),
        ("Accidents du travail", tc.get("Accidents du travail", 0.0220), "pct"),
        ("Chomage", tc.get("Chomage", 0.0405), "pct"),
        ("Retraite complementaire AGIRC-ARRCO", tc.get("Retraite complementaire patronal", 0.0460), "pct"),
        ("Formation professionnelle", tc.get("Formation professionnelle", 0.0055), "pct"),
    ]
    if mut_pat_mnt > 0:
        cp_list.append(("Mutuelle - part patronale", mut_pat_mnt, "fixe"))

    total_cotis_pat = sum(
        round(salaire_brut * v, 2) if t == "pct" else v
        for _, v, t in cp_list
    )
    cout_total = round(salaire_brut + total_cotis_pat + indemnite_cp, 2)

    # ── PDF ───────────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []

    # En-tête
    hd = Table([[
        Paragraph(f"<b>{prop_nom}</b><br/><font size='8'>{convention}</font>", s(13, WHITE, bold=True)),
        Paragraph(f"DOCUMENT PREPARATOIRE DE PAIE<br/>"
                  f"<font size='10'>{mois_noms[mois-1]} {annee}</font>",
                  s(12, WHITE, bold=True, align=2)),
    ]], colWidths=[8.7*cm, 8.7*cm])
    hd.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),NAVY),
        ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12),
        ("LEFTPADDING",(0,0),(0,-1),14),("RIGHTPADDING",(1,0),(1,-1),14),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(hd)
    bande = Table([[""]], colWidths=[17.4*cm], rowHeights=[4])
    bande.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),GOLD)]))
    story.append(bande)
    story.append(Spacer(1, 0.3*cm))

    # Infos salarié
    info = Table([[
        Paragraph(f"<b>Salarie :</b> {nom_emp}<br/>"
                  f"<b>N° SS :</b> {num_ss}<br/>"
                  f"<b>Naissance :</b> {date_naiss}", s(9, NAVY)),
        Paragraph(f"<b>Adresse :</b> {adresse_sal}", s(9, NAVY)),
        Paragraph(f"<b>Contrat :</b> {contrat}<br/>"
                  f"<b>Taux horaire :</b> {taux_h:.2f} EUR/h", s(9, NAVY)),
        Paragraph(f"<b>Employeur :</b> {prop_nom}<br/>"
                  f"<b>Periode :</b> {mois_noms[mois-1]} {annee}", s(9, NAVY)),
    ]], colWidths=[4.5*cm,4.5*cm,3.5*cm,4.9*cm])
    info.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),LIGHT),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
    ]))
    story.append(info)
    story.append(Spacer(1, 0.35*cm))

    # Section 1 — Détail pointages
    story.append(Paragraph("1. HEURES TRAVAILLEES", s(9, NAVY, bold=True)))
    story.append(Spacer(1, 0.1*cm))
    lig_pts = [[
        Paragraph("<b>Date</b>", s(8, WHITE, bold=True)),
        Paragraph("<b>Arrivee</b>", s(8, WHITE, bold=True, align=1)),
        Paragraph("<b>Depart</b>", s(8, WHITE, bold=True, align=1)),
        Paragraph("<b>Duree</b>", s(8, WHITE, bold=True, align=1)),
        Paragraph("<b>Valide</b>", s(8, WHITE, bold=True, align=1)),
        Paragraph("<b>Notes</b>", s(8, WHITE, bold=True)),
    ]]
    for p in sorted(pointages, key=lambda x: x.get("date_menage","")):
        dm = p.get("duree_minutes") or 0
        h, m = divmod(dm, 60)
        lig_pts.append([
            Paragraph(str(p.get("date_menage",""))[:10], s(8, NAVY)),
            Paragraph(str(p.get("heure_arrivee",""))[:5] or "--", s(8, GREY, align=1)),
            Paragraph(str(p.get("heure_depart",""))[:5] or "--", s(8, GREY, align=1)),
            Paragraph(f"{h}h{m:02d}", s(8, NAVY, bold=True, align=1)),
            Paragraph("Oui" if p.get("valide") else "Non", s(8, GREY, align=1)),
            Paragraph(str(p.get("notes","") or "")[:35], s(7, GREY)),
        ])
    lig_pts.append([
        Paragraph("<b>TOTAL</b>", s(9, WHITE, bold=True)),
        Paragraph("", s(8)),Paragraph("", s(8)),
        Paragraph(f"<b>{int(total_heures)}h{int((total_heures%1)*60):02d}</b>", s(9, WHITE, bold=True, align=1)),
        Paragraph("", s(8)),Paragraph("", s(8)),
    ])
    last_pt = len(lig_pts)-1
    dt = Table(lig_pts, colWidths=[2.4*cm,2*cm,2*cm,2*cm,2*cm,6.9*cm])
    dt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("BACKGROUND",(0,last_pt),(-1,last_pt),BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,last_pt-1),[WHITE,LIGHT]),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),5),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(dt)
    story.append(Spacer(1, 0.35*cm))

    # Section 2 — Cotisations salariales
    story.append(Paragraph("2. COTISATIONS SALARIALES", s(9, NAVY, bold=True)))
    story.append(Spacer(1, 0.1*cm))
    lig_sal = [[
        Paragraph("<b>Rubrique</b>", s(8, WHITE, bold=True)),
        Paragraph("<b>Base</b>", s(8, WHITE, bold=True, align=1)),
        Paragraph("<b>Taux</b>", s(8, WHITE, bold=True, align=1)),
        Paragraph("<b>Montant</b>", s(8, WHITE, bold=True, align=2)),
    ]]
    lig_sal.append([
        Paragraph("Salaire brut", s(9, NAVY, bold=True)),
        Paragraph(f"{salaire_brut:.2f}", s(8, GREY, align=1)),
        Paragraph(f"{total_heures:.2f} h x {taux_h:.2f}", s(8, GREY, align=1)),
        Paragraph(f"{salaire_brut:.2f} EUR", s(9, NAVY, bold=True, align=2)),
    ])
    for nom_c, val_c, typ_c in cs:
        if typ_c == "pct":
            mnt_c = round(salaire_brut * val_c, 2)
            taux_str = f"{val_c*100:.2f}%"
            base_str = f"{salaire_brut:.2f}"
        else:
            mnt_c = val_c
            taux_str = "forfait"
            base_str = "--"
        lig_sal.append([
            Paragraph(nom_c, s(8, NAVY)),
            Paragraph(base_str, s(8, GREY, align=1)),
            Paragraph(taux_str, s(8, GREY, align=1)),
            Paragraph(f"-{mnt_c:.2f} EUR", s(8, RED, align=2)),
        ])
    lig_sal.append([
        Paragraph("Indemnite conges payes", s(8, GREEN)),
        Paragraph(f"{salaire_brut:.2f}", s(8, GREY, align=1)),
        Paragraph(f"{cp_taux*100:.1f}%", s(8, GREY, align=1)),
        Paragraph(f"+{indemnite_cp:.2f} EUR", s(8, GREEN, align=2)),
    ])
    if pas_montant > 0:
        lig_sal.append([
            Paragraph(f"Prelevement a la source", s(8, RED)),
            Paragraph(f"{net_avant_pas:.2f}", s(8, GREY, align=1)),
            Paragraph(f"{pas_taux*100:.1f}%", s(8, GREY, align=1)),
            Paragraph(f"-{pas_montant:.2f} EUR", s(8, RED, align=2)),
        ])
    lig_sal.append([
        Paragraph("<b>NET A PAYER</b>", s(10, WHITE, bold=True)),
        Paragraph("", s(8)),Paragraph("", s(8)),
        Paragraph(f"<b>{net_a_payer:.2f} EUR</b>", s(10, WHITE, bold=True, align=2)),
    ])
    last_sal = len(lig_sal)-1
    st_sal = Table(lig_sal, colWidths=[8*cm,3*cm,2.5*cm,3.9*cm])
    st_sal.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("BACKGROUND",(0,1),(-1,1),LIGHT),
        ("ROWBACKGROUNDS",(0,2),(-1,last_sal-1),[WHITE,LIGHT]),
        ("BACKGROUND",(0,last_sal),(-1,last_sal),GREEN),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),7),
    ]))
    story.append(st_sal)
    story.append(Spacer(1, 0.35*cm))

    # Section 3 — Cotisations patronales
    story.append(Paragraph("3. CHARGES PATRONALES", s(9, NAVY, bold=True)))
    story.append(Spacer(1, 0.1*cm))
    lig_pat = [[
        Paragraph("<b>Rubrique</b>", s(8, WHITE, bold=True)),
        Paragraph("<b>Base</b>", s(8, WHITE, bold=True, align=1)),
        Paragraph("<b>Taux</b>", s(8, WHITE, bold=True, align=1)),
        Paragraph("<b>Montant</b>", s(8, WHITE, bold=True, align=2)),
    ]]
    for nom_c, val_c, typ_c in cp_list:
        if typ_c == "pct":
            mnt_c = round(salaire_brut * val_c, 2)
            taux_str = f"{val_c*100:.2f}%"
            base_str = f"{salaire_brut:.2f}"
        else:
            mnt_c = val_c
            taux_str = "forfait"
            base_str = "--"
        lig_pat.append([
            Paragraph(nom_c, s(8, NAVY)),
            Paragraph(base_str, s(8, GREY, align=1)),
            Paragraph(taux_str, s(8, GREY, align=1)),
            Paragraph(f"{mnt_c:.2f} EUR", s(8, NAVY, align=2)),
        ])
    lig_pat.append([
        Paragraph("<b>TOTAL CHARGES PATRONALES</b>", s(9, WHITE, bold=True)),
        Paragraph("", s(8)),Paragraph("", s(8)),
        Paragraph(f"<b>{total_cotis_pat:.2f} EUR</b>", s(9, WHITE, bold=True, align=2)),
    ])
    last_pat = len(lig_pat)-1
    st_pat = Table(lig_pat, colWidths=[8*cm,3*cm,2.5*cm,3.9*cm])
    st_pat.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,last_pat-1),[WHITE,LIGHT]),
        ("BACKGROUND",(0,last_pat),(-1,last_pat),BLUE),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),7),
    ]))
    story.append(st_pat)
    story.append(Spacer(1, 0.35*cm))

    # Section 4 — Récapitulatif
    story.append(Paragraph("4. RECAPITULATIF", s(9, NAVY, bold=True)))
    story.append(Spacer(1, 0.1*cm))
    recap = [
        [Paragraph("Heures travaillees", s(9, NAVY)),
         Paragraph(f"{total_heures:.2f} h", s(9, NAVY, bold=True, align=2))],
        [Paragraph("Salaire brut", s(9, NAVY)),
         Paragraph(f"{salaire_brut:.2f} EUR", s(9, NAVY, align=2))],
        [Paragraph("Total cotisations salariales", s(9, RED)),
         Paragraph(f"-{total_cotis_sal:.2f} EUR", s(9, RED, align=2))],
        [Paragraph("Indemnite conges payes", s(9, GREEN)),
         Paragraph(f"+{indemnite_cp:.2f} EUR", s(9, GREEN, align=2))],
    ]
    if pas_montant > 0:
        recap.append([
            Paragraph("Prelevement a la source", s(9, RED)),
            Paragraph(f"-{pas_montant:.2f} EUR", s(9, RED, align=2))
        ])
    recap += [
        [Paragraph("<b>NET A PAYER AU SALARIE</b>", s(10, GREEN, bold=True)),
         Paragraph(f"<b>{net_a_payer:.2f} EUR</b>", s(10, GREEN, bold=True, align=2))],
        [Paragraph("Charges patronales", s(9, GREY)),
         Paragraph(f"{total_cotis_pat:.2f} EUR", s(9, GREY, align=2))],
        [Paragraph("<b>COUT TOTAL EMPLOYEUR</b>", s(10, BLUE, bold=True)),
         Paragraph(f"<b>{cout_total:.2f} EUR</b>", s(10, BLUE, bold=True, align=2))],
    ]
    idx_net = len(recap) - 3
    idx_cout = len(recap) - 1
    rt = Table(recap, colWidths=[11.5*cm,5.9*cm])
    rt_styles = [
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("BACKGROUND",(0,idx_net),(-1,idx_net),LGREEN),
        ("BACKGROUND",(0,idx_cout),(-1,idx_cout),LBLUE),
        ("LINEABOVE",(0,idx_net),(-1,idx_net),1.5,GREEN),
        ("LINEABOVE",(0,idx_cout),(-1,idx_cout),1.5,BLUE),
    ]
    for i in range(len(recap)):
        if i % 2 == 0 and i not in [idx_net, idx_cout]:
            rt_styles.append(("BACKGROUND",(0,i),(-1,i),LIGHT))
    rt.setStyle(TableStyle(rt_styles))
    story.append(rt)
    story.append(Spacer(1, 0.5*cm))

    # Pied de page
    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 0.15*cm))
    from datetime import datetime as _dt
    story.append(Paragraph(
        f"Document preparatoire - non contractuel - taux indicatifs 2026 - "
        f"Convention : {convention} - "
        f"Genere le {_dt.now().strftime('%d/%m/%Y')} par LodgePro",
        s(7, GREY, align=1)
    ))

    doc.build(story)
    return buffer.getvalue()


def show():
    st.title("🧹 Ménage & RH")

    prop_id = st.session_state.get("prop_id", 0) or 0
    if not prop_id:
        st.warning("Sélectionnez une propriété.")
        return

    from database.proprietes_repo import fetch_all as _fa
    props = {p["id"]: p for p in _fa()}
    prop  = props.get(prop_id, {})
    prop_nom = prop.get("nom", "")

    tab_pointage, tab_employes, tab_taches, tab_recap, tab_bulletin = st.tabs([
        "⏱️ Pointage", "👥 Employés", "📋 Tâches", "📊 Récapitulatif", "📄 Bulletin"
    ])

    # ── ONGLET POINTAGE ───────────────────────────────────────────────────
    with tab_pointage:
        st.subheader("⏱️ Saisie des heures")

        employes = get_employes(prop_id)
        if not employes:
            st.warning("Ajoutez d'abord des employés dans l'onglet 'Employés'.")
        else:
            with st.form("form_pointage", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    emp_opts = {e["id"]: f"{e['prenom']} {e['nom']}" for e in employes}
                    emp_id   = st.selectbox("Employé", list(emp_opts.keys()),
                                             format_func=lambda x: emp_opts[x])
                    date_men = st.date_input("Date", value=date.today())
                with c2:
                    h_arr = st.time_input("Heure d'arrivée",  value=time(8, 0))
                    h_dep = st.time_input("Heure de départ",  value=time(12, 0))

                # Réservation liée (optionnel)
                df_resas = load_reservations()
                if not df_resas.empty:
                    df_p = df_resas[df_resas["propriete_id"] == prop_id].copy()
                    df_p["date_depart"] = pd.to_datetime(df_p["date_depart"], errors="coerce")
                    df_p = df_p[df_p["date_depart"].dt.date >= date_men - pd.Timedelta(days=3)]
                    if not df_p.empty:
                        resa_opts = {0: "— Aucune réservation liée —"}
                        resa_opts.update({
                            int(r["id"]): f"{r['nom_client']} — {str(r['date_depart'])[:10]}"
                            for _, r in df_p.iterrows()
                        })
                        resa_id = st.selectbox("Réservation liée", list(resa_opts.keys()),
                                                format_func=lambda x: resa_opts[x])
                    else:
                        resa_id = 0
                else:
                    resa_id = 0

                notes = st.text_area("Notes", height=60, placeholder="Observations...")
                submitted = st.form_submit_button("💾 Enregistrer le pointage",
                                                   type="primary", use_container_width=True)

            if submitted:
                dt_arr = datetime.combine(date_men, h_arr)
                dt_dep = datetime.combine(date_men, h_dep)
                duree  = max(0, int((dt_dep - dt_arr).total_seconds() / 60))
                data = {
                    "propriete_id":  prop_id,
                    "employe_id":    emp_id,
                    "date_menage":   str(date_men),
                    "heure_arrivee": str(h_arr),
                    "heure_depart":  str(h_dep),
                    "duree_minutes": duree,
                    "notes":         notes or None,
                    "valide":        False,
                }
                if resa_id:
                    data["reservation_id"] = resa_id
                pid = save_pointage(data)
                if pid:
                    h, m = divmod(duree, 60)
                    st.success(f"✅ Pointage enregistré — Durée : {h}h{m:02d}")
                    st.rerun()
                else:
                    st.error("❌ Erreur d'enregistrement.")

        # Liste des pointages récents
        st.divider()
        st.subheader("📋 Pointages récents")

        mois_sel  = st.selectbox("Mois", range(1,13),
                                  format_func=lambda m: ["Jan","Fév","Mar","Avr","Mai","Jun",
                                                          "Jul","Aoû","Sep","Oct","Nov","Déc"][m-1],
                                  index=date.today().month-1, key="men_mois_pt")
        annee_sel = st.selectbox("Année", [2024,2025,2026,2027],
                                  index=[2024,2025,2026,2027].index(date.today().year),
                                  key="men_annee_pt")

        pointages = get_pointages(prop_id, mois_sel, annee_sel)
        emp_dict  = {e["id"]: f"{e['prenom']} {e['nom']}" for e in get_employes(prop_id)}

        if not pointages:
            st.info("Aucun pointage ce mois.")
        else:
            for p in pointages:
                duree_min = p.get("duree_minutes") or 0
                h, m = divmod(duree_min, 60)
                emp_nom = emp_dict.get(p.get("employe_id"), "?")
                valide  = p.get("valide", False)

                with st.expander(
                    f"{'✅' if valide else '⏳'} {emp_nom} — "
                    f"{str(p.get('date_menage',''))[:10]} — {h}h{m:02d}",
                    expanded=False
                ):
                    col1, col2, col3 = st.columns(3)
                    col1.markdown(f"**Arrivée :** {str(p.get('heure_arrivee',''))[:5]}")
                    col2.markdown(f"**Départ :** {str(p.get('heure_depart',''))[:5]}")
                    col3.markdown(f"**Durée :** {h}h{m:02d}")

                    if p.get("notes"):
                        st.caption(f"Notes : {p['notes']}")

                    # Validation
                    col_v1, col_v2 = st.columns(2)
                    with col_v1:
                        if not valide:
                            if st.button("✅ Valider", key=f"val_{p['id']}"):
                                update_pointage(p["id"], {"valide": True})
                                st.rerun()
                        else:
                            if st.button("↩️ Annuler validation", key=f"unval_{p['id']}"):
                                update_pointage(p["id"], {"valide": False})
                                st.rerun()

                    # Ventilation des tâches
                    st.markdown("**Ventilation des tâches :**")
                    taches = get_taches(prop_id)
                    ventil = get_ventilation(p["id"])
                    ventil_dict = {v["tache_id"]: v["duree_minutes"] for v in ventil}

                    with st.form(f"form_ventil_{p['id']}"):
                        total_ventil = 0
                        saisies = {}
                        cols_t = st.columns(2)
                        for i, t in enumerate(taches):
                            with cols_t[i % 2]:
                                duree_t = st.number_input(
                                    t["nom"],
                                    min_value=0, max_value=480,
                                    value=ventil_dict.get(t["id"], 0),
                                    step=5,
                                    help=f"Estimé : {t.get('duree_estimee',30)} min",
                                    key=f"vent_{p['id']}_{t['id']}"
                                )
                                saisies[t["id"]] = duree_t
                                total_ventil += duree_t

                        st.caption(f"Total ventilé : {total_ventil} min / {duree_min} min disponibles")
                        if st.form_submit_button("💾 Enregistrer ventilation", use_container_width=True):
                            delete_ventilation(p["id"])
                            for tid, dur in saisies.items():
                                if dur > 0:
                                    save_ventilation(p["id"], tid, dur)
                            st.success("✅ Ventilation enregistrée !")
                            st.rerun()

    # ── ONGLET EMPLOYÉS ───────────────────────────────────────────────────
    with tab_employes:
        st.subheader("👥 Gestion des employés")

        employes = get_employes(prop_id)

        # Formulaire ajout
        with st.form("form_add_emp", clear_on_submit=True):
            st.markdown("**Ajouter un employé**")
            c1, c2, c3 = st.columns(3)
            with c1:
                prenom    = st.text_input("Prénom *")
                nom       = st.text_input("Nom *")
                naissance = st.text_input("Date naissance", placeholder="JJ/MM/AAAA")
            with c2:
                telephone = st.text_input("Téléphone")
                email_emp = st.text_input("Email")
                num_ss_a  = st.text_input("N° Sécurité sociale", placeholder="1 85 12 75 123 456 78")
            with c3:
                taux      = st.number_input("Taux horaire (€)", min_value=0.0, value=12.00, step=0.10)
                contrat   = st.selectbox("Contrat", ["CDI","CDD","Interim","Auto-entrepreneur"])
                adresse_a = st.text_input("Adresse")
            c4, c5 = st.columns([2,3])
            with c4: cp_a    = st.text_input("Code postal")
            with c5: ville_a = st.text_input("Ville")

            if st.form_submit_button("➕ Ajouter", type="primary", use_container_width=True):
                if not prenom or not nom:
                    st.error("Prénom et nom obligatoires.")
                elif save_employe({
                    "propriete_id":  prop_id,
                    "prenom":        prenom.strip(),
                    "nom":           nom.strip(),
                    "telephone":     telephone.strip() or None,
                    "email":         email_emp.strip() or None,
                    "taux_horaire":  taux,
                    "contrat":       contrat,
                    "numero_ss":     num_ss_a.strip() or None,
                    "adresse":       adresse_a.strip() or None,
                    "code_postal":   cp_a.strip() or None,
                    "ville":         ville_a.strip() or None,
                    "date_naissance":naissance.strip() or None,
                    "actif":         True,
                }):
                    st.success(f"✅ {prenom} {nom} ajouté !")
                    st.rerun()

        # Rattacher un employé existant d'une autre propriété
        st.divider()
        st.markdown("**Rattacher un employé existant à cette propriété**")
        st.caption("Si cet employé travaille déjà dans une autre propriété, rattachez-le ici.")

        # Récupérer tous les employés actifs pas encore rattachés
        try:
            tous = _sb().table("employes_menage").select("*").eq("actif", True).execute().data or []
            emp_ids_ici = {e["id"] for e in get_employes(prop_id)}
            disponibles = [e for e in tous if e["id"] not in emp_ids_ici]
            if disponibles:
                with st.form("form_rattacher"):
                    emp_ratt = st.selectbox(
                        "Employé à rattacher",
                        [e["id"] for e in disponibles],
                        format_func=lambda x: next(
                            (f"{e['prenom']} {e['nom']}" for e in disponibles if e["id"] == x), "?"
                        )
                    )
                    if st.form_submit_button("🔗 Rattacher", use_container_width=True):
                        if rattacher_employe(emp_ratt, prop_id):
                            st.success("✅ Employé rattaché !")
                            st.rerun()
        except: pass

        st.divider()

        if not employes:
            st.info("Aucun employé configuré.")
        else:
            for e in employes:
                with st.expander(f"👤 {e['prenom']} {e['nom']} — {e.get('contrat','?')} — {e.get('taux_horaire',0):.2f} €/h"):
                    with st.form(f"form_edit_emp_{e['id']}"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            new_prenom = st.text_input("Prénom", value=e.get("prenom",""))
                            new_nom    = st.text_input("Nom",    value=e.get("nom",""))
                        with c2:
                            new_tel   = st.text_input("Téléphone", value=e.get("telephone","") or "")
                            new_email = st.text_input("Email",     value=e.get("email","") or "")
                        with c3:
                            new_taux    = st.number_input("Taux (€/h)", value=float(e.get("taux_horaire",12) or 12), step=0.10)
                            new_contrat = st.selectbox("Contrat",
                                ["CDI","CDD","Interim","Auto-entrepreneur"],
                                index=["CDI","CDD","Interim","Auto-entrepreneur"].index(e.get("contrat","CDI"))
                                if e.get("contrat") in ["CDI","CDD","Interim","Auto-entrepreneur"] else 0)

                        col_s, col_d = st.columns(2)
                        with col_s:
                            if st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True):
                                update_employe(e["id"], {
                                    "prenom": new_prenom, "nom": new_nom,
                                    "telephone": new_tel or None, "email": new_email or None,
                                    "taux_horaire": new_taux, "contrat": new_contrat,
                                })
                                st.success("✅ Mis à jour !")
                                st.rerun()
                        with col_d:
                            if st.form_submit_button("🗑️ Désactiver", use_container_width=True):
                                update_employe(e["id"], {"actif": False})
                                st.warning("Employé désactivé.")
                                st.rerun()

    # ── ONGLET TÂCHES ─────────────────────────────────────────────────────
    with tab_taches:
        st.subheader("📋 Configuration des tâches")
        taches = get_taches(prop_id)

        with st.form("form_add_tache", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1: nom_t = st.text_input("Nom de la tâche *")
            with c2: duree_t = st.number_input("Durée estimée (min)", min_value=5, value=30, step=5)
            with c3: ordre_t = st.number_input("Ordre d'affichage", min_value=0, value=len(taches)+1)

            if st.form_submit_button("➕ Ajouter la tâche", use_container_width=True):
                if not nom_t:
                    st.error("Nom obligatoire.")
                else:
                    _sb().table("taches_menage").insert({
                        "propriete_id": prop_id, "nom": nom_t.strip(),
                        "duree_estimee": duree_t, "ordre": ordre_t, "actif": True,
                    }).execute()
                    st.success(f"✅ Tâche '{nom_t}' ajoutée !")
                    st.rerun()

        st.divider()
        if taches:
            for t in taches:
                try:
                    col1, col2, col3 = st.columns([3,1,1])
                    col1.markdown(f"**{t.get('nom','?')}** — {t.get('duree_estimee',0)} min estimées")
                    with col3:
                        if st.button("🗑️", key=f"del_tache_{t.get('id',0)}"):
                            _sb().table("taches_menage").update({"actif": False}).eq("id", t["id"]).execute()
                            st.rerun()
                except Exception as _et:
                    st.error(f"Erreur tâche : {_et} — données : {t}")

    # ── ONGLET RÉCAPITULATIF ──────────────────────────────────────────────
    with tab_recap:
        st.subheader("📊 Récapitulatif mensuel")

        # Sélecteurs mois/année d'abord
        c1, c2 = st.columns(2)
        with c1:
            mois_r = st.selectbox("Mois", range(1,13),
                                   format_func=lambda m: ["Janvier","Février","Mars","Avril","Mai","Juin",
                                                           "Juillet","Août","Septembre","Octobre","Novembre","Décembre"][m-1],
                                   index=date.today().month-1, key="men_mois_r")
        with c2:
            annee_r = st.selectbox("Année", [2024,2025,2026,2027],
                                    index=[2024,2025,2026,2027].index(date.today().year),
                                    key="men_annee_r")

        # Vue consolidée multi-propriétés pour l'admin
        is_admin = st.session_state.get("is_admin", False)
        if is_admin:
            try:
                from database.proprietes_repo import fetch_all as _fa_r
                all_props = _fa_r()
                all_prop_ids = [p["id"] for p in all_props]
            except:
                all_prop_ids = []
            if st.checkbox("Vue consolidée toutes propriétés", key="recap_all"):
                st.info("Vue consolidée — heures cumulées par employé sur toutes les propriétés")
                try:
                    emps_all = get_employes_all(all_prop_ids)
                except Exception as _e_all:
                    st.error(f"Erreur vue consolidée : {_e_all}")
                    emps_all = []
                if emps_all:
                    all_pts = []
                    for pid in all_prop_ids:
                        all_pts += get_pointages(pid, mois_r, annee_r)
                    
                    emp_dict_all = {e["id"]: e for e in emps_all}
                    recap_all = {}
                    for p in all_pts:
                        eid = p.get("employe_id")
                        if eid not in emp_dict_all: continue
                        if eid not in recap_all:
                            recap_all[eid] = {"minutes": 0, "interventions": 0}
                        recap_all[eid]["minutes"]       += p.get("duree_minutes",0) or 0
                        recap_all[eid]["interventions"] += 1

                    rows_all = []
                    for eid, data in recap_all.items():
                        e = emp_dict_all.get(eid, {})
                        taux   = float(e.get("taux_horaire",12) or 12)
                        heures = data["minutes"] / 60
                        h, m   = divmod(data["minutes"], 60)
                        nb_props = len(e.get("proprietes_rattachees", []))
                        rows_all.append({
                            "Employé":       f"{e.get('prenom','')} {e.get('nom','')}".strip(),
                            "Propriétés":    nb_props,
                            "Interventions": data["interventions"],
                            "Heures":        f"{h}h{m:02d}",
                            "Taux (€/h)":   f"{taux:.2f}",
                            "Salaire brut":  f"{heures*taux:,.2f} €",
                        })
                    if rows_all:
                        st.dataframe(pd.DataFrame(rows_all), use_container_width=True, hide_index=True)
                        total = sum(float(r["Salaire brut"].replace(" €","").replace(",","")) for r in rows_all)
                        st.metric("💶 Masse salariale totale", f"{total:,.2f} €")
                return

        pointages = get_pointages(prop_id, mois_r, annee_r)
        employes  = get_employes(prop_id)
        emp_dict  = {e["id"]: e for e in employes}

        if not pointages:
            st.info("Aucun pointage ce mois.")
        else:
            # Grouper par employé
            recap = {}
            for p in pointages:
                eid = p.get("employe_id")
                if eid not in recap:
                    recap[eid] = {"minutes": 0, "interventions": 0, "validees": 0}
                recap[eid]["minutes"]      += p.get("duree_minutes",0) or 0
                recap[eid]["interventions"] += 1
                if p.get("valide"):
                    recap[eid]["validees"] += 1

            rows = []
            total_sal = 0
            for eid, data in recap.items():
                e = emp_dict.get(eid, {})
                taux = float(e.get("taux_horaire",12) or 12)
                heures = data["minutes"] / 60
                salaire = heures * taux
                total_sal += salaire
                h, m = divmod(data["minutes"], 60)
                rows.append({
                    "Employé":        f"{e.get('prenom','')} {e.get('nom','')}".strip(),
                    "Contrat":        e.get("contrat","?"),
                    "Interventions":  data["interventions"],
                    "Validées":       data["validees"],
                    "Heures":         f"{h}h{m:02d}",
                    "Taux (€/h)":    f"{taux:.2f}",
                    "Salaire brut":   f"{salaire:,.2f} €",
                })

            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            st.metric("💶 Total masse salariale", f"{total_sal:,.2f} €")

    # ── ONGLET BULLETIN ───────────────────────────────────────────────────
    with tab_bulletin:
        st.subheader("📄 Document préparatoire de paie")
        st.caption("Récapitulatif complet avec cotisations salariales et patronales 2026 — à transmettre à votre cabinet de paie.")

        tab_gen, tab_taux = st.tabs(["📄 Générer", "⚙️ Taux de cotisations"])

        with tab_taux:
            st.subheader("⚙️ Taux de cotisations 2026")
            st.caption("Ces taux sont indicatifs. Modifiez-les selon votre convention collective.")

            # Convention collective
            convention = st.selectbox("Convention collective", [
                "Particuliers employeurs (CESU)",
                "Nettoyage industriel",
                "Hôtellerie - Restauration",
                "Autre"
            ], key="convention_cc")

            st.markdown("---")
            st.markdown("**Cotisations salariales**")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                t_mal_sal  = st.number_input("Maladie salarié (%)", value=0.75, step=0.01, format="%.2f", key="t_mal_sal")
                t_viei_sal = st.number_input("Vieillesse salarié (%)", value=6.90, step=0.01, format="%.2f", key="t_viei_sal")
                t_ret_sal  = st.number_input("Retraite complémentaire salarié (%)", value=3.15, step=0.01, format="%.2f", key="t_ret_sal")
            with col_s2:
                t_csg_nd   = st.number_input("CSG non déductible (%)", value=2.40, step=0.01, format="%.2f", key="t_csg_nd")
                t_csg_d    = st.number_input("CSG/CRDS déductible (%)", value=6.80, step=0.01, format="%.2f", key="t_csg_d")

            st.markdown("**Cotisations patronales**")
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                t_mal_pat  = st.number_input("Maladie patronal (%)", value=13.00, step=0.01, format="%.2f", key="t_mal_pat")
                t_viei_pat = st.number_input("Vieillesse patronal (%)", value=8.45, step=0.01, format="%.2f", key="t_viei_pat")
                t_fam      = st.number_input("Allocations familiales (%)", value=5.25, step=0.01, format="%.2f", key="t_fam")
                t_at       = st.number_input("Accidents du travail (%)", value=2.20, step=0.01, format="%.2f", key="t_at")
            with col_p2:
                t_cho      = st.number_input("Chômage (%)", value=4.05, step=0.01, format="%.2f", key="t_cho")
                t_ret_pat  = st.number_input("Retraite complémentaire patronal (%)", value=4.60, step=0.01, format="%.2f", key="t_ret_pat")
                t_form     = st.number_input("Formation professionnelle (%)", value=0.55, step=0.01, format="%.2f", key="t_form")

            st.markdown("---")
            st.markdown("**Mutuelle d'entreprise**")
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                mut_mensuel = st.number_input("Cotisation mensuelle (€)", min_value=0.0,
                                               value=0.0, step=0.50, format="%.2f",
                                               key="mut_mensuel",
                                               help="Montant total de la cotisation mutuelle par mois")
            with col_m2:
                mut_sal_pct = st.number_input("Part salariale (%)", min_value=0.0, max_value=100.0,
                                               value=50.0, step=1.0, format="%.1f",
                                               key="mut_sal_pct",
                                               help="% à la charge du salarié (ex: 50%)")
            with col_m3:
                mut_pat_pct = st.number_input("Part patronale (%)", min_value=0.0, max_value=100.0,
                                               value=50.0, step=1.0, format="%.1f",
                                               key="mut_pat_pct",
                                               help="% à la charge de l'employeur (ex: 50%)")

            if mut_mensuel > 0:
                mut_sal_mnt = round(mut_mensuel * mut_sal_pct / 100, 2)
                mut_pat_mnt = round(mut_mensuel * mut_pat_pct / 100, 2)
                st.info(f"Part salariale : **{mut_sal_mnt:.2f} €** | Part patronale : **{mut_pat_mnt:.2f} €**")

            st.markdown("---")
            st.markdown("**Congés payés**")
            cp_taux = st.number_input("Indemnité congés payés (%)", value=10.0,
                                       step=0.1, format="%.1f", key="cp_taux",
                                       help="10% du salaire brut par défaut (légal)")

            st.markdown("**Prélèvement à la source (PAS)**")
            pas_taux = st.number_input("Taux PAS (%)", min_value=0.0, max_value=45.0,
                                        value=0.0, step=0.1, format="%.1f", key="pas_taux",
                                        help="Taux communiqué par l'administration fiscale — 0% si non renseigné")

        with tab_gen:
            employes = get_employes(prop_id)
            if not employes:
                st.warning("Ajoutez des employés dans l'onglet 'Employés' d'abord.")
            else:
                c1, c2, c3 = st.columns(3)
                with c1:
                    emp_opts = {e["id"]: f"{e['prenom']} {e['nom']}" for e in employes}
                    emp_sel  = st.selectbox("Employé", list(emp_opts.keys()),
                                             format_func=lambda x: emp_opts[x], key="bul_emp")
                with c2:
                    mois_b = st.selectbox("Mois", range(1,13),
                                           format_func=lambda m: ["Janvier","Février","Mars","Avril","Mai","Juin",
                                                                   "Juillet","Août","Septembre","Octobre","Novembre","Décembre"][m-1],
                                           index=date.today().month-1, key="bul_mois")
                with c3:
                    annee_b = st.selectbox("Année", [2024,2025,2026,2027],
                                            index=[2024,2025,2026,2027].index(date.today().year),
                                            key="bul_annee")

                if st.button("📄 Générer le document préparatoire PDF",
                              type="primary", use_container_width=True):
                    emp_data = {e["id"]: e for e in employes}
                    employe  = emp_data.get(emp_sel, {})
                    pointages_emp = [p for p in get_pointages(prop_id, mois_b, annee_b)
                                      if p.get("employe_id") == emp_sel]
                    if not pointages_emp:
                        st.warning(f"Aucun pointage pour cet employé en "
                                   f"{['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'][mois_b-1]} {annee_b}.")
                    else:
                        # Passer les taux personnalisés
                        ss = st.session_state
                        mut_mensuel = ss.get("mut_mensuel", 0.0) or 0.0
                        mut_sal_pct = ss.get("mut_sal_pct", 50.0) or 50.0
                        mut_pat_pct = ss.get("mut_pat_pct", 50.0) or 50.0
                        taux_custom = {
                            "Securite sociale maladie salarie":    (ss.get("t_mal_sal", 0.75) or 0.75) / 100,
                            "Vieillesse plafonnee salarie":        (ss.get("t_viei_sal", 6.90) or 6.90) / 100,
                            "Retraite complementaire salarie":     (ss.get("t_ret_sal", 3.15) or 3.15) / 100,
                            "CSG non deductible":                  (ss.get("t_csg_nd", 2.40) or 2.40) / 100,
                            "CSG/CRDS deductible":                 (ss.get("t_csg_d", 6.80) or 6.80) / 100,
                            "Securite sociale maladie patronal":   (ss.get("t_mal_pat", 13.00) or 13.00) / 100,
                            "Vieillesse plafonnee patronal":       (ss.get("t_viei_pat", 8.45) or 8.45) / 100,
                            "Allocations familiales":              (ss.get("t_fam", 5.25) or 5.25) / 100,
                            "Accidents du travail":                (ss.get("t_at", 2.20) or 2.20) / 100,
                            "Chomage":                             (ss.get("t_cho", 4.05) or 4.05) / 100,
                            "Retraite complementaire patronal":    (ss.get("t_ret_pat", 4.60) or 4.60) / 100,
                            "Formation professionnelle":           (ss.get("t_form", 0.55) or 0.55) / 100,
                        }
                        extra = {
                            "mutuelle_mensuel":  mut_mensuel,
                            "mutuelle_sal_pct":  mut_sal_pct,
                            "mutuelle_pat_pct":  mut_pat_pct,
                            "cp_taux":           (ss.get("cp_taux", 10.0) or 10.0) / 100,
                            "pas_taux":          (ss.get("pas_taux", 0.0) or 0.0) / 100,
                            "convention":         ss.get("convention_cc", "Particuliers employeurs (CESU)"),
                        }
                        with st.spinner("Génération en cours..."):
                            pdf_bytes = _generer_bulletin(employe, pointages_emp,
                                                          prop_nom, mois_b, annee_b,
                                                          taux_custom=taux_custom,
                                                          extra=extra)
                        nom_safe = f"{employe.get('prenom','')}_{employe.get('nom','')}".replace(" ","_")
                        st.download_button(
                            label="⬇️ Télécharger le document PDF",
                            data=pdf_bytes,
                            file_name=f"Paie_{nom_safe}_{annee_b}_{mois_b:02d}.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True,
                        )
                        st.success("✅ Document prêt !")
