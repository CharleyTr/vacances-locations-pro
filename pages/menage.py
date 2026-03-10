"""
Page Ménage — Planning des interventions par propriété.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_dict, filter_df




def show():
    st.title("🧹 Planning Ménage")

    df_all = load_reservations()
    df = filter_df(df_all)
    if df.empty:
        st.info("Aucune réservation disponible.")
        return

    today    = pd.Timestamp(date.today())
    in_7     = today + timedelta(days=7)
    in_30    = today + timedelta(days=30)

    # Construire le planning : chaque départ = un ménage
    planning = _build_planning(df, today)

    if planning.empty:
        st.info("Aucun ménage planifié.")
        return

    # ── KPIs ──────────────────────────────────────────────────────────────
    urgents  = planning[planning["date_menage"] <= in_7]
    a_venir  = planning[(planning["date_menage"] > in_7) & (planning["date_menage"] <= in_30)]
    passes   = planning[planning["date_menage"] < today]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔴 Cette semaine",  len(urgents))
    c2.metric("🟡 Dans 30 jours",  len(a_venir))
    c3.metric("📋 Total à venir",  len(planning[planning["date_menage"] >= today]))
    c4.metric("✅ Passés",         len(passes))

    st.divider()

    # ── Filtres ───────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        periode = st.selectbox("Période", [
            "Cette semaine", "Ce mois", "Tous à venir", "Historique complet"
        ])
    with col2:
        prop_filter = st.multiselect(
            "Propriété",
            options=list(PROPRIETES.keys()),
            default=list(PROPRIETES.keys()),
            format_func=lambda x: get_proprietes_dict().get(x, f"Propriété {x}")
        )

    # Appliquer filtres
    df_plan = planning.copy()
    if prop_filter:
        df_plan = df_plan[df_plan["propriete_id"].isin(prop_filter)]

    if periode == "Cette semaine":
        df_plan = df_plan[(df_plan["date_menage"] >= today) & (df_plan["date_menage"] <= in_7)]
    elif periode == "Ce mois":
        df_plan = df_plan[(df_plan["date_menage"] >= today) & (df_plan["date_menage"] <= in_30)]
    elif periode == "Tous à venir":
        df_plan = df_plan[df_plan["date_menage"] >= today]

    df_plan = df_plan.sort_values("date_menage")

    if df_plan.empty:
        st.info("Aucun ménage pour cette période.")
        return

    st.subheader(f"📋 {len(df_plan)} intervention(s)")

    # Vue par propriété
    for prop_id in sorted(df_plan["propriete_id"].unique()):
        nom_prop = get_proprietes_dict().get(int(prop_id), f"Propriété {prop_id}")
        df_prop  = df_plan[df_plan["propriete_id"] == prop_id]

        with st.expander(f"🏠 {nom_prop} — {len(df_prop)} ménage(s)", expanded=True):
            for _, row in df_prop.iterrows():
                date_m  = row["date_menage"]
                jours   = (date_m - today).days

                if jours < 0:
                    badge = "✅ Passé"
                    color = "#E8F5E9"
                elif jours == 0:
                    badge = "🔴 Aujourd'hui !"
                    color = "#FFEBEE"
                elif jours <= 2:
                    badge = f"🔴 Dans {jours}j"
                    color = "#FFEBEE"
                elif jours <= 7:
                    badge = f"🟡 Dans {jours}j"
                    color = "#FFFDE7"
                else:
                    badge = f"🟢 Dans {jours}j"
                    color = "#F1F8E9"

                prochain = row.get("prochain_client", "—")
                duree    = row.get("nuitees_suivantes", "")
                duree_txt = f" ({duree} nuits)" if duree else ""

                st.markdown(
                    f"""<div style='background:{color}; padding:10px 14px; border-radius:8px; margin-bottom:8px;'>
                    <b>{date_m.strftime('%A %d %B %Y').capitalize()}</b> &nbsp;—&nbsp; {badge}<br>
                    <small>🛏️ Départ : <b>{row['nom_client']}</b> &nbsp;|&nbsp;
                    ➡️ Arrivée : <b>{prochain}{duree_txt}</b></small>
                    </div>""",
                    unsafe_allow_html=True
                )

    st.divider()

    # Export CSV du planning
    export = df_plan.copy()
    export["date_menage"] = export["date_menage"].dt.strftime("%d/%m/%Y")
    export["propriete"]   = export["propriete_id"].map(
        lambda x: get_proprietes_dict().get(int(x), f"Propriété {x}")
    )
    csv = export[["date_menage", "propriete", "nom_client", "prochain_client"]].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Exporter planning ménage", csv,
                       file_name="planning_menage.csv", mime="text/csv")


def _build_planning(df: pd.DataFrame, today: pd.Timestamp) -> pd.DataFrame:
    """Construit le planning en associant chaque départ à l'arrivée suivante."""
    rows = []
    for prop_id in df["propriete_id"].unique():
        df_prop = df[df["propriete_id"] == prop_id].sort_values("date_arrivee").reset_index(drop=True)

        for i, row in df_prop.iterrows():
            prochain_client = "—"
            nuitees_suiv    = None

            if i + 1 < len(df_prop):
                next_row = df_prop.iloc[i + 1]
                prochain_client = next_row["nom_client"]
                nuitees_suiv    = int(next_row.get("nuitees", 0))

            rows.append({
                "propriete_id":      prop_id,
                "date_menage":       pd.Timestamp(row["date_depart"]),
                "nom_client":        row["nom_client"],
                "prochain_client":   prochain_client,
                "nuitees_suivantes": nuitees_suiv,
                "nuitees":           row.get("nuitees", 0),
            })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)
