import asyncio
import httpx
import logging
import ebooklib
import shutil
import os
import tempfile
import time
import base64
import weakref

from typing import List
from dotenv import load_dotenv
from ebooklib import epub
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database.config import Images
from ..core.observability.metric import (
    ai_call_duration,
    ai_call_errors,
    ai_call_waiting,
    ai_call_in_flight,
    ai_call_wait,
)
from .repository import (
    create_task,
    create_epub,
    create_images_batch,
    set_images_storage as _repo_set_images_storage,
    create_image_descriptions_batch,
    save_image_descriptions_slice as _repo_save_image_descriptions_slice,
    set_task_total_images as _repo_set_task_total_images,
    set_task_processed_images as _repo_set_task_processed_images,
    update_task_status as _repo_update_task_status,
)

MODEL_KEYS = ("salesforce_blip", "florence2", "git_large")

load_dotenv()
logger = logging.getLogger(__name__)

# Sémaphores partagés par modèle, un jeu par event loop. Le worker tourne en un
# seul processus (un seul loop) : ces sémaphores plafonnent donc le nombre total
# de requêtes en vol PAR MODÈLE à travers TOUTES les tâches EPUB simultanées.
# Les modèles traitent en série -> au-delà de la limite, les requêtes
# s'empileraient dans leur file et timeout (ReadTimeout). Une requête en attente
# bloque sur le sémaphore avant de créer le client httpx, donc son chrono de
# timeout ne démarre qu'à son tour réel.
_model_semaphores: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _get_model_semaphores():
    loop = asyncio.get_running_loop()
    sems = _model_semaphores.get(loop)
    if sems is None:
        try:
            limit = max(1, int(os.getenv("MAX_CONCURRENT_PER_MODEL", "1")))
        except ValueError:
            limit = 1
        sems = {model_key: asyncio.Semaphore(limit) for model_key in MODEL_KEYS}
        _model_semaphores[loop] = sems
    return sems


def _resolve_batch_size() -> int:
    """Lit BATCH_SIZE/BATCH_MAX depuis l'environnement, valide et clamp.

    Défaut à 1 : chaque image part dans son propre appel HTTP, donc chaque
    description revient (et est persistée/exposée) dès que le modèle a fini
    cette image précise, au lieu d'attendre tout un batch.
    """
    try:
        batch_size = int(os.getenv("BATCH_SIZE", "1"))
    except ValueError:
        batch_size = 1
    if batch_size < 1:
        raise ValueError("BATCH_SIZE must be a positive integer")
    try:
        batch_max = int(os.getenv("BATCH_MAX", "200"))
    except ValueError:
        batch_max = 200
    return min(batch_size, batch_max)


async def stream_image_describe(images: List[str]):
    """Envoie les images aux 3 modèles par batch et *yield* chaque résultat
    (batch, modèle) dès qu'il revient, sans attendre les autres.

    Chaque event yield a la forme :
        {"batch_idx": int, "model_key": str, "batch_size": int,
         "result": <dict normalisé>, "total_images": int}
    """

    async def call(url, image_list: List[str]):
        timeout_image = 60
        total_timeout = max(60, timeout_image * len(image_list))
        async with httpx.AsyncClient(timeout=total_timeout) as client:
            try:
                response = await client.post(url, json={"images": image_list})
                if response.status_code != 200:
                    logger.error(
                        "Erreur modèle %s: status %s - %s", url, response.status_code, response.text
                    )
                    return {
                        "success": False,
                        "error": f"Erreur du service {url}: {response.status_code} - {response.text}",
                    }
                return response.json()
            except httpx.RequestError as e:
                logger.error("Erreur réseau vers %s: %s - %s", url, type(e).__name__, str(e))
                return {"success": False, "error": f"Request error: {type(e).__name__} - {str(e)}"}
            except SystemError as e:
                logger.error("Erreur inattendue vers %s: %s", url, str(e))
                return {"success": False, "error": f"Unexpected error: {str(e)}"}

    batch_size = _resolve_batch_size()
    total_images = len(images)
    batches = [images[i : i + batch_size] for i in range(0, total_images, batch_size)]

    model_urls = {
        "salesforce_blip": os.getenv("URL_SALESFORCE_CPU_LARGE"),
        "florence2": os.getenv("URL_FLORANCE_2_LARGE"),
        "git_large": os.getenv("URL_GIT_LARGE"),
    }

    sems = _get_model_semaphores()

    async def wrapped(batch_idx, model_key, url, batch):
        attrs = {"model": model_key}
        # +1 dès l'entrée dans la file : ai_call_waiting reflète les requêtes
        # bloquées sur le sémaphore — le vrai backlog, invisible côté queue Redis.
        wait_start = time.monotonic()
        ai_call_waiting.add(1, attrs)
        acquired = False
        try:
            await sems[model_key].acquire()
            acquired = True
            ai_call_waiting.add(-1, attrs)
            # Temps passé en file avant d'acquérir : la latence cachée.
            ai_call_wait.record(time.monotonic() - wait_start, attrs)
            ai_call_in_flight.add(1, attrs)
            try:
                # Chrono démarré après le sémaphore : on mesure la latence réelle
                # du modèle, pas le temps d'attente dans la file.
                call_start = time.monotonic()
                result = await call(url, batch)
                ai_call_duration.record(time.monotonic() - call_start, attrs)
                if result.get("success") is False:
                    ai_call_errors.add(1, attrs)
            finally:
                ai_call_in_flight.add(-1, attrs)
                sems[model_key].release()
        finally:
            # Annulé/erreur avant d'acquérir le sémaphore : rééquilibrer la jauge
            # pour qu'elle ne dérive pas.
            if not acquired:
                ai_call_waiting.add(-1, attrs)
        return {
            "batch_idx": batch_idx,
            "model_key": model_key,
            "batch_size": batch_size,
            "result": result,
            "total_images": total_images,
        }

    tasks = [
        asyncio.ensure_future(wrapped(batch_idx, model_key, model_urls[model_key], batch))
        for batch_idx, batch in enumerate(batches)
        for model_key in MODEL_KEYS
    ]

    for fut in asyncio.as_completed(tasks):
        try:
            yield await fut
        except Exception as e:  # défensif : call() ne devrait pas lever
            logger.exception("Tâche de description interrompue: %s", e)


