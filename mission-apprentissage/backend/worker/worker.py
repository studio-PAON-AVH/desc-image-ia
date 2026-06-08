import json
import shutil
import os
import base64

from sqlalchemy import select
from taskiq import TaskiqEvents

from ..broker import broker
from ..services.epub_service import (
    save_images,
    save_image_descriptions,
    extract_images_epub,
    get_image_describe,
    update_task_status,
)
from ..database import async_session, Task, Epub
from ..redis.redis import redis_server_dev

r = redis_server_dev()


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def recover_stuck_tasks(state):
    async with async_session() as session:
        result = await session.execute(
            select(Task).where(Task.status == "in_progress")
        )
        stuck_tasks = result.scalars().all()

        for task in stuck_tasks:
            redis_data = r.get(task.task_id_redis)
            if not redis_data:
                await update_task_status(session, task.id, "failed")
                continue

            data = json.loads(redis_data)
            epub_path = data.get("epub_path")

            epub_result = await session.execute(
                select(Epub).where(Epub.task_id == task.id)
            )
            epub = epub_result.scalar_one_or_none()

            if epub and epub_path and os.path.exists(epub_path):
                await update_task_status(session, task.id, "pending")
                await process_epub_describe.kiq(epub_path, task.task_id_redis, task.id, epub.id)
            else:
                await update_task_status(session, task.id, "failed")
                r.set(task.task_id_redis, json.dumps({"error": "Tâche interrompue, fichier perdu"}, ensure_ascii=False))


@broker.task(retry_on_error=True, max_retries=3)
async def process_epub_describe(epub_path: str, task_id: str, db_task_id: int, epub_id: int):
    try:
        async with async_session() as session:
            await update_task_status(session, db_task_id, "in_progress")

        image_paths, temp_folder = extract_images_epub(epub_path)

        async with async_session() as session:
            images = await save_images(session, db_task_id, epub_id, image_paths)

        img_list = []
        for img_path in image_paths:
            with open(img_path, "rb") as f:
                img_bs64 = base64.b64encode(f.read()).decode("utf-8")
                img_list.append(img_bs64)

        description = await get_image_describe(img_list)

        async with async_session() as session:
            from ..database import ModelsIA
            result_models = await session.execute(
                select(ModelsIA).where(ModelsIA.name.in_(["Salesforce BLIP", "Florence-2", "GIT Large"]))
            )
            models = {m.name: m.id for m in result_models.scalars().all()}
            model_mapping = {
                "salesforce_blip": models.get("Salesforce BLIP"),
                "florence2": models.get("Florence-2"),
                "git_large": models.get("GIT Large"),
            }
            await save_image_descriptions(session, images, description, model_mapping)
            await update_task_status(session, db_task_id, "completed")

        r.set(task_id, json.dumps(description, ensure_ascii=False))

        if temp_folder:
            shutil.rmtree(temp_folder)
        if os.path.exists(epub_path):
            os.remove(epub_path)

    except Exception as e:
        async with async_session() as session:
            await update_task_status(session, db_task_id, "failed")
        r.set(task_id, json.dumps({"error": str(e)}, ensure_ascii=False))
        raise