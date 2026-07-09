import json
import logging
import shutil
import os
import time

from opentelemetry import trace
from sqlalchemy import select
from taskiq import TaskiqEvents

from backend.broker import broker
from backend.core.observability.setup import setup_observability
from backend.core.observability.metric import (
    epub_images_per_file,
    task_counter,
    task_duration,
    worker_tasks_in_flight,
)
from backend.epub.service import (
    save_images,
    save_images_storage,
    extract_images_epub,
    set_total_images,
    update_task_status,
    _resolve_batch_size,
)
from backend.core.database.config import async_session, Task, Epub, ModelsIA
from backend.core.storage import storage_minio
from backend.core.redis.redis import redis_server_dev
from ..core.task_coordination import (
    MODEL_KEYS,
    COORDINATION_TTL_SECONDS,
    is_cancelled,
    remaining_key,
    processed_key,
    started_key,
)
from .model_tasks import (
    describe_batch_salesforce_blip,
    describe_batch_florence2,
    describe_batch_git_large,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

MODEL_SALESFORCE = "Salesforce BLIP"
MODEL_FLORENCE = "Florence-2"
MODEL_GIT = "GIT Large"

MODEL_BATCH_TASKS = {
    "salesforce_blip": describe_batch_salesforce_blip,
    "florence2": describe_batch_florence2,
    "git_large": describe_batch_git_large,
}

r = redis_server_dev()


# Ce module est aussi importé par l'API (pour .kiq) : le setup ne doit donc
# pas être fait à l'import, sinon il s'exécuterait dans le processus API avec
# le mauvais service.name. WORKER_STARTUP ne se déclenche que dans le worker.
@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def init_observability(state):
    setup_observability("desc-image-worker")


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
    """Orchestrateur : extrait les images, les stocke (DB + MinIO), puis
    répartit ("fan-out") chaque (batch, modèle) sur la queue taskiq dédiée à ce
    modèle. Ne fait plus lui-même les appels aux modèles IA — il ne les
    attend donc pas : chaque tâche modèle persiste directement son résultat et
    la dernière à se terminer finalise le statut de la tâche (cf. model_tasks.py).
    """
    started = time.monotonic()
    # Ne couvre que la phase d'ingestion (extraction + upload) : les appels aux
    # modèles se font maintenant dans des workers séparés, hors de ce gauge.
    worker_tasks_in_flight.add(1)
    try:
        async with async_session() as session:
            await update_task_status(session, db_task_id, "in_progress")

            if is_cancelled(r, task_id):
                await update_task_status(session, db_task_id, "cancelled")
                return

            with tracer.start_as_current_span("extract_images_epub"):
                image_paths, temp_folder = extract_images_epub(epub_path)
            images = await save_images(session, db_task_id, epub_id, image_paths)
            epub_record = await session.get(Epub, epub_id)
            bucket, object_keys = storage_minio(
                epub_path=epub_path,
                list_images_paths=image_paths,
                tmp=temp_folder,
                file_name=epub_record.file_name,
            )
            await save_images_storage(session, images, bucket, object_keys)

            if temp_folder:
                try:
                    shutil.rmtree(temp_folder)
                except OSError as e:
                    logger.error(
                        "Impossible de supprimer le dossier temporaire %s: %s", temp_folder, e
                    )

            total_images = len(image_paths)
            await set_total_images(session, db_task_id, total_images)
            epub_images_per_file.record(total_images)

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

        if total_images == 0:
            async with async_session() as session:
                await update_task_status(session, db_task_id, "completed")
            r.set(
                task_id,
                json.dumps({"status": "completed", "total_images": 0}, ensure_ascii=False),
            )
            return

        r.set(started_key(task_id), started, ex=COORDINATION_TTL_SECONDS)
        r.set(processed_key(task_id), 0, ex=COORDINATION_TTL_SECONDS)
        r.set(
            task_id,
            json.dumps(
                {"status": "in_progress", "epub_path": epub_path, "total_images": total_images},
                ensure_ascii=False,
            ),
        )

        batch_size = _resolve_batch_size()
        batches = [
            list(range(i, min(i + batch_size, total_images)))
            for i in range(0, total_images, batch_size)
        ]
        total_sub_tasks = len(batches) * len(MODEL_KEYS)
        r.set(remaining_key(task_id), total_sub_tasks, ex=COORDINATION_TTL_SECONDS)

        for indices in batches:
            batch_images = [
                {"image_id": images[i].id, "object_key": object_keys[i]} for i in indices
            ]
            for model_key in MODEL_KEYS:
                await MODEL_BATCH_TASKS[model_key].kiq(
                    task_id,
                    db_task_id,
                    model_key,
                    model_mapping.get(model_key),
                    bucket,
                    batch_images,
                    total_images,
                )

    except Exception as e:
        logger.exception("Erreur lors du traitement de la tâche %s", task_id)
        task_counter.add(1, {"status": "failed"})
        task_duration.record(time.monotonic() - started, {"status": "failed"})
        async with async_session() as session:
            await update_task_status(session, db_task_id, "failed")
        r.set(task_id, json.dumps({"error": str(e)}, ensure_ascii=False))
        raise
    finally:
        worker_tasks_in_flight.add(-1)