async def get_image_describe(images: List[str], file_names: List[str] | None = None):
    """Variante non-streaming : draine stream_image_describe et agrège par image.

    Conservée pour describe_images_epub et la compatibilité ascendante.
    `file_names` (optionnel) porte le nom d'origine de chaque image.
    """
    start = time.time()
    total_images = len(images)

    images_results = {
        f"image_{img_idx}": {
            "index": img_idx,
            "file_name": file_names[img_idx] if file_names else None,
            "salesforce_blip": None,
            "florence2": None,
            "git_large": None,
        }
        for img_idx in range(total_images)
    }

    async for evt in stream_image_describe(images):
        slice_map = slice_to_image_descriptions(
            evt["batch_idx"],
            evt["batch_size"],
            evt["model_key"],
            evt["result"],
            evt["total_images"],
        )
        for global_idx, item in slice_map.items():
            images_results[f"image_{global_idx}"][evt["model_key"]] = item

    end = time.time()
    return {"images": images_results, "total_images": total_images, "time": end - start}


async def describe_images_epub(epub_path: str):
    image_paths, temp_folder = extract_images_epub(epub_path)

    if not image_paths:
        return {"error": "Aucune image trouvée dans l'EPUB"}

    try:
        img_list = []
        for img_path in image_paths:
            with open(img_path, "rb") as f:
                img_bs64 = base64.b64encode(f.read()).decode("utf-8")
                img_list.append(img_bs64)

        file_names = [os.path.basename(p) for p in image_paths]
        return await get_image_describe(img_list, file_names)
    finally:
        if temp_folder:
            try:
                shutil.rmtree(temp_folder)
            except ValueError as e:
                logger.error("Error occurred while removing temp folder: %s", str(e))


def extract_images_epub(epub_path, output_dir=None):

    book = epub.read_epub(epub_path)
    items = list(book.get_items_of_type(ebooklib.ITEM_IMAGE))

    if not items:
        return [], None

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="epub_images_")
    else:
        os.makedirs(output_dir, exist_ok=True)

    images_paths = []

    for item in items:
        file_name = os.path.basename(item.file_name)
        output_path = os.path.join(output_dir, file_name)

        with open(output_path, "wb") as f:
            f.write(item.get_content())

        images_paths.append(output_path)
    return images_paths, output_dir


def aggregate_image(
    index: int, 
    size: int, 
    model: str, 
    model_result: List[dict], 
    images_results: dict, 
    images: dict
):
    offset = index * size

    if index < len(model_result):
        batch = model_result[index]
        if batch and batch.get("results"):
            for j, item in enumerate(batch["results"]):
                global_idx = offset + j
                if global_idx < images:
                    images_results[f"image_{global_idx}"][model] = item
                else:
                    logger.debug("%s: ignored result for global index =%s", model, global_idx)
        else:
            logger.debug("%s: no results for batch %s", model, index)


def slice_to_image_descriptions(batch_idx, batch_size, model_key, result, total_images):
    """Transforme la réponse d'un (batch, modèle) en {global_image_idx: item}.

    Parallèle à aggregate_image, mais pour un seul slice.
    """
    offset = batch_idx * batch_size
    out = {}
    if result and result.get("results"):
        for j, item in enumerate(result["results"]):
            global_idx = offset + j
            if global_idx < total_images:
                out[global_idx] = item
            else:
                logger.debug("%s: ignored result for global index =%s", model_key, global_idx)
    return out


async def save_epub(session: AsyncSession, task_id: int, file_name: str):
    return await create_epub(session, task_id, file_name)


async def save_task(session: AsyncSession, task_id_redis: str, user_id: int):
    return await create_task(session, task_id_redis, user_id)


async def save_images(session: AsyncSession, task_id: int, epub_id: int, image_paths: List[str]):
    return await create_images_batch(session, task_id, epub_id, image_paths)


async def save_images_storage(
    session: AsyncSession, images: List[Images], bucket: str, object_keys: List[str]
):
    return await _repo_set_images_storage(session, images, bucket, object_keys)


async def save_image_descriptions(
    session: AsyncSession, images: List[Images], results: dict, model_ia_mapping: dict
):
    return await create_image_descriptions_batch(session, images, results, model_ia_mapping)


async def update_task_status(session: AsyncSession, db_task_id: int, status: str):
    return await _repo_update_task_status(session, db_task_id, status)


async def save_descriptions_slice(
    session: AsyncSession, images: List[Images], model_id, slice_map: dict
):
    return await _repo_save_image_descriptions_slice(session, images, model_id, slice_map)


async def set_total_images(session: AsyncSession, db_task_id: int, total: int):
    return await _repo_set_task_total_images(session, db_task_id, total)


async def set_processed_images(session: AsyncSession, db_task_id: int, processed: int):
    return await _repo_set_task_processed_images(session, db_task_id, processed)
