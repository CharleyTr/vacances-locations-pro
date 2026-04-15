"""
Page DADS — Déclaration Annuelle des Données Sociales.
Récapitulatif annuel par salarié pour chaque propriété.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database.supabase_client import get_supabase


def _sb():
    return get_supabase()


def get_employes(prop_id):
    try:
        return _sb().table("employes_menage").select("*")\
            .eq("propriete_id", prop_id).eq("actif", True)\
            .order("nom").execute().data or []
    except: return []


def get_pointages_annee(prop_id, annee):
    try:
        debut = f"{annee}-01-01"
        fin   = f"{annee}-12-31"
        return _sb().table("pointages_menage").select("*")\
            .eq("propriete_id", prop_id)\
            .gte("date_menage", debut)\
            .lte("date_menage", fin)\
            .execute().data or []
    except: return []


def _calcul_annuel(employe, pointages, taux_custom=None):
    """Calcule les données annuelles d'un salarié."""
    tc = taux_custom or {}
    taux_h = float(employe.get("taux_horaire", 12) or 12)

    total_minutes = sum(p.get("duree_minutes") or 0 for p in pointages)
    total_heures  = total_minutes / 60
    salaire_brut  = round(total_heures * taux_h, 2)

    # Cotisations salariales
    cotis_sal = (
        tc.get("maladie_sal", 0.0075) +
        tc.get("vieillesse_sal", 0.0690) +
        tc.get("retraite_sal", 0.0315) +
        tc.get("csg_nd", 0.0240) +
        tc.get("csg_crds", 0.0680)
    )
    total_cotis_sal = round(salaire_brut * cotis_sal, 2)
    cp              = round(salaire_brut * tc.get("cp_taux", 0.10), 2)
    net_a_payer     = round(salaire_brut - total_cotis_sal + cp, 2)

    # Cotisations patronales
    cotis_pat = (
        tc.get("maladie_pat", 0.1300) +
        tc.get("vieillesse_pat", 0.0845) +
        tc.get("fam", 0.0525) +
        tc.get("at", 0.0220) +
        tc.get("chomage", 0.0405) +
        tc.get("retraite_pat", 0.0460) +
        tc.get("formation", 0.0055)
    )
    total_cotis_pat = round(salaire_brut * cotis_pat, 2)
    cout_total      = round(salaire_brut + total_cotis_pat + cp, 2)

    return {
        "total_heures":     total_heures,
        "salaire_brut":     salaire_brut,
        "cotisations_sal":  total_cotis_sal,
        "indemnite_cp":     cp,
        "net_a_payer":      net_a_payer,
        "cotisations_pat":  total_cotis_pat,
        "cout_total":       cout_total,
    }


