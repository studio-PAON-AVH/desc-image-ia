from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import (
    find_task_by_redis_id,
    find_images_with_descriptions,
    find_images_by_task,
    find_all_models,
    find_description_by_image_and_model,
    delete_ai_descriptions_for_image,
    delete_descriptions_except_model,
    create_human_description,
)


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
                    "is_written_by_ai": desc.is_written_by_ai,
                    "is_written_by_human": desc.is_written_by_human,
                    "validated_by_human": desc.validated_by_human,
                }
            )

        images_data.append(
            {
                "image_id": image.id,
                "image_file_name": image.image_file_name,
                "image_position_in_epub": image.image_position_in_epub,
                "descriptions": descriptions_data,
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
        "salesforce": next((m.id for m in models if "Salesforce" in m.name), None),
        "florence2": next((m.id for m in models if "Florence" in m.name), None),
        "git_large": next((m.id for m in models if "GIT" in m.name), None),
    }

    for desc_data in descriptions:
        image_index = desc_data.image_index
        if image_index >= len(images):
            continue

        image = images[image_index]

        if desc_data.is_written_by_human:
            await delete_ai_descriptions_for_image(session, image.id)
            await create_human_description(session, image.id, desc_data.text)

        elif desc_data.model:
            model_id = model_mapping.get(desc_data.model)
            if model_id:
                existing_desc = await find_description_by_image_and_model(
                    session, image.id, model_id
                )
                if existing_desc:
                    existing_desc.validated_by_human = True
                    existing_desc.updated_at = datetime.now()
                    await delete_descriptions_except_model(session, image.id, model_id)

    await session.commit()
    return True
