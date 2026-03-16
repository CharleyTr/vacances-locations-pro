"""
Page Messages - Email (Brevo) + SMS (Brevo) + WhatsApp (wa.me / Twilio)
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database.proprietes_repo import fetch_all as _fa_props
from services.auth_service import is_unlocked
from services.reservation_service import load_reservations
from services.messaging_service import (
    send_confirmation, send_checkin_reminder,
    send_checkout_followup, send_payment_reminder,
    send_checkin_sms, send_payment_sms,
    build_wa_confirmation, build_wa_checkin,
    build_wa_checkout, build_wa_payment,
)
from integrations.whatsapp_client import build_wa_link, send_whatsapp
from database.supabase_client import is_connected
import database.reservations_repo as repo
from config import BREVO_API_KEY, TWILIO_ACCOUNT_SID
from database.templates_repo import get_templates
from services.template_service import apply_template, MOMENTS
from database.proprietes_repo import fetch_all as fetch_proprietes, fetch_dict as fetch_props_dict


def show():
    st.title("📧 Messages & Notifications")

    df = load_reservations()
    if not df.empty:
        _auth = [p["id"] for p in _fa_props() if not p.get("mot_de_passe") or is_unlocked(p["id"])]
        df = df[df["propriete_id"].isin(_auth)]
    if df.empty:
        st.info("Aucune réservation disponible.")
        return

    tab_wa, tab_auto, tab_email, tab_sms, tab_histo = st.tabs([
        "💬 WhatsApp", "🤖 Automatique", "✉️ Email", "📱 SMS", "📊 Historique"
    ])

    with tab_wa:
        _show_whatsapp(df)

    with tab_auto:
        _show_auto(df)

    with tab_email:
        _show_email_manuel(df)

    with tab_sms:
        _show_sms_manuel(df)

    with tab_histo:
        _show_historique(df)


# ──────────────────────────────────────────────────────────────────────────────
# WHATSAPP
# ──────────────────────────────────────────────────────────────────────────────

def _show_whatsapp(df: pd.DataFrame):
    st.subheader("💬 WhatsApp")

    # Statut Twilio
    twilio_ok = bool(TWILIO_ACCOUNT_SID)
    col_brevo, col_twilio = st.columns(2)
    with col_brevo:
        st.info("🔗 **Mode lien wa.me** — toujours disponible\nOuvre WhatsApp avec le message pré-rempli", icon="✅")
    with col_twilio:
        if twilio_ok:
            st.success("🤖 **Twilio configuré** — envoi automatique activé", icon="✅")
        else:
            st.warning(
                "🤖 **Twilio non configuré** — envoi manuel uniquement\n\n"
                "Pour l'envoi automatique, ajoutez dans Streamlit Secrets :\n"
                "`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`",
                icon="⚠️"
            )

    st.divider()

    # Sélection réservation avec recherche
    search_wa = st.text_input("🔎 Rechercher un client", placeholder="Tapez un nom...", key="wa_search")
    df_all_for_select = df.sort_values("date_arrivee", ascending=False)
    if search_wa:
        df_all_for_select = df_all_for_select[
            df_all_for_select["nom_client"].str.contains(search_wa, case=False, na=False)
        ]

    options = {
        row["id"]: (
            f"{row['nom_client']} "
            f"({'📱 ' + str(row.get('telephone','')) if row.get('telephone') else '❌ sans tél'})"
            f"  |  {row['plateforme']}  |  {row['date_arrivee'].strftime('%d/%m/%Y') if hasattr(row['date_arrivee'], 'strftime') else str(row['date_arrivee'])[:10]}"
        )
        for _, row in df_all_for_select.iterrows()
    }

    if not options:
        st.info("Aucune réservation trouvée.")
        return

    col1, col2 = st.columns([3, 2])
    with col1:
        selected_id = st.selectbox(
            "Réservation",
            list(options.keys()),
            format_func=lambda x: options[x],
            key="wa_sel"
        )
    row = df[df["id"] == selected_id].iloc[0].to_dict()
    telephone = str(row.get("telephone", "") or "")

    with col2:
        # Charger modèles WhatsApp depuis la DB
        tpls_wa = get_templates(canal="whatsapp")
        tpl_options_wa = {0: "✏️ Message personnalisé"}
        tpl_options_wa.update({t["id"]: f"{t['nom']}  ({MOMENTS.get(t.get('moment',''), '')})" for t in tpls_wa})
        tpl_id_wa = st.selectbox("Modèle", list(tpl_options_wa.keys()),
                                  format_func=lambda x: tpl_options_wa[x], key="wa_tpl")

    # Résoudre propriété & signataire
    prop_id   = int(row.get("propriete_id", 0) or 0)
    props_map = {p["id"]: p for p in fetch_proprietes()}
    prop_nom  = props_map.get(prop_id, {}).get("nom", "")
    ville     = props_map.get(prop_id, {}).get("adresse", "")
    signataire = props_map.get(prop_id, {}).get("signataire", "") or ""

    if tpl_id_wa == 0:
        message = st.text_area(
            "Message WhatsApp",
            value=f"Bonjour {row.get('nom_client','').split()[0]} 👋\n\n",
            height=150, key="wa_custom_msg"
        )
    else:
        tpl_obj = next((t for t in tpls_wa if t["id"] == tpl_id_wa), None)
        if tpl_obj:
            message = apply_template(tpl_obj["contenu"], row,
                                     propriete_nom=prop_nom, ville=ville,
                                     signataire=signataire)
            st.text_area("Aperçu du message", value=message, height=180, disabled=True, key="wa_preview")
        else:
            message = ""

    tel_input = st.text_input("Numéro WhatsApp", value=telephone, placeholder="+33 6 12 34 56 78")

    st.markdown("---")
    col_a, col_b = st.columns(2)

    with col_a:
        # Bouton wa.me — toujours dispo
        if tel_input:
            from integrations.whatsapp_client import build_wa_link
            link = build_wa_link(tel_input, message)
            if link:
                st.link_button(
                    "💬 Ouvrir dans WhatsApp",
                    url=link,
                    type="primary",
                    use_container_width=True,
                )
            else:
                st.error("Numéro invalide")
        else:
            st.button("💬 Ouvrir dans WhatsApp", disabled=True, use_container_width=True)

    with col_b:
        # Bouton Twilio — seulement si configuré
        if twilio_ok:
            if st.button("🤖 Envoyer automatiquement (Twilio)", use_container_width=True):
                if not tel_input:
                    st.error("Numéro manquant")
                else:
                    result = send_whatsapp(tel_input, message)
                    if result.get("ok"):
                        st.success(f"✅ WhatsApp envoyé ! SID: {result.get('sid','')}")
                    else:
                        st.error(f"❌ {result.get('error')}")
        else:
            st.button("🤖 Envoyer (Twilio)", disabled=True, use_container_width=True,
                      help="Configurez Twilio dans les Secrets Streamlit Cloud")

    st.divider()

    # ── Envoi en masse ────────────────────────────────────────────────────
    st.subheader("📨 Envoi en masse")

    today  = pd.Timestamp(date.today())
    in_7   = today + timedelta(days=7)
    hier   = today - timedelta(days=1)

    preset = st.selectbox("Cibler", [
        "Arrivées dans 7 jours (sans téléphone exclus)",
        "Paiements en attente + arrivée dans 14 jours",
        "Tous les séjours à venir",
    ], key="wa_bulk_preset")

    if preset == "Arrivées dans 7 jours (sans téléphone exclus)":
        df_bulk = df[(df["date_arrivee"] >= today) & (df["date_arrivee"] <= in_7) & df["telephone"].notna()]
        tpl_bulk = build_wa_checkin
    elif preset == "Paiements en attente + arrivée dans 14 jours":
        df_bulk = df[(df["paye"] == False) & (df["date_arrivee"] >= today) & (df["date_arrivee"] <= today + timedelta(days=14)) & df["telephone"].notna()]
        tpl_bulk = build_wa_payment
    else:
        df_bulk = df[(df["date_arrivee"] >= today) & df["telephone"].notna()]
        tpl_bulk = build_wa_checkin

    st.markdown(f"**{len(df_bulk)} contact(s)** correspondant à ce critère")

    if not df_bulk.empty:
        st.dataframe(
            df_bulk[["nom_client", "telephone", "date_arrivee", "plateforme"]].head(10),
            use_container_width=True, hide_index=True
        )

        if twilio_ok:
            if st.button(f"🤖 Envoyer à tous ({len(df_bulk)}) via Twilio", type="primary"):
                ok, errors = 0, []
                prog = st.progress(0)
                for i, (_, r) in enumerate(df_bulk.iterrows()):
                    msg = tpl_bulk(r.to_dict())
                    res = send_whatsapp(str(r.get("telephone", "")), msg)
                    if res.get("ok"):
                        ok += 1
                    else:
                        errors.append(f"{r['nom_client']}: {res.get('error')}")
                    prog.progress((i + 1) / len(df_bulk))
                st.success(f"✅ {ok} message(s) envoyé(s)")
                for e in errors[:5]:
                    st.error(f"❌ {e}")
        else:
            # Générer tous les liens wa.me
            if st.button(f"💬 Générer les liens WhatsApp ({len(df_bulk)})", type="primary"):
                st.markdown("**Cliquez sur chaque lien pour envoyer :**")
                for _, r in df_bulk.iterrows():
                    msg = tpl_bulk(r.to_dict())
                    tel = str(r.get("telephone", ""))
                    lnk = build_wa_link(tel, msg)
                    if lnk:
                        nom = r.get("nom_client", "")
                        st.markdown(f"- [{nom} ({tel})]({lnk})")


# ──────────────────────────────────────────────────────────────────────────────
# AUTO
# ──────────────────────────────────────────────────────────────────────────────

def _show_auto(df: pd.DataFrame):
    st.subheader("🤖 Envois automatiques suggérés")
    st.caption("Réservations qui correspondent aux déclencheurs automatiques.")

    today = pd.Timestamp(date.today())
    j2    = today + timedelta(days=2)
    hier  = today - timedelta(days=1)

    rappels  = df[(df["date_arrivee"].dt.date == j2.date()) & (df["sms_envoye"] == False) & df["email"].notna()]
    post_dep = df[(df["date_depart"].dt.date == hier.date()) & (df["post_depart_envoye"] == False) & df["email"].notna()]
    paiements = df[(df["paye"] == False) & (df["date_arrivee"] >= today) & (df["date_arrivee"] <= today + timedelta(days=7)) & df["email"].notna()]

    _section_auto(rappels,  "🔔 Rappels arrivée (J-2)",           "Envoyer rappels arrivée",   send_checkin_reminder,  "sms_envoye",          "checkin")
    st.divider()
    _section_auto(post_dep, "🙏 Messages post-départ (J+1)",      "Envoyer post-départ",        send_checkout_followup, "post_depart_envoye",  "postdepart")
    st.divider()
    _section_auto(paiements,"💳 Rappels paiement (arrivée <7j)",  "Envoyer rappels paiement",   send_payment_reminder,  None,                  "paiement")


def _section_auto(df_sub, titre, btn_label, fn_send, flag_col, key_suffix):
    st.markdown(f"**{titre}**")
    if df_sub.empty:
        st.success("✅ Aucun envoi nécessaire.")
        return
    cols = ["nom_client", "email", "date_arrivee", "plateforme"]
    st.dataframe(df_sub[[c for c in cols if c in df_sub.columns]], use_container_width=True, hide_index=True)
    if st.button(f"📤 {btn_label} ({len(df_sub)})", key=f"btn_{key_suffix}", type="primary"):
        ok, errors = 0, []
        for _, row in df_sub.iterrows():
            result = fn_send(row.to_dict())
            if result.get("ok"):
                ok += 1
                if flag_col and is_connected():
                    try: repo.update_reservation(int(row["id"]), {flag_col: True})
                    except: pass
            else:
                errors.append(f"{row['nom_client']}: {result.get('error')}")
        if ok: st.success(f"✅ {ok} message(s) envoyé(s)")
        for e in errors: st.error(f"❌ {e}")


# ──────────────────────────────────────────────────────────────────────────────
# EMAIL MANUEL
# ──────────────────────────────────────────────────────────────────────────────

def _show_email_manuel(df: pd.DataFrame):
    st.subheader("✉️ Envoyer un email")

    if not BREVO_API_KEY:
        st.error("⛔ BREVO_API_KEY non configurée dans les Secrets Streamlit Cloud.")
        return

    search_email = st.text_input("🔎 Rechercher un client", placeholder="Tapez un nom...", key="email_search")
    df_email = df.sort_values("date_arrivee", ascending=False)
    if search_email:
        df_email = df_email[df_email["nom_client"].str.contains(search_email, case=False, na=False)]
    options = {row["id"]: f"{row['nom_client']} ({row.get('email','sans email')})"
               for _, row in df_email.iterrows()}
    if not options:
        st.info("Aucune réservation trouvée.")
        return
    selected_id = st.selectbox("Réservation", list(options.keys()), format_func=lambda x: options[x], key="email_sel")
    row = df[df["id"] == selected_id].iloc[0].to_dict()

    col1, col2 = st.columns(2)
    with col1:
        template = st.selectbox("Template", ["Confirmation", "Rappel arrivée", "Post-départ", "Rappel paiement", "Personnalisé"], key="email_tpl")
    with col2:
        email_dest = st.text_input("Email", value=str(row.get("email","") or ""))

    if template == "Personnalisé":
        sujet = st.text_input("Sujet")
        corps = st.text_area("Corps (HTML)", height=150)
    else:
        sujet = corps = None

    if st.button("📤 Envoyer l'email", type="primary"):
        if not email_dest:
            st.error("Email manquant.")
            return
        row["email"] = email_dest
        MAP = {"Confirmation": send_confirmation, "Rappel arrivée": send_checkin_reminder,
               "Post-départ": send_checkout_followup, "Rappel paiement": send_payment_reminder}
        if template == "Personnalisé":
            from integrations.brevo_client import send_email
            result = send_email(email_dest, row.get("nom_client",""), sujet, corps)
        else:
            result = MAP[template](row)
        if result.get("ok"):
            st.success(f"✅ Email envoyé à {email_dest}")
        else:
            st.error(f"❌ {result.get('error')}")


# ──────────────────────────────────────────────────────────────────────────────
# SMS MANUEL
# ──────────────────────────────────────────────────────────────────────────────

def _show_sms_manuel(df: pd.DataFrame):
    st.subheader("📱 Envoyer un SMS")

    if not BREVO_API_KEY:
        st.error("⛔ BREVO_API_KEY non configurée.")
        return

    df_tel = df[df["telephone"].notna()]
    if df_tel.empty:
        st.warning("Aucune réservation avec téléphone.")
        return

    options = {row["id"]: f"#{row['id']} — {row['nom_client']} ({row.get('telephone','')})"
               for _, row in df_tel.sort_values("date_arrivee", ascending=False).iterrows()}
    selected_id = st.selectbox("Réservation", list(options.keys()), format_func=lambda x: options[x], key="sms_sel")
    row = df[df["id"] == selected_id].iloc[0].to_dict()

    col1, col2 = st.columns(2)
    with col1:
        tpl = st.selectbox("Template", ["Rappel arrivée", "Rappel paiement", "Personnalisé"], key="sms_tpl")
    with col2:
        tel = st.text_input("Téléphone", value=str(row.get("telephone","") or ""))

    if tpl == "Personnalisé":
        msg = st.text_area("Message (160 car. max)", max_chars=160)
    else:
        if tpl == "Rappel arrivée":
            msg = f"Bonjour {row.get('nom_client','').split()[0]}, votre arrivée est le {row.get('date_arrivee','')}. A bientôt ! - Vacances-Locations"
        else:
            msg = f"Rappel: paiement de {row.get('prix_net',0):.0f}€ en attente. Merci. - Vacances-Locations"
        st.caption(f"Aperçu : *{msg[:160]}*")

    if st.button("📱 Envoyer SMS", type="primary"):
        row["telephone"] = tel
        if tpl == "Rappel arrivée":
            result = send_checkin_sms(row)
        elif tpl == "Rappel paiement":
            result = send_payment_sms(row)
        else:
            from integrations.brevo_client import send_sms
            result = send_sms(tel, msg)
        if result.get("ok"):
            st.success(f"✅ SMS envoyé au {tel}")
        else:
            st.error(f"❌ {result.get('error')}")


# ──────────────────────────────────────────────────────────────────────────────
# HISTORIQUE
# ──────────────────────────────────────────────────────────────────────────────

def _show_historique(df: pd.DataFrame):
    st.subheader("📊 Historique des envois")
    cols = ["nom_client", "email", "telephone", "date_arrivee", "sms_envoye", "post_depart_envoye", "plateforme"]
    st.dataframe(df[[c for c in cols if c in df.columns]].sort_values("date_arrivee", ascending=False),
                 use_container_width=True, hide_index=True,
                 column_config={
                     "sms_envoye":         st.column_config.CheckboxColumn("Email arrivée envoyé"),
                     "post_depart_envoye": st.column_config.CheckboxColumn("Post-départ envoyé"),
                 })
    c1, c2, c3 = st.columns(3)
    c1.metric("📧 Rappels arrivée",  int(df.get("sms_envoye", pd.Series(dtype=bool)).sum()) if "sms_envoye" in df.columns else 0)
    c2.metric("🙏 Post-départ",      int(df.get("post_depart_envoye", pd.Series(dtype=bool)).sum()) if "post_depart_envoye" in df.columns else 0)
    c3.metric("📋 Total",             len(df))
