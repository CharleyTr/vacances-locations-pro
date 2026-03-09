"""
Page Messages — Envoi d'emails et SMS aux voyageurs via Brevo.
"""
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from services.reservation_service import load_reservations
from services.messaging_service import (
    send_confirmation, send_checkin_reminder,
    send_checkout_followup, send_payment_reminder,
    send_checkin_sms, send_payment_sms
)
from database.supabase_client import is_connected
import database.reservations_repo as repo
from config import BREVO_API_KEY


def show():
    st.title("📧 Messages & Notifications")

    # Vérification config Brevo
    if not BREVO_API_KEY:
        st.error(
            "⛔ **BREVO_API_KEY non configurée.**\n\n"
            "Ajoutez votre clé API Brevo dans les Secrets Streamlit Cloud :\n"
            "`BREVO_API_KEY = \"votre-clé\"`"
        )
        st.info("Obtenez votre clé sur [app.brevo.com](https://app.brevo.com) → API Keys")
        return

    st.success("🟢 Brevo configuré", icon="✅")

    df = load_reservations()
    if df.empty:
        st.info("Aucune réservation disponible.")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        "🤖 Envoi automatique", "✉️ Email manuel", "📱 SMS manuel", "📊 Historique"
    ])

    with tab1:
        _show_auto(df)

    with tab2:
        _show_email_manuel(df)

    with tab3:
        _show_sms_manuel(df)

    with tab4:
        _show_historique(df)


# ──────────────────────────────────────────────────────────────────────────────
# AUTOMATIQUE
# ──────────────────────────────────────────────────────────────────────────────

def _show_auto(df: pd.DataFrame):
    st.subheader("🤖 Envois automatiques suggérés")
    st.caption("Réservations qui correspondent aux déclencheurs automatiques.")

    today = pd.Timestamp(date.today())
    j2    = today + timedelta(days=2)
    j1    = today + timedelta(days=1)
    hier  = today - timedelta(days=1)

    # Rappels J-2 arrivée
    rappels_arrivee = df[
        (df["date_arrivee"].dt.date == j2.date()) &
        (df["sms_envoye"] == False) &
        (df["email"].notna())
    ]

    # Post-départ J+1
    post_depart = df[
        (df["date_depart"].dt.date == hier.date()) &
        (df["post_depart_envoye"] == False) &
        (df["email"].notna())
    ]

    # Paiements en attente avec arrivée dans 7 jours
    paiements = df[
        (df["paye"] == False) &
        (df["date_arrivee"] >= today) &
        (df["date_arrivee"] <= today + timedelta(days=7)) &
        (df["email"].notna())
    ]

    # ── Rappels arrivée ──
    _section_auto(
        rappels_arrivee,
        "🔔 Rappels arrivée (J-2)",
        "Envoyer rappels arrivée",
        send_checkin_reminder,
        "sms_envoye",
        "checkin"
    )

    st.divider()

    # ── Post-départ ──
    _section_auto(
        post_depart,
        "🙏 Messages post-départ (J+1)",
        "Envoyer messages post-départ",
        send_checkout_followup,
        "post_depart_envoye",
        "postdepart"
    )

    st.divider()

    # ── Rappels paiement ──
    _section_auto(
        paiements,
        "💳 Rappels paiement (arrivée dans 7j)",
        "Envoyer rappels paiement",
        send_payment_reminder,
        None,
        "paiement"
    )


def _section_auto(df_sub, titre, btn_label, fn_send, flag_col, key_suffix):
    st.markdown(f"**{titre}**")

    if df_sub.empty:
        st.success("✅ Aucun envoi nécessaire pour le moment.")
        return

    cols = ["nom_client", "email", "date_arrivee", "date_depart", "plateforme"]
    cols_ok = [c for c in cols if c in df_sub.columns]
    st.dataframe(df_sub[cols_ok], use_container_width=True, hide_index=True)

    if st.button(f"📤 {btn_label} ({len(df_sub)})", key=f"btn_{key_suffix}", type="primary"):
        ok = 0
        erreurs = []
        for _, row in df_sub.iterrows():
            result = fn_send(row.to_dict())
            if result.get("ok"):
                ok += 1
                if flag_col and is_connected():
                    try:
                        repo.update_reservation(int(row["id"]), {flag_col: True})
                    except:
                        pass
            else:
                erreurs.append(f"{row['nom_client']}: {result.get('error')}")

        if ok:
            st.success(f"✅ {ok} message(s) envoyé(s)")
        if erreurs:
            for e in erreurs:
                st.error(f"❌ {e}")


# ──────────────────────────────────────────────────────────────────────────────
# EMAIL MANUEL
# ──────────────────────────────────────────────────────────────────────────────

