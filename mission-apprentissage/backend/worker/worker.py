import json
import logging
import shutil
import os
import base64

from sqlalchemy import select
from taskiq import TaskiqEvents

logger = logging.getLogger(__name__)

from ..broker import broker
from ..epub.service import (
    save_images,
    save_image_descriptions,
    extract_images_epub,
    get_image_describe,
    update_task_status,
)
from ..core.database.config import async_session, Task, Epub, ModelsIA

MODEL_SALESFORCE = "Salesforce BLIP"
MODEL_FLORENCE = "Florence-2"
MODEL_GIT = "GIT Large"
from ..core.redis.redis import redis_server_dev


r = redis_server_dev()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def recover_stuck_tasks(state):
    async with async_session() as session:
        result = await session.execute(select(Task).where(Task.status == "in_progress"))
        stuck_tasks = result.scalars().all()

        for task in stuck_tasks:
            redis_data = r.get(task.task_id_redis)
            if not redis_data:
                await update_task_status(session, task.id, "failed")
                continue

            data = json.loads(redis_data)
            epub_path = data.get("epub_path")

            epub_result = await session.execute(select(Epub).where(Epub.task_id == task.id))
            epub = epub_result.scalar_one_or_none()

            if epub and epub_path and os.path.exists(epub_path):
                await update_task_status(session, task.id, "pending")
                await process_epub_describe.kiq(epub_path, task.task_id_redis, task.id, epub.id)
            else:
                await update_task_status(session, task.id, "failed")
                r.set(
                    task.task_id_redis,
                    json.dumps({"error": "Tâche interrompue, fichier perdu"}, ensure_ascii=False),
                )


@broker.task(retry_on_error=True, max_retries=3)
async def process_epub_describe(epub_path: str, task_id: str, db_task_id: int, epub_id: int):
    try:
        async with async_session() as session:
            await update_task_status(session, db_task_id, "in_progress")
            image_paths, temp_folder = extract_images_epub(epub_path)
            images = await save_images(session, db_task_id, epub_id, image_paths)

            img_list = []
            for img_path in image_paths:
                with open(img_path, "rb") as f:
                    img_bs64 = base64.b64encode(f.read()).decode("utf-8")
                    img_list.append(img_bs64)

            description = await get_image_describe(img_list)

            result_models = await session.execute(
                select(ModelsIA).where(
                    ModelsIA.name.in_([MODEL_SALESFORCE, MODEL_FLORENCE, MODEL_GIT])
                )
            )
            models = {m.name: m.id for m in result_models.scalars().all()}
            model_mapping = {
                "salesforce_blip": models.get(MODEL_SALESFORCE),
                "florence2": models.get(MODEL_FLORENCE),
                "git_large": models.get(MODEL_GIT),
            }
            await save_image_descriptions(session, images, description, model_mapping)
            await update_task_status(session, db_task_id, "completed")

            r.set(
                task_id,
                json.dumps(
                    {"epub_path": epub_path, "descriptions": description}, ensure_ascii=False
                ),
            )

            if temp_folder:
                try:
                    shutil.rmtree(temp_folder)
                except OSError as e:
                    logger.error(
                        "Impossible de supprimer le dossier temporaire %s: %s", temp_folder, e
                    )

    except Exception as e:
        logger.exception("Erreur lors du traitement de la tâche %s", task_id)
        async with async_session() as session:
            await update_task_status(session, db_task_id, "failed")
        r.set(task_id, json.dumps({"error": str(e)}, ensure_ascii=False))
        raise
