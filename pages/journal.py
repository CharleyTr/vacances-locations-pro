"""
Page Journal des connexions — admin uniquement.
"""
import streamlit as st
import pandas as pd
from database.journal_repo import get_journal, get_stats_connexions


def show():
    st.title("📋 Journal des connexions")
    st.caption("Historique de toutes les connexions à l'application.")

    if not st.session_state.get("is_admin", False):
        st.error("⛔ Accès réservé à l'administrateur.")
        return

    stats = get_stats_connexions()

    # ── KPIs ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🔢 Total",           stats.get("total", 0))
    c2.metric("📅 Aujourd'hui",     stats.get("today", 0))
    c3.metric("📆 Cette semaine",   stats.get("week",  0))
    c4.metric("❌ Échecs aujourd'hui", stats.get("echecs_today", 0))
    c5.metric("🕐 Dernière connexion", stats.get("last", "—"))

    st.divider()

    # ── Filtres ───────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filtre_statut = st.selectbox("Statut", ["Tous", "✅ Succès", "❌ Échecs"], key="j_statut")
    with col_f2:
        filtre_mode = st.selectbox("Mode", ["Tous", "🔑 Code PIN", "📧 Email"], key="j_mode")
    with col_f3:
        filtre_search = st.text_input("🔎 Recherche email / propriété", key="j_search")

    # ── Données ───────────────────────────────────────────────────────────
    rows = get_journal(limit=500)

    if not rows:
        st.info("Aucune connexion enregistrée pour l'instant.")
        return

    df = pd.DataFrame(rows)

    # Appliquer filtres
    if filtre_statut == "✅ Succès":
        df = df[df["statut"] == "succes"]
    elif filtre_statut == "❌ Échecs":
        df = df[df["statut"] == "echec"]

    if filtre_mode == "🔑 Code PIN":
        df = df[df["mode"] == "pin"]
    elif filtre_mode == "📧 Email":
        df = df[df["mode"] == "email"]

    if filtre_search:
        mask = (
            df["user_email"].fillna("").str.contains(filtre_search, case=False) |
            df["propriete_nom"].fillna("").str.contains(filtre_search, case=False)
        )
        df = df[mask]

    st.caption(f"**{len(df)}** connexion(s) affichée(s)")

    # ── Tableau ───────────────────────────────────────────────────────────
    def fmt_statut(s):
        return "✅ Succès" if s == "succes" else "❌ Échec"

    def fmt_mode(m):
        return "🔑 PIN" if m == "pin" else "📧 Email"

    df_display = df[["created_at","statut","mode","user_email","propriete_nom","detail"]].copy()
    df_display["created_at"]   = df_display["created_at"].str[:16].str.replace("T"," ")
    df_display["statut"]       = df_display["statut"].apply(fmt_statut)
    df_display["mode"]         = df_display["mode"].apply(fmt_mode)
    df_display["user_email"]   = df_display["user_email"].fillna("—")
    df_display["propriete_nom"]= df_display["propriete_nom"].fillna("—")
    df_display["detail"]       = df_display["detail"].fillna("")

    df_display.columns = ["Date/heure", "Statut", "Mode", "Email", "Propriété", "Détail"]

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Statut": st.column_config.TextColumn(width="small"),
            "Mode":   st.column_config.TextColumn(width="small"),
        }
    )

    # ── Export ────────────────────────────────────────────────────────────
    csv = df_display.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exporter CSV", csv, "journal_connexions.csv", "text/csv")
