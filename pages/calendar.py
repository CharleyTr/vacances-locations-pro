"""
Page Calendrier - Vue mensuelle + Vue semaine + Gantt + Blocage dates + Conflits.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import json
from datetime import date, timedelta
from database.proprietes_repo import fetch_all as _fa_props
from services.auth_service import is_unlocked
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_dict, get_propriete_selectionnee, filter_df
from services.conflict_service import detect_conflicts
from database.reservations_repo import insert_reservation
from database.supabase_client import is_connected

COULEURS = {
    "Booking":   "#1565C0",
    "Airbnb":    "#E53935",
    "Direct":    "#2E7D32",
    "Abritel":   "#F57C00",
    "Fermeture": "#9E9E9E",
}
MOIS_FR  = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
             "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
JOURS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def show():
    st.title("📅 Calendrier des réservations")

    df_all = load_reservations()
    _is_admin = st.session_state.get("is_admin", False)
    if _is_admin:
        _auth = [p["id"] for p in _fa_props()]
    else:
        _auth = [p["id"] for p in _fa_props() if not p.get("mot_de_passe") or is_unlocked(p["id"])]
    df_all = df_all[df_all["propriete_id"].isin(_auth)]
    if df_all.empty:
        st.info("Aucune réservation à afficher.")
        return

    df_all["propriete_id"] = df_all["propriete_id"].fillna(0).astype(int)
    prop_choix = get_propriete_selectionnee()
    props      = get_proprietes_dict()
    st.caption(f"DEBUG — prop_choix={prop_choix} type={type(prop_choix).__name__} auth={_auth[:5]}")

    # Si l'utilisateur n'est autorisé que sur une propriété → forcer ce filtre
    if prop_choix == 0 and len(_auth) == 1:
        prop_choix = _auth[0]

    # Limiter props aux propriétés autorisées uniquement
    props = {k: v for k, v in props.items() if k in _auth}

    if prop_choix != 0:
        st.info(f"🏠 {props.get(prop_choix, f'Propriété {prop_choix}')} - changer dans la sidebar")
    else:
        labels_prop  = ["🏠 Toutes"] + list(props.values())
        options_prop = [0] + list(props.keys())
        prop_idx = st.radio("Filtrer par propriété", range(len(labels_prop)),
                             format_func=lambda i: labels_prop[i],
                             horizontal=True, key="cal_prop_local")
        prop_choix = options_prop[prop_idx]

    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        annees = sorted(df_all["annee"].dropna().unique().tolist())
        annee  = st.selectbox("Année", annees, index=len(annees)-1, key="cal_annee")
    with col2:
        mois = st.selectbox("Mois", list(range(1, 13)),
                             format_func=lambda x: MOIS_FR[x],
                             index=date.today().month-1, key="cal_mois")
    with col3:
        vue = st.radio("Vue", ["📅 Mois", "🗓️ Semaine", "📊 Gantt",
                                "🚫 Conflits", "🔒 Bloquer dates"],
                        horizontal=True, key="cal_vue")

    df_f = df_all.copy()
    if prop_choix and prop_choix != 0:
        prop_choix_int = int(prop_choix)
        df_f["propriete_id"] = df_f["propriete_id"].astype(int)
        df_f = df_f[df_f["propriete_id"] == prop_choix_int]

    # Inclure les réservations qui CHEVAUCHENT l'année sélectionnée
    # (pas seulement celles qui commencent dans cette année)
    df_f["date_arrivee"] = pd.to_datetime(df_f["date_arrivee"])
    df_f["date_depart"]  = pd.to_datetime(df_f["date_depart"])
    annee_debut = pd.Timestamp(f"{annee}-01-01")
    annee_fin   = pd.Timestamp(f"{annee}-12-31")
    df_year = df_f[
        (df_f["date_arrivee"] <= annee_fin) &
        (df_f["date_depart"]  >= annee_debut)
    ]

    # ── Bandeau événements du mois ────────────────────────────────────────
    try:
        from database.evenements_repo import get_evenements_mois, COULEURS_TYPE, TYPE_LABELS
        _evts = get_evenements_mois(int(annee), int(mois), 
                                     int(prop_choix) if prop_choix and prop_choix != 0 else None)
        if _evts:
            _evts_html = " &nbsp; ".join([
                f"<span style='background:{e.get('couleur') or COULEURS_TYPE.get(e.get('type',''),'#FF6B35')};"
                f"color:white;padding:2px 10px;border-radius:10px;font-size:12px'>"
                f"{TYPE_LABELS.get(e.get('type',''),'📅')} {e['nom']} "
                f"({e['date_debut'][8:10]}/{e['date_debut'][5:7]}–{e['date_fin'][8:10]}/{e['date_fin'][5:7]})"
                f"</span>"
                for e in _evts
            ])
            st.markdown(
                f"<div style='padding:8px 14px;background:#FFF8E1;border-radius:8px;"
                f"border-left:4px solid #FFB300;margin:6px 0'>"
                f"🎪 <b>Événements :</b> {_evts_html}</div>",
                unsafe_allow_html=True
            )
        else:
            st.caption(f"🔍 Aucun événement pour {mois}/{annee}")
    except Exception as _evt_err:
        st.caption(f"⚠️ Événements: {_evt_err}")

    if "📅 Mois" in vue:
        if df_year.empty:
            st.warning("Aucune réservation pour ces filtres.")
        else:
            _show_google_calendar(df_year, annee, mois)
            _show_month_summary(df_year, annee, mois, props=props)

    elif "🗓️ Semaine" in vue:
        _show_week_view(df_year, annee, mois, props, prop_choix)

    elif "📊 Gantt" in vue:
        if df_year.empty:
            st.warning("Aucune réservation pour ces filtres.")
        else:
            _show_gantt(df_year, prop_choix)

    elif "🚫 Conflits" in vue:
        _show_conflicts(df_all, props, prop_choix)

    elif "🔒 Bloquer" in vue:
        _show_blocage(prop_choix, props)


# ──────────────────────────────────────────────────────────────────────────────
# VUE MOIS (Google Calendar style)
# ──────────────────────────────────────────────────────────────────────────────

def _show_google_calendar(df: pd.DataFrame, annee: int, mois: int):
    st.subheader(f"📅 {MOIS_FR[mois]} {annee}")

    df = df.copy()
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"])
    df["date_depart"]  = pd.to_datetime(df["date_depart"])

    import calendar as cal_lib
    from datetime import date as ddate

    premier_jour = ddate(annee, mois, 1)
    nb_jours     = cal_lib.monthrange(annee, mois)[1]
    dernier_jour = ddate(annee, mois, nb_jours)

    plateau = []
    for d in range(nb_jours):
        current = premier_jour + timedelta(days=d)
        ts = pd.Timestamp(current)
        resa_jour = []
        for _, row in df.iterrows():
            arr = row["date_arrivee"]
            dep = row["date_depart"]
            if arr <= ts < dep:
                resa_jour.append(row)
        plateau.append((current, resa_jour))

    mois_fr_json   = json.dumps(MOIS_FR)
    jours_fr_json  = json.dumps(JOURS_FR)
    couleurs_json  = json.dumps(COULEURS)
    plateau_json   = json.dumps([
        {
            "date": str(j[0]),
            "reservations": [
                {
                    "client":     r.get("nom_client", "-"),
                    "plateforme": r.get("plateforme", "-"),
                    "numero":     r.get("numero_reservation", ""),
                    "arrivee":    str(r["date_arrivee"].date()),
                    "depart":     str(r["date_depart"].date()),
                    "nuitees":    int(r.get("nuitees", 0) or 0),
                    "prix_net":   float(r.get("prix_net", 0) or 0),
                    "paye":       bool(r.get("paye", False)),
                }
                for r in j[1]
            ]
        }
        for j in plateau
    ])

    first_dow = premier_jour.weekday()  # 0=lundi

    html = f"""
