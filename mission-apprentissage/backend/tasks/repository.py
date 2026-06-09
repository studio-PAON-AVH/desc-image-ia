from datetime import datetime
from typing import List
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database.config import Task, Images, ImageDescription, ModelsIA


async def find_task_by_redis_id(session: AsyncSession, task_id_redis: str) -> Task | None:
    result = await session.execute(select(Task).where(Task.task_id_redis == task_id_redis))
    return result.scalar_one_or_none()


async def find_all_tasks(session: AsyncSession, limit: int, offset: int) -> list:
    result = await session.execute(Task.__table__.select().limit(limit).offset(offset))
    return result.fetchall()


async def find_images_with_descriptions(session: AsyncSession, task_id: int) -> List[Images]:
    result = await session.execute(
        select(Images)
        .options(selectinload(Images.description).selectinload(ImageDescription.modelIA))
        .where(Images.task_id == task_id)
        .order_by(Images.image_position_in_epub)
    )
    return result.scalars().all()


async def find_images_by_task(session: AsyncSession, task_id: int) -> List[Images]:
    result = await session.execute(
        select(Images).where(Images.task_id == task_id).order_by(Images.image_position_in_epub)
    )
    return result.scalars().all()


async def find_all_models(session: AsyncSession) -> List[ModelsIA]:
    result = await session.execute(select(ModelsIA))
    return result.scalars().all()


async def find_description_by_image_and_model(
    session: AsyncSession, image_id: int, model_id: int
) -> ImageDescription | None:
    result = await session.execute(
        select(ImageDescription).where(
            ImageDescription.image_id == image_id,
            ImageDescription.model_ia_id == model_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_ai_descriptions_for_image(session: AsyncSession, image_id: int) -> None:
    await session.execute(
        delete(ImageDescription).where(
            ImageDescription.image_id == image_id,
            ImageDescription.is_written_by_ai == True,
        )
    )


async def delete_descriptions_except_model(
    session: AsyncSession, image_id: int, model_id: int
) -> None:
    await session.execute(
        delete(ImageDescription).where(
            ImageDescription.image_id == image_id,
            ImageDescription.model_ia_id != model_id,
        )
    )


async def create_human_description(
    session: AsyncSession, image_id: int, text: str
) -> ImageDescription:
    desc = ImageDescription(
        image_id=image_id,
        model_ia_id=None,
        description_text=text,
        is_written_by_ai=False,
        is_written_by_human=True,
        generated_at=datetime.now(),
        validated_by_human=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(desc)
    return desc
