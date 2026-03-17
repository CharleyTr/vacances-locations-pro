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
    Invite un nouvel utilisateur et lui donne accès aux propriétés spécifiées.
    Supabase envoie automatiquement un email d'invitation.
    """
    sb = get_supabase()
    if sb is None: return False
    try:
        # Inviter via Supabase Auth Admin API
        r = sb.auth.admin.invite_user_by_email(email)
        user_id = r.user.id if r.user else None
        if not user_id: return False

        # Créer le profil
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


def sign_out() -> bool:
    sb = get_supabase()
    if sb is None: return False
    try:
        sb.auth.sign_out()
        return True
    except: return False
