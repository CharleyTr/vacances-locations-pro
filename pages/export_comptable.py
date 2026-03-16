"""
Page Export Comptable — génère un fichier Excel annuel par propriété.
"""
import streamlit as st
from datetime import date
from services.reservation_service import load_reservations
from services.export_comptable_service import generate_export
from services.analytics_service import compute_kpis
from services.auth_service import is_unlocked
from database.proprietes_repo import fetch_all


def show():
    st.title("📊 Export Comptable")
    st.caption("Générez votre fichier Excel annuel pour votre comptable.")

    # ── Sélection propriété & année ───────────────────────────────────────
    props_list = fetch_all()
    props_dict = {p["id"]: p["nom"] for p in props_list}
    props_dict[0] = "Toutes les propriétés"

    col1, col2 = st.columns(2)
    with col1:
        prop_options = {0: "Toutes les propriétés"}
        prop_options.update(props_dict)
        prop_id = st.selectbox(
            "🏠 Propriété",
            options=[p["id"] for p in props_list],
            format_func=lambda x: props_dict.get(x, x),
            key="export_prop"
        )
    with col2:
        annee = st.selectbox(
            "📅 Année fiscale",
            options=list(range(date.today().year, 2019, -1)),
            index=0,
            key="export_annee"
        )

    # ── Chargement données ────────────────────────────────────────────────
    df_all = load_reservations()
    if df_all.empty:
        st.warning("Aucune réservation disponible.")
        return

    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)
    # Accès limité aux propriétés déverrouillées
    from database.proprietes_repo import fetch_all as _fa
    _autorises = [p["id"] for p in _fa() if not p.get("mot_de_passe") or is_unlocked(p["id"])]
    df_all = df_all[df_all["propriete_id"].isin(_autorises)]
    df_prop = df_all[df_all["propriete_id"] == prop_id]
    df_an   = df_prop[df_prop["annee"] == annee] if "annee" in df_prop.columns else df_prop
    prop_nom = props_dict.get(prop_id, "Toutes les propriétés")

    if df_an.empty:
        st.info(f"Aucune réservation pour {prop_nom} en {annee}.")
        return

    # ── Aperçu KPIs ───────────────────────────────────────────────────────
    st.divider()
    st.subheader(f"📋 Aperçu — {prop_nom} — {annee}")

    df_reel = df_an[df_an["plateforme"] != "Fermeture"]
    kpis = compute_kpis(df_reel)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Réservations",    kpis.get("nb_reservations", len(df_reel)))
    c2.metric("🌙 Nuits louées",    kpis.get("nuits_louees", 0))
    c3.metric("💶 CA Brut",        f"{kpis['ca_brut']:,.0f} €")
    c4.metric("💵 CA Net",         f"{kpis['ca_net']:,.0f} €")
    c5.metric("📊 Taux occupation", f"{kpis.get('taux_occupation', 0):.1f} %")

    c6, c7, c8 = st.columns(3)
    c6.metric("🔖 Commissions",    f"{kpis['commissions']:,.0f} €")
    c7.metric("🧹 Ménages",        f"{kpis['menage']:,.0f} €")
    c8.metric("💰 Rev. moy./nuit", f"{kpis['revenu_nuit']:,.0f} €")

    # ── Contenu du fichier Excel ──────────────────────────────────────────
    st.divider()
    st.subheader("📁 Contenu du fichier Excel")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
**4 onglets générés :**

🗒️ **Réservations** — toutes les lignes avec :
- Numéro, plateforme, client, dates, nuits
- CA Brut, Commission, Ménage, Taxes, CA Net
- Statut paiement

📅 **Mensuel** — récap mois par mois :
- Réservations, nuits, CA, commissions, taux d'occupation
        """)
    with col_b:
        st.markdown("""
&nbsp;

🌐 **Par plateforme** — ventilation Airbnb / Booking :
- Réservations, nuits, CA Brut, Commissions, CA Net
- % du CA Net total

📊 **Synthèse** — fiche récapitulative :
- Tous les KPIs annuels
- Prêt à imprimer / envoyer au comptable
        """)

    # ── Bouton export ─────────────────────────────────────────────────────
    st.divider()
    if st.button("🔄 Générer le fichier Excel", type="primary",
                 use_container_width=True, key="btn_export"):
        with st.spinner("Génération en cours..."):
            excel_bytes = generate_export(df_prop, annee, prop_nom)

        filename = f"comptable_{prop_nom.replace(' ','_').replace('-','')[:20]}_{annee}.xlsx"
        st.download_button(
            label=f"⬇️ Télécharger {filename}",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
        st.success("✅ Fichier prêt ! Cliquez sur le bouton pour télécharger.")

    # ── Note comptable ────────────────────────────────────────────────────
    with st.expander("ℹ️ Note pour votre comptable"):
        st.markdown(f"""
**Informations sur ce document :**
- Données extraites de Vacances-Locations Pro
- Propriété : **{prop_nom}**
- Exercice fiscal : **{annee}**
- Généré le : **{date.today().strftime('%d/%m/%Y')}**

**Colonnes financières :**
- **CA Brut** = montant facturé au voyageur (hors taxes de séjour)
- **Commission** = prélevée par la plateforme (Airbnb, Booking...)
- **Ménage** = frais de ménage (reversés au prestataire)
- **CA Net** = somme effectivement perçue par le propriétaire

*Les réservations "Fermeture" (blocages calendrier) sont exclues des totaux.*
        """)
