import asyncio
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from ..utils.image_request import ImageRequest
from ..utils.image_describe import get_image_describe
from ..utils.image_classifier import classify_image
from typing import List
import base64
import redis
import json

app = FastAPI()
r = redis.Redis(host='localhost', port=6379, db=0)
tasks_results= {}

@app.get("/")
def read_root():
    return {"API": "Success"}

@app.post("/classify")
def classify_images(request: ImageRequest):
    """
    Point de terminaison pour classifier des images
    Args:
        request (ImageRequest): Requête contenant les URLs des images
    Returns:
        dict: Résultats de classification pour chaque image
    """
    try:
        results = classify_image(request.images)
        return {"classification": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de classification: {str(e)}")

@app.get("/predict/{task_id}")
def get_prediction(task_id: str):
    result = r.get(task_id)
    if not result:
        return {"status": "en attente..."}
    try:
        result_json = json.loads(result.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Erreur lors du décodage du résultat")
    if isinstance(result_json, dict) and result_json.get("error"):
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    return {"result": result_json}

@app.post("/predict")
async def describe_image(request: ImageRequest, background_tasks: BackgroundTasks):
    """
    Point de terminaison pour décrire une image
    Args:
        request (ImageRequest): Requête contenant l'URL de l'image et l'option de traduction
    Returns:
        dict: Descriptions de l'image en anglais et français
    """
    try:
        task_id = str(uuid.uuid4())
        img_list = []
        for img_path in request.images:
            with open(img_path, "rb") as f:
                img_bs64 = base64.b64encode(f.read()).decode("utf-8")
                img_list.append(img_bs64)
        background_tasks.add_task(process_image_describe, img_list, task_id)
        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur de traitement: {str(e)}")
    
def process_image_describe(img_list: List[str], task_id: str):
    try:
        description = asyncio.run(get_image_describe(img_list))
        r.set(task_id, json.dumps(description, ensure_ascii=False))
    except Exception as e:
        r.set(task_id, json.dumps({"error": str(e)}, ensure_ascii=False))