def _show_email_manuel(df: pd.DataFrame):
    st.subheader("✉️ Envoyer un email")

    # Sélection réservation
    options = {
        row["id"]: f"#{row['id']} — {row['nom_client']} ({row.get('email', 'sans email')})"
        for _, row in df.sort_values("date_arrivee", ascending=False).iterrows()
    }

    selected_id = st.selectbox(
        "Réservation",
        list(options.keys()),
        format_func=lambda x: options[x],
        key="email_sel"
    )
    row = df[df["id"] == selected_id].iloc[0].to_dict()

    col1, col2 = st.columns(2)
    with col1:
        template = st.selectbox("Template", [
            "Confirmation de réservation",
            "Rappel arrivée (J-2)",
            "Message post-départ",
            "Rappel paiement",
            "Email personnalisé",
        ], key="email_tpl")
    with col2:
        email_dest = st.text_input("Email destinataire", value=str(row.get("email", "") or ""))

    if template == "Email personnalisé":
        sujet  = st.text_input("Sujet", value="Message de Vacances-Locations")
        corps  = st.text_area("Corps du message (HTML autorisé)", height=200)
    else:
        sujet  = None
        corps  = None

    if st.button("📤 Envoyer l'email", type="primary"):
        if not email_dest:
            st.error("Email destinataire manquant.")
            return

        row["email"] = email_dest
        nom = row.get("nom_client", "")

        MAP = {
            "Confirmation de réservation": send_confirmation,
            "Rappel arrivée (J-2)":        send_checkin_reminder,
            "Message post-départ":         send_checkout_followup,
            "Rappel paiement":             send_payment_reminder,
        }

        if template == "Email personnalisé":
            from integrations.brevo_client import send_email
            result = send_email(email_dest, nom, sujet, corps)
        else:
            result = MAP[template](row)

        if result.get("ok"):
            st.success(f"✅ Email envoyé à {email_dest}")
            # Mettre à jour les flags
            if template == "Rappel arrivée (J-2)" and is_connected():
                try:
                    repo.update_reservation(int(row["id"]), {"sms_envoye": True})
                except:
                    pass
            elif template == "Message post-départ" and is_connected():
                try:
                    repo.update_reservation(int(row["id"]), {"post_depart_envoye": True})
                except:
                    pass
        else:
            st.error(f"❌ Erreur : {result.get('error')}")


# ──────────────────────────────────────────────────────────────────────────────
# SMS MANUEL
# ──────────────────────────────────────────────────────────────────────────────

def _show_sms_manuel(df: pd.DataFrame):
    st.subheader("📱 Envoyer un SMS")

    df_avec_tel = df[df["telephone"].notna()]
    if df_avec_tel.empty:
        st.warning("Aucune réservation avec numéro de téléphone.")
        return

    options = {
        row["id"]: f"#{row['id']} — {row['nom_client']} ({row.get('telephone', '')})"
        for _, row in df_avec_tel.sort_values("date_arrivee", ascending=False).iterrows()
    }

    selected_id = st.selectbox(
        "Réservation",
        list(options.keys()),
        format_func=lambda x: options[x],
        key="sms_sel"
    )
    row = df[df["id"] == selected_id].iloc[0].to_dict()

    col1, col2 = st.columns(2)
    with col1:
        template_sms = st.selectbox("Template SMS", [
            "Rappel arrivée", "Rappel paiement", "SMS personnalisé"
        ], key="sms_tpl")
    with col2:
        tel_dest = st.text_input("Téléphone", value=str(row.get("telephone", "") or ""))

    if template_sms == "SMS personnalisé":
        msg_custom = st.text_area("Message (160 caractères max)", max_chars=160, height=80)
    else:
        msg_custom = None

    if template_sms != "SMS personnalisé":
        if template_sms == "Rappel arrivée":
            preview = f"Bonjour {row.get('nom_client','').split()[0]}, votre arrivée est prévue le {row.get('date_arrivee','')}.Merci de bien vouloir nous indiquer votre heure afin que nous puissions vous accueillir sur place. A bientot ! - Vacances-Locations"
        else:
            preview = f"Rappel: paiement de {row.get('prix_net',0):.0f}€ en attente. Merci. - Vacances-Locations"
        st.caption(f"Aperçu : *{preview[:160]}*")

    if st.button("📱 Envoyer le SMS", type="primary"):
        if not tel_dest:
            st.error("Numéro de téléphone manquant.")
            return
        row["telephone"] = tel_dest

        if template_sms == "SMS personnalisé":
            from integrations.brevo_client import send_sms
            result = send_sms(tel_dest, msg_custom)
        elif template_sms == "Rappel arrivée":
            result = send_checkin_sms(row)
        else:
            result = send_payment_sms(row)

        if result.get("ok"):
            st.success(f"✅ SMS envoyé au {tel_dest}")
        else:
            st.error(f"❌ Erreur : {result.get('error')}")


# ──────────────────────────────────────────────────────────────────────────────
# HISTORIQUE
# ──────────────────────────────────────────────────────────────────────────────

def _show_historique(df: pd.DataFrame):
    st.subheader("📊 Historique des envois")

    cols = ["nom_client", "email", "telephone", "date_arrivee",
            "sms_envoye", "post_depart_envoye", "plateforme"]
    cols_ok = [c for c in cols if c in df.columns]

    st.dataframe(
        df[cols_ok].sort_values("date_arrivee", ascending=False),
        use_container_width=True, hide_index=True,
        column_config={
            "sms_envoye":          st.column_config.CheckboxColumn("Email arrivée envoyé"),
            "post_depart_envoye":  st.column_config.CheckboxColumn("Post-départ envoyé"),
        }
    )

    # Stats
    c1, c2, c3 = st.columns(3)
    sms_ok  = df["sms_envoye"].sum()  if "sms_envoye"         in df.columns else 0
    post_ok = df["post_depart_envoye"].sum() if "post_depart_envoye" in df.columns else 0
    c1.metric("📧 Rappels arrivée envoyés",  int(sms_ok))
    c2.metric("🙏 Post-départ envoyés",       int(post_ok))
    c3.metric("📋 Total réservations",         len(df))
