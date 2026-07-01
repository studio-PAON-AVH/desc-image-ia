import json
import logging
import shutil
import os
import time
import base64

from collections import defaultdict
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
    stream_image_describe,
    slice_to_image_descriptions,
    save_descriptions_slice,
    set_total_images,
    set_processed_images,
    update_task_status,
)
from backend.core.database.config import async_session, Task, Epub, ModelsIA
from backend.core.storage import storage_minio
from backend.core.redis.redis import redis_server_dev

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

MODEL_SALESFORCE = "Salesforce BLIP"
MODEL_FLORENCE = "Florence-2"
MODEL_GIT = "GIT Large"

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
    started = time.monotonic()
    # Nombre d'EPUB traités en parallèle dans le worker : décrément garanti en
    # finally même en cas d'échec/retry, pour que la jauge ne dérive pas.
    worker_tasks_in_flight.add(1)
    try:
        async with async_session() as session:
            await update_task_status(session, db_task_id, "in_progress")
            with tracer.start_as_current_span("extract_images_epub"):
                image_paths, temp_folder = extract_images_epub(epub_path)
            images = await save_images(session, db_task_id, epub_id, image_paths)
            epub_record = await session.get(Epub, epub_id)
            bucket, object_keys = storage_minio(
                epub_path=epub_path,
                list_images_paths=image_paths,
                tmp=temp_folder,
                file_name=epub_record.file_name
            )
            await save_images_storage(session, images, bucket, object_keys)

            img_list = []
            for img_path in image_paths:
                with open(img_path, "rb") as f:
                    img_bs64 = base64.b64encode(f.read()).decode("utf-8")
                    img_list.append(img_bs64)

            total_images = len(img_list)
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

            # Structure partielle, miroir de la sortie de get_image_describe.
            # On embarque le vrai nom de fichier (issu de l'EPUB) pour que le
            # front puisse l'afficher au lieu d'un index synthétique.
            partial = {
                f"image_{i}": {
                    "index": i,
                    "file_name": os.path.basename(image_paths[i]),
                    "salesforce_blip": None,
                    "florence2": None,
                    "git_large": None,
                }
                for i in range(total_images)
            }
            done_counts = defaultdict(int)
            seen = set()
            processed_images = 0

            async for evt in stream_image_describe(img_list):
                model_key = evt["model_key"]
                slice_map = slice_to_image_descriptions(
                    evt["batch_idx"],
                    evt["batch_size"],
                    model_key,
                    evt["result"],
                    evt["total_images"],
                )

                # Persiste ce slice (commit par (batch, modèle))
                await save_descriptions_slice(
                    session, images, model_mapping.get(model_key), slice_map
                )

                # Met à jour la structure partielle + la progression par image.
                # On compte chaque (modèle, image) à la première vue — même si le
                # slice est vide (modèle en échec) — pour qu'un modèle mort ne
                # bloque pas le compteur processed_images.
                offset = evt["batch_idx"] * evt["batch_size"]
                batch_indices = range(
                    offset, min(offset + evt["batch_size"], total_images)
                )
                for global_idx in batch_indices:
                    if global_idx in slice_map:
                        partial[f"image_{global_idx}"][model_key] = slice_map[global_idx]
                    key = (model_key, global_idx)
                    if key not in seen:
                        seen.add(key)
                        done_counts[global_idx] += 1
                        if done_counts[global_idx] == len(model_mapping):
                            processed_images += 1

                await set_processed_images(session, db_task_id, processed_images)
                r.set(
                    task_id,
                    json.dumps(
                        {
                            "status": "in_progress",
                            "epub_path": epub_path,
                            "total_images": total_images,
                            "processed_images": processed_images,
                            "descriptions": {
                                "images": partial,
                                "total_images": total_images,
                            },
                        },
                        ensure_ascii=False,
                    ),
                )

            await update_task_status(session, db_task_id, "completed")
            task_counter.add(1, {"status": "completed"})
            task_duration.record(time.monotonic() - started, {"status": "completed"})
            r.set(
                task_id,
                json.dumps(
                    {
                        "status": "completed",
                        "epub_path": epub_path,
                        "total_images": total_images,
                        "processed_images": processed_images,
                        "descriptions": {
                            "images": partial,
                            "total_images": total_images,
                        },
                    },
                    ensure_ascii=False,
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
        task_counter.add(1, {"status": "failed"})
        task_duration.record(time.monotonic() - started, {"status": "failed"})
        async with async_session() as session:
            await update_task_status(session, db_task_id, "failed")
        r.set(task_id, json.dumps({"error": str(e)}, ensure_ascii=False))
        raise
    finally:
        worker_tasks_in_flight.add(-1)
