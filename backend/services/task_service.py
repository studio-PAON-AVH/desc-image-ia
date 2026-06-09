from datetime import datetime
from typing import List
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import Task, Images, ImageDescription, ModelsIA


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


async def get_task_descriptions(
    session: AsyncSession,
    task_id_redis: str
) -> dict | None:
    """Récupère toutes les descriptions pour toutes les images d'une tâche."""
    result = await session.execute(
        select(Task).where(Task.task_id_redis == task_id_redis)
    )
    task = result.scalar_one_or_none()

    if not task:
        return None

    result = await session.execute(
        select(Images).where(Images.task_id == task.id)
        .order_by(Images.image_position_in_epub)
    )
    images = result.scalars().all()

    images_data = []
    for image in images:
        descriptions_data = []
        for desc in image.description:
            descriptions_data.append({
                "description_id": desc.id,
                "description_text": desc.description_text,
                "model_name": desc.modelIA.name if desc.modelIA else None,
                "model_key": _get_model_key(desc.modelIA.name) if desc.modelIA else None,
                "is_written_by_ai": desc.is_written_by_ai,
                "is_written_by_human": desc.is_written_by_human,
                "validated_by_human": desc.validated_by_human,
            })

        images_data.append({
            "image_id": image.id,
            "image_file_name": image.image_file_name,
            "image_position_in_epub": image.image_position_in_epub,
            "descriptions": descriptions_data,
        })

    return {
        "task_id": task_id_redis,
        "status": task.status,
        "total_images": len(images),
        "images": images_data,
    }


async def validate_task_descriptions(
    session: AsyncSession,
    task_id_redis: str,
    descriptions: List
):
    """
    Marque les descriptions choisies comme validées
    ou crée de nouvelles descriptions écrites par humain
    """
    # Récupérer la tâche
    result = await session.execute(
        select(Task).where(Task.task_id_redis == task_id_redis)
    )
    task = result.scalar_one_or_none()

    if not task:
        return None

    # Récupérer toutes les images de cette tâche
    result = await session.execute(
        select(Images).where(Images.task_id == task.id).order_by(Images.image_position_in_epub)
    )
    images = result.scalars().all()

    # Mapping nom modèle → ID
    result = await session.execute(select(ModelsIA))
    models = result.scalars().all()
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
            # Supprimer d'abord toutes les descriptions IA pour cette image
            await session.execute(
                delete(ImageDescription).where(
                    ImageDescription.image_id == image.id,
                    ImageDescription.is_written_by_ai == True
                )
            )

            # Créer une nouvelle description écrite par humain
            new_desc = ImageDescription(
                image_id=image.id,
                model_ia_id=None,  # Pas de modèle IA
                description_text=desc_data.text,
                is_written_by_ai=False,
                is_written_by_human=True,
                generated_at=datetime.now(),
                validated_by_human=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(new_desc)

        elif desc_data.model:
            # Marquer la description IA comme validée
            model_id = model_mapping.get(desc_data.model)
            if model_id:
                result = await session.execute(
                    select(ImageDescription).where(
                        ImageDescription.image_id == image.id,
                        ImageDescription.model_ia_id == model_id
                    )
                )
                existing_desc = result.scalar_one_or_none()

                if existing_desc:
                    existing_desc.validated_by_human = True
                    existing_desc.updated_at = datetime.now()

                    # Supprimer les descriptions non validées
                    await session.execute(
                        delete(ImageDescription).where(
                            ImageDescription.image_id == image.id,
                            ImageDescription.model_ia_id != model_id
                        )
                    )

    await session.commit()
    return True