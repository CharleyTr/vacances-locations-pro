"""
Page Calendrier - Vue Google Calendar mensuelle + Vue Gantt.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import json
from datetime import date, timedelta
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_dict, get_propriete_selectionnee, filter_df



COULEURS = {
    "Booking":   "#1565C0",
    "Airbnb":    "#E53935",
    "Direct":    "#2E7D32",
    "Abritel":   "#F57C00",
    "Fermeture": "#9E9E9E",
}

MOIS_FR = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
           "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
JOURS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]


def show():
    st.title("📅 Calendrier des réservations")

    df = load_reservations()
    if df.empty:
        st.info("Aucune réservation à afficher.")
        return

    # ── Forcer propriete_id en int ────────────────────────────────────────
    df["propriete_id"] = df["propriete_id"].fillna(0).astype(int)

    # ── Filtre propriété depuis sidebar ───────────────────────────────────
    prop_choix = get_propriete_selectionnee()
    props = get_proprietes_dict()

    # Affichage propriété active
    if prop_choix != 0:
        st.info(f"🏠 {props.get(prop_choix, f'Propriété {prop_choix}')} — changer dans la sidebar")
    else:
        # Boutons rapides si toutes sélectionnées
        labels_prop  = ["🏠 Toutes"] + list(props.values())
        options_prop = [0] + list(props.keys())
        prop_idx = st.radio(
            "Filtrer par propriété",
            range(len(labels_prop)),
            format_func=lambda i: labels_prop[i],
            horizontal=True,
            key="cal_prop_local"
        )
        prop_choix = options_prop[prop_idx]

    # ── Autres contrôles ──────────────────────────────────────────────────
    col2, col3, col4 = st.columns([2, 2, 2])
    with col2:
        annees = sorted(df["annee"].dropna().unique().tolist())
        annee = st.selectbox("Année", annees, index=len(annees) - 1, key="cal_annee")
    with col3:
        mois_idx = date.today().month
        mois = st.selectbox("Mois", list(range(1, 13)),
                            format_func=lambda x: MOIS_FR[x],
                            index=mois_idx - 1, key="cal_mois")
    with col4:
        vue = st.radio("Vue", ["📅 Calendrier", "📊 Gantt"], horizontal=True, key="cal_vue")

    # ── Filtrage ──────────────────────────────────────────────────────────
    df_f = df.copy()
    if prop_choix != 0:
        df_f = df_f[df_f["propriete_id"] == prop_choix]
    df_f = df_f[df_f["annee"] == annee]

    if df_f.empty:
        st.warning("Aucune réservation pour ces filtres.")
        return

    if "📅 Calendrier" in vue:
        _show_google_calendar(df_f, annee, mois)
    else:
        _show_gantt(df_f, prop_choix)


# ──────────────────────────────────────────────────────────────────────────────
# VUE GOOGLE CALENDAR
# ──────────────────────────────────────────────────────────────────────────────

def _show_google_calendar(df: pd.DataFrame, annee: int, mois: int):
    st.subheader(f"📅 {MOIS_FR[mois]} {annee}")

    # Construire les events JSON pour le mois affiché + débordement
    events = _build_events(df, annee, mois)
    events_json = json.dumps(events)
    couleurs_json = json.dumps(COULEURS)
    mois_fr_json  = json.dumps(MOIS_FR)
    jours_fr_json = json.dumps(JOURS_FR)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}

  body {{ background: #f8f9fa; padding: 8px; }}

  .cal-header {{
    display: flex; align-items: center; justify-content: space-between;
    background: white; border-radius: 10px; padding: 12px 20px;
    margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  }}
  .cal-header h2 {{ font-size: 18px; color: #1a1a2e; font-weight: 600; }}
  .nav-btn {{
    background: #f1f3f4; border: none; border-radius: 6px;
    padding: 6px 14px; cursor: pointer; font-size: 14px; color: #444;
    transition: background 0.2s;
  }}
  .nav-btn:hover {{ background: #e0e0e0; }}

  .legend {{
    display: flex; gap: 12px; flex-wrap: wrap;
    background: white; border-radius: 10px; padding: 10px 16px;
    margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.08);
  }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 12px; color: #555; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}

  .cal-grid {{
    background: white; border-radius: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1); overflow: hidden;
  }}
  .day-headers {{
    display: grid; grid-template-columns: repeat(7, 1fr);
    background: #f8f9fa; border-bottom: 1px solid #e8eaed;
  }}
  .day-header {{
    padding: 10px 6px; text-align: center;
    font-size: 12px; font-weight: 600; color: #70757a; letter-spacing: 0.5px;
  }}
  .day-header.weekend {{ color: #EA4335; }}

  .weeks {{ display: flex; flex-direction: column; }}
  .week {{ display: grid; grid-template-columns: repeat(7, 1fr); border-bottom: 1px solid #f1f3f4; }}
  .week:last-child {{ border-bottom: none; }}

  .day {{
    min-height: 110px; padding: 6px 4px;
    border-right: 1px solid #f1f3f4; position: relative; vertical-align: top;
  }}
  .day:last-child {{ border-right: none; }}
  .day.other-month {{ background: #fafafa; }}
  .day.today {{ background: #fff8e1; }}
  .day.today .day-num {{ background: #1a73e8; color: white; border-radius: 50%; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center; font-weight: 600; }}

  .day-num {{
    font-size: 13px; color: #3c4043; font-weight: 500;
    margin-bottom: 4px; width: 24px; height: 24px;
    display: flex; align-items: center; justify-content: center;
  }}
  .day.other-month .day-num {{ color: #b0b3b8; }}
  .day.weekend-day .day-num {{ color: #EA4335; }}

  .event {{
    border-radius: 4px; padding: 2px 6px; margin-bottom: 2px;
    font-size: 11px; font-weight: 500; color: white;
    cursor: pointer; white-space: nowrap; overflow: hidden;
    text-overflow: ellipsis; transition: opacity 0.15s; line-height: 1.5;
    position: relative;
  }}
  .event:hover {{ opacity: 0.85; }}
  .event.start {{ border-radius: 4px 0 0 4px; margin-right: -2px; }}
  .event.middle {{ border-radius: 0; margin-left: -2px; margin-right: -2px; opacity: 0.85; }}
  .event.end {{ border-radius: 0 4px 4px 0; margin-left: -2px; }}
  .event.single {{ border-radius: 4px; }}

  /* Tooltip */
  .tooltip {{
    display: none; position: fixed; z-index: 9999;
    background: #202124; color: white; border-radius: 8px;
    padding: 12px 14px; font-size: 12px; min-width: 200px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3); pointer-events: none;
    line-height: 1.8;
  }}
  .tooltip.visible {{ display: block; }}
  .tooltip b {{ font-size: 13px; }}
</style>
</head>
<body>

<div class="legend" id="legend"></div>
<div class="cal-grid">
  <div class="day-headers" id="dayHeaders"></div>
  <div class="weeks" id="calBody"></div>
</div>

<div class="tooltip" id="tooltip"></div>

<script>
const EVENTS   = {events_json};
const COULEURS = {couleurs_json};
const MOIS_FR  = {mois_fr_json};
const JOURS_FR = {jours_fr_json};
let currentYear  = {annee};
let currentMonth = {mois};
const today = new Date();

function pad(n) {{ return String(n).padStart(2, '0'); }}
function dateStr(y, m, d) {{ return y + '-' + pad(m) + '-' + pad(d); }}

function buildLegend() {{
  const leg = document.getElementById('legend');
  const plateformes = [...new Set(EVENTS.map(e => e.plateforme))];
  leg.innerHTML = plateformes.map(p =>
    `<div class="legend-item">
      <div class="legend-dot" style="background:${{COULEURS[p] || '#607D8B'}}"></div>
      <span>${{p}}</span>
    </div>`
  ).join('');
}}

function buildHeaders() {{
  const h = document.getElementById('dayHeaders');
  h.innerHTML = JOURS_FR.map((j, i) =>
    `<div class="day-header${{i >= 5 ? ' weekend' : ''}}">${{j}}</div>`
  ).join('');
}}

function getEventsForDate(ds) {{
  return EVENTS.filter(e => e.start <= ds && e.end > ds);
}}

function buildCalendar() {{
  const body = document.getElementById('calBody');
  body.innerHTML = '';

  const firstDay = new Date(currentYear, currentMonth - 1, 1);
  const lastDay  = new Date(currentYear, currentMonth, 0);
  
  // Lundi=0 ... Dimanche=6
  let startDow = (firstDay.getDay() + 6) % 7;
  
  let days = [];
  // Jours mois précédent
  for (let i = startDow - 1; i >= 0; i--) {{
    const d = new Date(firstDay); d.setDate(-i);
    days.push({{ date: d, otherMonth: true }});
  }}
  // Jours du mois
  for (let d = 1; d <= lastDay.getDate(); d++) {{
    days.push({{ date: new Date(currentYear, currentMonth - 1, d), otherMonth: false }});
  }}
  // Compléter jusqu'à 42 cases (6 semaines)
  while (days.length < 42) {{
    const last = days[days.length - 1].date;
    const next = new Date(last); next.setDate(last.getDate() + 1);
    days.push({{ date: next, otherMonth: true }});
  }}

  for (let w = 0; w < 6; w++) {{
    const week = document.createElement('div');
    week.className = 'week';
    
    for (let d = 0; d < 7; d++) {{
      const {{ date: dt, otherMonth }} = days[w * 7 + d];
      const y = dt.getFullYear(), m = dt.getMonth() + 1, day = dt.getDate();
      const ds = dateStr(y, m, day);
      const isToday = (y === today.getFullYear() && m === today.getMonth() + 1 && day === today.getDate());
      const isWeekend = (d === 5 || d === 6);
      
      const cell = document.createElement('div');
      cell.className = 'day' +
        (otherMonth ? ' other-month' : '') +
        (isToday ? ' today' : '') +
        (isWeekend && !otherMonth ? ' weekend-day' : '');

      const numDiv = document.createElement('div');
      numDiv.className = 'day-num';
      numDiv.textContent = day;
      cell.appendChild(numDiv);

      // Events de ce jour
      const evs = getEventsForDate(ds);
      evs.slice(0, 3).forEach(ev => {{
        const isStart  = ev.start === ds;
        const isEnd    = ev.endDisplay === ds;
        const isSingle = ev.start === ev.endDisplay;
        
        const evDiv = document.createElement('div');
        evDiv.className = 'event ' + (isSingle ? 'single' : isStart ? 'start' : isEnd ? 'end' : 'middle');
        evDiv.style.background = COULEURS[ev.plateforme] || '#607D8B';
        
        // Texte uniquement au début
        if (isStart || isSingle) {{
          evDiv.textContent = ev.client;
        }} else {{
          evDiv.textContent = '\u00A0';  // espace insécable pour garder la hauteur
        }}
        
        evDiv.addEventListener('mouseenter', (e) => showTooltip(e, ev));
        evDiv.addEventListener('mouseleave', hideTooltip);
        cell.appendChild(evDiv);
      }});
      
      if (evs.length > 3) {{
        const more = document.createElement('div');
        more.style.cssText = 'font-size:10px; color:#70757a; padding:1px 4px;';
        more.textContent = `+${{evs.length - 3}} autre(s)`;
        cell.appendChild(more);
      }}

      week.appendChild(cell);
    }}
    body.appendChild(week);
  }}
}}

function showTooltip(e, ev) {{
  const t = document.getElementById('tooltip');
  t.innerHTML = `
    <b>${{ev.client}}</b><br>
    📅 ${{ev.startFr}} → ${{ev.endFr}}<br>
    🌙 ${{ev.nuits}} nuit(s)<br>
    🏷️ ${{ev.plateforme}}<br>
    💶 ${{ev.prix}} € net<br>
    ${{ev.paye ? '✅ Payé' : '⏳ En attente'}}
  `;
  t.classList.add('visible');
  moveTooltip(e);
}}

function moveTooltip(e) {{
  const t = document.getElementById('tooltip');
  const x = e.clientX + 12, y = e.clientY + 12;
  t.style.left = Math.min(x, window.innerWidth - 220) + 'px';
  t.style.top  = Math.min(y, window.innerHeight - 160) + 'px';
}}

function hideTooltip() {{
  document.getElementById('tooltip').classList.remove('visible');
}}

document.addEventListener('mousemove', moveTooltip);

buildLegend();
buildHeaders();
buildCalendar();
</script>
</body>
</html>
"""
    components.html(html, height=760, scrolling=False)

    # Navigation mois précédent / suivant via selectbox Streamlit (au-dessus)
    _show_month_summary(df, annee, mois)


