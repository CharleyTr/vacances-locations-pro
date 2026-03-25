"""
Page import corrections — met à jour uniquement les montants modifiés.
Compare le CSV avec la BDD et génère/exécute les UPDATE.
"""
import streamlit as st
import pandas as pd
from database.supabase_client import get_supabase, is_connected
from services.auth_service import is_unlocked
from database.proprietes_repo import fetch_all as _fetch_props


def show():
    st.title("🔧 Correction de réservations")
    st.caption("Importez un CSV exporté depuis l'app — seuls les montants modifiés seront mis à jour.")

    if not is_connected():
        st.error("⛔ Connexion Supabase requise.")
        return

    if not st.session_state.get("is_admin", False):
        st.error("⛔ Accès réservé à l'administrateur.")
        return

    st.info("""
    **Comment utiliser :**
    1. Exportez vos réservations depuis **💾 Sauvegarde**
    2. Corrigez les montants dans Excel
    3. Enregistrez en CSV et uploadez ici
    4. Vérifiez les différences détectées
    5. Cliquez **Appliquer les corrections**
    """)

    uploaded = st.file_uploader("📂 Uploadez le CSV corrigé", type=["csv"], key="csv_corrections")
    if not uploaded:
        return

    # ── Lire le CSV ───────────────────────────────────────────────────────
    try:
        df_csv = pd.read_csv(uploaded, dtype={"id": str})
    except Exception as e:
        st.error(f"❌ Erreur lecture CSV : {e}")
        return

    if "id" not in df_csv.columns:
        st.error("❌ Le CSV doit contenir une colonne 'id'.")
        return

    st.success(f"✅ CSV lu : {len(df_csv)} réservations")

    # ── Colonnes de montants à comparer ──────────────────────────────────
    COLS_MONTANTS = ["prix_brut", "prix_net", "commissions", "prix_menage",
                     "menage", "taxes_sejour", "acompte"]
    cols_presentes = [c for c in COLS_MONTANTS if c in df_csv.columns]

    if not cols_presentes:
        st.warning("Aucune colonne de montant trouvée dans le CSV.")
        st.write("Colonnes disponibles :", list(df_csv.columns))
        return

    st.markdown(f"**Colonnes de montants détectées :** {', '.join(cols_presentes)}")

    # ── Charger les données BDD ───────────────────────────────────────────
    with st.spinner("Chargement des données depuis Supabase..."):
        sb = get_supabase()
        ids_csv = df_csv["id"].dropna().tolist()
        cols_select = "id," + ",".join(cols_presentes)
        try:
            rows = sb.table("reservations").select(cols_select)\
                     .in_("id", ids_csv).execute().data or []
            df_bdd = pd.DataFrame(rows, dtype=str)
        except Exception as e:
            st.error(f"❌ Erreur Supabase : {e}")
            return

    if df_bdd.empty:
        st.warning("Aucune réservation trouvée en BDD pour les IDs du CSV.")
        return

    # ── Comparer et détecter les différences ─────────────────────────────
    df_csv["id"] = df_csv["id"].astype(str)
    df_bdd["id"] = df_bdd["id"].astype(str)
    df_merge = df_csv[["id"] + cols_presentes].merge(
        df_bdd, on="id", suffixes=("_nouveau", "_actuel")
    )

    corrections = []
    for _, row in df_merge.iterrows():
        champs_modifies = {}
        for col in cols_presentes:
            try:
                val_nouveau = round(float(str(row.get(f"{col}_nouveau", 0) or 0).replace(",",".")), 2)
                val_actuel  = round(float(str(row.get(f"{col}_actuel",  0) or 0).replace(",",".")), 2)
                if val_nouveau != val_actuel:
                    champs_modifies[col] = {"avant": val_actuel, "apres": val_nouveau}
            except Exception:
                pass
        if champs_modifies:
            # Récupérer le nom du client pour l'affichage
            nom = df_csv[df_csv["id"] == row["id"]]["nom_client"].values
            corrections.append({
                "id":      row["id"],
                "client":  nom[0] if len(nom) > 0 else "?",
                "champs":  champs_modifies,
            })

    if not corrections:
        st.success("✅ Aucune différence détectée — les montants sont identiques.")
        return

    # ── Afficher les différences ──────────────────────────────────────────
    st.divider()
    st.markdown(f"### ⚠️ {len(corrections)} réservation(s) avec des montants modifiés")

    rows_display = []
    for c in corrections:
        for champ, vals in c["champs"].items():
            rows_display.append({
                "ID":      c["id"],
                "Client":  c["client"],
                "Champ":   champ,
                "Avant":   f"{vals['avant']:,.2f} €",
                "Après":   f"{vals['apres']:,.2f} €",
                "Écart":   f"{vals['apres'] - vals['avant']:+,.2f} €",
            })

    df_diff = pd.DataFrame(rows_display)
    st.dataframe(df_diff, use_container_width=True, hide_index=True)

    # ── Générer le SQL pour vérification ─────────────────────────────────
    with st.expander("📋 Voir le SQL généré", expanded=False):
        sql_lines = []
        for c in corrections:
            sets = ", ".join([f"{k} = {v['apres']}" for k, v in c["champs"].items()])
            sql_lines.append(f"UPDATE reservations SET {sets} WHERE id = {c['id']};")
        st.code("\n".join(sql_lines), language="sql")

    # ── Appliquer ─────────────────────────────────────────────────────────
    st.divider()
    st.warning(f"⚠️ Cette action va modifier **{len(corrections)} réservation(s)** directement en base.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Appliquer les corrections", type="primary",
                     use_container_width=True, key="btn_apply"):
            ok, errors = 0, []
            prog = st.progress(0)
            for i, c in enumerate(corrections):
                try:
                    updates = {k: v["apres"] for k, v in c["champs"].items()}
                    sb.table("reservations").update(updates)\
                      .eq("id", int(c["id"])).execute()
                    ok += 1
                except Exception as e:
                    errors.append(f"ID {c['id']} : {e}")
                prog.progress((i+1) / len(corrections))

            if ok:
                st.success(f"✅ {ok} réservation(s) corrigée(s) avec succès !")
                st.balloons()
            for err in errors:
                st.error(f"❌ {err}")

    with col2:
        if st.button("❌ Annuler", use_container_width=True, key="btn_cancel"):
            st.info("Annulé — aucune modification effectuée.")
            st.rerun()
