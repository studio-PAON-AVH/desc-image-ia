from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from .repository import (
    find_task_by_redis_id,
    find_images_with_descriptions,
    find_images_by_task,
    find_all_models,
    upsert_final_description,
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