def _build_events(df: pd.DataFrame, annee: int, mois: int) -> list:
    """Construit la liste d'events pour le calendrier HTML."""
    events = []
    # Inclure les réservations qui chevauchent le mois
    from datetime import date as ddate
    import calendar
    last_day = calendar.monthrange(annee, mois)[1]
    month_start = ddate(annee, mois, 1)
    month_end   = ddate(annee, mois, last_day)

    # Élargir fenêtre pour afficher débordements
    win_start = month_start - timedelta(days=7)
    win_end   = month_end   + timedelta(days=7)

    for _, row in df.iterrows():
        arr = row["date_arrivee"]
        dep = row["date_depart"]
        if hasattr(arr, "date"): arr = arr.date()
        if hasattr(dep, "date"): dep = dep.date()

        if dep <= win_start or arr >= win_end:
            continue

        # endDisplay = dernier jour visible (veille du départ)
        end_display = dep - timedelta(days=1)

        events.append({
            "client":     row.get("nom_client", "—"),
            "start":      str(arr),
            "end":        str(dep),       # exclusif pour comparaison
            "endDisplay": str(end_display),
            "startFr":    arr.strftime("%d/%m/%Y"),
            "endFr":      dep.strftime("%d/%m/%Y"),
            "nuits":      int(row.get("nuitees", 0)),
            "plateforme": row.get("plateforme", "Direct"),
            "prix":       f"{float(row.get('prix_net', 0)):.0f}",
            "paye":       bool(row.get("paye", False)),
        })

    return events


