"""
Page Gestion des barèmes fiscaux — mise à jour annuelle des paramètres.
"""
import streamlit as st
import json
import pandas as pd
from datetime import date
from database.baremes_repo import get_all_baremes, get_bareme, save_bareme, bareme_to_dict
from database.supabase_client import is_connected

TRANCHES_DEFAULT = [
    {"bas": 0,      "haut": 11497,  "taux": 0.00},
    {"bas": 11497,  "haut": 29315,  "taux": 0.11},
    {"bas": 29315,  "haut": 83823,  "taux": 0.30},
    {"bas": 83823,  "haut": 180294, "taux": 0.41},
    {"bas": 180294, "haut": None,   "taux": 0.45},
]


def show():
    st.title("📐 Barèmes fiscaux")
    st.caption("Mettez à jour les paramètres fiscaux dès parution des textes officiels (PLF, LFI, BOFiP).")

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise.")
        return

    tab1, tab2 = st.tabs(["📋 Barèmes existants", "➕ Ajouter / Modifier un barème"])

    # ── TAB 1 : Vue d'ensemble ────────────────────────────────────────────
    with tab1:
        baremes = get_all_baremes()
        if not baremes:
            st.info("Aucun barème en base. Exécutez d'abord le SQL 009_baremes_fiscaux.sql.")
        else:
            st.markdown(f"**{len(baremes)} année(s) configurée(s)**")
            for b in baremes:
                tranches = b.get("tranches_ir", [])
                if isinstance(tranches, str):
                    tranches = json.loads(tranches)

                with st.expander(
                    f"📅 **{b['annee']}** — {b.get('loi_note','')}"
                    f"  |  Classé {float(b.get('abattement_classe',0.71))*100:.0f}%"
                    f"  |  Non classé {float(b.get('abattement_non_classe',0.50))*100:.0f}%",
                    expanded=False
                ):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Seuil classé",      f"{int(b.get('seuil_classe',188700)):,} €")
                    col2.metric("Seuil non classé",  f"{int(b.get('seuil_non_classe',77700)):,} €")
                    col3.metric("CSG/CRDS",          f"{float(b.get('csg_crds',0.172))*100:.1f}%")

                    col4, col5, col6 = st.columns(3)
                    col4.metric("Abattement classé",     f"{float(b.get('abattement_classe',0.71))*100:.0f}%")
                    col5.metric("Abattement non classé", f"{float(b.get('abattement_non_classe',0.50))*100:.0f}%")
                    col6.metric("Seuil cotisations SSI", f"{int(b.get('seuil_cotisations',23000)):,} €")

                    st.markdown("**Tranches IR :**")
                    df_t = pd.DataFrame([{
                        "De (€)": t["bas"],
                        "À (€)": t.get("haut") or "∞",
                        "Taux": f"{float(t['taux'])*100:.0f}%",
                    } for t in tranches])
                    st.dataframe(df_t, use_container_width=True, hide_index=True)

                    if st.button("✏️ Modifier ce barème", key=f"edit_b_{b['annee']}"):
                        st.session_state["edit_bareme"] = b
                        st.rerun()

    # ── TAB 2 : Formulaire création / édition ─────────────────────────────
    with tab2:
        editing = st.session_state.get("edit_bareme")
        if editing:
            st.info(f"✏️ Modification du barème **{editing['annee']}**")
            if st.button("❌ Annuler", key="cancel_edit_b"):
                st.session_state.pop("edit_bareme", None)
                st.rerun()

        st.subheader("📝 Paramètres du barème")
        st.markdown(
            "Sources officielles : "
            "[PLF / LFI](https://www.legifrance.gouv.fr) · "
            "[BOFiP](https://bofip.impots.gouv.fr) · "
            "[DGFiP](https://www.impots.gouv.fr)"
        )

        col1, col2 = st.columns(2)
        with col1:
            annee_b = st.number_input("Année fiscale *",
                min_value=2020, max_value=2035,
                value=int(editing["annee"]) if editing else date.today().year + 1,
                step=1, key="b_annee")
            loi_note = st.text_input("Source / Note de loi",
                value=editing.get("loi_note","") if editing else "",
                placeholder="Ex: LFI 2026 — art. 12 — JO du 30/12/2025",
                key="b_note")

        with col2:
            st.markdown("**Micro-BIC — Seuils de recettes**")
            seuil_classe = st.number_input("Seuil meublé classé / Gîte (€)",
                min_value=0, value=int(editing.get("seuil_classe",77700)) if editing else 77700,
                step=100, key="b_s_cl")
            seuil_non_classe = st.number_input("Seuil non classé (€)",
                min_value=0, value=int(editing.get("seuil_non_classe",15000)) if editing else 15000,
                step=100, key="b_s_ncl")

        st.divider()
        col3, col4, col5, col6 = st.columns(4)
        with col3:
            abatt_cl = st.number_input("Abattement classé (%)",
                min_value=0.0, max_value=100.0,
                value=float(editing.get("abattement_classe",0.50))*100 if editing else 50.0,
                step=1.0, key="b_a_cl") / 100
        with col4:
            abatt_ncl = st.number_input("Abattement non classé (%)",
                min_value=0.0, max_value=100.0,
                value=float(editing.get("abattement_non_classe",0.30))*100 if editing else 30.0,
                step=1.0, key="b_a_ncl") / 100
        with col5:
            csg = st.number_input("CSG/CRDS (%)",
                min_value=0.0, max_value=30.0,
                value=float(editing.get("csg_crds",0.172))*100 if editing else 17.2,
                step=0.1, key="b_csg") / 100
        with col6:
            seuil_cot = st.number_input("Seuil SSI (€)",
                min_value=0, value=int(editing.get("seuil_cotisations",23000)) if editing else 23000,
                step=500, key="b_seuil_cot")

        st.divider()
        st.markdown("**Tranches d'imposition (IR) — Barème progressif**")
        st.caption("Saisissez les tranches après parution du barème officiel. 'Haut = 0' pour la dernière tranche (sans plafond).")

        tranches_init = []
        if editing:
            t_raw = editing.get("tranches_ir", [])
            if isinstance(t_raw, str):
                t_raw = json.loads(t_raw)
            tranches_init = [{"De (€)": t["bas"],
                               "À (€)": t.get("haut") or 0,
                               "Taux (%)": float(t["taux"]) * 100}
                             for t in t_raw]
        else:
            tranches_init = [{"De (€)": t["bas"],
                               "À (€)": t.get("haut") or 0,
                               "Taux (%)": float(t["taux"]) * 100}
                             for t in TRANCHES_DEFAULT]

        df_tranches = pd.DataFrame(tranches_init)
        edited_tranches = st.data_editor(
            df_tranches,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "De (€)":   st.column_config.NumberColumn("De (€)",   min_value=0, step=100, format="%d €"),
                "À (€)":    st.column_config.NumberColumn("À (€)",    min_value=0, step=100, format="%d €",
                                                           help="Mettre 0 pour la dernière tranche (∞)"),
                "Taux (%)": st.column_config.NumberColumn("Taux (%)", min_value=0, max_value=100,
                                                           step=0.5, format="%.1f%%"),
            },
            key="b_tranches_editor"
        )

        # Bouton sauvegarde
        st.divider()
        if st.button("💾 Enregistrer le barème", type="primary", use_container_width=True, key="save_bareme"):
            tranches_json = []
            for _, row in edited_tranches.iterrows():
                haut = int(row["À (€)"]) if row["À (€)"] > 0 else None
                tranches_json.append({
                    "bas":  int(row["De (€)"]),
                    "haut": haut,
                    "taux": round(float(row["Taux (%)"]) / 100, 4),
                })

            data = {
                "annee":                 int(annee_b),
                "seuil_classe":          int(seuil_classe),
                "seuil_non_classe":      int(seuil_non_classe),
                "abattement_classe":     abatt_cl,
                "abattement_non_classe": abatt_ncl,
                "csg_crds":              csg,
                "seuil_cotisations":     int(seuil_cot),
                "loi_note":              loi_note.strip(),
                "tranches_ir":           tranches_json,
                "actif":                 True,
            }
            if editing and editing.get("id"):
                data["id"] = editing["id"]

            if save_bareme(data):
                st.success(f"✅ Barème {int(annee_b)} enregistré !")
                st.session_state.pop("edit_bareme", None)
                st.rerun()
            else:
                st.error("Erreur lors de la sauvegarde.")

    # ── Notice ────────────────────────────────────────────────────────────
    with st.expander("ℹ️ Guide de mise à jour annuelle"):
        st.markdown("""
**Quand mettre à jour ?**
- Fin décembre / début janvier : parution de la **Loi de Finances (LFI)** au Journal Officiel
- Les barèmes IR sont revalorisés chaque année selon l'inflation
- Les seuils micro-BIC peuvent être modifiés par LFR (Loi de Finances Rectificative)

**Sources officielles :**
- [impots.gouv.fr](https://www.impots.gouv.fr) → rubrique Particuliers → Barème IR
- [legifrance.gouv.fr](https://www.legifrance.gouv.fr) → recherche "loi de finances"
- [bofip.impots.gouv.fr](https://bofip.impots.gouv.fr) → BOI-IR-LIQ-10

**Procédure :**
1. Consultez le barème officiel dès publication (souvent fin décembre)
2. Dans cette page, cliquez **Ajouter / Modifier un barème**
3. Saisissez les nouvelles tranches et seuils
4. Enregistrez — le tableau de bord fiscal utilisera automatiquement les nouvelles valeurs
        """)