def _generer_dads_pdf(employe, donnees_annuelles, prop_nom, prop):
    """Génère le PDF DADS multi-années."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from datetime import datetime as _dt
    import io

    NAVY  = colors.HexColor("#0B1F3A")
    BLUE  = colors.HexColor("#1565C0")
    GOLD  = colors.HexColor("#F0B429")
    GREY  = colors.HexColor("#6B7280")
    LIGHT = colors.HexColor("#F4F7FF")
    WHITE = colors.white
    GREEN = colors.HexColor("#1B5E20")
    LGREEN= colors.HexColor("#E8F5E9")
    RED   = colors.HexColor("#B71C1C")

    def s(size, color=NAVY, bold=False, align=0):
        return ParagraphStyle("_", fontSize=size, textColor=color,
                              fontName="Helvetica-Bold" if bold else "Helvetica",
                              alignment=align, leading=size*1.4, spaceAfter=2)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    story = []

    nom_emp   = f"{employe.get('prenom','')} {employe.get('nom','')}".strip()
    num_ss    = employe.get("numero_ss","") or "Non renseigne"
    date_naiss= str(employe.get("date_naissance","") or "Non renseignee")[:10]
    adresse   = " ".join(filter(None, [
        employe.get("adresse","") or "",
        employe.get("code_postal","") or "",
        employe.get("ville","") or "",
    ])) or "Non renseignee"
    contrat   = employe.get("contrat","CDI") or "CDI"
    taux_h    = float(employe.get("taux_horaire",12) or 12)
    prop_siret = prop.get("siret","") or "Non renseigne"
    prop_adr   = " ".join(filter(None,[
        prop.get("rue","") or "",
        prop.get("code_postal","") or "",
        prop.get("ville","") or "",
    ])) or ""

    # En-tête
    hd = Table([[
        Paragraph("<b>DADS - DECLARATION ANNUELLE</b><br/>"
                  "<font size='9'>Donnees Sociales Individuelles</font>",
                  s(13, WHITE, bold=True)),
        Paragraph(f"{prop_nom}<br/>"
                  f"<font size='8'>SIRET : {prop_siret}</font>",
                  s(10, WHITE, bold=True, align=2)),
    ]], colWidths=[9*cm, 8.4*cm])
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
    story.append(Spacer(1, 0.4*cm))

    # Infos employeur
    story.append(Paragraph("EMPLOYEUR", s(9, BLUE, bold=True)))
    story.append(Spacer(1,0.1*cm))
    emp_tbl = Table([[
        Paragraph(f"<b>Raison sociale :</b> {prop_nom}", s(9,NAVY)),
        Paragraph(f"<b>Adresse :</b> {prop_adr}", s(9,NAVY)),
        Paragraph(f"<b>SIRET :</b> {prop_siret}", s(9,NAVY)),
    ]], colWidths=[5.5*cm, 7*cm, 4.9*cm])
    emp_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),LIGHT),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
    ]))
    story.append(emp_tbl)
    story.append(Spacer(1, 0.35*cm))

    # Infos salarié
    story.append(Paragraph("SALARIE", s(9, BLUE, bold=True)))
    story.append(Spacer(1,0.1*cm))
    sal_rows = [
        [Paragraph("<b>Nom et Prenom</b>", s(9,GREY,bold=True)),
         Paragraph(nom_emp, s(9,NAVY,bold=True)),
         Paragraph("<b>N° Securite Sociale</b>", s(9,GREY,bold=True)),
         Paragraph(num_ss, s(9,NAVY,bold=True))],
        [Paragraph("<b>Date de naissance</b>", s(9,GREY,bold=True)),
         Paragraph(date_naiss, s(9,NAVY)),
         Paragraph("<b>Adresse</b>", s(9,GREY,bold=True)),
         Paragraph(adresse, s(9,NAVY))],
        [Paragraph("<b>Contrat</b>", s(9,GREY,bold=True)),
         Paragraph(contrat, s(9,NAVY)),
         Paragraph("<b>Taux horaire</b>", s(9,GREY,bold=True)),
         Paragraph(f"{taux_h:.2f} EUR/h", s(9,NAVY))],
    ]
    sal_tbl = Table(sal_rows, colWidths=[4*cm,4.7*cm,4*cm,4.7*cm])
    sal_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHITE,LIGHT]),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),8),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("LINEAFTER",(0,0),(0,-1),1,colors.HexColor("#D0D5DD")),
        ("LINEAFTER",(2,0),(2,-1),1,colors.HexColor("#D0D5DD")),
    ]))
    story.append(sal_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Tableau récapitulatif annuel
    story.append(Paragraph("RECAPITULATIF ANNUEL DES REMUNÉRATIONS", s(9, BLUE, bold=True)))
    story.append(Spacer(1,0.1*cm))

    entetes = [
        Paragraph("<b>Annee</b>", s(8,WHITE,bold=True,align=1)),
        Paragraph("<b>Heures</b>", s(8,WHITE,bold=True,align=1)),
        Paragraph("<b>Salaire Brut</b>", s(8,WHITE,bold=True,align=1)),
        Paragraph("<b>Cotis. Sal.</b>", s(8,WHITE,bold=True,align=1)),
        Paragraph("<b>Ind. CP</b>", s(8,WHITE,bold=True,align=1)),
        Paragraph("<b>Net a Payer</b>", s(8,WHITE,bold=True,align=1)),
        Paragraph("<b>Charges Pat.</b>", s(8,WHITE,bold=True,align=1)),
        Paragraph("<b>Cout Total</b>", s(8,WHITE,bold=True,align=1)),
    ]
    lignes = [entetes]

    tot_heures = tot_brut = tot_cotis_sal = tot_cp = tot_net = tot_cotis_pat = tot_cout = 0

    for annee, d in sorted(donnees_annuelles.items()):
        h, m = divmod(int(d["total_heures"]*60), 60)
        lignes.append([
            Paragraph(str(annee), s(8,NAVY,bold=True,align=1)),
            Paragraph(f"{h}h{m:02d}", s(8,GREY,align=1)),
            Paragraph(f"{d['salaire_brut']:,.2f}", s(8,NAVY,align=1)),
            Paragraph(f"-{d['cotisations_sal']:,.2f}", s(8,RED,align=1)),
            Paragraph(f"+{d['indemnite_cp']:,.2f}", s(8,GREEN,align=1)),
            Paragraph(f"{d['net_a_payer']:,.2f}", s(8,GREEN,bold=True,align=1)),
            Paragraph(f"{d['cotisations_pat']:,.2f}", s(8,GREY,align=1)),
            Paragraph(f"{d['cout_total']:,.2f}", s(8,BLUE,bold=True,align=1)),
        ])
        tot_heures    += d["total_heures"]
        tot_brut      += d["salaire_brut"]
        tot_cotis_sal += d["cotisations_sal"]
        tot_cp        += d["indemnite_cp"]
        tot_net       += d["net_a_payer"]
        tot_cotis_pat += d["cotisations_pat"]
        tot_cout      += d["cout_total"]

    # Ligne totaux
    th, tm = divmod(int(tot_heures*60), 60)
    lignes.append([
        Paragraph("<b>TOTAL</b>", s(9,WHITE,bold=True,align=1)),
        Paragraph(f"{th}h{tm:02d}", s(9,WHITE,bold=True,align=1)),
        Paragraph(f"{tot_brut:,.2f}", s(9,WHITE,bold=True,align=1)),
        Paragraph(f"-{tot_cotis_sal:,.2f}", s(9,WHITE,bold=True,align=1)),
        Paragraph(f"+{tot_cp:,.2f}", s(9,WHITE,bold=True,align=1)),
        Paragraph(f"{tot_net:,.2f}", s(9,WHITE,bold=True,align=1)),
        Paragraph(f"{tot_cotis_pat:,.2f}", s(9,WHITE,bold=True,align=1)),
        Paragraph(f"{tot_cout:,.2f}", s(9,WHITE,bold=True,align=1)),
    ])

    last = len(lignes)-1
    col_w = [1.6*cm,1.8*cm,2.4*cm,2.2*cm,1.8*cm,2.2*cm,2.2*cm,3.2*cm]
    ann_tbl = Table(lignes, colWidths=col_w)
    ann_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,last-1),[WHITE,LIGHT]),
        ("BACKGROUND",(0,last),(-1,last),BLUE),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),4),
    ]))
    story.append(ann_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Récap global
    recap = [
        [Paragraph("Total salaires bruts cumules", s(10,NAVY)),
         Paragraph(f"{tot_brut:,.2f} EUR", s(10,NAVY,bold=True,align=2))],
        [Paragraph("Total cotisations salariales", s(10,RED)),
         Paragraph(f"-{tot_cotis_sal:,.2f} EUR", s(10,RED,align=2))],
        [Paragraph("Total indemnites conges payes", s(10,GREEN)),
         Paragraph(f"+{tot_cp:,.2f} EUR", s(10,GREEN,align=2))],
        [Paragraph("<b>Total net verse au salarie</b>", s(11,GREEN,bold=True)),
         Paragraph(f"<b>{tot_net:,.2f} EUR</b>", s(11,GREEN,bold=True,align=2))],
        [Paragraph("Total charges patronales", s(10,GREY)),
         Paragraph(f"{tot_cotis_pat:,.2f} EUR", s(10,GREY,align=2))],
        [Paragraph("<b>Cout total employeur</b>", s(11,BLUE,bold=True)),
         Paragraph(f"<b>{tot_cout:,.2f} EUR</b>", s(11,BLUE,bold=True,align=2))],
    ]
    rt = Table(recap, colWidths=[11.5*cm,5.9*cm])
    rt.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[WHITE,LIGHT,WHITE,LGREEN,WHITE,colors.HexColor("#E3F2FD")]),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7),
        ("LEFTPADDING",(0,0),(-1,-1),10),("RIGHTPADDING",(0,0),(-1,-1),10),
        ("LINEABOVE",(0,3),(-1,3),1.5,GREEN),
        ("LINEABOVE",(0,5),(-1,5),1.5,BLUE),
    ]))
    story.append(rt)
    story.append(Spacer(1, 0.5*cm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    story.append(Spacer(1, 0.15*cm))
    story.append(Paragraph(
        f"Document genere le {_dt.now().strftime('%d/%m/%Y')} par LodgePro -- "
        "Taux de cotisations indicatifs -- A transmettre a votre organisme de gestion de paie",
        s(7, GREY, align=1)
    ))

    doc.build(story)
    return buffer.getvalue()


def show():
    st.title("📋 DADS — Déclaration Annuelle des Données Sociales")
    st.caption("Récapitulatif annuel des rémunérations par salarié — multi-années")

    prop_id  = st.session_state.get("prop_id", 0) or 0
    if not prop_id:
        st.warning("Sélectionnez une propriété.")
        return

    from database.proprietes_repo import fetch_all as _fa
    props = {p["id"]: p for p in _fa()}
    prop  = props.get(prop_id, {})
    prop_nom = prop.get("nom", "")

    employes = get_employes(prop_id)
    if not employes:
        st.warning("Aucun employé configuré. Allez dans **🧹 Ménage → Employés**.")
        return

    # ── Paramètres taux ───────────────────────────────────────────────────
    with st.expander("⚙️ Paramètres des taux de cotisations", expanded=False):
        st.caption("Ces taux sont utilisés pour le calcul indicatif.")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Salariales**")
            t_mal_sal  = st.number_input("Maladie sal. (%)",    value=0.75, step=0.01, key="dads_mal_sal") / 100
            t_viei_sal = st.number_input("Vieillesse sal. (%)", value=6.90, step=0.01, key="dads_viei") / 100
            t_ret_sal  = st.number_input("Retraite sal. (%)",   value=3.15, step=0.01, key="dads_ret_sal") / 100
            t_csg_nd   = st.number_input("CSG non déd. (%)",    value=2.40, step=0.01, key="dads_csg_nd") / 100
            t_csg_d    = st.number_input("CSG/CRDS (%)",        value=6.80, step=0.01, key="dads_csg_d") / 100
        with c2:
            st.markdown("**Patronales**")
            t_mal_pat  = st.number_input("Maladie pat. (%)",    value=13.00, step=0.01, key="dads_mal_pat") / 100
            t_viei_pat = st.number_input("Vieillesse pat. (%)", value=8.45,  step=0.01, key="dads_viei_pat") / 100
            t_fam      = st.number_input("Alloc. fam. (%)",     value=5.25,  step=0.01, key="dads_fam") / 100
            t_at       = st.number_input("AT (%)",              value=2.20,  step=0.01, key="dads_at") / 100
            t_cho      = st.number_input("Chômage (%)",         value=4.05,  step=0.01, key="dads_cho") / 100
            t_ret_pat  = st.number_input("Retraite pat. (%)",   value=4.60,  step=0.01, key="dads_ret_pat") / 100
            t_form     = st.number_input("Formation (%)",       value=0.55,  step=0.01, key="dads_form") / 100
        t_cp = st.number_input("Congés payés (%)", value=10.0, step=0.1, key="dads_cp") / 100

    taux_custom = {
        "maladie_sal":   t_mal_sal,  "vieillesse_sal": t_viei_sal,
        "retraite_sal":  t_ret_sal,  "csg_nd":         t_csg_nd,
        "csg_crds":      t_csg_d,    "maladie_pat":    t_mal_pat,
        "vieillesse_pat":t_viei_pat, "fam":            t_fam,
        "at":            t_at,       "chomage":        t_cho,
        "retraite_pat":  t_ret_pat,  "formation":      t_form,
        "cp_taux":       t_cp,
    }

    st.divider()

    # ── Sélection employé et années ───────────────────────────────────────
    c1, c2 = st.columns([2,3])
    with c1:
        emp_sel = st.selectbox(
            "Employé",
            [e["id"] for e in employes],
            format_func=lambda x: next(
                (f"{e['prenom']} {e['nom']}" for e in employes if e["id"] == x), "?"
            ), key="dads_emp"
        )
    with c2:
        annees_dispo = list(range(2020, date.today().year + 1))
        annees_sel = st.multiselect(
            "Années à inclure",
            annees_dispo,
            default=[date.today().year - 1, date.today().year],
            key="dads_annees"
        )

    employe = next((e for e in employes if e["id"] == emp_sel), {})
    nom_emp = f"{employe.get('prenom','')} {employe.get('nom','')}".strip()

    if not annees_sel:
        st.warning("Sélectionnez au moins une année.")
        return

    # ── Calcul des données ────────────────────────────────────────────────
    donnees = {}
    rows_tableau = []

    for annee in sorted(annees_sel):
        pts = [p for p in get_pointages_annee(prop_id, annee)
               if p.get("employe_id") == emp_sel]
        if not pts:
            continue
        d = _calcul_annuel(employe, pts, taux_custom)
        donnees[annee] = d
        h, m = divmod(int(d["total_heures"]*60), 60)
        rows_tableau.append({
            "Année":           annee,
            "Heures":          f"{h}h{m:02d}",
            "Salaire brut":    f"{d['salaire_brut']:,.2f} €",
            "Cotis. sal.":     f"-{d['cotisations_sal']:,.2f} €",
            "Ind. CP":         f"+{d['indemnite_cp']:,.2f} €",
            "Net à payer":     f"{d['net_a_payer']:,.2f} €",
            "Charges pat.":    f"{d['cotisations_pat']:,.2f} €",
            "Coût employeur":  f"{d['cout_total']:,.2f} €",
        })

    if not donnees:
        st.info(f"Aucun pointage trouvé pour {nom_emp} sur les années sélectionnées.")
        return

    # ── Tableau récapitulatif ─────────────────────────────────────────────
    st.markdown(f"### {nom_emp} — DADS {min(annees_sel)}–{max(annees_sel)}")
    st.dataframe(pd.DataFrame(rows_tableau), use_container_width=True, hide_index=True)

    # Totaux
    tot_brut = sum(d["salaire_brut"] for d in donnees.values())
    tot_net  = sum(d["net_a_payer"] for d in donnees.values())
    tot_cout = sum(d["cout_total"] for d in donnees.values())
    k1, k2, k3 = st.columns(3)
    k1.metric("💶 Total brut cumulé",  f"{tot_brut:,.2f} €")
    k2.metric("💚 Total net versé",    f"{tot_net:,.2f} €")
    k3.metric("🏢 Coût total employeur",f"{tot_cout:,.2f} €")

    st.divider()

    # ── Export ────────────────────────────────────────────────────────────
    col_pdf, col_csv = st.columns(2)

    with col_pdf:
        if st.button("📄 Générer PDF DADS", type="primary", use_container_width=True):
            with st.spinner("Génération..."):
                pdf_bytes = _generer_dads_pdf(employe, donnees, prop_nom, prop)
            nom_safe = nom_emp.replace(" ","_")
            st.download_button(
                label="⬇️ Télécharger le PDF DADS",
                data=pdf_bytes,
                file_name=f"DADS_{nom_safe}_{min(annees_sel)}_{max(annees_sel)}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

    with col_csv:
        if rows_tableau:
            df_csv = pd.DataFrame(rows_tableau)
            csv_bytes = df_csv.to_csv(index=False, sep=";", encoding="utf-8-sig").encode()
            st.download_button(
                label="📊 Exporter CSV",
                data=csv_bytes,
                file_name=f"DADS_{nom_emp.replace(' ','_')}_{min(annees_sel)}_{max(annees_sel)}.csv",
                mime="text/csv",
                use_container_width=True,
            )
