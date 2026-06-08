import asyncio
import httpx
import logging
import ebooklib
import shutil
import os
import tempfile
import time
from datetime import datetime

from typing import List
from dotenv import load_dotenv
from ebooklib import epub
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import Epub, Task, Images, ImageDescription, ModelsIA

load_dotenv()
logger = logging.getLogger(__name__)

async def get_image_describe(images: List[str]):
    start = time.time()
    async def call(url, image_list: List[str]):
        timeout_image =  60
        total_timeout = max(60, timeout_image * len(images))
        async with httpx.AsyncClient(timeout=total_timeout) as client:
            try: 
                response = await client.post(url, json={"images": image_list})
                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Erreur du service {url}: {response.status_code} - {response.text}"
                    }
                return response.json()
            except httpx.RequestError as e:
                return {
                    "success": False,
                    "error": f"Request error: {type(e).__name__} - {str(e)}"
                }
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                return {
                    "success": False,
                    "error": f"Unexpected error: {str(e)}"
                }
                    
    # Batch size configurable via env var, default 5
    try:
        batch_size = int(os.getenv('BATCH_SIZE', '5'))
    except Exception:
        batch_size = 5
    # Validate and clamp
    if batch_size < 1:
        batch_size = 5
    try:
        batch_max = int(os.getenv('BATCH_MAX', '200'))
    except Exception:
        batch_max = 200
    batch_size = min(batch_size, batch_max)

    batches = [images[i:i + batch_size] for i in range(0, len(images), batch_size)]

    tasks = []
    for batch in batches:
        tasks.append(call(os.getenv('URL_SALESFORCE_CPU_LARGE'), batch))
        tasks.append(call(os.getenv('URL_FLORANCE_2_LARGE'), batch))
        tasks.append(call(os.getenv('URL_GIT_LARGE'), batch))

    results = await asyncio.gather(*tasks)
    
    end = time.time()

    # Regroupe les résultats par modèle (liste de réponses par batch)
    salesforce_results = []
    florence_results = []
    git_results = []
    for i in range(0, len(results), 3):
        salesforce_results.append(results[i])
        florence_results.append(results[i + 1])
        git_results.append(results[i + 2])

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
            "git_large": None
        }


    for batch_idx in range(len(batches)):
        aggregate_image(batch_idx, batch_size, "salesforce_blip", salesforce_results, images_results, total_images)
        aggregate_image(batch_idx, batch_size, "florence2", florence_results, images_results, total_images)
        aggregate_image(batch_idx, batch_size, "git_large", git_results, images_results, total_images)

    return {
        "images": images_results,
        "total_images": total_images,
        "time": end - start
    }
    
async def describe_images_epub(epub_path: str):
    image_paths, temp_folder = extract_images_epub(epub_path)

    if not image_paths:
        return {"error": "Aucune image trouvée dans l'EPUB"}

    try:
        import base64
        img_list = []
        for img_path in image_paths:
            with open(img_path, "rb") as f:
                img_bs64 = base64.b64encode(f.read()).decode("utf-8")
                img_list.append(img_bs64)

        return await get_image_describe(img_list)
    finally:
        if temp_folder:
            shutil.rmtree(temp_folder)
            
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
        fileName = os.path.basename(item.file_name)
        output_path = os.path.join(output_dir, fileName)
        
        with open(output_path, 'wb') as f:
            f.write(item.get_content())
            
        images_paths.append(output_path)
    return images_paths, output_dir

def aggregate_image(index: int, size: int, model: str, model_result: List[dict], images_results: dict, images: dict):
        offset = index * size

        if index < len(model_result):
            batch = model_result[index]
            if batch and batch.get('results'):
                for j, item in enumerate(batch['results']):
                    global_idx = offset + j
                    if global_idx < images:
                        images_results[f"image_{global_idx}"][model] = item
                    else:
                        logger.debug("%s: ignored result for global index =%s", model, global_idx)
            else:
                logger.debug("%s: no results for batch %s", model, index)
                
async def save_epub(session: AsyncSession, task_id: int, file_name: str):
    new_epub = Epub(
        task_id=task_id,
        file_name=file_name,
        upload_date=datetime.now(),
        status="uploaded",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    session.add(new_epub)
    await session.commit()
    await session.refresh(new_epub)
    return new_epub
    
async def save_task(session: AsyncSession, task_id_redis: str, user_id: int):
    new_task = Task(
        task_id_redis=task_id_redis,
        user_id=user_id,
        status="pending",
        total_images=0,
        processed_images=0,
        created_at=datetime.now(),
        started_at=datetime.now(),
        completed_at=datetime.now(),
    )
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return new_task

async def save_images(session: AsyncSession, task_id: int, epub_id: int, image_paths: List[str]):
    """Sauvegarde les images extraites de l'EPUB dans la base"""
    images = []
    for position, image_path in enumerate(image_paths):
        image_file_name = os.path.basename(image_path)
        new_image = Images(
            task_id=task_id,
            epub_id=epub_id,
            image_file_name=image_file_name,
            image_position_in_epub=position,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        session.add(new_image)
        images.append(new_image)

    await session.commit()
    for img in images:
        await session.refresh(img)
    return images

async def save_image_descriptions(session: AsyncSession, images: List[Images], results: dict, model_ia_mapping: dict):
    """
    Sauvegarde les descriptions générées par les modèles IA

    Args:
        images: liste des objets Images de la base
        results: résultats retournés par get_image_describe()
        model_ia_mapping: {"salesforce_blip": 1, "florence2": 2, "git_large": 3}
    """
    for idx, image in enumerate(images):
        image_key = f"image_{idx}"
        if image_key in results["images"]:
            descriptions = results["images"][image_key]

            for model_name, model_id in model_ia_mapping.items():
                description_data = descriptions.get(model_name)
                if description_data and isinstance(description_data, dict):
                    # Extraire le texte de la description (français par défaut)
                    description_text = description_data.get('french_description')

                    if description_text:
                        desc = ImageDescription(
                            image_id=image.id,
                            model_ia_id=model_id,
                            description_text=description_text,
                            is_written_by_ai=True,
                            is_written_by_human=False,
                            generated_at=datetime.now(),
                            validated_by_human=False,
                            created_at=datetime.now(),
                            updated_at=datetime.now()
                        )
                        session.add(desc)

    await session.commit()