"""
Page Factures — Génération de factures PDF par réservation.
"""
import streamlit as st
from datetime import date
from services.reservation_service import load_reservations
from services.facture_service import generate_facture
from database.proprietes_repo import fetch_all
from services.proprietes_service import get_proprietes_autorises


def show():
    st.title("🧾 Factures")
    st.caption("Générez une facture PDF professionnelle pour n'importe quelle réservation.")

    props_auth = get_proprietes_autorises()
    props_full = {p["id"]: p for p in fetch_all() if p["id"] in props_auth}

    df = load_reservations()
    if df.empty:
        st.warning("Aucune réservation disponible.")
        return
    df["propriete_id"] = df["propriete_id"].fillna(0).astype(int)
    df = df[df["propriete_id"].isin(props_auth.keys())]
    df = df[df["plateforme"] != "Fermeture"].copy()

    # ── Recherche & sélection ─────────────────────────────────────────────
    col1, col2 = st.columns([3, 2])
    with col1:
        search = st.text_input("🔎 Rechercher un client", placeholder="Tapez un nom...", key="fac_search")
    with col2:
        prop_filter = st.selectbox(
            "🏠 Propriété",
            options=[0] + list(props_auth.keys()),
            format_func=lambda x: "Toutes" if x == 0 else props_auth[x],
            key="fac_prop"
        )

    df_f = df.copy()
    if search:
        df_f = df_f[df_f["nom_client"].str.contains(search, case=False, na=False)]
    if prop_filter:
        df_f = df_f[df_f["propriete_id"] == prop_filter]
    df_f = df_f.sort_values("date_arrivee", ascending=False)

    if df_f.empty:
        st.info("Aucune réservation trouvée.")
        return

    res_options = {
        row["id"]: (
            f"{row['nom_client']}  |  "
            f"{str(row['date_arrivee'])[:10]} → {str(row['date_depart'])[:10]}  |  "
            f"{props_auth.get(int(row['propriete_id']), '?')}  |  "
            f"{row['plateforme']}"
        )
        for _, row in df_f.iterrows()
    }
    res_id = st.selectbox("📋 Réservation", list(res_options.keys()),
                           format_func=lambda x: res_options[x], key="fac_res")

    row = df[df["id"] == res_id].iloc[0].to_dict()
    prop_id = int(row.get("propriete_id", 0))
    prop_data = props_full.get(prop_id, {})
    signataire = prop_data.get("signataire", "") or ""
    prop_nom = prop_data.get("nom", "")

    st.divider()

    # ── Paramètres de la facture ──────────────────────────────────────────
    st.subheader("⚙️ Paramètres")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        num_facture = st.text_input(
            "Numéro de facture",
            value=f"FAC-{date.today().strftime('%Y%m')}-{res_id:04d}",
            key="fac_num"
        )
    with col_b:
        st.text_input("Signataire", value=signataire, key="fac_sign", disabled=True,
                      help="Configurez-le dans la fiche propriété")
    with col_c:
        inclure_taxes = st.checkbox("Inclure taxes de séjour", value=True, key="fac_taxes")

    # ── Aperçu des montants ───────────────────────────────────────────────
    def _fv(k, d=0):
        v = row.get(k, d)
        try: return float(v) if v else d
        except: return d

    prix_brut = _fv("prix_brut")
    menage    = _fv("menage") or _fv("prix_menage")
    taxes     = _fv("taxes_sejour") if inclure_taxes else 0.0
    total     = prix_brut + menage + taxes

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🌙 Nuits",    f"{int(_fv('nuitees'))}")
    col2.metric("💶 Location", f"{prix_brut:,.0f} €")
    col3.metric("🧹 Ménage",   f"{menage:,.0f} €")
    col4.metric("💳 TOTAL",    f"{total:,.0f} €")

    st.divider()

    # ── Génération ────────────────────────────────────────────────────────
    if st.button("🖨️ Générer la facture PDF", type="primary",
                 use_container_width=True, key="btn_gen_fac"):
        with st.spinner("Génération en cours..."):
            res_copy = dict(row)
            if not inclure_taxes:
                res_copy["taxes_sejour"] = 0
            pdf_bytes = generate_facture(
                reservation=res_copy,
                propriete_id=prop_id,
                signataire=signataire,
                prop_nom=prop_nom,
                numero_facture=num_facture,
                prop_data=prop_data,
            )

        nom_client_safe = row.get("nom_client","client").replace(" ","_")
        filename = f"Facture_{num_facture}_{nom_client_safe}.pdf"
        st.download_button(
            label=f"⬇️ Télécharger {filename}",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
        st.success("✅ Facture prête !")

    # ── Note légale ───────────────────────────────────────────────────────
    with st.expander("ℹ️ Mentions légales incluses dans la facture"):
        st.markdown("""
La facture inclut automatiquement :
- **TVA non applicable** — art. 293B du CGI (LMNP non assujetti)
- Désignation de la location avec dates précises
- Numéro SIRET (à renseigner dans la fiche propriété)
- Identification complète du client
- Mentions de régime fiscal (micro-BIC)
        """)
