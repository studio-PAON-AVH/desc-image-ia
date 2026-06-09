import asyncio
import httpx
import logging
import ebooklib
import shutil
import os
import tempfile
import time
import base64

from typing import List
from dotenv import load_dotenv
from ebooklib import epub
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.database.config import Images
from .repository import (
    create_task,
    create_epub,
    create_images_batch,
    create_image_descriptions_batch,
    update_task_status as _repo_update_task_status,
)

load_dotenv()
logger = logging.getLogger(__name__)


async def get_image_describe(images: List[str]):
    start = time.time()

    async def call(url, image_list: List[str]):
        timeout_image = 60
        total_timeout = max(60, timeout_image * len(images))
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

    # Batch size configurable via env var, default 5
    try:
        batch_size = int(os.getenv("BATCH_SIZE", "5"))
    except ValueError:
        batch_size = 5
    # Validate and clamp
    if batch_size < 1:
        raise ValueError("BATCH_SIZE must be a positive integer")
    try:
        batch_max = int(os.getenv("BATCH_MAX", "200"))
    except ValueError:
        batch_max = 200
    batch_size = min(batch_size, batch_max)

    batches = [images[i : i + batch_size] for i in range(0, len(images), batch_size)]

    tasks = []
    for batch in batches:
        tasks.append(call(os.getenv("URL_SALESFORCE_CPU_LARGE"), batch))
        tasks.append(call(os.getenv("URL_FLORANCE_2_LARGE"), batch))
        tasks.append(call(os.getenv("URL_GIT_LARGE"), batch))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    end = time.time()

    # Regroupe les résultats par modèle (liste de réponses par batch)
    salesforce_results = []
    florence_results = []
    git_results = []
    for i in range(0, len(results), 3):

        def safe(r):
            return r if not isinstance(r, Exception) else {"success": False, "error": str(r)}

        salesforce_results.append(safe(results[i]))
        florence_results.append(safe(results[i + 1]))
        git_results.append(safe(results[i + 2]))

    # Réorganiser les résultats par image au lieu de par modèle
    images_results = {}

    total_images = len(images)

    # initialize
    for img_idx in range(total_images):
        image_key = f"image_{img_idx}"
        images_results[image_key] = {
            "index": img_idx,
            "salesforce_blip": None,
            "florence2": None,
            "git_large": None,
        }

    for batch_idx in range(len(batches)):
        aggregate_image(
            batch_idx,
            batch_size,
            "salesforce_blip",
            salesforce_results,
            images_results,
            total_images,
        )
        aggregate_image(
            batch_idx, batch_size, "florence2", florence_results, images_results, total_images
        )
        aggregate_image(
            batch_idx, batch_size, "git_large", git_results, images_results, total_images
        )

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

        return await get_image_describe(img_list)
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


async def save_epub(session: AsyncSession, task_id: int, file_name: str):
    return await create_epub(session, task_id, file_name)


async def save_task(session: AsyncSession, task_id_redis: str, user_id: int):
    return await create_task(session, task_id_redis, user_id)


async def save_images(session: AsyncSession, task_id: int, epub_id: int, image_paths: List[str]):
    return await create_images_batch(session, task_id, epub_id, image_paths)


async def save_image_descriptions(
    session: AsyncSession, images: List[Images], results: dict, model_ia_mapping: dict
):
    return await create_image_descriptions_batch(session, images, results, model_ia_mapping)


async def update_task_status(session: AsyncSession, db_task_id: int, status: str):
    return await _repo_update_task_status(session, db_task_id, status)
