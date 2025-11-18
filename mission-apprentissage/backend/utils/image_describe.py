import requests
import asyncio
import httpx
from typing import List

async def get_image_describe(images: List[str]):
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
                print(f"Request error pour {url}: {type(e).__name__} - {str(e)}")
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
            
    tasks = [
        call("http://localhost:8001/describe", images),
        call("http://localhost:8002/describe", images),
        call("http://localhost:8003/describe", images)
    ]
    
    result = await asyncio.gather(*tasks)
    
    return {
        "image": images,
        "salesforce_cpu_large": result[0],
        "florence2_large": result[1],
        "git_large": result[2]
        
    }