"""
Page Import Airbnb - Import CSV transactions Airbnb.
"""
import streamlit as st
import pandas as pd
from services.import_airbnb_service import parse_airbnb_csv, preview_airbnb_csv
from database.reservations_repo import upsert_reservations, fetch_all
from services.proprietes_service import get_proprietes_dict
from database.supabase_client import is_connected


def show():
    st.title("📥 Import Airbnb")
    st.markdown("Importez vos fichiers CSV Airbnb — historique et réservations à venir.")

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise.")
        return

    props = get_proprietes_dict()

    with st.expander("📖 Comment télécharger les fichiers Airbnb ?"):
        st.markdown("""
        **Fichier historique** (réservations payées) :
        1. **airbnb.com** → Menu profil → **Tableau de bord** → **Transactions**
        2. Cliquez **Exporter les données** → choisissez la période → **Télécharger CSV**
        
        **Fichier pending** (réservations confirmées, pas encore versées) :
        1. Même menu → **Réservations** → **À venir**
        2. **Exporter** → CSV
        """)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📂 Fichier historique** *(transactions versées)*")
        f_hist = st.file_uploader("CSV historique Airbnb", type=["csv"], key="airbnb_hist")
    with col2:
        st.markdown("**📂 Fichier pending** *(réservations à venir)*")
        f_pend = st.file_uploader("CSV pending Airbnb", type=["csv"], key="airbnb_pend")

    if not f_hist and not f_pend:
        st.info("Uploadez un ou deux fichiers CSV Airbnb pour commencer.")
        return

    # Parser les fichiers
    dfs = []
    if f_hist:
        try:
            df_h = parse_airbnb_csv(f_hist.read(), pending=False)
            if not df_h.empty:
                dfs.append(df_h)
                st.success(f"✅ Historique : **{len(df_h)}** réservations payées")
        except Exception as e:
            st.error(f"Erreur fichier historique : {e}")

    if f_pend:
        try:
            df_p = parse_airbnb_csv(f_pend.read(), pending=True)
            if not df_p.empty:
                dfs.append(df_p)
                st.success(f"✅ Pending : **{len(df_p)}** réservations à venir")
        except Exception as e:
            st.error(f"Erreur fichier pending : {e}")

    if not dfs:
        st.warning("Aucune réservation valide trouvée.")
        return

    df_full = pd.concat(dfs, ignore_index=True)

    # ── Stats ────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📋 Total",      len(df_full))
    c2.metric("🌙 Nuits",      int(df_full["nuitees"].sum()))
    c3.metric("💶 CA Brut",    f"{df_full['prix_brut'].sum():,.0f} €")
    c4.metric("💵 Prix net",   f"{df_full['prix_net'].sum():,.0f} €")
    c5.metric("🏷️ Commissions", f"{df_full['commissions'].sum():,.0f} €")

    # ── Vérifier doublons ─────────────────────────────────────────────────
    try:
        df_exist = fetch_all()
        existing = set(df_exist["numero_reservation"].dropna().astype(str)) \
                   if not df_exist.empty else set()
    except Exception:
        existing = set()

    df_full["Statut"] = df_full["numero_reservation"].apply(
        lambda x: "⚠️ Existe déjà" if str(x) in existing else "✅ Nouveau"
    )
    nouveaux = (df_full["Statut"] == "✅ Nouveau").sum()
    doublons = (df_full["Statut"] == "⚠️ Existe déjà").sum()

    # ── Gestion propriétés non reconnues ─────────────────────────────────
    st.divider()
    if 0 in df_full["propriete_id"].values:
        nb_inconnu = (df_full["propriete_id"] == 0).sum()
        st.warning(f"⚠️ {nb_inconnu} réservation(s) : logement non identifié automatiquement.")
        prop_fallback = st.selectbox(
            "Attribuer ces réservations à :",
            options=list(props.keys()),
            format_func=lambda x: props[x],
            key="airbnb_prop"
        )
        df_full.loc[df_full["propriete_id"] == 0, "propriete_id"] = prop_fallback

    # ── Aperçu tableau ───────────────────────────────────────────────────
    st.markdown("### 👁️ Aperçu")
    if doublons > 0:
        st.warning(f"⚠️ {doublons} réservation(s) existent déjà → mises à jour")
    if nouveaux > 0:
        st.success(f"✅ {nouveaux} nouvelle(s) réservation(s)")

    display_cols = ["Statut","nom_client","date_arrivee","date_depart",
                    "nuitees","prix_brut","commissions","frais_menage","prix_net","paye"]
    df_display = df_full[display_cols].copy()
    df_display["propriete"] = df_full["propriete_id"].map(props)

    def color_row(row):
        c = "background-color:#E8F5E9" if "Nouveau" in str(row["Statut"]) \
            else "background-color:#FFF8E1"
        return [c] * len(row)

    st.dataframe(
        df_display.style.apply(color_row, axis=1),
        use_container_width=True, hide_index=True
    )

    # ── Import ────────────────────────────────────────────────────────────
    st.divider()
    if st.button(f"⬆️ Importer {len(df_full)} réservation(s)", 
                 type="primary", use_container_width=True):
        rows = df_full.drop(columns=["Statut"]).to_dict("records")
        for row in rows:
            for k, v in row.items():
                try:
                    if pd.isna(v):
                        row[k] = None
                except (TypeError, ValueError):
                    pass

        with st.spinner("Import en cours..."):
            try:
                nb = upsert_reservations(rows)
                st.success(f"🎉 {nb} réservation(s) importée(s) !")
                st.balloons()
                cc1, cc2, cc3, cc4 = st.columns(4)
                cc1.metric("✅ Importées", nb)
                cc2.metric("💶 CA Brut", f"{df_full['prix_brut'].sum():,.0f} €")
                cc3.metric("💵 Net",     f"{df_full['prix_net'].sum():,.0f} €")
                cc4.metric("🧹 Ménage",  f"{df_full['frais_menage'].sum():,.0f} €")
            except Exception as e:
                st.error(f"Erreur : {e}")
