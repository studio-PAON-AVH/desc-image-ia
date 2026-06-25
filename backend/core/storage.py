import os
import re
import unicodedata
from datetime import timedelta
from typing import List, Optional, Tuple

import ebooklib
from ebooklib import epub
from minio import Minio
from minio.error import S3Error

from ..epub.service import extract_images_epub


def _slugify(value: str) -> str:
    """Translitère + nettoie une chaîne pour un usage S3 (minuscules, [a-z0-9-])."""
    # "Les Misérables" -> "les miserables"
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = value.lower()
    # tout ce qui n'est pas alphanumérique devient un tiret
    value = re.sub(r"[^a-z0-9]+", "-", value)
    # pas de tirets en début/fin ni de doublons
    return re.sub(r"-{2,}", "-", value).strip("-")


def epub_name(epub_path: str, use_title: bool = False) -> str:
    """Nom de base d'un EPUB.

    - use_title=False : nom du fichier sans extension (ex: "mon_livre").
    - use_title=True  : titre des métadonnées DC:title, avec repli sur le
    nom de fichier si absent.
    """
    if use_title:
        book = epub.read_epub(epub_path)
        meta = book.get_metadata("DC", "title")
        if meta and meta[0] and meta[0][0]:
            return meta[0][0]
    return os.path.splitext(os.path.basename(epub_path))[0]


def year_bucket(year: Optional[int] = None, prefix: str = "epub") -> str:
    """Nom de bucket par année, pour faciliter l'archivage (ex: "epub-2026").

    `year=None` -> année courante (année de traitement/ingestion).
    """
    if year is None:
        from datetime import datetime, timezone

        year = datetime.now(timezone.utc).year
    return f"{prefix}-{year}" if prefix else str(year)


def sanitize_bucket_name(name: str, prefix: str = "epub", fallback: str = "epub") -> str:
    """Rend un nom conforme aux règles de bucket S3/MinIO.

    Règles : 3-63 caractères, minuscules, [a-z0-9.-], commence/finit par
    un alphanumérique. `prefix` permet de regrouper/garantir la longueur min.
    """
    slug = _slugify(name) or fallback
    bucket = f"{prefix}-{slug}" if prefix else slug
    bucket = bucket[:63].strip("-")
    # garantit la longueur minimale de 3 caractères
    if len(bucket) < 3:
        bucket = f"{bucket}-{fallback}"[:63].strip("-")
    return bucket


def get_client() -> Minio:
    return Minio(
        endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        secure=False,
    )


def ensure_bucket(client: Minio, bucket: str) -> None:
    """Crée le bucket s'il n'existe pas (idempotent)."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def _content_type(file_name: str) -> str:
    ext = os.path.splitext(file_name)[1].lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")


def upload_image(
    client: Minio, local_path: str, object_name: str, bucket: str
) -> None:
    client.fput_object(
        bucket_name=bucket,
        object_name=object_name,
        file_path=local_path,
        content_type=_content_type(local_path),
    )


def upload_extracted_images(
    image_paths: List[str], prefix: str, bucket: str
) -> List[Tuple[str, str]]:
    """Uploade les images extraites d'un EPUB dans MinIO.

    `prefix` isole les images d'un EPUB/tâche (ex: f"epub_{epub_id}").
    Retourne la liste [(local_path, object_name), ...].
    """
    client = get_client()
    ensure_bucket(client, bucket)

    uploaded = []
    for path in image_paths:
        base = os.path.basename(path)
        object_name = f"{prefix}/{base}" if prefix else base
        upload_image(client, path, object_name, bucket)
        uploaded.append((path, object_name))
    return uploaded


def presigned_url(
    object_name: str, bucket: str, hours: int = 1
) -> str:
    client = get_client()
    return client.presigned_get_object(
        bucket, object_name, expires=timedelta(hours=hours)
    )

def storage_minio(epub_path: str, list_images_paths: List[str], tmp: str, file_name: str):
    if not epub_path:
        print("Epub non trouvé")
        return

    # `file_name` = nom d'origine de l'EPUB uploadé (ex: "Les Misérables.epub").
    # On nomme le dossier MinIO d'après lui, et non d'après `epub_path` qui est
    # le fichier temporaire (ex: "tmp1a2b3c.epub").
    name = epub_name(file_name, use_title=False)
    bucket = year_bucket()
    folder = _slugify(name)
    uploaded = upload_extracted_images(list_images_paths, prefix=folder, bucket=bucket)

    for _, object_name in uploaded:
        print("upload ok:", object_name)   # ex: collection-200-images/image_001.jpg
        print("url:", presigned_url(object_name, bucket))

    

if __name__ == "__main__":
    try:
        storage_minio()
    except S3Error as exc:
        print("error S3.", exc)
