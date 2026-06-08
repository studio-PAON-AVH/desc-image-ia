import asyncio
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from ..utils.image_request import ImageRequest
from ..utils.image_describe import get_image_describe
from ..utils.image_classifier import classify_image
from ..redis.redis import redis_server_prod
from typing import List
import base64
import redis
import json
import logging 

app = FastAPI()
r = redis_server_prod()
log = logging.getLogger("uvicorn.error")

try: 
    r.ping()
    info = r.info('server')
    log.info(f"Redis connecté avec succès")
except Exception as e:
    log.error(f"Erreur de connexion Redis: {e}")

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

@app.get("/predict/{task_id}", status_code=status.HTTP_200_OK)
def get_prediction(task_id: str):
    result = r.get(task_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche non trouvée")
    
    try:
        result_json = json.loads(result.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors du décodage du résultat", headers={"Error": str(e)})
    
    if isinstance(result_json, dict) and result_json.get("error"):
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement de la tâche: {result_json['error']}")
    
    if isinstance(result_json, dict) and result_json.get("status") == "en attente":
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"message": "Tâche en attente ou en cours"})
    
    return {"result": result_json}

@app.post("/predict", status_code=status.HTTP_201_CREATED)
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
        r.set(task_id, json.dumps({"status": "en attente"}, ensure_ascii=False))
        background_tasks.add_task(process_image_describe, img_list, task_id)
        #asyncio.create_task(process_image_describe(img_list, task_id))
        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Erreur de traitement: {str(e)}")

def process_image_describe(img_list: List[str], task_id: str):
    try:
        description = asyncio.run(get_image_describe(img_list))
        r.set(task_id, json.dumps(description, ensure_ascii=False))
    except Exception as e:
        r.set(task_id, json.dumps({"error": str(e)}, ensure_ascii=False))