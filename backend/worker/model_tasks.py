import asyncio
import base64
import json
import logging
import time

from opentelemetry import trace
from taskiq import TaskiqEvents

from backend.broker import broker_salesforce, broker_florence2, broker_git
from backend.core.database.config import async_session, Task
from backend.core.observability.metric import (
    ai_call_duration,
    ai_call_errors,
    ai_call_in_flight,
    ai_call_wait,
    ai_call_waiting,
    task_counter,
    task_duration,
)
from backend.core.observability.setup import setup_observability
from backend.core.redis.redis import redis_server_dev
from backend.core.storage import download_object_bytes
from backend.epub.repository import update_task_status as _repo_update_task_status
from backend.epub.service import (
    call_model,
    get_model_semaphore,
    get_model_url,
    save_descriptions_by_ids,
    set_processed_images,
)
from ..core.task_coordination import (
    NUM_MODELS,
    is_cancelled,
    image_done_key,
    processed_key,
    remaining_key,
    started_key,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

r = redis_server_dev()
CALL_MODEL_MAX_ATTEMPTS = 3
CALL_MODEL_RETRY_DELAYS_SECONDS = [2, 5]


# broker (l'orchestrateur, worker.py) a son propre WORKER_STARTUP qui appelle
# setup_observability : chaque worker taskiq ne démarre qu'un seul broker, donc
# ce hook doit être répété ici pour broker_salesforce/florence2/git, sans quoi
# ces 3 processus tournent sans OTel (métriques ai_call_*/task_* et traces
# jamais exportées, cf. WORKER_STARTUP ne se déclenche que pour le broker
# effectivement lancé dans le processus).
@broker_salesforce.on_event(TaskiqEvents.WORKER_STARTUP)
async def _init_observability_salesforce(state):
    setup_observability("desc-image-worker")


@broker_florence2.on_event(TaskiqEvents.WORKER_STARTUP)
async def _init_observability_florence2(state):
    setup_observability("desc-image-worker")


@broker_git.on_event(TaskiqEvents.WORKER_STARTUP)
async def _init_observability_git(state):
    setup_observability("desc-image-worker")


async def _persist_slice(model_id, batch_images: list[dict], results: list) -> None:
    """Associe chaque résultat du modèle à l'image correspondante (même ordre
    que batch_images, qui est l'ordre d'envoi au modèle) et persiste."""
    items = []
    for i, entry in enumerate(batch_images):
        item = results[i] if i < len(results) else None
        if item and isinstance(item, dict):
            text = item.get("french_description")
            if text:
                items.append((entry["image_id"], text))

    async with async_session() as session:
        await save_descriptions_by_ids(session, model_id, items)


async def _finalize_if_done(task_id: str, db_task_id: int, total_images: int) -> None:
    """Décrémente le compteur de sous-tâches restantes ; la dernière à
    atteindre 0 finalise la tâche (marque "completed", enregistre les
    métriques). Ne fait rien si la tâche a déjà été finalisée autrement
    (échec d'un autre batch, annulation)."""
    remaining = r.decr(remaining_key(task_id))
    if remaining != 0:
        return

    async with async_session() as session:
        task = await session.get(Task, db_task_id)
        if task is None or task.status != "in_progress":
            return
        await _repo_update_task_status(session, db_task_id, "completed")

    started_raw = r.get(started_key(task_id))
    if started_raw is not None:
        task_duration.record(time.monotonic() - float(started_raw), {"status": "completed"})
    task_counter.add(1, {"status": "completed"})

    # epub_path n'est pas passé aux tâches modèles (elles ne travaillent que sur
    # des objets MinIO) : on le récupère du blob "in_progress" écrit par
    # l'orchestrateur pour ne pas le perdre dans le blob final — download_epub
    # et add_descriptions_to_epub en ont besoin pour générer l'EPUB modifié.
    epub_path = None
    existing_raw = r.get(task_id)
    if existing_raw:
        try:
            existing_data = json.loads(existing_raw)
        except (ValueError, TypeError):
            existing_data = None
        if isinstance(existing_data, dict):
            epub_path = existing_data.get("epub_path")

    r.set(
        task_id,
        json.dumps(
            {"status": "completed", "epub_path": epub_path, "total_images": total_images},
            ensure_ascii=False,
        ),
    )


async def _mark_failed(task_id: str, db_task_id: int, error: str) -> None:
    async with async_session() as session:
        await _repo_update_task_status(session, db_task_id, "failed")
    r.set(task_id, json.dumps({"error": error}, ensure_ascii=False))
    task_counter.add(1, {"status": "failed"})
    started_raw = r.get(started_key(task_id))
    if started_raw is not None:
        task_duration.record(time.monotonic() - float(started_raw), {"status": "failed"})


async def _describe_batch(
    task_id: str,
    db_task_id: int,
    model_key: str,
    model_id: int | None,
    bucket: str,
    batch_images: list[dict],
    total_images: int,
) -> None:
    """Implémentation commune aux 3 tâches par modèle : télécharge les images
    du batch depuis MinIO, appelle le modèle, persiste le résultat, met à jour
    la progression et finalise la tâche si c'est le dernier batch en attente.

    Un échec du modèle appelé (après retries, cf. CALL_MODEL_MAX_ATTEMPTS)
    n'interrompt pas la tâche : seules les images de ce batch restent sans
    description pour ce modèle-là, les 2 autres modèles et les autres batches
    continuent normalement. Seule une erreur inattendue (téléchargement MinIO,
    DB...) fait échouer toute la tâche via _mark_failed, dans le except plus bas.

    Coopératif avec l'annulation : vérifie le flag Redis avant de démarrer et
    juste avant de persister quoi que ce soit, pour ne pas ressusciter des
    données qu'un DELETE /task/{id}/cancel concurrent viendrait de supprimer.
    """
    if is_cancelled(r, task_id):
        logger.info("Tâche %s annulée : batch ignoré (modèle %s)", task_id, model_key)
        return

    try:
        with tracer.start_as_current_span("describe_batch", attributes={"model": model_key}):
            attrs = {"model": model_key}
            sem = get_model_semaphore(model_key)
            # Même pattern que stream_image_describe (epub/service.py) : mesure
            # le temps bloqué sur le sémaphore avant l'appel (ai_call_waiting/
            # ai_call_wait), séparément de la durée de l'appel lui-même.
            wait_start = time.monotonic()
            ai_call_waiting.add(1, attrs)
            acquired = False
            try:
                await sem.acquire()
                acquired = True
                ai_call_waiting.add(-1, attrs)
                ai_call_wait.record(time.monotonic() - wait_start, attrs)
                ai_call_in_flight.add(1, attrs)
                try:
                    img_list = [
                        base64.b64encode(
                            download_object_bytes(bucket, entry["object_key"])
                        ).decode("utf-8")
                        for entry in batch_images
                    ]
                    url = get_model_url(model_key)
                    last_error = None
                    for attempt in range(1, CALL_MODEL_MAX_ATTEMPTS + 1):
                        call_start = time.monotonic()
                        result = await call_model(url, img_list)
                        ai_call_duration.record(time.monotonic() - call_start, attrs)
                        if result.get("success") is not False:
                            last_error = None
                            break
                        last_error = result.get("error") or f"Échec du modèle {model_key}"
                        ai_call_errors.add(1, attrs)
                        if attempt < CALL_MODEL_MAX_ATTEMPTS:
                            logger.warning(
                                "Échec du modèle %s (tentative %d/%d) pour la tâche %s : %s",
                                model_key,
                                attempt,
                                CALL_MODEL_MAX_ATTEMPTS,
                                task_id,
                                last_error,
                            )
                            await asyncio.sleep(
                                CALL_MODEL_RETRY_DELAYS_SECONDS[attempt - 1]
                            )
                    if last_error is not None:
                        # Échec définitif du modèle pour ce batch (après
                        # CALL_MODEL_MAX_ATTEMPTS tentatives) : on journalise et on
                        # continue sans lever d'exception. Un modèle en panne ne doit
                        # pas faire échouer toute la tâche ni bloquer les 2 autres
                        # modèles — seules les images de ce batch resteront sans
                        # description pour ce modèle précis (`results` reste vide,
                        # cf. plus bas).
                        logger.error(
                            "Échec définitif du modèle %s pour la tâche %s après %d tentatives : %s"
                            " — batch ignoré pour ce modèle, la tâche continue.",
                            model_key,
                            task_id,
                            CALL_MODEL_MAX_ATTEMPTS,
                            last_error,
                        )
                finally:
                    ai_call_in_flight.add(-1, attrs)
                    sem.release()
            finally:
                if not acquired:
                    ai_call_waiting.add(-1, attrs)

            if is_cancelled(r, task_id):
                logger.info(
                    "Tâche %s annulée pendant l'appel au modèle %s : résultat ignoré",
                    task_id,
                    model_key,
                )
                return

            results = (result or {}).get("results") or []
            await _persist_slice(model_id, batch_images, results)

            processed_count = None
            for entry in batch_images:
                done = r.incr(image_done_key(task_id, entry["image_id"]))
                if done == NUM_MODELS:
                    processed_count = r.incr(processed_key(task_id))

            if processed_count is not None:
                async with async_session() as session:
                    await set_processed_images(session, db_task_id, processed_count)

            await _finalize_if_done(task_id, db_task_id, total_images)
    except Exception as exc:
        if is_cancelled(r, task_id):
            logger.info(
                "Tâche %s annulée : exception ignorée pour le batch %s (%s)",
                task_id,
                model_key,
                exc,
            )
            return
        logger.exception(
            "Erreur lors du traitement du batch (modèle %s) pour la tâche %s", model_key, task_id
        )
        await _mark_failed(task_id, db_task_id, str(exc))


@broker_salesforce.task(name="describe_batch_salesforce_blip")
async def describe_batch_salesforce_blip(
    task_id: str,
    db_task_id: int,
    model_key: str,
    model_id: int | None,
    bucket: str,
    batch_images: list[dict],
    total_images: int,
) -> None:
    await _describe_batch(task_id, db_task_id, model_key, model_id, bucket, batch_images, total_images)


@broker_florence2.task(name="describe_batch_florence2")
async def describe_batch_florence2(
    task_id: str,
    db_task_id: int,
    model_key: str,
    model_id: int | None,
    bucket: str,
    batch_images: list[dict],
    total_images: int,
) -> None:
    await _describe_batch(task_id, db_task_id, model_key, model_id, bucket, batch_images, total_images)


@broker_git.task(name="describe_batch_git_large")
async def describe_batch_git_large(
    task_id: str,
    db_task_id: int,
    model_key: str,
    model_id: int | None,
    bucket: str,
    batch_images: list[dict],
    total_images: int,
) -> None:
    await _describe_batch(task_id, db_task_id, model_key, model_id, bucket, batch_images, total_images)
