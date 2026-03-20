"""
Page Tableau de bord fiscal — LMNP / Meublé tourisme
Suivi seuils micro-BIC, estimation impôt, cotisations sociales
"""
import streamlit as st
from datetime import date
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from services.reservation_service import load_reservations
from database.proprietes_repo import fetch_all
from services.auth_service import is_unlocked
from database.frais_repo import get_frais, save_frais, delete_frais, CATEGORIES, IR_RUBRIQUES
from database.justificatifs_repo import upload_justificatif, get_justificatifs, get_download_url, delete_justificatif
from database.baremes_repo import get_bareme, bareme_to_dict
from database.supabase_client import is_connected

# ─── Barèmes fiscaux 2024/2025 ───────────────────────────────────────────────

# ─── Loi de finances 2024 (applicable revenus 2025+) ────────────────────────
# Avant 2025 : classé 71% / seuil 188 700€ — non classé 50% / seuil 77 700€
# Après 2025  : classé 50% / seuil 77 700€  — non classé 30% / seuil 15 000€
# Source : art. 45 LFR 2024 — applicable déclarations 2025 sur revenus 2024
#          MAIS report partiel : loi 2024 votée fin 2024, revenus 2023 non touchés
#          Revenus 2024 : anciens taux maintenus (report voté)
#          Revenus 2025+ : nouveaux taux applicables

BAREMES = {
    2026: {
        # Nouveaux taux LFR 2024 — applicables revenus 2025+
        "micro_bic_classe_seuil":      77700,   # abaissé (= niveau non classé avant)
        "micro_bic_non_classe_seuil":  15000,   # très fortement abaissé
        "abattement_classe":           0.50,    # réduit de 71% → 50%
        "abattement_non_classe":       0.30,    # réduit de 50% → 30%
        "abattement_min_classe":       305,
        "loi_note": "LFR 2024 — nouveaux taux (revenus 2025+)",
        "tranches_ir": [
            (0,     11497,  0.00),
            (11497, 29315,  0.11),
            (29315, 83823,  0.30),
            (83823, 180294, 0.41),
            (180294, None,  0.45),
        ],
        "cotisations_ssi_taux":    0.231,
        "cotisations_urssaf_taux": 0.172,
        "csg_crds":                0.172,
        "seuil_cotisations":       23000,
    },
    2025: {
        # Nouveaux taux LFR 2024 — applicables revenus 2025
        "micro_bic_classe_seuil":      77700,
        "micro_bic_non_classe_seuil":  15000,
        "abattement_classe":           0.50,
        "abattement_non_classe":       0.30,
        "abattement_min_classe":       305,
        "loi_note": "LFR 2024 — nouveaux taux (revenus 2025+)",
        "tranches_ir": [
            (0,     11294,  0.00),
            (11294, 28797,  0.11),
            (28797, 82341,  0.30),
            (82341, 177106, 0.41),
            (177106, None,  0.45),
        ],
        "cotisations_ssi_taux":    0.231,
        "cotisations_urssaf_taux": 0.172,
        "csg_crds":                0.172,
        "seuil_cotisations":       23000,
    },
    2024: {
        # Anciens taux — revenus 2024 (report voté, ancienne loi maintenue)
        "micro_bic_classe_seuil":      188700,
        "micro_bic_non_classe_seuil":   77700,
        "abattement_classe":            0.71,
        "abattement_non_classe":        0.50,
        "abattement_min_classe":        305,
        "loi_note": "Ancienne loi — taux 2024 (71%/50%)",
        "tranches_ir": [
            (0,     11294,  0.00),
            (11294, 28797,  0.11),
            (28797, 82341,  0.30),
            (82341, 177106, 0.41),
            (177106, None,  0.45),
        ],
        "cotisations_ssi_taux":    0.231,
        "cotisations_urssaf_taux": 0.172,
        "csg_crds":                0.172,
        "seuil_cotisations":       23000,
    },
    2023: {
        # Anciens taux
        "micro_bic_classe_seuil":      188700,
        "micro_bic_non_classe_seuil":   77700,
        "abattement_classe":            0.71,
        "abattement_non_classe":        0.50,
        "abattement_min_classe":        305,
        "loi_note": "Ancienne loi — taux 2023 (71%/50%)",
        "tranches_ir": [
            (0,     10777,  0.00),
            (10777, 27478,  0.11),
            (27478, 78570,  0.30),
            (78570, 168994, 0.41),
            (168994, None,  0.45),
        ],
        "cotisations_ssi_taux":    0.231,
        "cotisations_urssaf_taux": 0.172,
        "csg_crds":                0.172,
        "seuil_cotisations":       23000,
    },
}


def _impot_tranche(revenu_imposable: float, b: dict) -> float:
    """Calcule l'IR sur 1 part fiscale (célibataire) — à ajuster selon quotient."""
    impot = 0.0
    for bas, haut, taux in b["tranches_ir"]:
        if revenu_imposable <= bas:
            break
        plafond = haut if haut else float("inf")
        impot += min(revenu_imposable, plafond) - bas if revenu_imposable > bas else 0
        impot_tranche = (min(revenu_imposable, plafond) - bas) * taux if revenu_imposable > bas else 0
        # recalcul propre
    # recalcul correct
    impot = 0.0
    for bas, haut, taux in b["tranches_ir"]:
        plafond = haut if haut is not None else revenu_imposable + 1
        if revenu_imposable > bas:
            impot += (min(revenu_imposable, plafond) - bas) * taux
    return round(impot, 2)


def _micro_bic(ca: float, classe: bool, b: dict):
    abatt_taux = b["abattement_classe"] if classe else b["abattement_non_classe"]
    abatt_min  = b["abattement_min_classe"] if classe else 0
    abattement = max(ca * abatt_taux, abatt_min)
    revenu_net = max(0, ca - abattement)
    return abattement, revenu_net


def _couleur_seuil(pct):
    if pct < 0.70: return "#4CAF50"
    if pct < 0.90: return "#FF9800"
    return "#F44336"


def _jauge(label, valeur, seuil, unite="€"):
    pct = min(valeur / seuil, 1.0) if seuil > 0 else 0
    couleur = _couleur_seuil(pct)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=valeur,
        delta={"reference": seuil, "valueformat": ",.0f", "suffix": unite},
        number={"valueformat": ",.0f", "suffix": f" {unite}"},
        title={"text": label, "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, seuil * 1.1], "tickformat": ",.0f"},
            "bar":  {"color": couleur},
            "steps": [
                {"range": [0, seuil * 0.70], "color": "#E8F5E9"},
                {"range": [seuil * 0.70, seuil * 0.90], "color": "#FFF3E0"},
                {"range": [seuil * 0.90, seuil * 1.1],  "color": "#FFEBEE"},
            ],
            "threshold": {
                "line": {"color": "#B71C1C", "width": 3},
                "thickness": 0.85,
                "value": seuil
            }
        }
    ))
    fig.update_layout(height=220, margin=dict(t=40, b=10, l=20, r=20))
    return fig


# ─────────────────────────────────────────────────────────────────────────────



