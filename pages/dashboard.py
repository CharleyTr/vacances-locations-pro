import streamlit as st
import pandas as pd
import plotly.express as px
from services.reservation_service import load_reservations
from services.analytics_service import compute_kpis, compute_monthly
from services.alert_service import upcoming_arrivals, unpaid_reservations
from database.supabase_client import is_connected, get_supabase
from services.proprietes_service import get_proprietes_dict, filter_df, get_propriete_selectionnee




def show():
    # ── Bandeau arrivées demain ──────────────────────────────────────────────
    try:
        from datetime import date, timedelta
        import pandas as pd
        _demain = date.today() + timedelta(days=1)
        _df_all = load_reservations()
        if not _df_all.empty:
            _df_all["date_arrivee"] = pd.to_datetime(_df_all["date_arrivee"])
            _arr = _df_all[
                (_df_all["date_arrivee"].dt.date == _demain) &
                (_df_all["plateforme"] != "Fermeture")
            ]
            if not _arr.empty:
                _lignes = []
                for _, _r in _arr.iterrows():
                    _tel = str(_r.get("telephone","") or "")
                    _lignes.append(
                        f"<b>{_r.get('nom_client','?')}</b> — "
                        f"{_r.get('plateforme','?')} — "
                        f"📱 {_tel if _tel else 'pas de tél'}"
                    )
                st.markdown(
                    f"<div style='background:#1B5E20;border-left:5px solid #69F0AE;"
                    f"padding:12px 18px;border-radius:0 8px 8px 0;margin-bottom:16px'>"
                    f"<b style='color:#69F0AE;font-size:15px'>🏠 Arrivée(s) demain "
                    f"({_demain.strftime('%d/%m/%Y')}) :</b><br>"
                    f"<span style='color:#FFFFFF'>{'<br>'.join(_lignes)}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    except Exception as _e:
        st.caption(f"⚠️ Bandeau: {_e}")

    st.title("📊 Dashboard")

    if is_connected():
        st.success("🟢 Connecté à Supabase", icon="✅")
    else:
        st.warning("🟡 Mode hors ligne — données CSV locales", icon="⚠️")

    # ── Diagnostic table vide ─────────────────────────────────────────────
    if is_connected():
        try:
            sb = get_supabase()
            count = sb.table("reservations").select("id", count="exact").execute()
            nb = count.count if hasattr(count, "count") else len(count.data)
            if nb == 0:
                st.warning("⚠️ **La table Supabase est vide.**")
                st.info("Allez dans 📋 Réservations → 📤 Import CSV pour importer vos données.")
                return
        except Exception as e:
            err_str = str(e)
            if "JWT" in err_str or "expired" in err_str or "PGRST303" in err_str:
                # JWT expiré — renouveler le client Supabase
                try:
                    from database.supabase_client import _reset_client
                    _reset_client()
                except Exception:
                    pass
                st.warning("⚠️ Session expirée — rechargement en cours...")
                import time; time.sleep(1)
                st.rerun()
            else:
                st.error(f"Erreur vérification table : {e}")
                return

    df_all = load_reservations()
    if df_all.empty:
        st.info("Aucune réservation chargée.")
        return

    # ── Filtre propriété ──────────────────────────────────────────────────
    # Filtre propriété depuis la sidebar (session_state)
    prop_choix = get_propriete_selectionnee()
    props = get_proprietes_dict()

    col_info, col_annee, _ = st.columns([3, 2, 3])
    with col_info:
        if prop_choix != 0:
            st.info(f"🏠 {props.get(prop_choix, f'Propriété {prop_choix}')}")
        else:
            st.info(f"🏠 Toutes les propriétés ({len(props)})")
    with col_annee:
        annees = sorted(df_all["annee"].dropna().unique().tolist(), reverse=True)
        annee_choix = st.selectbox("📆 Année", ["Toutes"] + annees, key="dash_annee")

    # Appliquer filtres
    df = filter_df(df_all, prop_choix)
    if annee_choix != "Toutes":
        df = df[df["annee"] == int(annee_choix)]

    if df.empty:
        st.info("Aucune réservation pour ce filtre.")
        return

    kpis = compute_kpis(df)

    # ── Calcul Fermeture directement dans le dashboard ────────────────────
    df_c = df.copy()
    df_c["date_arrivee"] = pd.to_datetime(df_c["date_arrivee"])
    df_c["date_depart"]  = pd.to_datetime(df_c["date_depart"])
    mask_ferm   = df_c["plateforme"] == "Fermeture"
    df_ferm     = df_c[mask_ferm]
    df_reel     = df_c[~mask_ferm]

    def _n(d):
        if d.empty: return 0
        n = d["nuitees"].copy() if "nuitees" in d.columns else pd.Series(dtype=float)
        if n.empty: n = pd.Series([0]*len(d))
        mask0 = n.isna() | (n == 0)
        if mask0.any():
            n.loc[mask0] = (d.loc[mask0,"date_depart"] - d.loc[mask0,"date_arrivee"]).dt.days
        return int(n.fillna(0).sum())

    nuits_fermeture = _n(df_ferm)
    nuits_louees    = _n(df_reel)
    ca_net_reel     = float(df_reel["prix_net"].sum()) if not df_reel.empty else 0
    revenu_nuit     = round(ca_net_reel / nuits_louees) if nuits_louees > 0 else 0
    label_nuits     = f"{nuits_louees} (+{nuits_fermeture}🔒)" if nuits_fermeture else str(nuits_louees)

    # ── KPIs ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 CA Brut",       f"{kpis['ca_brut']:,.0f} €")
    c2.metric("💵 CA Net",         f"{kpis['ca_net']:,.0f} €")
    c3.metric("📅 Réservations",   len(df_reel))
    c4.metric("🌙 Nuits louées",   label_nuits)
    c5.metric("📈 Revenu / nuit",  f"{revenu_nuit:.0f} €")

    c6, c7, c8 = st.columns(3)
    frais_cb_total = float(df_reel["frais_cb"].fillna(0).sum())                      if "frais_cb" in df_reel.columns else 0
    c6.metric("⏳ En attente",      f"{kpis['montant_en_attente']:,.0f} €")
    c7.metric("🏡 Taux occupation", f"{kpis['taux_occupation']} %")
    c8.metric("🔖 Commissions",     f"{kpis['commissions']:,.0f} €")
    c9, c10 = st.columns(2)
    c9.metric("💳 Frais CB",        f"{frais_cb_total:,.0f} €",
              help="Total des frais carte bancaire sur la période")
    ca_net_apres_cb = (kpis['ca_net'] - frais_cb_total) if frais_cb_total else kpis['ca_net']
    c10.metric("💵 CA Net (après CB)", f"{ca_net_apres_cb:,.0f} €",
               delta=f"-{frais_cb_total:,.0f} €" if frais_cb_total else None,
               delta_color="inverse")

    st.divider()

    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("📆 CA mensuel")
        monthly = compute_monthly(df)
        if not monthly.empty:
            fig = px.bar(monthly, x="mois_str", y="ca_net",
                         labels={"mois_str": "Mois", "ca_net": "CA Net (€)"},
                         color_discrete_sequence=["#2196F3"])
            fig.update_layout(height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("🏷️ Répartition plateformes")
        if kpis["repartition_plateformes"]:
            fig2 = px.pie(
                names=list(kpis["repartition_plateformes"].keys()),
                values=list(kpis["repartition_plateformes"].values()),
                color_discrete_sequence=px.colors.qualitative.Set2)
            fig2.update_layout(height=300, margin=dict(t=20, b=20))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🔔 Arrivées dans 3 jours")
        arrivees = upcoming_arrivals(df)
        if arrivees.empty:
            st.info("Aucune arrivée imminente")
        else:
            st.dataframe(arrivees[["nom_client", "date_arrivee", "plateforme", "nuitees"]],
                         use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("⚠️ Paiements en attente")
        non_payes = unpaid_reservations(df)
        if non_payes.empty:
            st.success("Tous les séjours sont payés ✅")
        else:
            st.dataframe(non_payes[["nom_client", "date_arrivee", "prix_net", "plateforme"]],
                         use_container_width=True, hide_index=True)
