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


# ─────────────────────────────────────────────────────────────────────────────
# GENERATION PDF BULLETIN
# ─────────────────────────────────────────────────────────────────────────────

def _generer_bulletin(employe, pointages, prop_nom, mois, annee):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    import io

    NAVY = colors.HexColor("#0B1F3A")
    BLUE = colors.HexColor("#1565C0")
    GREY = colors.HexColor("#6B7280")
    LIGHT= colors.HexColor("#F4F7FF")
    WHITE= colors.white
    GOLD = colors.HexColor("#F0B429")

    mois_noms = ["Janvier","Fevrier","Mars","Avril","Mai","Juin",
                 "Juillet","Aout","Septembre","Octobre","Novembre","Decembre"]

    def s(size, color=NAVY, bold=False, align=0):
        return ParagraphStyle("_", fontSize=size, textColor=color,
                              fontName="Helvetica-Bold" if bold else "Helvetica",
                              alignment=align, leading=size*1.4, spaceAfter=4)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    story = []

    # En-tête
    header = Table([[Paragraph(
        f"RECAPITULATIF DES HEURES<br/>"
        f"<font size='12'>{mois_noms[mois-1]} {annee}</font>",
        s(16, WHITE, bold=True, align=1)
    )]], colWidths=[17*cm])
    header.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), NAVY),
        ("TOPPADDING",(0,0),(-1,-1),14),("BOTTOMPADDING",(0,0),(-1,-1),14),
    ]))
    story.append(header)

    bande = Table([[""]], colWidths=[17*cm], rowHeights=[4])
    bande.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),GOLD)]))
    story.append(bande)
    story.append(Spacer(1,0.4*cm))

    # Infos employé / employeur
    nom_emp  = f"{employe.get('prenom','')} {employe.get('nom','')}".strip()
    taux     = float(employe.get("taux_horaire",12) or 12)
    contrat  = employe.get("contrat","CDI") or "CDI"

    parties = [[
        Paragraph(f"<b>EMPLOYEUR</b><br/>{prop_nom}", s(10, NAVY)),
        Paragraph(f"<b>EMPLOYE</b><br/>{nom_emp}<br/>"
                  f"Contrat : {contrat}<br/>"
                  f"Taux horaire : {taux:.2f} EUR", s(10, NAVY)),
    ]]
    pt = Table(parties, colWidths=[8.5*cm,8.5*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0), LIGHT),("BACKGROUND",(1,0),(1,0), LIGHT),
        ("TOPPADDING",(0,0),(-1,-1),10),("BOTTOMPADDING",(0,0),(-1,-1),10),
        ("LEFTPADDING",(0,0),(-1,-1),10),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
    ]))
    story.append(pt)
    story.append(Spacer(1,0.5*cm))

    # Détail des pointages
    story.append(Paragraph("DETAIL DES INTERVENTIONS", s(10, NAVY, bold=True)))
    story.append(Spacer(1,0.2*cm))

    total_minutes = 0
    lignes = [[
        Paragraph("<b>Date</b>", s(9, WHITE, bold=True)),
        Paragraph("<b>Arrivee</b>", s(9, WHITE, bold=True, align=1)),
        Paragraph("<b>Depart</b>", s(9, WHITE, bold=True, align=1)),
        Paragraph("<b>Duree</b>", s(9, WHITE, bold=True, align=1)),
        Paragraph("<b>Statut</b>", s(9, WHITE, bold=True, align=1)),
        Paragraph("<b>Notes</b>", s(9, WHITE, bold=True)),
    ]]

    for p in pointages:
        duree_min = p.get("duree_minutes") or 0
        total_minutes += duree_min
        h, m = divmod(duree_min, 60)
        duree_str = f"{h}h{m:02d}" if duree_min else "—"
        statut = "Valide" if p.get("valide") else "En attente"
        lignes.append([
            Paragraph(str(p.get("date_menage",""))[:10], s(9, NAVY)),
            Paragraph(str(p.get("heure_arrivee",""))[:5] or "—", s(9, GREY, align=1)),
            Paragraph(str(p.get("heure_depart",""))[:5] or "—", s(9, GREY, align=1)),
            Paragraph(duree_str, s(9, NAVY, bold=True, align=1)),
            Paragraph(statut, s(9, GREY, align=1)),
            Paragraph(str(p.get("notes","") or ""), s(8, GREY)),
        ])

    dt = Table(lignes, colWidths=[2.5*cm,2*cm,2*cm,2*cm,2.5*cm,6*cm])
    dt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE,LIGHT]),
        ("GRID",(0,0),(-1,-1),0.3,colors.HexColor("#D0D5DD")),
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(dt)
    story.append(Spacer(1,0.4*cm))

    # Totaux
    total_heures = total_minutes / 60
    salaire_brut = total_heures * taux

    totaux_data = [
        ["", Paragraph("Total heures :", s(10, GREY, align=2)),
         Paragraph(f"{total_heures:.2f} h", s(10, NAVY, bold=True, align=2))],
        ["", Paragraph("Taux horaire :", s(10, GREY, align=2)),
         Paragraph(f"{taux:.2f} EUR/h", s(10, NAVY, align=2))],
        ["", Paragraph("<b>SALAIRE BRUT :</b>", s(12, WHITE, bold=True, align=2)),
         Paragraph(f"<b>{salaire_brut:.2f} EUR</b>", s(12, WHITE, bold=True, align=2))],
    ]
    tt = Table(totaux_data, colWidths=[9.5*cm,4*cm,3.5*cm])
    last = len(totaux_data)-1
    tt.setStyle(TableStyle([
        ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),8),
        ("BACKGROUND",(0,last),(-1,last),NAVY),
    ]))
    story.append(tt)
    story.append(Spacer(1,0.8*cm))

    story.append(HRFlowable(width="100%",thickness=0.5,color=GREY))
    story.append(Spacer(1,0.2*cm))
    story.append(Paragraph(
        f"Document genere le {datetime.now().strftime('%d/%m/%Y')} — "
        "Ce document est un recapitulatif indicatif, non un bulletin de paie officiel.",
        s(8, GREY, align=1)
    ))

    doc.build(story)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

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
                prenom = st.text_input("Prénom *")
                nom    = st.text_input("Nom *")
            with c2:
                telephone = st.text_input("Téléphone")
                email_emp = st.text_input("Email")
            with c3:
                taux     = st.number_input("Taux horaire (€)", min_value=0.0,
                                            value=12.00, step=0.10)
                contrat  = st.selectbox("Contrat", ["CDI","CDD","Interim","Auto-entrepreneur"])

            if st.form_submit_button("➕ Ajouter", type="primary", use_container_width=True):
                if not prenom or not nom:
                    st.error("Prénom et nom obligatoires.")
                elif save_employe({
                    "propriete_id": prop_id, "prenom": prenom.strip(),
                    "nom": nom.strip(), "telephone": telephone.strip() or None,
                    "email": email_emp.strip() or None,
                    "taux_horaire": taux, "contrat": contrat, "actif": True,
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
                col1, col2, col3 = st.columns([3,1,1])
                col1.markdown(f"**{t['nom']}** — {t.get('duree_estimee',0)} min estimées")
                with col3:
                    if st.button("🗑️", key=f"del_tache_{t['id']}"):
                        _sb().table("taches_menage").update({"actif": False}).eq("id", t["id"]).execute()
                        st.rerun()

    # ── ONGLET RÉCAPITULATIF ──────────────────────────────────────────────
    with tab_recap:
        st.subheader("📊 Récapitulatif mensuel")

        # Vue consolidée multi-propriétés pour l'admin
        is_admin = st.session_state.get("is_admin", False)
        if is_admin:
            from database.proprietes_repo import fetch_all as _fa_r
            all_props = _fa_r()
            all_prop_ids = [p["id"] for p in all_props]
            if st.checkbox("Vue consolidée toutes propriétés", key="recap_all"):
                st.info("Vue consolidée — heures cumulées par employé sur toutes les propriétés")
                emps_all = get_employes_all(all_prop_ids)
                if emps_all:
                    # Récupérer tous les pointages de toutes les propriétés
                    all_pts = []
                    for pid in all_prop_ids:
                        all_pts += get_pointages(pid, mois_r if 'mois_r' in dir() else date.today().month,
                                                  annee_r if 'annee_r' in dir() else date.today().year)
                    
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
        st.subheader("📄 Générer un récapitulatif d'heures")
        st.caption("Ce document est un récapitulatif indicatif pour préparer la paie — pas un bulletin officiel.")

        employes = get_employes(prop_id)
        if not employes:
            st.warning("Ajoutez des employés d'abord.")
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

            if st.button("📄 Générer le récapitulatif PDF", type="primary", use_container_width=True):
                emp_data  = emp_dict = {e["id"]: e for e in employes}
                employe   = emp_data.get(emp_sel, {})
                pointages_emp = [p for p in get_pointages(prop_id, mois_b, annee_b)
                                  if p.get("employe_id") == emp_sel]
                if not pointages_emp:
                    st.warning("Aucun pointage pour cet employé ce mois.")
                else:
                    with st.spinner("Génération..."):
                        pdf_bytes = _generer_bulletin(employe, pointages_emp, prop_nom, mois_b, annee_b)
                    nom_safe = f"{employe.get('prenom','')}_{employe.get('nom','')}".replace(" ","_")
                    st.download_button(
                        label="⬇️ Télécharger le récapitulatif PDF",
                        data=pdf_bytes,
                        file_name=f"Recap_heures_{nom_safe}_{annee_b}_{mois_b:02d}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
