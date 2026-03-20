"""
Page Sauvegarde — Export complet des données en CSV/Excel.
Admin uniquement.
"""
import streamlit as st
import pandas as pd
import io
from datetime import date
from database.supabase_client import get_supabase


def show():
    st.title("💾 Sauvegarde des données")
    st.caption("Exportez toutes vos données en cas de besoin. À faire régulièrement.")

    if not st.session_state.get("is_admin", False):
        st.error("⛔ Accès réservé à l'administrateur.")
        return

    sb = get_supabase()
    if sb is None:
        st.error("Connexion Supabase requise.")
        return

    today = date.today().strftime("%Y%m%d")

    st.info("💡 Cliquez sur chaque bouton pour télécharger les données correspondantes. "
            "Conservez ces fichiers sur votre disque dur ou Google Drive.")

    st.divider()

    # ── Export par table ──────────────────────────────────────────────────────
    tables = [
        ("reservations",     "📋 Réservations",       "reservations"),
        ("proprietes",       "🏠 Propriétés",          "proprietes"),
        ("frais_deductibles","🧾 Frais déductibles",   "frais"),
        ("avis",             "⭐ Avis / Livre d'or",   "avis"),
        ("profiles",         "👥 Utilisateurs",        "profiles"),
        ("propriete_access", "🔐 Accès propriétés",    "acces"),
        ("tarifs_saison",    "💶 Tarifs",              "tarifs"),
        ("message_templates","📧 Modèles messages",    "templates"),
        ("chat_messages",    "💬 Messages chat",       "chat"),
        ("journal_connexions","📋 Journal connexions", "journal"),
    ]

    col1, col2 = st.columns(2)
    for i, (table, label, fname) in enumerate(tables):
        col = col1 if i % 2 == 0 else col2
        with col:
            with st.container():
                st.markdown(f"**{label}**")
                try:
                    data = sb.table(table).select("*").execute().data or []
                    nb   = len(data)
                    if nb == 0:
                        st.caption(f"Aucune donnée")
                    else:
                        df  = pd.DataFrame(data)
                        csv = df.to_csv(index=False).encode("utf-8-sig")
                        st.download_button(
                            f"⬇️ {nb} lignes",
                            data=csv,
                            file_name=f"vlp_{fname}_{today}.csv",
                            mime="text/csv",
                            key=f"dl_{table}",
                            use_container_width=True
                        )
                except Exception as e:
                    st.caption(f"Erreur: {e}")

    st.divider()

    # ── Export TOUT en Excel ──────────────────────────────────────────────────
    st.subheader("📦 Export complet en Excel (toutes les tables)")
    if st.button("⬇️ Télécharger le fichier Excel complet", type="primary",
                  use_container_width=True):
        with st.spinner("Génération du fichier Excel..."):
            try:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    for table, label, fname in tables:
                        try:
                            data = sb.table(table).select("*").execute().data or []
                            if data:
                                pd.DataFrame(data).to_excel(
                                    writer, sheet_name=fname[:31], index=False
                                )
                        except: pass
                buf.seek(0)
                st.download_button(
                    "📥 Télécharger vacances_locations_pro_backup.xlsx",
                    data=buf.getvalue(),
                    file_name=f"vlp_backup_complet_{today}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
                st.success("✅ Fichier Excel prêt !")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")

    st.divider()
    st.markdown("### 📅 Recommandations")
    st.markdown("""
    - **Hebdomadaire** : Export Réservations (les données les plus importantes)
    - **Mensuel** : Export complet Excel
    - **Avant chaque mise à jour** : Export complet Excel
    - **Stockage** : Google Drive, Dropbox, ou disque dur externe
    """)