def _show_month_summary(df: pd.DataFrame, annee: int, mois: int):
    """Résumé du mois — nuits ventilées jour par jour dans le bon mois."""
    import calendar as cal_lib
    from datetime import date as ddate
    last_day = cal_lib.monthrange(annee, mois)[1]
    ms = pd.Timestamp(ddate(annee, mois, 1))
    me = pd.Timestamp(ddate(annee, mois, last_day))

    # me_exclu = 1er jour du mois suivant
    me_exclu = me + pd.Timedelta(days=1)

    # Réservations qui ont AU MOINS 1 nuit dans ce mois
    def nuits_dans_mois(row):
        debut = max(row["date_arrivee"], ms)
        fin   = min(row["date_depart"],  me_exclu)
        return max(0, (fin - debut).days)

    df_tmp = df[(df["date_arrivee"] < me_exclu) & (df["date_depart"] > ms)].copy()
    df_tmp["nuits_mois"] = df_tmp.apply(nuits_dans_mois, axis=1)

    # Garder uniquement celles avec au moins 1 nuit dans le mois
    df_mois = df_tmp[df_tmp["nuits_mois"] > 0].copy()

    st.divider()
    st.subheader(f"📊 Résumé {MOIS_FR[mois]} {annee}")

    if df_mois.empty:
        st.info("Aucune réservation ce mois.")
        return

    nuits_reelles = int(df_mois["nuits_mois"].sum())
    ca_net        = df_mois["prix_net"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Réservations", len(df_mois))
    c2.metric("Nuits",        nuits_reelles)
    c3.metric("CA Net",       f"{ca_net:,.0f} €")
    c4.metric("Revenu/nuit",  f"{ca_net/max(nuits_reelles,1):.0f} €")

    with st.expander("📋 Détail du mois"):
        df_mois = df_mois.rename(columns={"nuits_mois": "nuits_ce_mois"})
        cols = ["nom_client", "plateforme", "date_arrivee", "date_depart", "nuits_ce_mois", "prix_net", "paye"]
        cols_ok = [c for c in cols if c in df_mois.columns]
        st.dataframe(df_mois[cols_ok].sort_values("date_arrivee"),
                     use_container_width=True, hide_index=True,
                     column_config={
                         "prix_net": st.column_config.NumberColumn("Prix net", format="%.0f €"),
                         "paye":     st.column_config.CheckboxColumn("Payé"),
                     })


# ──────────────────────────────────────────────────────────────────────────────
# VUE GANTT
# ──────────────────────────────────────────────────────────────────────────────

def _show_gantt(df: pd.DataFrame, prop_choix: int):
    st.subheader("📊 Planning Gantt")

    df_g = df.copy()
    df_g["date_arrivee"] = pd.to_datetime(df_g["date_arrivee"])
    df_g["date_depart"]  = pd.to_datetime(df_g["date_depart"])
    df_g["Propriété"] = df_g["propriete_id"].map(
        lambda x: PROPRIETES.get(int(x), f"Propriété {x}")
    )
    df_g["Label"] = df_g.apply(
        lambda r: f"{r['nom_client']}  ({int(r['nuitees'])}n)", axis=1
    )
    df_g["Info"] = df_g.apply(
        lambda r: (
            f"<b>{r['nom_client']}</b><br>"
            f"📅 {r['date_arrivee'].strftime('%d/%m')} → {r['date_depart'].strftime('%d/%m/%Y')}<br>"
            f"🌙 {int(r['nuitees'])} nuits — {r['plateforme']}<br>"
            f"💶 {r['prix_net']:.0f} € net — "
            f"{'✅ Payé' if r['paye'] else '⏳ En attente'}"
        ), axis=1
    )

    nb_props = df_g["propriete_id"].nunique() if prop_choix == 0 else 1
    fig = px.timeline(
        df_g, x_start="date_arrivee", x_end="date_depart",
        y="Propriété", color="plateforme",
        color_discrete_map=COULEURS, text="Label",
        custom_data=["Info"],
    )
    fig.update_traces(
        textposition="inside", insidetextanchor="middle",
        textfont=dict(size=11, color="white"),
        hovertemplate="%{customdata[0]}<extra></extra>",
    )
    fig.update_layout(
        height=max(250, nb_props * 120 + 100),
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(tickformat="%d %b", dtick="M1", showgrid=True, gridcolor="#EEEEEE"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white", legend_title="Plateforme",
    )
    st.plotly_chart(fig, use_container_width=True)
