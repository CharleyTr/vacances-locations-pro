import streamlit as st
import plotly.express as px
from services.reservation_service import load_reservations
from services.analytics_service import compute_kpis, compute_monthly
from services.proprietes_service import get_proprietes_dict


def show():
    st.title("📈 Analyses financières")

    # ── DEBUG — à retirer après validation ───────────────────────────────
    with st.expander("🔍 Debug session_state", expanded=True):
        prop_val = st.session_state.get("propriete_selectionnee", "ABSENT")
        st.write(f"**propriete_selectionnee** = `{prop_val}` (type: `{type(prop_val).__name__}`)")
        st.write("**session_state complet :**", dict(st.session_state))

    df_all = load_reservations()
    if df_all.empty:
        st.info("Aucune donnée disponible.")
        return

    # ── Debug df ─────────────────────────────────────────────────────────
    with st.expander("🔍 Debug données"):
        st.write(f"Total lignes : {len(df_all)}")
        st.write(f"propriete_id unique : {sorted(df_all['propriete_id'].unique().tolist())}")
        st.write(f"types propriete_id : {df_all['propriete_id'].dtype}")
        st.dataframe(df_all[["id","nom_client","propriete_id","plateforme"]].head(5))

    # ── Filtre propriété ──────────────────────────────────────────────────
    prop_id = st.session_state.get("propriete_selectionnee", 0)

    # Forcer int (Supabase peut renvoyer float)
    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)
    prop_id = int(prop_id) if prop_id else 0

    if prop_id != 0:
        df = df_all[df_all["propriete_id"] == prop_id]
    else:
        df = df_all

    props = get_proprietes_dict()
    label = props.get(prop_id, "Toutes les propriétés") if prop_id else "Toutes les propriétés"

    st.info(f"🏠 **{label}** — {len(df)} réservation(s) affichées")

    annees = sorted(df["annee"].dropna().unique().tolist(), reverse=True)
    if not annees:
        st.warning("Aucune donnée pour cette propriété.")
        return

    annee = st.selectbox("Année", annees, index=0)
    df_an = df[df["annee"] == annee]

    kpis = compute_kpis(df_an)

    st.subheader(f"Bilan {annee}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 CA Brut",    f"{kpis['ca_brut']:,.0f} €")
    c2.metric("💵 CA Net",      f"{kpis['ca_net']:,.0f} €")
    c3.metric("🔖 Commissions", f"{kpis['commissions']:,.0f} €")
    c4.metric("🧹 Ménages",     f"{kpis['menage']:,.0f} €")

    monthly = compute_monthly(df_an)
    if not monthly.empty:
        fig = px.bar(monthly, x="mois_str", y=["ca_brut", "ca_net"],
                     barmode="group",
                     labels={"value": "€", "mois_str": "Mois", "variable": ""},
                     color_discrete_map={"ca_brut": "#90CAF9", "ca_net": "#1565C0"})
        st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Répartition plateformes")
        plat = df_an.groupby("plateforme").agg(ca_net=("prix_net","sum"), nb=("id","count")).reset_index()
        fig2 = px.pie(plat, names="plateforme", values="ca_net",
                      color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("Revenu moyen / nuit")
        if not monthly.empty and "nuits" in monthly.columns:
            monthly["rev_par_nuit"] = (monthly["ca_net"] / monthly["nuits"].replace(0,1)).round(2)
            fig3 = px.line(monthly, x="mois_str", y="rev_par_nuit", markers=True,
                           labels={"rev_par_nuit": "€/nuit", "mois_str": "Mois"})
            st.plotly_chart(fig3, use_container_width=True)
