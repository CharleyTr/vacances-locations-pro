"""
Page Paiements — Suivi complet des paiements, acomptes, soldes.
"""
import streamlit as st
import pandas as pd
from datetime import date
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_dict, filter_df, get_propriete_selectionnee
from database.supabase_client import is_connected
import database.reservations_repo as repo




def show():
    st.title("💳 Suivi des paiements")

    df_all = load_reservations()
    df = filter_df(df_all)
    if df.empty:
        st.info("Aucune réservation disponible.")
        return

    # ── KPIs paiements ────────────────────────────────────────────────────
    payes     = df[df["paye"] == True]
    non_payes = df[df["paye"] == False]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Payées",        len(payes),
              f"{payes['prix_net'].sum():,.0f} €")
    c2.metric("⏳ En attente",    len(non_payes),
              f"{non_payes['prix_net'].sum():,.0f} €")
    c3.metric("💰 CA Net total",  f"{df['prix_net'].sum():,.0f} €")
    c4.metric("📊 Taux recouvrement",
              f"{len(payes)/len(df)*100:.0f} %" if len(df) > 0 else "—")

    st.divider()

    # ── Onglets ───────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "⏳ En attente", "✅ Payées", "📅 À venir"
    ])

    with tab1:
        _show_non_payes(non_payes)

    with tab2:
        _show_payes(payes)

    with tab3:
        _show_a_venir(df)


def _show_non_payes(df: pd.DataFrame):
    st.subheader(f"⏳ {len(df)} paiement(s) en attente")

    if df.empty:
        st.success("🎉 Tous les séjours sont payés !")
        return

    cols = ["id", "nom_client", "propriete_id", "plateforme",
            "date_arrivee", "date_depart", "prix_net", "paye"]
    cols_ok = [c for c in cols if c in df.columns]
    df_view = df[cols_ok].sort_values("date_arrivee").copy()
    df_view["propriete_id"] = df_view["propriete_id"].map(
        lambda x: get_proprietes_dict().get(int(x), f"Prop {x}")
    )

    st.dataframe(
        df_view.rename(columns={
            "id": "ID", "nom_client": "Client",
            "propriete_id": "Propriété", "plateforme": "Plateforme",
            "date_arrivee": "Arrivée", "date_depart": "Départ",
            "prix_net": "Montant (€)", "paye": "Payé"
        }),
        use_container_width=True, hide_index=True,
        column_config={
            "Montant (€)": st.column_config.NumberColumn(format="%.2f €"),
            "Payé": st.column_config.CheckboxColumn(),
        }
    )

    st.divider()

    # Marquage rapide comme payé
    if is_connected():
        st.subheader("✅ Marquer comme payé")
        options = {
            row["id"]: f"#{row['id']} — {row['nom_client']} ({row['prix_net']:.0f} €)"
            for _, row in df.iterrows()
        }
        selected = st.selectbox(
            "Choisir une réservation",
            options=list(options.keys()),
            format_func=lambda x: options[x],
            key="sel_paiement"
        )
        col_a, col_b = st.columns([2, 1])
        with col_a:
            note = st.text_input("Note (optionnel)", placeholder="Ex: virement reçu le 01/01")
        with col_b:
            if st.button("✅ Marquer payé", type="primary", use_container_width=True):
                try:
                    repo.update_reservation(selected, {"paye": True})
                    st.success(f"✅ Réservation #{selected} marquée comme payée !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")
    else:
        st.warning("⚠️ Connexion Supabase requise pour modifier les paiements.")


def _show_payes(df: pd.DataFrame):
    st.subheader(f"✅ {len(df)} paiement(s) encaissé(s)")

    if df.empty:
        st.info("Aucun paiement enregistré.")
        return

    # Par mois
    if "mois" in df.columns:
        monthly = df.groupby("mois").agg(
            nb=("id", "count"),
            total=("prix_net", "sum")
        ).reset_index()
        monthly["mois_str"] = monthly["mois"].dt.strftime("%B %Y")
        monthly["total"] = monthly["total"].round(0).astype(int)

        import plotly.express as px
        fig = px.bar(monthly, x="mois_str", y="total",
                     labels={"mois_str": "Mois", "total": "CA Net (€)"},
                     color_discrete_sequence=["#43A047"])
        fig.update_layout(height=250, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    cols = ["id", "nom_client", "plateforme", "date_arrivee", "prix_net"]
    cols_ok = [c for c in cols if c in df.columns]
    st.dataframe(
        df[cols_ok].sort_values("date_arrivee", ascending=False),
        use_container_width=True, hide_index=True,
        column_config={
            "prix_net": st.column_config.NumberColumn("Montant", format="%.2f €"),
        }
    )


def _show_a_venir(df: pd.DataFrame):
    st.subheader("📅 Paiements des séjours à venir")
    today = pd.Timestamp(date.today())
    df_futur = df[df["date_arrivee"] >= today].sort_values("date_arrivee")

    if df_futur.empty:
        st.info("Aucun séjour à venir.")
        return

    cols = ["id", "nom_client", "plateforme", "date_arrivee", "date_depart",
            "nuitees", "prix_net", "paye", "statut_paiement"]
    cols_ok = [c for c in cols if c in df_futur.columns]

    st.dataframe(
        df_futur[cols_ok],
        use_container_width=True, hide_index=True,
        column_config={
            "prix_net": st.column_config.NumberColumn("Montant", format="%.2f €"),
            "paye": st.column_config.CheckboxColumn("Payé"),
        }
    )

    non_payes_futur = df_futur[df_futur["paye"] == False]
    if not non_payes_futur.empty:
        total_attendu = non_payes_futur["prix_net"].sum()
        st.warning(
            f"💡 **{len(non_payes_futur)} séjour(s)** à venir non payés "
            f"— {total_attendu:,.0f} € à encaisser"
        )
