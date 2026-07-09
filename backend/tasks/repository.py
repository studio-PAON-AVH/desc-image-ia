from datetime import datetime
from typing import List
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database.config import (
    Task,
    Epub,
    Images,
    DescriptionByIA,
    DescriptionFinale,
    ModelsIA,
)


async def find_task_by_redis_id(session: AsyncSession, task_id_redis: str) -> Task | None:
    result = await session.execute(select(Task).where(Task.task_id_redis == task_id_redis))
    return result.scalar_one_or_none()


async def find_all_tasks(session: AsyncSession, limit: int, offset: int) -> list:
    result = await session.execute(Task.__table__.select().limit(limit).offset(offset))
    return result.fetchall()


async def find_images_with_descriptions(session: AsyncSession, task_id: int) -> List[Images]:
    result = await session.execute(
        select(Images)
        .options(
            selectinload(Images.description).selectinload(DescriptionByIA.modelIA),
            selectinload(Images.final_description).selectinload(DescriptionFinale.modelIA),
        )
        .where(Images.task_id == task_id)
        .order_by(Images.image_position_in_epub)
    )
    return result.scalars().all()


async def find_images_by_task(session: AsyncSession, task_id: int) -> List[Images]:
    result = await session.execute(
        select(Images).where(Images.task_id == task_id).order_by(Images.image_position_in_epub)
    )
    return result.scalars().all()


async def find_image_by_position(
    session: AsyncSession, task_id: int, position: int
) -> Images | None:
    result = await session.execute(
        select(Images).where(
            Images.task_id == task_id,
            Images.image_position_in_epub == position,
        )
    )
    return result.scalar_one_or_none()


async def delete_epub_and_children(session: AsyncSession, task_id: int) -> List[tuple]:
    """Supprime l'Epub et toutes les données dérivées (images, descriptions)
    liées à une tâche, afin de permettre un nouvel upload du même fichier.

    Retourne la liste des emplacements MinIO (bucket, object_key) des images
    qui étaient stockées, pour que l'appelant supprime aussi les objets.
    """
    images = await find_images_by_task(session, task_id)
    image_ids = [image.id for image in images]
    storage_locations = [
        (image.storage_bucket, image.storage_object_key)
        for image in images
        if image.storage_bucket and image.storage_object_key
    ]

    if image_ids:
        await session.execute(delete(DescriptionByIA).where(DescriptionByIA.image_id.in_(image_ids)))
        await session.execute(
            delete(DescriptionFinale).where(DescriptionFinale.image_id.in_(image_ids))
        )
        await session.execute(delete(Images).where(Images.id.in_(image_ids)))

    await session.execute(delete(Epub).where(Epub.task_id == task_id))
    await session.commit()
    return storage_locations


async def find_all_models(session: AsyncSession) -> List[ModelsIA]:
    result = await session.execute(select(ModelsIA))
    return result.scalars().all()


async def find_description_by_image_and_model(
    session: AsyncSession, image_id: int, model_id: int
) -> DescriptionByIA | None:
    result = await session.execute(
        select(DescriptionByIA).where(
            DescriptionByIA.image_id == image_id,
            DescriptionByIA.model_ia_id == model_id,
        )
    )
    return result.scalar_one_or_none()


async def find_final_description_by_image(
    session: AsyncSession, image_id: int
) -> DescriptionFinale | None:
    result = await session.execute(
        select(DescriptionFinale).where(DescriptionFinale.image_id == image_id)
    )
    return result.scalar_one_or_none()


async def upsert_final_description(
    session: AsyncSession,
    image_id: int,
    user_id: int,
    model_ia_id: int | None,
    text: str,
) -> DescriptionFinale:
    """Crée ou met à jour la DescriptionFinale d'une image.

    model_ia_id=None signifie description écrite à la main (aucun modèle IA choisi).
    """
    now = datetime.now()
    existing = await find_final_description_by_image(session, image_id)
    if existing is not None:
        existing.user_id = user_id
        existing.model_ia_id = model_ia_id
        existing.description_text = text
        existing.validated_by_human = True
        existing.updated_at = now
        return existing
    desc = DescriptionFinale(
        user_id=user_id,
        image_id=image_id,
        model_ia_id=model_ia_id,
        description_text=text,
        validated_by_human=True,
        created_at=now,
        updated_at=now,
    )
    session.add(desc)
    return desc
