from fastapi import HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from fastapi.responses import JSONResponse
from ..redis.redis import redis_server_dev
from ..database import User
from sqlalchemy import select
import json
from ..database import Task, get_session
from ..middlewares.auth_middleware import get_current_user

redis_dev = redis_server_dev()

async def get_all_tasks(db: Annotated[AsyncSession, Depends(get_session)]):
    result = await db.execute(Task.__table__.select())
    tasks = result.fetchall()
    return {"tasks": [dict(task._mapping) for task in tasks]}

async def get_task_result(task_id: str, current_user: Annotated[User, Depends(get_current_user)], db: Annotated[AsyncSession, Depends(get_session)]):
    result = await db.execute(select(Task).where(Task.task_id_redis == task_id))
    task = result.scalars().first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche non trouvée")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès interdit")
    
    redis_result = redis_dev.get(task_id)
    if redis_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Résultat non trouvé")
    try:
        result_json = json.loads(redis_result.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur lors du décodage du résultat")
    
    if isinstance(result_json, dict) and result_json.get("error"):
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement: {result_json['error']}")
    
    if isinstance(result_json, dict) and result_json.get("status") == "en attente":
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"message": "Tâche en attente ou en cours"})
    
    return {"result": result_json}