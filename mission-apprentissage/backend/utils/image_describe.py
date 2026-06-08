import requests
import asyncio
import httpx
import time
import logging
from typing import List
from dotenv import load_dotenv
import os
from .extract import extract_images_epub
import shutil
from .batching import aggregate_image

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
            