def _show_liasse_2033(df_an, annee, props, barem):
    """Liasse fiscale 2033 pré-remplie avec les vraies catégories de frais."""
    import pandas as pd

    st.subheader(f"📋 Liasse fiscale 2033 — Exercice {annee}")
    st.caption("Pré-remplissage automatique depuis vos données. À vérifier avec votre expert-comptable.")

    props_opt = {0: "Toutes les propriétés"}
    props_opt.update({p["id"]: p["nom"] for p in props.values()})
    prop_id = st.selectbox("Propriété", list(props_opt.keys()),
                            format_func=lambda x: props_opt[x], key="liasse_prop")

    df = df_an if prop_id == 0 else df_an[df_an["propriete_id"] == prop_id]

    ca_brut      = float(df["prix_brut"].fillna(0).sum())
    commissions  = float(df["commission"].fillna(0).sum()) if "commission" in df.columns else 0
    taxes_sejour = float(df["taxes_sejour"].fillna(0).sum()) if "taxes_sejour" in df.columns else 0
    ca_net       = ca_brut - commissions - taxes_sejour

    # Charger TOUS les frais avec les vraies catégories
    frais_total   = 0
    frais_par_cat = {}
    try:
        from database.frais_repo import get_frais
        pids = [prop_id] if prop_id else list(props.keys())
        for pid in pids:
            frais_list = get_frais(pid, annee) or []
            for f in frais_list:
                m   = float(f.get("montant", 0) or 0)
                cat = str(f.get("categorie") or "Frais divers").strip()
                frais_par_cat[cat] = frais_par_cat.get(cat, 0) + m
                frais_total += m
    except Exception as e:
        st.warning(f"Erreur chargement frais : {e}")

    # Debug temporaire — afficher les catégories trouvées
    if frais_par_cat:
        st.caption(f"📊 Catégories trouvées : {list(frais_par_cat.keys())}")

    resultat = ca_net - frais_total

    # ── Regroupement par ligne 2033-B via IR_RUBRIQUES ───────────────────
    from database.frais_repo import IR_RUBRIQUES
    lignes = {}
    for cat, montant in frais_par_cat.items():
        rubrique = IR_RUBRIQUES.get(cat, "2033-B Ligne 258 — Autres charges")
        # Extraire le numéro de ligne
        import re as _re
        m_ligne = _re.search(r"Ligne (\d+)", rubrique)
        num = int(m_ligne.group(1)) if m_ligne else 258
        lignes[num] = lignes.get(num, 0) + montant

    ligne236 = lignes.get(236, 0)
    ligne240 = lignes.get(240, 0)
    ligne250 = lignes.get(250, 0)
    ligne256 = lignes.get(256, 0)
    ligne258 = lignes.get(258, 0)

    st.divider()
    st.markdown("### 📄 2033-B — Compte de résultat simplifié")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**PRODUITS**")
        df_prod = pd.DataFrame([
            ("Ligne 214 — Recettes locatives brutes",  f"{ca_brut:,.0f} €"),
            ("Ligne 218 — Taxes de séjour (-)",        f"-{taxes_sejour:,.0f} €"),
            ("Ligne 218 — Commissions plateformes (-)",f"-{commissions:,.0f} €"),
            ("= Recettes nettes déclarées",            f"{ca_net:,.0f} €"),
        ], columns=["Libellé", "Montant"])
        st.dataframe(df_prod, use_container_width=True, hide_index=True)

    with col2:
        st.markdown("**CHARGES**")
        df_chg = pd.DataFrame([
            ("Ligne 236 — Charges externes",          f"{ligne236:,.0f} €",
             "Travaux, gestion, assurances, ménage, plateforme..."),
            ("Ligne 240 — Impôts & taxes",            f"{ligne240:,.0f} €",
             "Taxe foncière"),
            ("Ligne 250 — Amortissements",            f"{ligne250:,.0f} €",
             "Immobilier + mobilier"),
            ("Ligne 256 — Charges financières",       f"{ligne256:,.0f} €",
             "Intérêts d'emprunt"),
            ("Ligne 258 — Autres charges",            f"{ligne258:,.0f} €",
             "Frais divers"),
            ("= Total charges déductibles",           f"{frais_total:,.0f} €", ""),
        ], columns=["Ligne", "Montant", "Détail"])
        st.dataframe(df_chg, use_container_width=True, hide_index=True)

    # Détail par catégorie
    if frais_par_cat:
        with st.expander("🔍 Détail par catégorie de frais"):
            df_det = pd.DataFrame([
                (cat, f"{m:,.0f} €") for cat, m in sorted(frais_par_cat.items())
            ], columns=["Catégorie", "Montant"])
            st.dataframe(df_det, use_container_width=True, hide_index=True)
    else:
        st.warning("⚠️ Aucun frais enregistré pour cette propriété / année. "
                    "Saisissez vos dépenses dans l'onglet **Frais déductibles**.")

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("📥 Recettes nettes", f"{ca_net:,.0f} €")
    c2.metric("📤 Charges totales", f"{frais_total:,.0f} €")
    c3.metric("✅ Résultat fiscal",  f"{resultat:,.0f} €",
              delta=f"{resultat:+,.0f} €",
              delta_color="normal" if resultat >= 0 else "inverse")

    st.divider()
    st.markdown("### 📌 Cases à reporter sur la 2042-C-PRO")
    st.dataframe(pd.DataFrame([
        ("5NA", "Recettes brutes LMNP",    f"{ca_brut:,.0f} €"),
        ("5NF", "Recettes nettes",          f"{ca_net:,.0f} €"),
        ("5NK", "Résultat bénéficiaire",    f"{max(resultat,0):,.0f} €"),
        ("5NM", "Déficit reportable",       f"{abs(min(resultat,0)):,.0f} €"),
    ], columns=["Case", "Libellé", "Montant"]), use_container_width=True, hide_index=True)


