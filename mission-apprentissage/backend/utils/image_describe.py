import requests
import asyncio
import httpx
import time
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()

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
                    
    batch_size = 5
    batches = [images[i:i + batch_size] for i in range(0, len(images), batch_size)]

    tasks = []
    for batch in batches:
        tasks.append(call(os.getenv('URL_SALESFORCE_CPU_LARGE'), batch))
        tasks.append(call(os.getenv('URL_FLORANCE_2_LARGE'), batch))
        tasks.append(call(os.getenv('URL_GIT_LARGE'), batch))

    results = await asyncio.gather(*tasks)
    
    end = time.time()

    # Regroupe les résultats par modèle
    salesforce_results = []
    florence_results = []
    git_results = []
    for i in range(0, len(results), 3):
        salesforce_results.append(results[i])
        florence_results.append(results[i + 1])
        git_results.append(results[i + 2])

    # Réorganiser les résultats par image au lieu de par modèle
    images_results = {}
    
    # Déterminer le nombre total d'images
    total_images = 0
    if salesforce_results and salesforce_results[0].get('results'):
        total_images = len(salesforce_results[0]['results'])
    
    # Pour chaque image, regrouper les résultats des 3 modèles
    for img_idx in range(total_images):
        image_key = f"image_{img_idx}"
        images_results[image_key] = {
            "index": img_idx,
            "salesforce_blip": None,
            "florence2": None,
            "git_large": None
        }
        
        # Extraire les résultats de chaque modèle pour cette image
        for batch in salesforce_results:
            if batch.get('results') and img_idx < len(batch['results']):
                images_results[image_key]["salesforce_blip"] = batch['results'][img_idx]
                break
        
        for batch in florence_results:
            if batch.get('results') and img_idx < len(batch['results']):
                images_results[image_key]["florence2"] = batch['results'][img_idx]
                break
        
        for batch in git_results:
            if batch.get('results') and img_idx < len(batch['results']):
                images_results[image_key]["git_large"] = batch['results'][img_idx]
                break

    return {
        "images": images_results,
        "total_images": total_images,
        "time": end - start
    }