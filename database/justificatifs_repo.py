"""Repository pour les justificatifs de dépenses (Supabase Storage)."""
import io
from database.supabase_client import get_supabase

TABLE   = "justificatifs"
BUCKET  = "justificatifs"


def upload_justificatif(
    frais_id: int,
    propriete_id: int,
    annee: int,
    nom_fichier: str,
    file_bytes: bytes,
    mime_type: str = "application/octet-stream",
) -> dict | None:
    """Upload un fichier dans Supabase Storage et enregistre le lien en DB."""
    sb = get_supabase()
    if sb is None:
        return None
    try:
        # Chemin unique dans le bucket
        import hashlib, time
        h = hashlib.md5(f"{frais_id}{nom_fichier}{time.time()}".encode()).hexdigest()[:8]
        ext = nom_fichier.rsplit(".", 1)[-1] if "." in nom_fichier else "bin"
        storage_path = f"prop{propriete_id}/{annee}/frais{frais_id}/{h}.{ext}"

        # Upload dans Storage
        sb.storage.from_(BUCKET).upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": mime_type, "upsert": "true"},
        )

        # Enregistrer le lien en DB
        row = sb.table(TABLE).insert({
            "frais_id":     frais_id,
            "propriete_id": propriete_id,
            "annee":        annee,
            "nom_fichier":  nom_fichier,
            "storage_path": storage_path,
            "taille_bytes": len(file_bytes),
            "mime_type":    mime_type,
        }).execute()
        return row.data[0] if row.data else None
    except Exception as e:
        print(f"upload_justificatif error: {e}")
        return None


def get_justificatifs(frais_id: int) -> list:
    sb = get_supabase()
    if sb is None:
        return []
    try:
        return sb.table(TABLE).select("*").eq("frais_id", frais_id)\
                 .order("created_at").execute().data or []
    except Exception:
        return []


def get_justificatifs_prop(propriete_id: int, annee: int) -> list:
    sb = get_supabase()
    if sb is None:
        return []
    try:
        return sb.table(TABLE).select("*, frais_deductibles(categorie, libelle, montant)")\
                 .eq("propriete_id", propriete_id).eq("annee", annee)\
                 .order("created_at").execute().data or []
    except Exception:
        return []


def get_download_url(storage_path: str) -> str | None:
    """Retourne une URL signée temporaire (1h) pour télécharger le fichier."""
    sb = get_supabase()
    if sb is None:
        return None
    try:
        r = sb.storage.from_(BUCKET).create_signed_url(storage_path, 3600)
        return r.get("signedURL") or r.get("signedUrl")
    except Exception as e:
        print(f"get_download_url error: {e}")
        return None


def delete_justificatif(justif_id: int, storage_path: str) -> bool:
    sb = get_supabase()
    if sb is None:
        return False
    try:
        sb.storage.from_(BUCKET).remove([storage_path])
        sb.table(TABLE).delete().eq("id", justif_id).execute()
        return True
    except Exception as e:
        print(f"delete_justificatif error: {e}")
        return False