def _show_export_fiscal(df_an, annee, props, barem):
    """Export PDF rapport fiscal."""
    st.subheader(f"📄 Export rapport fiscal {annee}")

    props_opt = {0: "Toutes les propriétés"}
    props_opt.update({p["id"]: p["nom"] for p in props.values()})
    prop_id   = st.selectbox("Propriété", list(props_opt.keys()),
                              format_func=lambda x: props_opt[x], key="export_prop")
    df        = df_an if prop_id == 0 else df_an[df_an["propriete_id"] == prop_id]
    prop_nom  = props_opt[prop_id]
    prop_data = props.get(prop_id, {}) if prop_id else {}

    ca_brut      = float(df["prix_brut"].fillna(0).sum())
    commissions  = float(df["commission"].fillna(0).sum()) if "commission" in df.columns else 0
    taxes_sejour = float(df["taxes_sejour"].fillna(0).sum()) if "taxes_sejour" in df.columns else 0
    ca_net       = ca_brut - commissions - taxes_sejour
    frais_total  = 0
    try:
        from database.frais_repo import get_frais
        frais_total = sum(float(f.get("montant",0) or 0)
                         for f in (get_frais(prop_id if prop_id else None, annee) or []))
    except: pass
    resultat = ca_net - frais_total
    nb_nuits = int(df["nuitees"].fillna(0).sum()) if "nuitees" in df.columns else 0

    col_a, col_b = st.columns(2)
    with col_a:
        nom_d    = st.text_input("Nom / Raison sociale", key="pdf_nom",
                                  value=prop_data.get("signataire","") if isinstance(prop_data,dict) else "")
        siret    = st.text_input("SIRET", key="pdf_siret",
                                  value=prop_data.get("siret","") if isinstance(prop_data,dict) else "")
        adresse  = st.text_input("Adresse", key="pdf_adresse",
                                  value=f"{prop_data.get('rue','')} {prop_data.get('code_postal','')} {prop_data.get('ville','')}".strip() if isinstance(prop_data,dict) else "")
    with col_b:
        regime   = st.selectbox("Régime", ["Micro-BIC","Réel simplifié"], key="pdf_regime")
        classe   = st.selectbox("Classement", ["Non classé","Classé / Meublé tourisme"], key="pdf_classe")
        st.metric("Nuits louées", nb_nuits)

    if st.button("📥 Générer le PDF", type="primary", use_container_width=True):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, HRFlowable
            from reportlab.lib.units import cm
            import io

            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4,
                                     rightMargin=2*cm, leftMargin=2*cm,
                                     topMargin=2*cm, bottomMargin=2*cm)
            S   = getSampleStyleSheet()
            h1  = ParagraphStyle("h1",  fontSize=18, fontName="Helvetica-Bold",
                                  spaceAfter=4, textColor=colors.HexColor("#1565C0"))
            h2  = ParagraphStyle("h2",  fontSize=13, fontName="Helvetica-Bold",
                                  spaceAfter=6, spaceBefore=10,
                                  textColor=colors.HexColor("#1565C0"))
            sub = ParagraphStyle("sub", fontSize=10, fontName="Helvetica",
                                  spaceAfter=3, textColor=colors.grey)
            ft  = ParagraphStyle("ft",  fontSize=8,  fontName="Helvetica",
                                  textColor=colors.grey, alignment=1)

            def tbl(data, widths, header_color="#1565C0"):
                t = Table(data, colWidths=widths)
                t.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0),(-1,0), colors.HexColor(header_color)),
                    ("TEXTCOLOR",     (0,0),(-1,0), colors.white),
                    ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0),(-1,-1), 9),
                    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#F0F4FF")]),
                    ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#90CAF9")),
                    ("INNERGRID",     (0,0),(-1,-1), 0.25, colors.HexColor("#E0E0E0")),
                    ("PADDING",       (0,0),(-1,-1), 5),
                ]))
                return t

            story = []
            story.append(Paragraph(f"Rapport Fiscal LMNP — {annee}", h1))
            story.append(Paragraph(nom_d or prop_nom, sub))
            if adresse: story.append(Paragraph(adresse, sub))
            if siret:   story.append(Paragraph(f"SIRET : {siret}", sub))
            story.append(HRFlowable(width="100%", thickness=1,
                                     color=colors.HexColor("#1565C0")))
            story.append(Spacer(1, 0.4*cm))

            story.append(Paragraph("Compte de résultat", h2))
            story.append(tbl([
                ["Libellé","Montant"],
                ["Recettes brutes",           f"{ca_brut:,.0f} €"],
                ["− Taxes de séjour",         f"-{taxes_sejour:,.0f} €"],
                ["− Commissions",             f"-{commissions:,.0f} €"],
                ["= Recettes nettes",         f"{ca_net:,.0f} €"],
                ["− Charges déductibles",     f"-{frais_total:,.0f} €"],
                ["= Résultat fiscal",         f"{resultat:,.0f} €"],
            ], [12*cm, 5*cm]))
            story.append(Spacer(1, 0.4*cm))

            story.append(Paragraph("Activité locative", h2))
            story.append(tbl([
                ["Indicateur","Valeur"],
                ["Nuits louées",              str(nb_nuits)],
                ["Réservations",              str(len(df))],
                ["Revenu moyen / nuit",       f"{ca_net/nb_nuits:.0f} €" if nb_nuits else "—"],
                ["Régime",                    regime],
                ["Classement",               classe],
            ], [12*cm, 5*cm]))
            story.append(Spacer(1, 0.4*cm))

            story.append(Paragraph("Cases 2042-C-PRO", h2))
            story.append(tbl([
                ["Case","Libellé","Montant"],
                ["5NA","Recettes brutes LMNP",   f"{ca_brut:,.0f} €"],
                ["5NF","Recettes nettes",          f"{ca_net:,.0f} €"],
                ["5NK","Résultat bénéficiaire",    f"{max(resultat,0):,.0f} €"],
                ["5NM","Déficit reportable",       f"{abs(min(resultat,0)):,.0f} €"],
            ], [3*cm, 9*cm, 5*cm]))
            story.append(Spacer(1, 0.8*cm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            story.append(Paragraph(
                f"Généré par Vacances-Locations Pro — {annee} | "
                "À titre indicatif — consultez votre expert-comptable", ft))

            doc.build(story)
            buf.seek(0)
            st.download_button(
                "📥 Télécharger le PDF",
                data=buf.getvalue(),
                file_name=f"fiscal_lmnp_{annee}_{prop_nom.replace(' ','_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            st.success("✅ PDF prêt !")
        except Exception as e:
            st.error(f"❌ Erreur : {e}")


def show():
    st.title("🏛️ Tableau de bord fiscal")
    st.caption("LMNP — Meublé de tourisme — Suivi micro-BIC & estimation fiscale")

    # ── Paramètres ────────────────────────────────────────────────────────
    with st.expander("⚙️ Paramètres fiscaux", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            annee = st.selectbox("Année fiscale",
                                  list(range(date.today().year, 2022, -1)), key="fisc_annee",
                                  help="2025+ : nouveaux taux LFR 2024 (50%/30%) | 2024 et avant : anciens taux (71%/50%)")
        with col2:
            classement = st.radio("Classement meublé tourisme",
                                   ["Non classé", "Classé / Gîte de France"],
                                   index=1,
                                   key="fisc_class")
        with col3:
            situation = st.selectbox("Situation familiale", [
                "Célibataire / Divorcé (1 part)",
                "Pacsé / Concubin (1 part chacun)",
                "Marié sans enfant (2 parts)",
                "Marié + 1 enfant (2,5 parts)",
                "Marié + 2 enfants (3 parts)",
                "Marié + 3 enfants (4 parts)",
                "Marié + 4 enfants (5 parts)",
                "Parent isolé + 1 enfant (2 parts)",
                "Parent isolé + 2 enfants (2,5 parts)",
                "Personnalisé",
            ], key="fisc_situation")

            _PARTS_MAP = {
                "Célibataire / Divorcé (1 part)":       1.0,
                "Pacsé / Concubin (1 part chacun)":     1.0,
                "Marié sans enfant (2 parts)":          2.0,
                "Marié + 1 enfant (2,5 parts)":         2.5,
                "Marié + 2 enfants (3 parts)":          3.0,
                "Marié + 3 enfants (4 parts)":          4.0,
                "Marié + 4 enfants (5 parts)":          5.0,
                "Parent isolé + 1 enfant (2 parts)":    2.0,
                "Parent isolé + 2 enfants (2,5 parts)": 2.5,
            }
            if situation == "Personnalisé":
                nb_parts = st.number_input("Nombre de parts",
                    min_value=0.5, max_value=8.0, value=1.0, step=0.5, key="fisc_parts_custom")
            else:
                nb_parts = _PARTS_MAP.get(situation, 1.0)
                st.caption(f"→ **{nb_parts:.1f} part(s)** fiscale(s)")
        with col4:
            autres_revenus = st.number_input("Autres revenus imposables (€)",
                                              min_value=0, value=0, step=1000,
                                              key="fisc_autres",
                                              help="Salaires, pensions, autres BIC...")

    # Charger barème depuis DB (priorité) avec fallback sur code
    _db_bareme = get_bareme(int(annee))
    b = bareme_to_dict(_db_bareme) if _db_bareme else BAREMES.get(int(annee), BAREMES[2025])
    classe = "Classé" in classement or "Gîte" in classement
    seuil_applicable = b["micro_bic_classe_seuil"] if classe else b["micro_bic_non_classe_seuil"]
    abatt_taux = b["abattement_classe"] if classe else b["abattement_non_classe"]

    # Badge récapitulatif taux applicables
    loi = b.get("loi_note","")
    st.caption(f"📋 **{loi}** — Abattement applicable : **{abatt_taux*100:.0f}%** | Seuil : **{seuil_applicable:,.0f} €**")

    # ── Chargement données ────────────────────────────────────────────────
    df_all = load_reservations()
    props  = {
        p["id"]: p for p in fetch_all()
        if not p.get("mot_de_passe") or is_unlocked(p["id"])
    }

    if df_all.empty:
        st.warning("Aucune réservation disponible.")
        return

    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)
    df_an = df_all[df_all["annee"] == annee] if "annee" in df_all.columns else df_all
    df_an = df_an[df_an["plateforme"] != "Fermeture"].copy()

    # ── Filtre plateforme global ──────────────────────────────────────────
    plateformes_dispo = sorted(df_an["plateforme"].dropna().unique().tolist())
    plat_fisc = st.multiselect(
        "🔀 Filtrer par plateforme",
        options=plateformes_dispo,
        default=[],
        key="fisc_plat",
        placeholder="Toutes les plateformes"
    )
    if plat_fisc:
        df_an = df_an[df_an["plateforme"].isin(plat_fisc)]

    ca_total = float(df_an["prix_brut"].fillna(0).sum()) if "prix_brut" in df_an.columns else 0.0
    # Recettes = CA brut total (ce que le locataire a payé)
    # Pour LMNP le CA déclaré = recettes brutes encaissées

    # ── Onglets ───────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Seuils & Alertes",
        "💶 Estimation fiscale",
        "⚖️ Micro-BIC vs Réel",
        "🧾 Cotisations sociales",
        "📅 Projection annuelle",
        "📋 Liasse 2033",
        "📄 Export PDF",
    ])

    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        st.subheader(f"📊 Seuils micro-BIC {annee}")

        # CA par propriété
        ca_par_prop = {}
        for pid, prop in props.items():
            df_p = df_an[df_an["propriete_id"] == pid]
            ca_par_prop[pid] = float(df_p["prix_brut"].fillna(0).sum()) if not df_p.empty else 0.0

        # Jauges
        cols = st.columns(max(1, len(props)))
        for i, (pid, prop) in enumerate(props.items()):
            ca = ca_par_prop.get(pid, 0)
            pct = ca / seuil_applicable if seuil_applicable > 0 else 0
            couleur = _couleur_seuil(pct)
            with cols[i % len(cols)]:
                st.plotly_chart(
                    _jauge(prop["nom"], ca, seuil_applicable),
                    use_container_width=True, key=f"jauge_{pid}"
                )
                reste = seuil_applicable - ca
                if reste > 0:
                    st.markdown(
                        f"<div style='background:{couleur}22;border-left:4px solid {couleur};"
                        f"padding:8px;border-radius:4px;font-size:13px'>"
                        f"<b>{pct*100:.1f}%</b> du seuil utilisé<br>"
                        f"Reste disponible : <b>{reste:,.0f} €</b></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.error(f"⚠️ Seuil dépassé de {abs(reste):,.0f} € — passage au réel obligatoire !")

        st.divider()

        # Tableau récap seuils
        st.subheader("📋 Récapitulatif des seuils")
        seuils_data = {
            "Régime": [
                "Micro-BIC non classé",
                "Micro-BIC classé / Gîte ⭐",
                "TVA (franchise en base)",
                "SSI obligatoire",
            ],
            "Seuil": [
                f"{b['micro_bic_non_classe_seuil']:,.0f} €",
                f"{b['micro_bic_classe_seuil']:,.0f} €",
                "91 900 €",
                "23 000 €",
            ],
            "Abattement": [
                f"{b['abattement_non_classe']*100:.0f}%",
                f"{b['abattement_classe']*100:.0f}%",
                "N/A", "N/A",
            ],
            "Votre CA": [f"{ca_total:,.0f} €"] * 4,
            "Statut": [
                "✅ OK" if ca_total < b["micro_bic_non_classe_seuil"] else "⛔ Dépassé",
                "✅ OK" if ca_total < b["micro_bic_classe_seuil"] else "⛔ Dépassé",
                "✅ OK" if ca_total < 91900 else "⚠️ Vérifier",
                "✅ OK" if ca_total < 23000 else "⚠️ Vérifier",
            ]
        }

        # Badge loi applicable
        loi_note = b.get("loi_note", "")
        if "nouveaux" in loi_note:
            st.warning(f"⚠️ **{loi_note}** — Abattements réduits : classé 50% (au lieu de 71%), non classé 30% (au lieu de 50%). Seuils également abaissés.")
        else:
            st.info(f"ℹ️ **{loi_note}** — Anciens taux en vigueur.")

        st.dataframe(pd.DataFrame(seuils_data), use_container_width=True, hide_index=True)

        # Note TVA
        st.info("""
**💡 TVA — Franchise en base :** Tant que vos recettes restent sous 91 900 €, vous n'êtes pas soumis à la TVA
(régime LMNP). Au-delà, TVA collectée à 10% sur les prestations para-hôtelières (ménage, petit-déjeuner...).

**💡 Seuil SSI :** Si vos recettes de location meublée dépassent 23 000 € ET représentent plus de 50%
de vos revenus du foyer, vous basculez en LMP (Loueur Meublé Professionnel) avec cotisations SSI.
        """)

    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        st.subheader(f"💶 Estimation impôt {annee}")
        st.caption("Simulation indicative — consultez un expert-comptable pour votre situation réelle.")

        # ── Filtre propriété ──────────────────────────────────────────────
        props_opt_t2 = {0: "Toutes les propriétés"}
        props_opt_t2.update({p["id"]: p["nom"] for p in props.values()})
        prop_id_t2 = st.selectbox(
            "🏠 Propriété (foyer fiscal)",
            options=list(props_opt_t2.keys()),
            format_func=lambda x: props_opt_t2[x],
            key="prop_t2",
            help="Chaque bien est un foyer fiscal distinct"
        )
        df_t2 = df_an if prop_id_t2 == 0 else df_an[df_an["propriete_id"] == prop_id_t2]
        ca_t2 = float(df_t2["prix_brut"].fillna(0).sum()) if "prix_brut" in df_t2.columns else 0.0
        st.caption(f"CA {annee} — **{props_opt_t2[prop_id_t2]}** : **{ca_t2:,.0f} €**")
        st.divider()

        abattement, revenu_bic = _micro_bic(ca_t2, classe, b)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Calcul Micro-BIC**")
            st.markdown(f"""
| Étape | Montant |
|-------|---------|
| CA Brut (recettes) | **{ca_t2:,.0f} €** |
| Abattement {abatt_taux*100:.0f}% | — {abattement:,.0f} € |
| **Revenu BIC net** | **{revenu_bic:,.0f} €** |
| Autres revenus | + {autres_revenus:,.0f} € |
| **Revenu total imposable** | **{revenu_bic + autres_revenus:,.0f} €** |
""")

        revenu_total = revenu_bic + autres_revenus
        ir_brut = _impot_tranche(revenu_total, b)
        ir_par_part = _impot_tranche(revenu_total / nb_parts, b) * nb_parts
        csg = ca_t2 * b["csg_crds"]   # CSG/CRDS sur revenus patrimoine

        with col2:
            st.markdown("**Estimation fiscale**")
            st.markdown(f"""
| Poste | Montant estimé |
|-------|----------------|
| IR (1 part) | {ir_brut:,.0f} € |
| IR ({nb_parts:.1f} parts) | **{ir_par_part:,.0f} €** |
| CSG/CRDS (17,2%) | {csg:,.0f} € |
| **Total prélèvements** | **{ir_par_part + csg:,.0f} €** |
| Taux effectif | {((ir_par_part + csg)/ca_t2*100):.1f}% du CA |
""")

        st.divider()

        # Répartition visuelle
        if ca_t2 > 0:
            charges = ir_par_part + csg
            net_apres_impot = ca_t2 - charges
            labels = ["Net après impôt", "IR estimé", "CSG/CRDS"]
            values = [max(0, net_apres_impot), ir_par_part, csg]
            colors = ["#2E7D32", "#1565C0", "#E65100"]
            fig = go.Figure(go.Pie(
                labels=labels, values=values,
                hole=0.5,
                marker_colors=colors,
                textinfo="label+percent",
            ))
            fig.update_layout(height=280, margin=dict(t=10, b=10),
                              showlegend=True,
                              annotations=[{"text": f"{net_apres_impot:,.0f}€<br>net", "showarrow": False, "font_size": 13}])
            st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("⚖️ Comparaison Micro-BIC vs Régime Réel")

        # ── Filtre propriété ──────────────────────────────────────────────
        props_options = {0: "Toutes les propriétés"}
        props_options.update({p["id"]: p["nom"] for p in props.values()})
        prop_id_reel = st.selectbox(
            "🏠 Propriété (foyer fiscal)",
            options=list(props_options.keys()),
            format_func=lambda x: props_options[x],
            key="reel_prop",
            help="Chaque bien est un foyer fiscal distinct — sélectionnez la propriété à analyser"
        )
        if prop_id_reel == 0:
            df_reel_prop = df_an
            prop_label_reel = "Toutes les propriétés"
        else:
            df_reel_prop = df_an[df_an["propriete_id"] == prop_id_reel]
            prop_label_reel = props_options[prop_id_reel]

        ca_reel_prop = float(df_reel_prop["prix_brut"].fillna(0).sum()) if "prix_brut" in df_reel_prop.columns else 0.0
        st.caption(f"CA {annee} — **{prop_label_reel}** : **{ca_reel_prop:,.0f} €**")

        st.divider()
        # ── Chargement frais depuis Supabase ─────────────────────────────
        frais_list = get_frais(prop_id_reel, annee) if prop_id_reel != 0 else []

        # ── Tabs internes : Saisie / Récap ────────────────────────────────
        sub_saisie, sub_recap = st.tabs(["📝 Saisie des frais", "📋 Récapitulatif"])

        with sub_saisie:
            if prop_id_reel == 0:
                st.info("Sélectionnez une propriété pour saisir les frais déductibles.")
            else:
                st.markdown(f"**Frais déductibles — {prop_label_reel} — {annee}**")

                # Tableau éditable des frais existants
                if frais_list:
                    st.markdown("##### Frais enregistrés")
                    df_frais = pd.DataFrame(frais_list)

                    df_frais["rubrique_ir"] = df_frais["categorie"].map(
                        lambda c: IR_RUBRIQUES.get(c, "—")
                    )
                    edited_frais = st.data_editor(
                        df_frais[["id", "categorie", "libelle", "montant", "rubrique_ir"]],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "id":         st.column_config.Column("ID", disabled=True, width="small"),
                            "categorie":  st.column_config.SelectboxColumn(
                                "Catégorie", options=CATEGORIES, required=True
                            ),
                            "libelle":    st.column_config.TextColumn("Libellé", required=True),
                            "montant":    st.column_config.NumberColumn(
                                "Montant (€)", min_value=0, format="%.2f €"
                            ),
                            "rubrique_ir": st.column_config.TextColumn(
                                "📋 Rubrique déclaration IR", disabled=True, width="large"
                            ),
                        },
                        key="frais_editor"
                    )

                    col_save, col_del = st.columns([2, 1])
                    with col_save:
                        if st.button("💾 Enregistrer les modifications", type="primary", key="save_frais_edit"):
                            ok = 0
                            for _, row in edited_frais.iterrows():
                                if save_frais({
                                    "id": int(row["id"]),
                                    "propriete_id": prop_id_reel,
                                    "annee": annee,
                                    "categorie": row["categorie"],
                                    "libelle":   row["libelle"],
                                    "montant":   float(row["montant"]),
                                }):
                                    ok += 1
                            st.success(f"✅ {ok} frais mis à jour !")
                            st.rerun()

                st.divider()

                # ── Upload justificatif rapide en face de chaque frais ────────
                st.markdown("##### 📎 Attacher un justificatif")
                col_jf, col_ju = st.columns([3, 2])
                with col_jf:
                    frais_opts_s = {f["id"]: f"{f['categorie']} — {f['libelle']} ({f['montant']:.0f} €)"
                                    for f in frais_list}
                    justif_frais_id = st.selectbox(
                        "Dépense concernée",
                        list(frais_opts_s.keys()),
                        format_func=lambda x: frais_opts_s[x],
                        key="justif_frais_quick"
                    )
                with col_ju:
                    justif_file = st.file_uploader(
                        "📸 Photo ou scan (PDF, JPG, PNG)",
                        type=["pdf","jpg","jpeg","png","heic","webp"],
                        key="justif_upload_quick",
                        label_visibility="visible"
                    )
                if justif_file:
                    if st.button("📎 Attacher ce justificatif", type="primary", key="btn_justif_quick"):
                        result = upload_justificatif(
                            frais_id=justif_frais_id,
                            propriete_id=prop_id_reel,
                            annee=annee,
                            nom_fichier=justif_file.name,
                            file_bytes=justif_file.read(),
                            mime_type=justif_file.type or "application/octet-stream",
                        )
                        if result:
                            st.success(f"✅ Justificatif « {justif_file.name} » enregistré !")
                            st.rerun()
                        else:
                            st.error("❌ Erreur — vérifiez que le bucket 'justificatifs' est créé dans Supabase Storage.")

                st.divider()

                # Formulaire ajout nouveau frais
                st.markdown("##### ➕ Ajouter un frais")
                with st.form("form_add_frais", clear_on_submit=True):
                    fa_col1, fa_col2, fa_col3 = st.columns([2, 3, 2])
                    with fa_col1:
                        fa_cat = st.selectbox("Catégorie", CATEGORIES, key="fa_cat")
                    with fa_col2:
                        fa_lib = st.text_input("Libellé", placeholder="Ex: Assurance PNO Generali", key="fa_lib")
                    with fa_col3:
                        fa_mnt = st.number_input("Montant (€)", min_value=0.0, step=10.0, key="fa_mnt")
                    submitted_frais = st.form_submit_button("➕ Ajouter", type="primary", use_container_width=True)

                if submitted_frais:
                    if fa_lib and fa_mnt > 0:
                        if save_frais({
                            "propriete_id": prop_id_reel,
                            "annee":        annee,
                            "categorie":    fa_cat,
                            "libelle":      fa_lib,
                            "montant":      float(fa_mnt),
                        }):
                            st.success(f"✅ Frais ajouté : {fa_lib} — {fa_mnt:.0f} €")
                            st.rerun()
                    else:
                        st.error("Libellé et montant sont obligatoires.")

                # Suppression
                if frais_list:
                    with st.expander("🗑️ Supprimer un frais"):
                        del_options = {f["id"]: f"{f['categorie']} — {f['libelle']} ({f['montant']:.0f} €)"
                                       for f in frais_list}
                        del_id = st.selectbox("Frais à supprimer", list(del_options.keys()),
                                               format_func=lambda x: del_options[x], key="del_frais")
                        if st.button("🗑️ Supprimer", type="secondary", key="btn_del_frais"):
                            delete_frais(del_id)
                            st.success("Supprimé !")
                            st.rerun()

        with sub_recap:
            if frais_list:
                st.markdown(f"**Récapitulatif par catégorie — {prop_label_reel} — {annee}**")
                df_recap_frais = pd.DataFrame(frais_list)
                recap_cat = df_recap_frais.groupby("categorie")["montant"].agg(
                    Total="sum", Nb="count"
                ).reset_index().sort_values("Total", ascending=False)
                recap_cat["Rubrique IR"] = recap_cat["categorie"].map(
                    lambda c: IR_RUBRIQUES.get(c, "—")
                )
                recap_cat["Total"] = recap_cat["montant_sum"] if "montant_sum" in recap_cat.columns else recap_cat["Total"]
                recap_cat["Total"] = recap_cat["Total"].map("{:,.2f} €".format)
                st.dataframe(recap_cat.rename(columns={
                    "categorie": "Catégorie", "Total": "Total €", "Nb": "Nb"
                })[["Catégorie", "Nb", "Total €", "Rubrique IR"]],
                use_container_width=True, hide_index=True)

                total_affiche = sum(f["montant"] for f in frais_list)
                st.metric("💶 Total charges déductibles", f"{total_affiche:,.2f} €")

                st.divider()
                st.markdown("#### 📑 Récapitulatif par ligne de déclaration 2033-B")
                st.caption("Montants à reporter sur votre formulaire 2033-B (régime réel simplifié LMNP)")

                # Regrouper par ligne IR
                from collections import defaultdict
                lignes = defaultdict(float)
                for f in frais_list:
                    rubrique = IR_RUBRIQUES.get(f["categorie"], "Ligne 258 — Autres charges")
                    # Extraire le numéro de ligne pour le tri
                    lignes[rubrique] += float(f["montant"])

                # Construire le tableau trié par numéro de ligne
                lignes_rows = []
                for rubrique, total in sorted(lignes.items(), key=lambda x: x[0]):
                    # Extraire numéro de ligne (ex: "2033-B Ligne 236" → 236)
                    try:
                        num = int(rubrique.split("Ligne ")[1].split(" ")[0].split("/")[0].strip())
                    except:
                        num = 999
                    lignes_rows.append({
                        "_sort": num,
                        "Ligne formulaire": rubrique.split(" — ")[0],
                        "Intitulé": rubrique.split(" — ")[1] if " — " in rubrique else rubrique,
                        "Montant à reporter": total,
                    })

                lignes_rows.sort(key=lambda x: x["_sort"])
                df_lignes = pd.DataFrame(lignes_rows).drop(columns=["_sort"])
                df_lignes["Montant à reporter"] = df_lignes["Montant à reporter"].map("{:,.2f} €".format)

                # Ligne total
                total_row_ir = pd.DataFrame([{
                    "Ligne formulaire": "**TOTAL**",
                    "Intitulé": "Total charges déductibles",
                    "Montant à reporter": f"{total_affiche:,.2f} €",
                }])
                df_lignes = pd.concat([df_lignes, total_row_ir], ignore_index=True)

                st.dataframe(df_lignes, use_container_width=True, hide_index=True)
                st.info(
                    "💡 **Ligne 250** = amortissements annuels (tableau d'amortissement obligatoire) · "
                    "**Ligne 236** = charges d'exploitation courantes · "
                    "**Ligne 240** = impôts et taxes (taxe foncière, CFE) · "
                    "**Ligne 256** = intérêts d'emprunt"
                )
            else:
                st.info("Aucun frais enregistré pour cette propriété.")

            # ── Justificatifs ─────────────────────────────────────────────
            st.divider()
            st.markdown("#### 📎 Justificatifs de dépenses")
            st.caption("Scannez ou photographiez vos justificatifs et attachez-les à chaque dépense.")

            if prop_id_reel == 0:
                st.info("Sélectionnez une propriété pour gérer les justificatifs.")
            elif not frais_list:
                st.info("Ajoutez des frais dans l'onglet Saisie pour pouvoir attacher des justificatifs.")
            else:
                with st.expander("📤 Ajouter un justificatif", expanded=True):
                    col_f, col_u = st.columns([3, 2])
                    with col_f:
                        frais_opts = {f["id"]: f"{f['categorie']} — {f['libelle']} ({f['montant']:.0f} €)"
                                      for f in frais_list}
                        frais_sel = st.selectbox("Dépense concernée",
                                                  list(frais_opts.keys()),
                                                  format_func=lambda x: frais_opts[x],
                                                  key="justif_frais_sel")
                    with col_u:
                        uploaded = st.file_uploader(
                            "Fichier (PDF, JPG, PNG)",
                            type=["pdf","jpg","jpeg","png","heic","webp"],
                            key="justif_upload"
                        )
                    if uploaded:
                        if st.button("📎 Attacher le justificatif", type="primary", key="btn_attach_justif"):
                            result = upload_justificatif(
                                frais_id=frais_sel,
                                propriete_id=prop_id_reel,
                                annee=annee,
                                nom_fichier=uploaded.name,
                                file_bytes=uploaded.read(),
                                mime_type=uploaded.type or "application/octet-stream",
                            )
                            if result:
                                st.success(f"✅ « {uploaded.name} » attaché !")
                                st.rerun()
                            else:
                                st.error("Erreur upload — vérifiez le bucket 'justificatifs' dans Supabase Storage.")

                st.markdown("##### 📋 Justificatifs enregistrés")
                from database.justificatifs_repo import get_justificatifs_prop
                justifs_all = get_justificatifs_prop(prop_id_reel, annee)

                if not justifs_all:
                    st.caption("Aucun justificatif pour cette propriété / année.")
                else:
                    for j in justifs_all:
                        frais_info = j.get("frais_deductibles") or {}
                        frais_label = (f"{frais_info.get('categorie','?')} — "
                                       f"{frais_info.get('libelle','?')} "
                                       f"({float(frais_info.get('montant',0)):.0f} €)"
                                       if frais_info else f"Frais #{j.get('frais_id','?')}")
                        taille = j.get("taille_bytes", 0) or 0
                        taille_str = f"{taille/1024:.0f} Ko" if taille < 1024*1024 else f"{taille/1024/1024:.1f} Mo"
                        col1, col2, col3 = st.columns([4, 2, 1])
                        with col1:
                            st.markdown(
                                f"📄 **{j['nom_fichier']}** — {frais_label}<br>"
                                f"<small style='color:#888'>{taille_str} · {str(j.get('created_at',''))[:10]}</small>",
                                unsafe_allow_html=True
                            )
                        with col2:
                            url = get_download_url(j["storage_path"])
                            if url:
                                st.link_button("⬇️ Télécharger", url, use_container_width=True)
                        with col3:
                            if st.button("🗑️", key=f"del_justif_{j['id']}", help="Supprimer"):
                                delete_justificatif(j["id"], j["storage_path"])
                                st.rerun()

        # Total pour le calcul
        total_charges_reelles = sum(f["montant"] for f in frais_list) if frais_list else 0.0
        revenu_reel = max(0, ca_reel_prop - total_charges_reelles)
        ir_reel     = _impot_tranche(revenu_reel + autres_revenus, b) * nb_parts if nb_parts >= 1 else _impot_tranche(revenu_reel + autres_revenus, b)
        csg_reel    = revenu_reel * b["csg_crds"]

        abattement_micro, revenu_micro = _micro_bic(ca_reel_prop, classe, b)
        ir_micro = _impot_tranche((revenu_micro + autres_revenus) / nb_parts, b) * nb_parts
        csg_micro = ca_reel_prop * b["csg_crds"]

        # ── Tableau de comparaison ────────────────────────────────────────
        st.divider()
        st.subheader("📊 Résultat de la comparaison")
        total_reel  = ir_reel + csg_reel
        total_micro = ir_micro + csg_micro
        economie    = total_micro - total_reel

        col_t, col_g = st.columns([3, 2])
        with col_t:
            st.markdown(f"""
|  | Micro-BIC | Réel simplifié |
|--|-----------|----------------|
| **Revenu brut (CA)** | **{ca_reel_prop:,.0f} €** | **{ca_reel_prop:,.0f} €** |
| Abattement / Charges déduites | {abattement_micro:,.0f} € ({abatt_taux*100:.0f}%) | {total_charges_reelles:,.0f} € |
| **Revenu imposable** | **{revenu_micro:,.0f} €** | **{revenu_reel:,.0f} €** |
| IR estimé | {ir_micro:,.0f} € | {ir_reel:,.0f} € |
| CSG/CRDS | {csg_micro:,.0f} € | {csg_reel:,.0f} € |
| **Total prélèvements** | **{total_micro:,.0f} €** | **{total_reel:,.0f} €** |
| **Net après impôt** | **{ca_reel_prop - total_micro:,.0f} €** | **{ca_reel_prop - total_reel:,.0f} €** |
""")
            if economie > 0:
                st.success(f"✅ Le **régime réel** vous ferait économiser **{economie:,.0f} €** cette année.")
            elif economie < 0:
                st.info(f"💡 Le **micro-BIC** est plus avantageux de **{abs(economie):,.0f} €** cette année.")
            else:
                st.info("Les deux régimes sont équivalents.")

        with col_g:
            fig = go.Figure()
            for regime, ir, csg_v in [("Micro-BIC", ir_micro, csg_micro), ("Réel simplifié", ir_reel, csg_reel)]:
                fig.add_trace(go.Bar(name="IR", x=[regime], y=[ir], marker_color="#1565C0"))
                fig.add_trace(go.Bar(name="CSG/CRDS", x=[regime], y=[csg_v], marker_color="#E65100"))
            fig.update_layout(barmode="stack", height=280,
                              margin=dict(t=10,b=10), showlegend=True,
                              legend=dict(orientation="h", y=1.1))
            st.plotly_chart(fig, use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    # ════════════════════════════════════════════════════════════════════════
    with tab4:
        st.subheader("🧾 Cotisations sociales & prélèvements")
        st.caption("Simulation selon votre statut LMNP/LMP et vos recettes.")

        # ── Filtre propriété ──────────────────────────────────────────────
        props_opt_t4 = {0: "Toutes les propriétés"}
        props_opt_t4.update({p["id"]: p["nom"] for p in props.values()})
        prop_id_t4 = st.selectbox(
            "🏠 Propriété (foyer fiscal)",
            options=list(props_opt_t4.keys()),
            format_func=lambda x: props_opt_t4[x],
            key="prop_t4",
            help="Chaque bien est un foyer fiscal distinct"
        )
        df_t4 = df_an if prop_id_t4 == 0 else df_an[df_an["propriete_id"] == prop_id_t4]
        ca_t4 = float(df_t4["prix_brut"].fillna(0).sum()) if "prix_brut" in df_t4.columns else 0.0
        st.caption(f"CA {annee} — **{props_opt_t4[prop_id_t4]}** : **{ca_t4:,.0f} €**")
        st.divider()

        col1, col2 = st.columns(2)
        with col1:
            statut = st.radio("Statut locatif",
                ["LMNP (Loueur Meublé Non Professionnel)",
                 "LMP (Loueur Meublé Professionnel)"],
                key="fisc_statut",
                help="LMP si recettes > 23 000€ ET > 50% revenus du foyer"
            )
            regime_social = st.radio("Régime social",
                ["Pas de cotisations SSI (LMNP pur)",
                 "Micro-entrepreneur (URSSAF)",
                 "TNS / Régime réel SSI"],
                key="fisc_regime_soc"
            )

        with col2:
            st.markdown("**Récapitulatif recettes**")
            st.metric("CA Brut total", f"{ca_t4:,.0f} €")
            abatt_m, rev_bic_m = _micro_bic(ca_t4, classe, b)
            st.metric(f"Revenu BIC net (abatt. {abatt_taux*100:.0f}%)", f"{rev_bic_m:,.0f} €")
            is_lmp = ca_t4 > b["seuil_cotisations"]
            if is_lmp:
                st.warning(f"⚠️ Recettes > {b['seuil_cotisations']:,} € → Vérifiez si LMP s'applique")
            else:
                st.success(f"✅ Recettes < {b['seuil_cotisations']:,} € → Pas de SSI obligatoire")

        st.divider()

        # ── Calcul cotisations selon régime ──────────────────────────────
        st.subheader("📋 Détail des cotisations")

        if "Pas de cotisations" in regime_social:
            # LMNP classique : CSG/CRDS sur revenus du patrimoine uniquement
            csg_patrim = rev_bic_m * 0.172
            rows_cot = [
                ("CSG (9,9%)",                   rev_bic_m * 0.099),
                ("CRDS (0,5%)",                  rev_bic_m * 0.005),
                ("Prélèvement solidarité (7,5%)", rev_bic_m * 0.075),
                ("Prélèvement libératoire",       0.0),
            ]
            total_cot = csg_patrim
            st.info("**LMNP — Prélèvements sociaux sur revenus du patrimoine (17,2%)** — Pas de cotisations SSI obligatoires.")

        elif "Micro-entrepreneur" in regime_social:
            # Taux micro-entrepreneur meublé tourisme classé : 6% (2024)
            taux_me = 0.06 if classe else 0.06
            cot_me  = ca_t4 * taux_me
            csg_me  = ca_t4 * 0.172
            rows_cot = [
                ("Cotisations sociales micro-entrepreneur (6%)", cot_me),
                ("CSG/CRDS (inclus dans taux)",                  0.0),
                ("CFE (Cotisation Foncière Entreprises)",         "Variable"),
            ]
            total_cot = cot_me
            st.info("**Micro-entrepreneur meublé de tourisme classé** Taux global : 6% sur CA — inclut retraite, maladie, famille.")

        else:
            # TNS / SSI régime réel
            taux_ssi = b["cotisations_ssi_taux"]
            base_ssi = rev_bic_m
            cot_maladie  = base_ssi * 0.013  # maladie
            cot_retraite = base_ssi * 0.178  # retraite base + compl
            cot_famille  = base_ssi * 0.031  # allocations familiales
            cot_invalid  = base_ssi * 0.013  # invalidité/décès
            cot_csg      = base_ssi * 0.097  # CSG déductible
            cot_crds     = base_ssi * 0.005  # CRDS
            total_cot    = base_ssi * taux_ssi
            rows_cot = [
                ("Maladie (1,3%)",              cot_maladie),
                ("Retraite de base + compl. (17,8%)", cot_retraite),
                ("Allocations familiales (3,1%)", cot_famille),
                ("Invalidité/Décès (1,3%)",     cot_invalid),
                ("CSG déductible (9,7%)",        cot_csg),
                ("CRDS (0,5%)",                  cot_crds),
            ]
            st.info(f"**Régime TNS/SSI — Base : revenu BIC net ({rev_bic_m:,.0f} €)**")

        # Tableau cotisations
        rows_display = []
        total_num = 0.0
        for poste, montant in rows_cot:
            if isinstance(montant, float):
                rows_display.append({"Poste": poste, "Montant": f"{montant:,.0f} €"})
                total_num += montant
            else:
                rows_display.append({"Poste": poste, "Montant": str(montant)})
        rows_display.append({"Poste": "**TOTAL COTISATIONS**", "Montant": f"**{total_num:,.0f} €**"})
        st.dataframe(pd.DataFrame(rows_display), use_container_width=True, hide_index=True)

        st.divider()

        # ── Synthèse globale prélèvements ─────────────────────────────────
        st.subheader("📊 Synthèse globale des prélèvements")

        abatt_m2, rev_bic_m2 = _micro_bic(ca_t4, classe, b)
        ir_final = _impot_tranche((rev_bic_m2 + autres_revenus) / nb_parts, b) * nb_parts
        csg_ir   = ca_total * b["csg_crds"] if "Pas de cotisations" in regime_social else 0

        total_prelevements = ir_final + csg_ir + total_num
        net_final = ca_t4 - total_prelevements

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💶 CA Brut",             f"{ca_t4:,.0f} €")
        c2.metric("🏛️ IR estimé",           f"{ir_final:,.0f} €")
        c3.metric("🧾 Cotisations sociales", f"{total_num:,.0f} €")
        c4.metric("💵 Net après tout",       f"{net_final:,.0f} €",
                  delta=f"{net_final/ca_t4*100:.1f}% du CA" if ca_t4 > 0 else "")

        if ca_t4 > 0:
            fig = go.Figure(go.Waterfall(
                name="", orientation="v",
                measure=["absolute", "relative", "relative", "relative", "total"],
                x=["CA Brut", f"Abattement {abatt_taux*100:.0f}%",
                   "IR estimé", "Cotisations", "Net final"],
                y=[ca_t4, -abatt_m2, -ir_final, -total_num, 0],
                connector={"line": {"color": "rgb(63, 63, 63)"}},
                increasing={"marker": {"color": "#2E7D32"}},
                decreasing={"marker": {"color": "#C62828"}},
                totals={"marker": {"color": "#1565C0"}},
            ))
            fig.update_layout(height=320, margin=dict(t=10, b=10),
                              showlegend=False, yaxis_title="€")
            st.plotly_chart(fig, use_container_width=True)

    with tab5:
        st.subheader(f"📅 Projection annuelle {annee}")

        df_mois = df_an.copy()
        if not df_mois.empty and "date_arrivee" in df_mois.columns:
            df_mois["mois"] = pd.to_datetime(df_mois["date_arrivee"]).dt.month
            ca_par_mois = df_mois.groupby("mois")["prix_brut"].sum().reindex(range(1,13), fill_value=0)
            ca_cumul    = ca_par_mois.cumsum()

            MOIS_FR = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=MOIS_FR, y=ca_par_mois.values,
                name="CA mensuel", marker_color="#90CAF9"
            ))
            fig.add_trace(go.Scatter(
                x=MOIS_FR, y=ca_cumul.values,
                name="Cumul annuel", mode="lines+markers",
                line=dict(color="#1565C0", width=2),
                yaxis="y2"
            ))
            # Lignes seuils
            for seuil_v, label_s, color_s in [
                (23000,  "Seuil SSI", "#FF9800"),
                (77700,  "Seuil non classé", "#F44336"),
                (188700, "Seuil classé", "#9C27B0"),
            ]:
                fig.add_hline(y=seuil_v, line_dash="dot", line_color=color_s,
                              annotation_text=label_s, annotation_position="right",
                              yref="y2")

            fig.update_layout(
                height=380,
                margin=dict(t=10, b=30),
                legend=dict(orientation="h", y=1.05),
                yaxis=dict(title="CA mensuel (€)"),
                yaxis2=dict(title="Cumul (€)", overlaying="y", side="right"),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Projection fin d'année
            mois_en_cours = date.today().month if annee == date.today().year else 12
            if mois_en_cours < 12 and ca_total > 0:
                ca_moyen_mensuel = ca_total / mois_en_cours
                ca_projete = ca_moyen_mensuel * 12
                st.info(
                    f"📈 **Projection fin {annee}** (base CA moyen mensuel {ca_moyen_mensuel:,.0f} €) : "
                    f"**{ca_projete:,.0f} €**  "
                    + ("⛔ Dépassement seuil prévu !" if ca_projete > seuil_applicable
                       else f"— reste {seuil_applicable - ca_projete:,.0f} € de marge.")
                )
        else:
            st.info("Données mensuelles insuffisantes pour la projection.")

    # ── Disclaimer ───────────────────────────────────────────────────────
    with tab6:
        _show_liasse_2033(df_an, annee, props, b)

    with tab7:
        _show_export_fiscal(df_an, annee, props, b)

    st.caption(
        "⚠️ Ce tableau de bord est un outil d'aide à la décision. "
        "Les calculs sont indicatifs et ne remplacent pas l'avis d'un expert-comptable. "
        f"Barèmes {annee} — sources DGFiP / BOFIP."
    )
