from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from ..redis.redis import redis_server_dev
import json

redis_dev = redis_server_dev()

async def get_all_tasks():
    keys = redis_dev.keys("*")
    tasks = []
    for key in keys:
        task_id = key.decode("utf-8")
        tasks.append({"task_id": task_id})
    return {"tasks": tasks}

async def get_task_result(task_id: str):
    result = redis_dev.get(task_id)
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