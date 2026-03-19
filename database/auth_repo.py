"""
Repository pour la gestion des utilisateurs via Supabase Auth.
Coexiste avec le système PIN actuel pendant la migration.
"""
from database.supabase_client import get_supabase


def get_profile(user_id: str) -> dict | None:
    """Retourne le profil d'un utilisateur."""
    sb = get_supabase()
    if sb is None: return None
    try:
        r = sb.table("profiles").select("*").eq("id", user_id).single().execute()
        return r.data
    except: return None


def get_all_profiles() -> list:
    """Retourne tous les profils (admin uniquement)."""
    sb = get_supabase()
    if sb is None: return []
    try:
        return sb.table("profiles").select("*").order("created_at").execute().data or []
    except: return []


def get_proprietes_for_user(user_id: str, role: str = "admin") -> list:
    """
    Retourne les proprietes accessibles pour un utilisateur.
    Admin → toutes. Autres → via propriete_access.
    """
    sb = get_supabase()
    if sb is None: return []
    try:
        if role == "admin":
            return sb.table("proprietes").select("*").eq("actif", True).order("id").execute().data or []
        else:
            # Joindre propriete_access et proprietes
            access = sb.table("propriete_access").select("propriete_id")\
                       .eq("user_id", user_id).execute().data or []
            prop_ids = [a["propriete_id"] for a in access]
            if not prop_ids: return []
            return sb.table("proprietes").select("*")\
                     .in_("id", prop_ids).eq("actif", True).execute().data or []
    except: return []


def invite_user(email: str, propriete_ids: list, role: str = "gestionnaire") -> bool:
    """
    Invite un nouvel utilisateur via l'API Admin Supabase (service_role key).
    Supabase envoie automatiquement un email d'invitation.
    """
    import requests, os
    import streamlit as st

    sb = get_supabase()
    if sb is None: return False

    # Récupérer l'URL et la service_role key
    try:
        supabase_url = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL",""))
        service_key  = st.secrets.get("SUPABASE_SERVICE_KEY",
                       os.environ.get("SUPABASE_SERVICE_KEY",""))
    except Exception as se:
        supabase_url = os.environ.get("SUPABASE_URL","")
        service_key  = os.environ.get("SUPABASE_SERVICE_KEY","")
        print(f"invite_user secrets error: {se}")

    if not service_key:
        msg = "SUPABASE_SERVICE_KEY manquant — ajoutez-le dans Streamlit Cloud Secrets"
        print(f"invite_user: {msg}")
        try: _st.session_state["_invite_error"] = msg
        except: pass
        return False
    
    # Masquer la clé dans les logs
    key_preview = service_key[:20] + "..." if len(service_key) > 20 else "???"
    print(f"invite_user: URL={supabase_url[:40]}, key={key_preview}")

    try:
        # Appel API Admin Supabase pour inviter l'utilisateur
        r = requests.post(
            f"{supabase_url}/auth/v1/invite",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
            },
            json={"email": email},
            timeout=15,
        )
        if r.status_code not in (200, 201):
            print(f"invite_user API error: {r.status_code} — {r.text}")
            # Stocker l'erreur pour l'afficher dans l'UI
            import streamlit as _st
            try: _st.session_state["_invite_error"] = f"API {r.status_code}: {r.text[:200]}"
            except: pass
            return False

        user_data = r.json()
        user_id = user_data.get("id")
        if not user_id: return False

        # Créer le profil dans notre table
        sb.table("profiles").upsert({
            "id": user_id, "email": email, "role": role
        }).execute()

        # Donner accès aux propriétés
        for pid in propriete_ids:
            sb.table("propriete_access").upsert({
                "user_id": user_id, "propriete_id": pid, "role": role
            }, on_conflict="user_id,propriete_id").execute()

        return True
    except Exception as e:
        print(f"invite_user error: {e}")
        import streamlit as _st
        try: _st.session_state["_invite_error"] = str(e)
        except: pass
        return False


def revoke_access(user_id: str, propriete_id: int) -> bool:
    """Supprime l'accès d'un utilisateur à une propriété."""
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.table("propriete_access").delete()\
          .eq("user_id", user_id).eq("propriete_id", propriete_id).execute()
        return True
    except: return False


def sign_in_with_email(email: str, password: str) -> dict | None:
    """Connexion via email/mot de passe Supabase Auth."""
    sb = get_supabase()
    if sb is None: return None
    try:
        r = sb.auth.sign_in_with_password({"email": email, "password": password})
        return {"user": r.user, "session": r.session} if r.user else None
    except Exception as e:
        print(f"sign_in error: {e}")
        return None


def sign_in_with_code(email: str, code: str) -> dict | None:
    """
    Connexion via email + code d'accès personnel (défini par le propriétaire).
    Ne nécessite pas le mot de passe Supabase Auth.
    """
    import hashlib
    sb = get_supabase()
    if sb is None: return None
    try:
        # Chercher le profil par email
        rows = sb.table("profiles").select("id,email,role,code_acces")                 .eq("email", email.strip().lower()).execute().data or []
        if not rows:
            return None
        profile = rows[0]
        stored = profile.get("code_acces", "") or ""
        if not stored:
            return None
        # Vérifier le code (en clair ou hashé)
        code_hash = hashlib.sha256(code.strip().encode()).hexdigest()
        if code != stored and code_hash != stored:
            return None
        # Code OK → retourner les infos du profil
        return {"user_id": profile["id"], "email": profile["email"],
                "role": profile["role"]}
    except Exception as e:
        print(f"sign_in_with_code error: {e}")
        return None


def set_code_acces(user_id: str, nouveau_code: str, hint: str = "") -> bool:
    """Définit ou modifie le code d'accès personnel d'un utilisateur."""
    import hashlib
    sb = get_supabase()
    if sb is None: return False
    try:
        code_hash = hashlib.sha256(nouveau_code.strip().encode()).hexdigest()
        sb.table("profiles").update({
            "code_acces":      code_hash,
            "code_acces_hint": hint or None,
        }).eq("id", user_id).execute()
        return True
    except Exception as e:
        print(f"set_code_acces error: {e}")
        return False


def get_profile_by_email(email: str) -> dict | None:
    """Retourne le profil par email."""
    sb = get_supabase()
    if sb is None: return None
    try:
        rows = sb.table("profiles").select("*")                 .eq("email", email.strip().lower()).execute().data or []
        return rows[0] if rows else None
    except: return None


def sign_out() -> bool:
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.auth.sign_out()
        return True
    except: return False
