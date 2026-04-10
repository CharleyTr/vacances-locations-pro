"""
Page Rapport - Export Excel + Previsions de CA
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from services.reservation_service import load_reservations
from services.analytics_service import compute_kpis
from services.report_service import generate_report
from services.proprietes_service import get_proprietes_dict
from services.proprietes_service import get_proprietes_autorises, filter_df, get_propriete_selectionnee, get_label


def show():
    st.title("📊 Rapports & Prévisions")

    df_all = load_reservations()
    if df_all.empty:
        st.info("Aucune réservation disponible.")
        return

    df_all["date_arrivee"] = pd.to_datetime(df_all["date_arrivee"])
    df_all["date_depart"]  = pd.to_datetime(df_all["date_depart"])
    df_all["annee"]        = df_all["date_arrivee"].dt.year

    prop_id   = get_propriete_selectionnee()
    prop_nom  = get_label(prop_id)
    df        = filter_df(df_all)
    props     = get_proprietes_autorises()

    tab_export, tab_nvn, tab_prev = st.tabs([
        "📥 Export Excel",
        "📈 Comparaison N / N-1",
        "🔮 Prévisions",
    ])

    with tab_export:
        _show_export(df, prop_nom)

    with tab_nvn:
        _show_nvn(df, prop_nom)

    with tab_prev:
        _show_previsions(df_all, props, prop_id, prop_nom)


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT EXCEL
# ─────────────────────────────────────────────────────────────────────────────

def _show_export(df: pd.DataFrame, prop_nom: str):
    st.subheader("📥 Export Excel — Rapport propriétaire")
    st.markdown(
        "Génère un fichier Excel professionnel avec 4 onglets : "
        "**Résumé**, **Détail mensuel**, **Liste des réservations**, **Prévisions**."
    )

    col1, col2 = st.columns(2)
    with col1:
        annees = sorted(df["annee"].dropna().unique().tolist(), reverse=True)
        annee  = st.selectbox("Année", annees, key="rpt_annee")
    with col2:
        inclure_prev = st.checkbox("Inclure les réservations futures", value=True)

    df_annee = df[df["annee"] == annee]
    if df_annee.empty:
        st.warning("Aucune donnée pour cette année.")
        return

    df_reel = df_annee[df_annee["plateforme"] != "Fermeture"]
    kpis    = compute_kpis(df_reel)

    # Aperçu rapide
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📅 Réservations",  kpis["nb_reservations"])
    c2.metric("💵 CA Net",         f"{kpis['ca_net']:,.0f} €")
    c3.metric("🌙 Nuits",          kpis["nuits_total"])
    c4.metric("📈 Revenu/nuit",    f"{kpis['revenu_nuit']:,.0f} €")

    st.divider()

    # Génération du rapport
    df_export = df if inclure_prev else df_annee
    try:
        xlsx_bytes = generate_report(df_export, prop_nom, annee)
        safe_nom   = prop_nom.replace(" ", "_").replace("/", "-")
        filename   = f"Rapport_{safe_nom}_{annee}.xlsx"

        st.download_button(
            label=f"⬇️ Télécharger le rapport Excel {annee}",
            data=xlsx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
        st.caption(f"Fichier : **{filename}** — 4 onglets inclus")

        # ── Export PDF mensuel ───────────────────────────────────────────
        st.divider()
        st.subheader("📄 Rapport PDF mensuel")
        st.markdown("Génère un rapport PDF professionnel pour un mois donné.")

        col_pdf1, col_pdf2 = st.columns(2)
        with col_pdf1:
            mois_noms = ["Janvier","Février","Mars","Avril","Mai","Juin",
                         "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
            mois_sel = st.selectbox("Mois", range(1,13),
                                     format_func=lambda m: mois_noms[m-1],
                                     index=datetime.now().month-1,
                                     key="rpt_pdf_mois")
        with col_pdf2:
            annee_pdf = st.selectbox("Année PDF", annees, key="rpt_pdf_annee")

        if st.button("📄 Générer le PDF", type="primary", use_container_width=True, key="btn_pdf"):
            try:
                from services.pdf_rapport import generer_rapport_pdf
                from datetime import date, datetimetime as _dt
                _resas_all = df.to_dict("records")
                _resas_n1  = df[df["annee"] == annee_pdf - 1].to_dict("records")
                pdf_bytes = generer_rapport_pdf(
                    prop_nom  = prop_nom,
                    mois      = mois_sel,
                    annee     = annee_pdf,
                    reservations    = _resas_all,
                    reservations_n1 = _resas_n1,
                )
                safe_nom_pdf = prop_nom.replace(" ", "_").replace("/", "-")
                filename_pdf = f"Rapport_{safe_nom_pdf}_{annee_pdf}_{mois_sel:02d}.pdf"
                st.download_button(
                    label=f"⬇️ Télécharger le PDF — {mois_noms[mois_sel-1]} {annee_pdf}",
                    data=pdf_bytes,
                    file_name=filename_pdf,
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                    key="btn_dl_pdf"
                )
            except Exception as e_pdf:
                st.error(f"Erreur PDF : {e_pdf}")
    except Exception as e:
        st.error(f"❌ Erreur génération : {e}")


# ─────────────────────────────────────────────────────────────────────────────
# COMPARAISON N / N-1
# ─────────────────────────────────────────────────────────────────────────────

def _show_nvn(df: pd.DataFrame, prop_nom: str):
    st.subheader("📈 Comparaison année N / N-1")

    annees = sorted(df["annee"].dropna().unique().tolist(), reverse=True)
    if len(annees) < 2:
        st.info("Il faut au moins 2 années de données pour comparer.")
        return

    col1, col2 = st.columns(2)
    with col1:
        annee_n  = st.selectbox("Année N",   annees,     index=0, key="nvn_n")
    with col2:
        annee_n1 = st.selectbox("Année N-1", annees,     index=min(1, len(annees)-1), key="nvn_n1")

    if annee_n == annee_n1:
        st.warning("Sélectionnez deux années différentes.")
        return

    df_n  = df[(df["annee"] == annee_n)  & (df["plateforme"] != "Fermeture")]
    df_n1 = df[(df["annee"] == annee_n1) & (df["plateforme"] != "Fermeture")]

    kn  = compute_kpis(df_n)
    kn1 = compute_kpis(df_n1)

    def _delta(v_n, v_n1):
        if v_n1 == 0:
            return None
        return round((v_n - v_n1) / v_n1 * 100, 1)

    st.markdown(f"### {annee_n} vs {annee_n1}")

    metrics = [
        ("💰 CA Brut",      kn["ca_brut"],         kn1["ca_brut"],         "{:,.0f} €"),
        ("💵 CA Net",        kn["ca_net"],          kn1["ca_net"],          "{:,.0f} €"),
        ("📅 Réservations",  kn["nb_reservations"], kn1["nb_reservations"], "{:,.0f}"),
        ("🌙 Nuits louées",  kn["nuits_total"],     kn1["nuits_total"],     "{:,.0f}"),
        ("📈 Revenu/nuit",   kn["revenu_nuit"],     kn1["revenu_nuit"],     "{:,.0f} €"),
        ("🔖 Commissions",   kn["commissions"],     kn1["commissions"],     "{:,.0f} €"),
    ]

    cols = st.columns(3)
    for i, (label, vn, vn1, fmt) in enumerate(metrics):
        delta = _delta(vn, vn1)
        delta_str = f"{'+' if delta and delta > 0 else ''}{delta}%" if delta is not None else "—"
        cols[i % 3].metric(
            label=label,
            value=fmt.format(vn),
            delta=delta_str,
        )

    st.divider()

    # Graphique comparatif mensuel CA
    MOIS = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

    def _monthly_ca(d, label):
        d = d.copy()
        d["mois_num"] = d["date_arrivee"].dt.month
        m = d.groupby("mois_num")["prix_net"].sum().reset_index()
        rows = []
        for num in range(1, 13):
            row = m[m["mois_num"] == num]
            rows.append({"Mois": MOIS[num-1], "CA Net": float(row["prix_net"].iloc[0]) if not row.empty else 0, "Année": str(label)})
        return pd.DataFrame(rows)

    df_chart = pd.concat([_monthly_ca(df_n, annee_n), _monthly_ca(df_n1, annee_n1)])
    fig = px.bar(
        df_chart, x="Mois", y="CA Net", color="Année", barmode="group",
        labels={"CA Net": "CA Net (€)"},
        color_discrete_map={str(annee_n): "#1565C0", str(annee_n1): "#90CAF9"},
    )
    fig.update_layout(height=350, margin=dict(t=20, b=20), legend_title="")
    st.plotly_chart(fig, use_container_width=True)

    # Tableau détaillé
    with st.expander("📋 Tableau comparatif mensuel"):
        rows = []
        for m in range(1, 13):
            dn  = df_n[ df_n["date_arrivee"].dt.month == m]
            dn1 = df_n1[df_n1["date_arrivee"].dt.month == m]
            ca_n  = float(dn["prix_net"].sum())
            ca_n1 = float(dn1["prix_net"].sum())
            delta = _delta(ca_n, ca_n1)
            rows.append({
                "Mois":            MOIS[m-1],
                f"CA Net {annee_n}":   f"{ca_n:,.0f} €",
                f"CA Net {annee_n1}":  f"{ca_n1:,.0f} €",
                "Évolution":           f"{'+' if delta and delta > 0 else ''}{delta}%" if delta else "—",
                f"Rés. {annee_n}":     len(dn),
                f"Rés. {annee_n1}":    len(dn1),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# PRÉVISIONS
# ─────────────────────────────────────────────────────────────────────────────

def _show_previsions(df_all: pd.DataFrame, props: dict, prop_id: int, prop_nom: str):
    st.subheader("🔮 Prévisions de CA — Réservations confirmées")
    st.markdown(
        "Basées uniquement sur les **réservations déjà enregistrées** dans Supabase. "
        "Ne tient pas compte des futures réservations non encore saisies."
    )

    today = pd.Timestamp(date.today())
    df    = filter_df(df_all)
    df_future = df[(df["date_arrivee"] > today) & (df["plateforme"] != "Fermeture")].copy()

    if df_future.empty:
        st.info("Aucune réservation future enregistrée.")
        return

    df_future["annee"]    = df_future["date_arrivee"].dt.year
    df_future["mois_num"] = df_future["date_arrivee"].dt.month

    annees_fut = sorted(df_future["annee"].unique().tolist())
    MOIS = ["Jan","Fév","Mar","Avr","Mai","Jun","Jul","Aoû","Sep","Oct","Nov","Déc"]

    # ── KPIs globaux future ───────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Réservations futures",  len(df_future))
    c2.metric("💵 CA Net confirmé",        f"{df_future['prix_net'].sum():,.0f} €")
    c3.metric("🌙 Nuits réservées",        int(df_future["nuitees"].fillna(0).sum()))
    paye_fut = float(df_future[df_future["paye"] == True]["prix_net"].sum())
    att_fut  = float(df_future[df_future["paye"] != True]["prix_net"].sum())
    c4.metric("⏳ En attente de paiement", f"{att_fut:,.0f} €")

    st.divider()

    # ── Vue par année ──────────────────────────────────────────────────────
    for annee in annees_fut:
        df_an = df_future[df_future["annee"] == annee]
        st.markdown(f"#### 📅 {annee}")

        # Graphique mensuel
        rows_chart = []
        for m in range(1, 13):
            dm = df_an[df_an["mois_num"] == m]
            if not dm.empty:
                rows_chart.append({
                    "Mois":     MOIS[m-1],
                    "Payé":     float(dm[dm["paye"] == True]["prix_net"].sum()),
                    "En attente": float(dm[dm["paye"] != True]["prix_net"].sum()),
                })

        if rows_chart:
            df_c = pd.DataFrame(rows_chart)
            fig = go.Figure()
            fig.add_bar(x=df_c["Mois"], y=df_c["Payé"],
                        name="Payé", marker_color="#2E7D32")
            fig.add_bar(x=df_c["Mois"], y=df_c["En attente"],
                        name="En attente", marker_color="#FF8F00")
            fig.update_layout(
                barmode="stack", height=280,
                margin=dict(t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                yaxis_title="CA Net (€)"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Tableau
        rows_tab = []
        for m in range(1, 13):
            dm = df_an[df_an["mois_num"] == m]
            if dm.empty:
                continue
            paye  = float(dm[dm["paye"] == True]["prix_net"].sum())
            att   = float(dm[dm["paye"] != True]["prix_net"].sum())
            rows_tab.append({
                "Mois":            MOIS[m-1],
                "Réservations":    len(dm),
                "Nuits":           int(dm["nuitees"].fillna(0).sum()),
                "CA Net total":    f"{paye+att:,.0f} €",
                "Payé":            f"{paye:,.0f} €",
                "En attente":      f"{att:,.0f} €",
            })

        if rows_tab:
            df_tab = pd.DataFrame(rows_tab)
            # Totaux
            df_num = df_an.copy()
            tot_paye = float(df_num[df_num["paye"] == True]["prix_net"].sum())
            tot_att  = float(df_num[df_num["paye"] != True]["prix_net"].sum())
            st.dataframe(df_tab, use_container_width=True, hide_index=True)
            col_a, col_b, col_c = st.columns(3)
            col_a.metric(f"Total CA Net {annee}",    f"{tot_paye+tot_att:,.0f} €")
            col_b.metric("Déjà payé",                 f"{tot_paye:,.0f} €",
                         delta=f"{round(tot_paye/(tot_paye+tot_att)*100) if (tot_paye+tot_att) else 0}%")
            col_c.metric("Reste à encaisser",          f"{tot_att:,.0f} €")

        # Liste détaillée des réservations futures
        with st.expander(f"📋 Détail {annee} ({len(df_an)} réservations)"):
            cols_show = ["nom_client","plateforme","date_arrivee","date_depart","nuitees","prix_net","paye"]
            cols_ok   = [c for c in cols_show if c in df_an.columns]
            st.dataframe(df_an[cols_ok].sort_values("date_arrivee"),
                         use_container_width=True, hide_index=True,
                         column_config={"paye": st.column_config.CheckboxColumn("Payé")})

        st.divider()