<style>
  .cal-wrap  {{ font-family: Arial, sans-serif; user-select:none; }}
  .cal-grid  {{ display:grid; grid-template-columns:repeat(7,1fr); gap:4px; margin-top:8px; }}
  @media (prefers-color-scheme: dark) {{
    .cal-cell  {{ background:#1A2332 !important; border-color:#2D3748 !important; }}
    .cal-cell.today {{ background:#0D2137 !important; border-color:#4A90D9 !important; }}
    .cal-cell.empty {{ background:#111827 !important; border-color:#1F2937 !important; }}
    .cal-day-num {{ color:#9CA3AF !important; }}
  }}
  .cal-hdr   {{ background:#1565C0; color:#fff; text-align:center;
                font-weight:bold; padding:6px; border-radius:4px; font-size:13px; }}
  .cal-cell  {{ background:#fff; border:1px solid var(--border-color,#E0E0E0); border-radius:6px;
                min-height:90px; padding:6px; cursor:default; position:relative; }}
  .cal-cell.today {{ border:2px solid #1565C0; background:var(--bg-info,#E3F2FD); }}
  .cal-cell.empty {{ background:var(--bg-neutral,#FAFAFA); border:1px solid #F0F0F0; }}
  .cal-day-num {{ font-size:12px; color:var(--text-secondary,#666); font-weight:bold; margin-bottom:4px; }}
  .cal-resa  {{ border-radius:4px; padding:2px 5px; font-size:11px;
                margin-bottom:2px; color:#fff; white-space:nowrap;
                overflow:hidden; text-overflow:ellipsis; cursor:pointer;
                transition:opacity .15s; }}
  .cal-resa:hover {{ opacity:.85; }}
  .cal-resa.arrive {{ border-left:4px solid rgba(255,255,255,.6); }}
  .cal-resa.depart {{ border-right:4px solid rgba(255,255,255,.6); }}
  .tooltip   {{ display:none; position:absolute; left:50%; transform:translateX(-50%);
                top:110%; background:#212121; color:#fff; padding:8px 12px;
                border-radius:6px; z-index:999; font-size:12px; min-width:180px;
                box-shadow:0 4px 12px rgba(0,0,0,.3); pointer-events:none; }}
  .cal-cell:hover .tooltip {{ display:block; }}
  @media(max-width:600px) {{ .cal-resa {{ font-size:9px; }} }}
</style>
<div class='cal-wrap'>
<div class='cal-grid'>
  <div class='cal-hdr'>Lun</div><div class='cal-hdr'>Mar</div>
  <div class='cal-hdr'>Mer</div><div class='cal-hdr'>Jeu</div>
  <div class='cal-hdr'>Ven</div><div class='cal-hdr'>Sam</div>
  <div class='cal-hdr'>Dim</div>
</div>
<div class='cal-grid' id='calGrid'></div>
</div>
<script>
const PLATEAU   = {plateau_json};
const COULEURS  = {couleurs_json};
const today     = new Date().toISOString().slice(0,10);
const firstDow  = {first_dow};

function couleur(plat) {{
  return COULEURS[plat] || '#607D8B';
}}

const grid = document.getElementById('calGrid');

// Cases vides avant le 1er
for(let i=0; i<firstDow; i++) {{
  const e = document.createElement('div');
  e.className = 'cal-cell empty';
  grid.appendChild(e);
}}

PLATEAU.forEach(day => {{
  const cell = document.createElement('div');
  cell.className = 'cal-cell' + (day.date === today ? ' today' : '');

  let html = `<div class='cal-day-num'>${{day.date.slice(8)}}</div>`;

  day.reservations.forEach(r => {{
    const isArr = r.arrivee === day.date;
    const isDep = r.depart  === day.date;
    const bg    = couleur(r.plateforme);
    const cls   = isArr ? 'arrive' : (isDep ? 'depart' : '');
    const paye  = r.paye ? '✅' : '⏳';
    // Construire l'URL de la réservation selon la plateforme
    let url = '';
    const num = r.numero || '';
    if (r.plateforme === 'Airbnb' && num) {{
      url = 'https://www.airbnb.fr/hosting/reservations/details/' + num;
    }} else if (r.plateforme === 'Booking' && num) {{
      url = 'https://admin.booking.com/hotel/hoteladmin/extranet_ng/manage/booking.html?res_id=' + num;
    }} else if (r.plateforme === 'Abritel' && num) {{
      url = 'https://www.abritel.fr/';
    }}
    const linkIcon = url ? ' 🔗' : '';
    // Utiliser <a> avec target="_blank" — fonctionne dans l'iframe Streamlit
    const inner = `
        ${{r.plateforme}} - ${{r.client}}${{linkIcon}}
        <div class='tooltip'>
          <b>${{r.client}}</b><br>
          ${{r.arrivee}} → ${{r.depart}}<br>
          ${{r.nuitees}} nuits | ${{r.prix_net.toFixed(0)}} € net ${{paye}}
          ${{url ? '<br><span style=\"color:#90CAF9\">🔗 Ouvrir sur la plateforme</span>' : ''}}
        </div>`;
    if (url) {{
      html += `<a href="${{url}}" target="_blank" style="text-decoration:none">
        <div class='cal-resa ${{cls}}' style='background:${{bg}};cursor:pointer'>${{inner}}</div>
      </a>`;
    }} else {{
      html += `<div class='cal-resa ${{cls}}' style='background:${{bg}}'>${{inner}}</div>`;
    }}
  }});

  cell.innerHTML = html;
  grid.appendChild(cell);
}});
</script>"""

    # Forcer le rechargement de l'iframe quand les données changent
    import hashlib as _hl
    _key = _hl.md5(plateau_json.encode()).hexdigest()[:8]
    components.html(f"<!-- {_key} -->" + html, height=520, scrolling=True)


# ──────────────────────────────────────────────────────────────────────────────
# VUE SEMAINE
# ──────────────────────────────────────────────────────────────────────────────

def _show_week_view(df: pd.DataFrame, annee: int, mois: int, props: dict, prop_choix: int):
    st.subheader("🗓️ Vue semaine")

    # Sélection de la semaine
    import calendar as cal_lib
    premier = date(annee, mois, 1)
    nb_jours = cal_lib.monthrange(annee, mois)[1]

    # Semaines du mois
    semaines = []
    d = premier
    while d <= date(annee, mois, nb_jours):
        lundi = d - timedelta(days=d.weekday())
        dim   = lundi + timedelta(days=6)
        label = f"{lundi.strftime('%d %b')} - {dim.strftime('%d %b')}"
        if label not in [s[0] for s in semaines]:
            semaines.append((label, lundi))
        d += timedelta(days=1)

    sem_labels = [s[0] for s in semaines]
    sem_idx    = st.selectbox("Semaine", range(len(sem_labels)),
                               format_func=lambda i: sem_labels[i], key="cal_sem")
    lundi_sem  = semaines[sem_idx][1]
    jours_sem  = [lundi_sem + timedelta(days=i) for i in range(7)]

    df = df.copy()
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"])
    df["date_depart"]  = pd.to_datetime(df["date_depart"])

    # Affichage grille semaine
    cols = st.columns(7)
    noms_jours = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    today = date.today()

    for i, (col, jour) in enumerate(zip(cols, jours_sem)):
        is_today = jour == today
        bg_hdr   = "#1565C0" if is_today else "#F5F5F5"
        fg_hdr   = "white"   if is_today else "#212121"

        resa_jour = []
        for _, row in df.iterrows():
            arr = row["date_arrivee"].date() if hasattr(row["date_arrivee"], 'date') else row["date_arrivee"]
            dep = row["date_depart"].date()  if hasattr(row["date_depart"],  'date') else row["date_depart"]
            if arr <= jour < dep:
                resa_jour.append(row)

        with col:
            st.markdown(
                f"""<div style='background:{bg_hdr};color:{fg_hdr};
                text-align:center;padding:6px;border-radius:8px 8px 0 0;
                font-weight:bold;font-size:13px'>
                {noms_jours[i]}<br><span style='font-size:18px'>{jour.day}</span>
                </div>""", unsafe_allow_html=True
            )
            if not resa_jour:
                st.markdown(
                    "<div style='background:var(--bg-neutral,#FAFAFA);border:1px solid var(--border-color,#E0E0E0);"
                    "border-radius:0 0 8px 8px;min-height:120px;padding:8px;"
                    "text-align:center;color:#BDBDBD;font-size:12px'>Libre</div>",
                    unsafe_allow_html=True
                )
            else:
                content = ""
                for r in resa_jour:
                    couleur = COULEURS.get(r.get("plateforme", ""), "#607D8B")
                    is_arr  = r["date_arrivee"].date() == jour if hasattr(r["date_arrivee"], 'date') else False
                    is_dep  = r["date_depart"].date()  == jour if hasattr(r["date_depart"],  'date') else False
                    icon    = "→" if is_arr else ("←" if is_dep else "·")
                    content += f"""<div style='background:{couleur};color:white;
                        border-radius:6px;padding:4px 6px;margin:3px 0;
                        font-size:11px;font-weight:bold'>
                        {icon} {r.get('nom_client','?')[:12]}<br>
                        <span style='font-weight:normal'>{r.get('plateforme','')}</span>
                        </div>"""
                st.markdown(
                    f"<div style='border:1px solid var(--border-color,#E0E0E0);border-radius:0 0 8px 8px;"
                    f"padding:6px;min-height:120px'>{content}</div>",
                    unsafe_allow_html=True
                )

    # Taux d'occupation par propriété cette semaine
    if props:
        st.divider()
        st.markdown("**Taux d'occupation cette semaine par propriété :**")
        cols_occ = st.columns(len(props))
        for i, (pid, pnom) in enumerate(props.items()):
            df_p    = df[df["propriete_id"] == pid]
            jours_occ = 0
            for jour in jours_sem:
                for _, row in df_p.iterrows():
                    arr = row["date_arrivee"].date() if hasattr(row["date_arrivee"],'date') else row["date_arrivee"]
                    dep = row["date_depart"].date()  if hasattr(row["date_depart"], 'date') else row["date_depart"]
                    if arr <= jour < dep:
                        jours_occ += 1
                        break
            pct = round(jours_occ / 7 * 100)
            with cols_occ[i]:
                st.metric(f"🏠 {pnom}", f"{pct}%",
                          delta=f"{jours_occ}/7 jours")


# ──────────────────────────────────────────────────────────────────────────────
# TAUX OCCUPATION PAR PROPRIETE (Vue annuelle)
# ──────────────────────────────────────────────────────────────────────────────

def _show_month_summary(df: pd.DataFrame, annee: int, mois: int, props: dict = None):
    import calendar as cal_lib
    from datetime import date as ddate

    ms       = pd.Timestamp(ddate(annee, mois, 1))
    nb_jours = cal_lib.monthrange(annee, mois)[1]
    me_exclu = ms + pd.offsets.MonthBegin(1)

    # props est passé en paramètre depuis show() — déjà filtré par _auth
    # NE PAS appeler get_proprietes_dict() ici

    # Taux occupation côte à côte par propriété
    if len(props) > 1:
        st.divider()
        st.markdown(f"**Taux d'occupation — {MOIS_FR[mois]} {annee} par propriété :**")
        cols = st.columns(len(props))
        for i, (pid, pnom) in enumerate(props.items()):
            df_p = df[df["propriete_id"] == pid].copy()
            df_p["date_arrivee"] = pd.to_datetime(df_p["date_arrivee"])
            df_p["date_depart"]  = pd.to_datetime(df_p["date_depart"])
            df_p_reel = df_p[df_p.get("plateforme", pd.Series(dtype=str)).ne("Fermeture")] \
                if "plateforme" in df_p.columns else df_p

            nuits = 0
            for _, row in df_p_reel.iterrows():
                debut = max(row["date_arrivee"], ms)
                fin   = min(row["date_depart"],  me_exclu)
                nuits += max(0, (fin - debut).days)

            pct = round(nuits / nb_jours * 100, 1)
            ca  = float(df_p_reel["prix_net"].sum()) if "prix_net" in df_p_reel.columns else 0
            with cols[i]:
                st.metric(f"🏠 {pnom}", f"{pct}%",
                          delta=f"{nuits} nuits | {ca:,.0f} €")

        # Pas de return — on continue pour afficher le tableau

    # Résumé mensuel (toutes propriétés ou unique)
    df = df.copy()
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"])
    df["date_depart"]  = pd.to_datetime(df["date_depart"])

    def _nuits_mois(row):
        debut = max(row["date_arrivee"], ms)
        fin   = min(row["date_depart"],  me_exclu)
        return max(0, (fin - debut).days)

    df["nuits_mois"] = df.apply(_nuits_mois, axis=1)

    # Inclure TOUTES les réservations qui ont des nuits dans ce mois
    # (qu'elles arrivent avant ou pendant le mois)
    df_mois = df[df["nuits_mois"] > 0].copy()

    if df_mois.empty:
        return

    st.divider()
    st.subheader(f"📊 Résumé {MOIS_FR[mois]} {annee}")

    df_reel = df_mois[df_mois["plateforme"] != "Fermeture"] if "plateforme" in df_mois.columns else df_mois
    nuits_louees    = int(df_reel["nuits_mois"].sum())
    nuits_fermeture = int(df_mois[df_mois["plateforme"] == "Fermeture"]["nuits_mois"].sum()) \
                      if "plateforme" in df_mois.columns else 0
    # CA rattaché au mois d'ARRIVÉE uniquement (convention comptable)
    # Les résas qui chevauchent 2 mois n'ont leur CA que dans le mois d'arrivée
    df_reel = df_reel.copy()
    df_reel["ca_net_mois"] = df_reel.apply(
        lambda r: float(r.get("prix_net", 0) or 0)
                  if r["date_arrivee"].month == mois and r["date_arrivee"].year == annee
                  else 0.0,
        axis=1
    )
    ca_net = float(df_reel["ca_net_mois"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📅 Réservations",   len(df_reel))
    c2.metric("🌙 Nuits louées",   nuits_louees)
    c3.metric("🔒 Fermeture",      nuits_fermeture)
    c4.metric("💵 CA Net",         f"{ca_net:,.0f} €")
    taux = round((nuits_louees + nuits_fermeture) / nb_jours * 100, 1)
    st.metric("🏡 Taux occupation", f"{taux}%",
              help=f"({nuits_louees} louées + {nuits_fermeture} fermées) / {nb_jours} jours")

    # ── Tableau des réservations du mois ─────────────────────────────────
    st.markdown("#### 📋 Réservations du mois")

    df_display = df_reel.copy()
    df_display["Arrivée"]    = df_display["date_arrivee"].dt.strftime("%d/%m/%Y")
    df_display["Départ"]     = df_display["date_depart"].apply(
        lambda x: str(x)[:10] if pd.notna(x) else "")
    df_display["Nuits mois"] = df_display["nuits_mois"].astype(int)
    # CA, Commission, Ménage : affichés seulement dans le mois d'arrivée
    def _ca_mois(row, col):
        if row["date_arrivee"].month == mois and row["date_arrivee"].year == annee:
            return f"{float(row.get(col, 0) or 0):,.0f} €"
        return "—"  # Pas de CA dans le mois de chevauchement

    df_display["CA Brut"]    = df_display.apply(lambda r: _ca_mois(r, "prix_brut"), axis=1)
    df_display["CA Net"]     = df_display.apply(lambda r: _ca_mois(r, "prix_net"), axis=1)
    df_display["Commission"] = df_display.apply(
        lambda r: _ca_mois(r, "commissions") if "commissions" in r.index else "—", axis=1)
    df_display["Ménage"]     = df_display.apply(
        lambda r: _ca_mois(r, "prix_menage") if "prix_menage" in r.index
                  else (_ca_mois(r, "menage") if "menage" in r.index else "—"), axis=1)
    df_display["Payé"]       = df_display["paye"].apply(lambda v: "✅" if v else "⏳")

    # Ajouter colonne propriété pour debug
    props_map_debug = {p["id"]: p["nom"] for p in _fa_props()}
    df_display["Propriété"] = df_display["propriete_id"].map(
        lambda x: props_map_debug.get(int(x), f"#{x}"))

    cols_show = ["Propriété","nom_client","plateforme","Arrivée","Départ","Nuits mois",
                 "CA Brut","Commission","Ménage","CA Net","Payé"]
    rename_map = {"nom_client":"Client","plateforme":"Plateforme"}
    df_table = df_display[cols_show].rename(columns=rename_map).sort_values("Arrivée")

    st.dataframe(df_table, use_container_width=True, hide_index=True)

    # ── Ligne de totaux ───────────────────────────────────────────────────
    st.markdown("---")
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("📋 Réservations", len(df_reel))
    t2.metric("🌙 Nuits louées", nuits_louees)
    # Totaux uniquement sur les résas dont l'arrivée est dans ce mois
    df_arrivee_mois = df_reel[
        (df_reel["date_arrivee"].dt.month == mois) &
        (df_reel["date_arrivee"].dt.year == annee)
    ]
    ca_brut_total = float(df_arrivee_mois["prix_brut"].fillna(0).sum())
    comm_total    = float(df_arrivee_mois["commissions"].fillna(0).sum())                     if "commissions" in df_arrivee_mois.columns else 0
    t3.metric("💶 CA Brut",    f"{ca_brut_total:,.0f} €")
    t4.metric("🔖 Commissions", f"{comm_total:,.0f} €")
    t5.metric("💵 CA Net",     f"{ca_net:,.0f} €")


# ──────────────────────────────────────────────────────────────────────────────
# GANTT
# ──────────────────────────────────────────────────────────────────────────────

def _show_gantt(df: pd.DataFrame, prop_choix: int):
    st.subheader("📊 Vue Gantt")
    df = df.copy()
    df["date_arrivee"] = pd.to_datetime(df["date_arrivee"])
    df["date_depart"]  = pd.to_datetime(df["date_depart"])
    df = df.dropna(subset=["date_arrivee", "date_depart"])

    props = get_proprietes_dict()
    df["Propriété"] = df["propriete_id"].map(lambda x: props.get(int(x), f"Prop {x}"))
    df["Client"]    = df["nom_client"].fillna("?") + " (" + df["plateforme"].fillna("") + ")"
    df["Info"]      = df["nom_client"].fillna("?") + "<br>" + \
                      df["date_arrivee"].dt.strftime("%d/%m") + " → " + \
                      df["date_depart"].dt.strftime("%d/%m")

    y_col = "Propriété" if prop_choix == 0 else "Client"

    fig = px.timeline(
        df, x_start="date_arrivee", x_end="date_depart", y=y_col,
        color="plateforme",
        hover_name="nom_client",
        hover_data={"date_arrivee": True, "date_depart": True, "nuitees": True, "prix_net": True},
        color_discrete_map=COULEURS,
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=max(350, len(df) * 30 + 100),
                      showlegend=True, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)


# ──────────────────────────────────────────────────────────────────────────────
# DETECTION CONFLITS
# ──────────────────────────────────────────────────────────────────────────────

def _show_conflicts(df: pd.DataFrame, props: dict, prop_choix: int):
    st.subheader("🚫 Détection des conflits")
    st.markdown(
        "Un conflit survient quand deux réservations se chevauchent "
        "sur la **même propriété**."
    )

    df_check = df.copy()
    if prop_choix != 0:
        df_check = df_check[df_check["propriete_id"] == prop_choix]

    # Exclure les fermetures de la détection de conflits
    df_check = df_check[df_check["plateforme"] != "Fermeture"] if "plateforme" in df_check.columns else df_check

    conflicts = detect_conflicts(df_check)

    if conflicts.empty:
        st.success("✅ Aucun conflit détecté ! Toutes les réservations sont cohérentes.")

        # Afficher quand même le récap par propriété
        if props:
            st.divider()
            st.markdown("**Récapitulatif par propriété :**")
            cols = st.columns(len(props))
            for i, (pid, pnom) in enumerate(props.items()):
                df_p = df[df["propriete_id"] == pid]
                with cols[i]:
                    st.metric(f"🏠 {pnom}", f"{len(df_p)} réservations",
                               delta="0 conflit ✅")
        return

    st.error(f"⚠️ {len(conflicts)} conflit(s) détecté(s) !")

    for _, row in conflicts.iterrows():
        prop_nom = props.get(int(row["propriete_id"]), f"Propriété {row['propriete_id']}")
        st.markdown(
            f"""<div style='background:var(--bg-danger,#FFEBEE);border-left:5px solid #C62828;
            padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:12px'>
            <b>🏠 {prop_nom}</b> — Chevauchement de <b>{int(row['overlap_days'])} jour(s)</b><br>
            <table style='margin-top:8px;font-size:13px;width:100%'>
              <tr>
                <td>📋 <b>{row['res1_client']}</b></td>
                <td>{row['res1_arrivee']} → {row['res1_depart']}</td>
                <td><span style='background:#1565C0;color:white;padding:2px 8px;border-radius:12px'>
                    {row['res1_plat']}</span></td>
              </tr>
              <tr style='margin-top:4px'>
                <td>📋 <b>{row['res2_client']}</b></td>
                <td>{row['res2_arrivee']} → {row['res2_depart']}</td>
                <td><span style='background:#E53935;color:white;padding:2px 8px;border-radius:12px'>
                    {row['res2_plat']}</span></td>
              </tr>
            </table>
            </div>""", unsafe_allow_html=True
        )

    # Export CSV des conflits
    if not conflicts.empty:
        csv = conflicts.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exporter les conflits", csv,
                           file_name="conflits.csv", mime="text/csv")


# ──────────────────────────────────────────────────────────────────────────────
# BLOCAGE DATES
# ──────────────────────────────────────────────────────────────────────────────

def _show_blocage(prop_choix: int, props: dict):
    st.subheader("🔒 Bloquer des dates")
    st.markdown(
        "Créez une **Fermeture** directement depuis le calendrier "
        "(travaux, indisponibilité, usage personnel...)."
    )

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise pour bloquer des dates.")
        return

    if not props:
        st.info("Aucune propriété configurée.")
        return

    # Sélection propriété
    if prop_choix != 0:
        prop_id  = prop_choix
        prop_nom = props.get(prop_choix, "")
        st.info(f"🏠 Propriété : **{prop_nom}**")
    else:
        prop_id = st.selectbox("Propriété", options=list(props.keys()),
                                format_func=lambda x: props[x], key="bloc_prop")
        prop_nom = props[prop_id]

    col1, col2 = st.columns(2)
    with col1:
        date_debut = st.date_input("Début du blocage",  value=date.today(), key="bloc_debut")
    with col2:
        date_fin   = st.date_input("Fin du blocage",    value=date.today() + timedelta(days=7), key="bloc_fin")

    raison = st.selectbox("Raison", [
        "Travaux", "Usage personnel", "Maintenance", "Indisponibilité", "Autre"
    ], key="bloc_raison")

    note = st.text_input("Note (optionnel)", placeholder="Ex: Plombier prévu ces jours-là", key="bloc_note")

    nuitees = (date_fin - date_debut).days
    if nuitees <= 0:
        st.warning("La date de fin doit être après la date de début.")
        return

    st.info(f"🔒 **{nuitees} nuit(s)** bloquée(s) sur **{prop_nom}**")

    if st.button("🔒 Bloquer ces dates", type="primary", use_container_width=True):
        data = {
            "propriete_id":       prop_id,
            "nom_client":         raison,
            "plateforme":         "Fermeture",
            "date_arrivee":       date_debut.isoformat(),
            "date_depart":        date_fin.isoformat(),
            "nuitees":            nuitees,
            "prix_brut":          0.0,
            "prix_net":           0.0,
            "commissions":        0.0,
            "commissions_hote":   0.0,
            "menage":             0.0,
            "taxes_sejour":       0.0,
            "base":               0.0,
            "charges":            0.0,
            "pct_commission":     0.0,
            "paye":               True,
            "numero_reservation": note or raison,
        }
        try:
            result = insert_reservation(data)
            if result:
                st.success(f"✅ Dates bloquées du {date_debut} au {date_fin} ({nuitees} nuits) !")
                st.balloons()
            else:
                st.error("Erreur lors du blocage.")
        except Exception as e:
            st.error(f"Erreur : {e}")

    # Fermetures existantes pour cette propriété
    st.divider()
    df_all = load_reservations()
    df_ferm = df_all[
        (df_all["plateforme"] == "Fermeture") &
        (df_all["propriete_id"] == prop_id)
    ].copy() if not df_all.empty else pd.DataFrame()

    if not df_ferm.empty:
        df_ferm["date_arrivee"] = pd.to_datetime(df_ferm["date_arrivee"])
        df_ferm = df_ferm[df_ferm["date_arrivee"] >= pd.Timestamp(date.today())]

    if not df_ferm.empty:
        st.markdown(f"**Fermetures à venir ({len(df_ferm)}) :**")
        for _, row in df_ferm.sort_values("date_arrivee").iterrows():
            arr = str(row["date_arrivee"])[:10]
            dep = str(row.get("date_depart", ""))[:10]
            st.markdown(
                f"<div style='background:var(--bg-neutral,#F5F5F5);border-left:4px solid #9E9E9E;"
                f"padding:8px 14px;border-radius:0 6px 6px 0;margin-bottom:6px'>"
                f"🔒 <b>{row.get('nom_client','')}</b> &nbsp;|&nbsp; {arr} → {dep} "
                f"({int(row.get('nuitees',0) or 0)} nuits)</div>",
                unsafe_allow_html=True
            )
    else:
        st.caption("Aucune fermeture à venir.")
