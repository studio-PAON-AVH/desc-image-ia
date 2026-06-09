import os
from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update as sql_update
from ..core.database.config import Task, Epub, Images, ImageDescription


async def create_task(session: AsyncSession, task_id_redis: str, user_id: int) -> Task:
    new_task = Task(
        task_id_redis=task_id_redis,
        user_id=user_id,
        status="pending",
        total_images=0,
        processed_images=0,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        started_at=datetime.now(timezone.utc).replace(tzinfo=None),
        completed_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return new_task


async def create_epub(session: AsyncSession, task_id: int, file_name: str) -> Epub:
    new_epub = Epub(
        task_id=task_id,
        file_name=file_name,
        upload_date=datetime.now(timezone.utc).replace(tzinfo=None),
        status="uploaded",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    session.add(new_epub)
    await session.commit()
    await session.refresh(new_epub)
    return new_epub


async def create_images_batch(
    session: AsyncSession, task_id: int, epub_id: int, image_paths: List[str]
) -> List[Images]:
    images = []
    for position, image_path in enumerate(image_paths):
        new_image = Images(
            task_id=task_id,
            epub_id=epub_id,
            image_file_name=os.path.basename(image_path),
            image_position_in_epub=position,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        session.add(new_image)
        images.append(new_image)
    await session.commit()
    for img in images:
        await session.refresh(img)
    return images


async def create_image_descriptions_batch(
    session: AsyncSession,
    images: List[Images],
    results: dict,
    model_ia_mapping: dict,
) -> None:
    for idx, image in enumerate(images):
        image_key = f"image_{idx}"
        if image_key not in results["images"]:
            continue
        descriptions = results["images"][image_key]
        for model_name, model_id in model_ia_mapping.items():
            description_data = descriptions.get(model_name)
            if description_data and isinstance(description_data, dict):
                description_text = description_data.get("french_description")
                if description_text:
                    session.add(
                        ImageDescription(
                            image_id=image.id,
                            model_ia_id=model_id,
                            description_text=description_text,
                            is_written_by_ai=True,
                            is_written_by_human=False,
                            generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                            validated_by_human=False,
                            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        )
                    )
    await session.commit()


async def update_task_status(session: AsyncSession, db_task_id: int, status: str) -> None:
    await session.execute(
        sql_update(Task)
        .where(Task.id == db_task_id)
        .values(status=status, updated_at=datetime.now(timezone.utc).replace(tzinfo=None))
    )
    await session.commit()
