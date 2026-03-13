"""
Page de gestion des modèles de messages WhatsApp & SMS.
"""
import streamlit as st
import urllib.parse
from database.templates_repo import get_templates, save_template, delete_template
from database.supabase_client import is_connected
from services.template_service import VARIABLES, MOMENTS, apply_template
from services.reservation_service import load_reservations
from services.proprietes_service import get_proprietes_dict


def show():
    st.title("📝 Modèles de messages")
    st.caption("Créez et gérez vos modèles WhatsApp & SMS avec variables automatiques.")

    if not is_connected():
        st.warning("⚠️ Connexion Supabase requise.")
        return

    tab_wa, tab_sms, tab_envoyer, tab_variables = st.tabs([
        "📱 WhatsApp", "💬 SMS", "🚀 Envoyer depuis modèle", "📋 Variables disponibles"
    ])

    with tab_variables:
        _show_variables()

    with tab_wa:
        _show_templates_canal("whatsapp")

    with tab_sms:
        _show_templates_canal("sms")

    with tab_envoyer:
        _show_envoyer()


# ─────────────────────────────────────────────────────────────────────────────

def _show_variables():
    st.subheader("📋 Variables disponibles dans vos messages")
    st.markdown("Copiez-collez ces variables dans vos modèles — elles seront remplacées automatiquement :")

    cols = st.columns(2)
    items = list(VARIABLES.items())
    mid = len(items) // 2
    for i, (var, desc) in enumerate(items):
        col = cols[0] if i < mid else cols[1]
        col.markdown(
            f"<div style='background:#F3F4F6;border-radius:6px;padding:6px 10px;margin:3px 0'>"
            f"<code style='color:#1565C0;font-size:14px'>{var}</code>"
            f" — <span style='color:#555;font-size:13px'>{desc}</span></div>",
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────────────────────────────

def _show_templates_canal(canal: str):
    icon = "📱" if canal == "whatsapp" else "💬"
    label = "WhatsApp" if canal == "whatsapp" else "SMS"

    templates = get_templates(canal=canal)

    # ── Liste des templates existants ────────────────────────────────────
    if templates:
        st.markdown(f"**{len(templates)} modèle(s) {label}**")
        for t in templates:
            with st.expander(
                f"{icon} {t['nom']}  —  _{MOMENTS.get(t.get('moment',''), t.get('moment',''))}_",
                expanded=False
            ):
                # Aperçu du contenu
                st.text_area("Contenu", value=t["contenu"], height=150,
                             key=f"view_{canal}_{t['id']}", disabled=True)

                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    if st.button("✏️ Modifier", key=f"edit_{canal}_{t['id']}"):
                        st.session_state[f"edit_tpl_{canal}"] = t
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"del_{canal}_{t['id']}", help="Supprimer"):
                        delete_template(t["id"])
                        st.success("Supprimé !")
                        st.rerun()
    else:
        st.info(f"Aucun modèle {label} — créez-en un ci-dessous.")

    st.divider()

    # ── Formulaire création / modification ────────────────────────────────
    editing = st.session_state.get(f"edit_tpl_{canal}")
    titre_form = f"✏️ Modifier le modèle" if editing else f"➕ Nouveau modèle {label}"

    with st.expander(titre_form, expanded=editing is not None or not templates):
        nom = st.text_input("Nom du modèle *",
                            value=editing["nom"] if editing else "",
                            placeholder="Ex: Confirmation réservation",
                            key=f"tpl_nom_{canal}")

        moment = st.selectbox("Moment d'envoi",
                              options=list(MOMENTS.keys()),
                              format_func=lambda x: MOMENTS[x],
                              index=list(MOMENTS.keys()).index(editing["moment"])
                                    if editing and editing.get("moment") in MOMENTS else 0,
                              key=f"tpl_moment_{canal}")

        # Aide variables inline
        with st.expander("📋 Variables disponibles", expanded=False):
            st.markdown(" · ".join([f"`{v}`" for v in VARIABLES.keys()]))

        contenu = st.text_area(
            "Contenu du message *",
            value=editing["contenu"] if editing else "",
            height=200,
            placeholder="Bonjour {prenom},\n\nVotre séjour à {propriete} du {date_arrivee}...",
            key=f"tpl_contenu_{canal}",
            help="Utilisez les variables ci-dessus — ex: {prenom}, {date_arrivee}, {propriete}"
        )

        if canal == "sms":
            nb_chars = len(contenu)
            nb_sms = max(1, (nb_chars + 159) // 160)
            color = "#4CAF50" if nb_chars <= 160 else "#FF9800" if nb_chars <= 320 else "#F44336"
            st.markdown(
                f"<small style='color:{color}'>{nb_chars} caractères — {nb_sms} SMS</small>",
                unsafe_allow_html=True
            )

        col1, col2 = st.columns([2, 2])
        with col1:
            if st.button("💾 Enregistrer", type="primary", key=f"tpl_save_{canal}"):
                if not nom or not contenu:
                    st.error("Nom et contenu sont obligatoires.")
                else:
                    data = {
                        "nom":     nom,
                        "canal":   canal,
                        "moment":  moment,
                        "contenu": contenu,
                        "actif":   True,
                    }
                    if editing:
                        data["id"] = editing["id"]
                    if save_template(data):
                        st.success("✅ Modèle enregistré !")
                        st.session_state.pop(f"edit_tpl_{canal}", None)
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'enregistrement.")
        with col2:
            if editing and st.button("❌ Annuler modification", key=f"tpl_cancel_{canal}"):
                st.session_state.pop(f"edit_tpl_{canal}", None)
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────

def _show_envoyer():
    st.subheader("🚀 Envoyer un message depuis un modèle")

    props = get_proprietes_dict()
    df = load_reservations()
    if df.empty:
        st.warning("Aucune réservation disponible.")
        return

    col1, col2 = st.columns(2)
    with col1:
        canal = st.radio("Canal", ["📱 WhatsApp", "💬 SMS"],
                         horizontal=True, key="send_canal")
    canal_key = "whatsapp" if "WhatsApp" in canal else "sms"

    templates = get_templates(canal=canal_key)
    if not templates:
        st.info(f"Aucun modèle {canal_key} — créez-en dans l'onglet correspondant.")
        return

    with col2:
        tpl_options = {t["id"]: f"{t['nom']}  ({MOMENTS.get(t.get('moment',''), '')})"
                       for t in templates}
        tpl_id = st.selectbox("Modèle", list(tpl_options.keys()),
                               format_func=lambda x: tpl_options[x], key="send_tpl")

    tpl = next((t for t in templates if t["id"] == tpl_id), None)
    if not tpl:
        return

    st.divider()

    # Sélection client
    search = st.text_input("🔎 Rechercher un client", placeholder="Tapez un nom...", key="send_search")
    df_f = df.sort_values("date_arrivee", ascending=False)
    if search:
        df_f = df_f[df_f["nom_client"].str.contains(search, case=False, na=False)]

    if df_f.empty:
        st.info("Aucune réservation trouvée.")
        return

    res_options = {
        row["id"]: f"{row['nom_client']}  |  "
                   f"{str(row['date_arrivee'])[:10]} → {str(row['date_depart'])[:10]}  |  "
                   f"{row['plateforme']}"
        for _, row in df_f.iterrows()
    }
    res_id = st.selectbox("Réservation", list(res_options.keys()),
                           format_func=lambda x: res_options[x], key="send_res")

    row = df[df["id"] == res_id].iloc[0].to_dict()
    prop_id  = int(row.get("propriete_id", 0) or 0)
    prop_nom = props.get(prop_id, "")
    ville    = "Bordeaux" if prop_id == 1 else "Nice" if prop_id == 2 else ""

    # Aperçu message rempli
    msg_final = apply_template(tpl["contenu"], row,
                                propriete_nom=prop_nom, ville=ville)

    st.markdown("#### 👁️ Aperçu du message")
    st.text_area("Message final", value=msg_final, height=200, key="send_preview", disabled=True)

    if canal_key == "sms":
        nb = len(msg_final)
        st.caption(f"{nb} caractères — {max(1,(nb+159)//160)} SMS")

    # Boutons envoi
    telephone = str(row.get("telephone", "") or "").strip()
    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        if canal_key == "whatsapp":
            wa_num = telephone.replace("+","").replace(" ","").replace("-","")
            wa_url = f"https://wa.me/{wa_num}?text={urllib.parse.quote(msg_final)}" \
                     if wa_num else f"https://wa.me/?text={urllib.parse.quote(msg_final)}"
            st.markdown(
                f"<a href='{wa_url}' target='_blank'>"
                f"<div style='background:#25D366;color:white;text-align:center;"
                f"padding:12px;border-radius:8px;font-weight:bold;font-size:15px'>"
                f"📱 Ouvrir WhatsApp</div></a>",
                unsafe_allow_html=True
            )
        else:
            sms_url = f"sms:{telephone}?body={urllib.parse.quote(msg_final)}"
            st.markdown(
                f"<a href='{sms_url}'>"
                f"<div style='background:#1565C0;color:white;text-align:center;"
                f"padding:12px;border-radius:8px;font-weight:bold;font-size:15px'>"
                f"💬 Ouvrir SMS</div></a>",
                unsafe_allow_html=True
            )

    with c2:
        if st.button("📋 Copier le message", use_container_width=True, key="send_copy"):
            st.code(msg_final, language=None)
            st.info("Sélectionnez le texte ci-dessus et copiez (Ctrl+A, Ctrl+C)")
