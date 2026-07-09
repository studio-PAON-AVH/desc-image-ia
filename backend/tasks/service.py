import json
import logging
import os
from collections import defaultdict
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database.config import Task
from ..core.storage import remove_objects
from ..core.task_coordination import mark_cancelled
from ..epub.repository import update_task_status as _update_task_status
from .repository import (
    find_task_by_redis_id,
    find_images_with_descriptions,
    find_images_by_task,
    find_image_by_position,
    find_all_models,
    delete_epub_and_children,
    upsert_final_description,
)

logger = logging.getLogger(__name__)

CANCELLABLE_STATUSES = ("pending", "in_progress")


async def get_image_location(
    session: AsyncSession, task_id_redis: str, index: int
) -> tuple[str, str] | None:
    """Retourne (bucket, object_key) de l'image à la position `index`, ou None."""
    task = await find_task_by_redis_id(session, task_id_redis)
    if not task:
        return None
    image = await find_image_by_position(session, task.id, index)
    if not image or not image.storage_object_key or not image.storage_bucket:
        return None
    return image.storage_bucket, image.storage_object_key


def _get_model_key(model_name: str) -> str | None:
    """Convertit le nom du modèle DB en clé frontend."""
    if not model_name:
        return None
    name_lower = model_name.lower()
    if "salesforce" in name_lower:
        return "salesforce_blip"
    if "florence" in name_lower:
        return "florence2"
    if "git" in name_lower:
        return "git_large"
    return model_name


async def build_task_progress_payload(session: AsyncSession, task_id_redis: str) -> dict | None:
    """Reconstruit le payload {images: {image_N: {modèle: {...}}}, total_images}
    attendu par le front (même forme que l'ancien blob Redis mis à jour à
    chaque slice), mais depuis la DB.

    Nécessaire depuis le passage en multi-queue : chaque tâche modèle persiste
    directement son résultat en DB, il n'y a plus de blob Redis agrégé à jour
    en continu à lire pour le polling in_progress/completed.
    """
    task = await find_task_by_redis_id(session, task_id_redis)
    if not task:
        return None

    images = await find_images_with_descriptions(session, task.id)

    images_payload = {}
    for image in images:
        entry = {
            "index": image.image_position_in_epub,
            "file_name": image.image_file_name,
            "salesforce_blip": None,
            "florence2": None,
            "git_large": None,
        }
        for desc in image.description:
            model_key = _get_model_key(desc.modelIA.name) if desc.modelIA else None
            if model_key in entry:
                entry[model_key] = {"french_description": desc.description_text}
        images_payload[f"image_{image.image_position_in_epub}"] = entry

    return {"images": images_payload, "total_images": len(images)}


async def get_task_descriptions(session: AsyncSession, task_id_redis: str) -> dict | None:
    """Récupère toutes les descriptions pour toutes les images d'une tâche."""
    task = await find_task_by_redis_id(session, task_id_redis)

    if not task:
        return None

    images = await find_images_with_descriptions(session, task.id)

    images_data = []
    for image in images:
        descriptions_data = []
        for desc in image.description:
            descriptions_data.append(
                {
                    "description_id": desc.id,
                    "description_text": desc.description_text,
                    "model_name": desc.modelIA.name if desc.modelIA else None,
                    "model_key": _get_model_key(desc.modelIA.name) if desc.modelIA else None,
                }
            )

        final = image.final_description[0] if image.final_description else None
        final_data = (
            {
                "description_text": final.description_text,
                "model_key": _get_model_key(final.modelIA.name) if final.modelIA else None,
            }
            if final
            else None
        )

        images_data.append(
            {
                "image_id": image.id,
                "image_file_name": image.image_file_name,
                "image_position_in_epub": image.image_position_in_epub,
                "descriptions": descriptions_data,
                "final_description": final_data,
            }
        )

    return {
        "task_id": task_id_redis,
        "status": task.status,
        "total_images": len(images),
        "images": images_data,
    }


async def validate_task_descriptions(session: AsyncSession, task_id_redis: str, descriptions: List):
    """
    Marque les descriptions choisies comme validées
    ou crée de nouvelles descriptions écrites par humain
    """
    task = await find_task_by_redis_id(session, task_id_redis)
    if not task:
        return None

    images = await find_images_by_task(session, task.id)

    models = await find_all_models(session)
    model_mapping = {
        "salesforce_blip": next((m.id for m in models if "Salesforce" in m.name), None),
        "florence2": next((m.id for m in models if "Florence" in m.name), None),
        "git_large": next((m.id for m in models if "GIT" in m.name), None),
    }

    for desc_data in descriptions:
        image_index = desc_data.image_index
        if image_index >= len(images):
            continue

        image = images[image_index]
        model_ia_id = model_mapping.get(desc_data.model) if desc_data.model else None

        await upsert_final_description(
            session=session,
            image_id=image.id,
            user_id=task.user_id,
            model_ia_id=model_ia_id,
            text=desc_data.text,
        )

    await session.commit()
    return True


async def cancel_task(session: AsyncSession, r, task: Task) -> None:
    """Annule une tâche en cours (ou en attente).

    Pose le flag Redis coopératif lu par les sous-tâches modèles avant de
    traiter leur batch, marque la tâche "cancelled", puis supprime l'Epub et
    toutes les données dérivées (DB + MinIO + fichier temporaire) afin de
    permettre de relancer un traitement sur le même fichier.
    """
    mark_cancelled(r, task.task_id_redis)
    await _update_task_status(session, task.id, "cancelled")

    epub_path = None
    redis_payload = r.get(task.task_id_redis)
    if redis_payload:
        try:
            epub_path = json.loads(redis_payload).get("epub_path")
        except ValueError:
            epub_path = None

    storage_locations = await delete_epub_and_children(session, task.id)
    by_bucket = defaultdict(list)
    for bucket, object_key in storage_locations:
        by_bucket[bucket].append(object_key)
    for bucket, object_keys in by_bucket.items():
        remove_objects(bucket, object_keys)

    if epub_path and os.path.exists(epub_path):
        try:
            os.remove(epub_path)
        except OSError as exc:
            logger.error("Impossible de supprimer le fichier epub %s: %s", epub_path, exc)

    r.set(task.task_id_redis, json.dumps({"status": "cancelled"}, ensure_ascii=False))
