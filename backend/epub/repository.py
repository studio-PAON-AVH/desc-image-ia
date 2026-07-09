import os
from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update as sql_update, delete
from ..core.database.config import Task, Epub, Images, DescriptionByIA


async def create_task(session: AsyncSession, task_id_redis: str, user_id: int) -> Task:
    new_task = Task(
        task_id_redis=task_id_redis,
        user_id=user_id,
        status="pending",
        total_images=0,
        processed_images=0,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
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


async def set_images_storage(
    session: AsyncSession, images: List[Images], bucket: str, object_keys: List[str]
) -> None:
    """Associe à chaque image son emplacement MinIO (bucket + clé d'objet).

    `images` et `object_keys` sont dans le même ordre (tous deux dérivés de la
    même liste `image_paths`), donc on les apparie avec zip().
    """
    if not bucket:
        return
    for img, object_key in zip(images, object_keys):
        img.storage_bucket = bucket
        img.storage_object_key = object_key
    await session.commit()


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
                        DescriptionByIA(
                            image_id=image.id,
                            model_ia_id=model_id,
                            description_text=description_text,
                            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                        )
                    )
    await session.commit()


async def save_image_descriptions_slice(
    session: AsyncSession,
    images: List[Images],
    model_id: int | None,
    slice_map: dict,
) -> int:
    """Persiste les descriptions d'un slice (un batch pour un seul modèle).

    Idempotent : pour chaque (image, modèle) on supprime l'éventuelle ligne
    existante avant d'insérer, afin de ne pas créer de doublon lors d'un retry
    de la tâche. Commit par slice. Retourne le nombre de lignes écrites.
    """
    written = 0
    for global_idx, item in slice_map.items():
        if global_idx >= len(images):
            continue
        if not (item and isinstance(item, dict)):
            continue
        description_text = item.get("french_description")
        if not description_text:
            continue
        image_id = images[global_idx].id
        await session.execute(
            delete(DescriptionByIA).where(
                DescriptionByIA.image_id == image_id,
                DescriptionByIA.model_ia_id == model_id,
            )
        )
        session.add(
            DescriptionByIA(
                image_id=image_id,
                model_ia_id=model_id,
                description_text=description_text,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        written += 1
    await session.commit()
    return written


async def save_image_descriptions_by_ids(
    session: AsyncSession,
    model_id: int | None,
    items: List[tuple[int, str]],
) -> int:
    """Persiste des descriptions identifiées par (image_id, texte) directement,
    sans dépendre d'une liste ordonnée d'Images complète.

    Utilisé par les tâches taskiq par modèle : chacune ne connaît que le
    sous-ensemble d'images de son propre batch, pas la liste complète de
    l'EPUB. Idempotent comme save_image_descriptions_slice (delete puis insert).
    """
    written = 0
    for image_id, description_text in items:
        if not description_text:
            continue
        await session.execute(
            delete(DescriptionByIA).where(
                DescriptionByIA.image_id == image_id,
                DescriptionByIA.model_ia_id == model_id,
            )
        )
        session.add(
            DescriptionByIA(
                image_id=image_id,
                model_ia_id=model_id,
                description_text=description_text,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
                updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
        written += 1
    await session.commit()
    return written


async def set_task_total_images(session: AsyncSession, db_task_id: int, total: int) -> None:
    await session.execute(
        sql_update(Task)
        .where(Task.id == db_task_id)
        .values(total_images=total)
    )
    await session.commit()


async def set_task_processed_images(
    session: AsyncSession, db_task_id: int, processed: int
) -> None:
    await session.execute(
        sql_update(Task)
        .where(Task.id == db_task_id)
        .values(processed_images=processed)
    )
    await session.commit()


async def update_task_status(session: AsyncSession, db_task_id: int, status: str) -> None:
    await session.execute(
        sql_update(Task)
        .where(Task.id == db_task_id)
        .values(status=status)
    )
    await session.commit()
