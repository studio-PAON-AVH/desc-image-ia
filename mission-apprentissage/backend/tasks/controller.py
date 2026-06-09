from fastapi import HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from ..core.redis.redis import redis_server_dev
from ..core.database.config import User, get_session
import json
import logging
from ..auth.middleware import get_current_user
from .repository import find_all_tasks, find_task_by_redis_id

redis_dev = redis_server_dev()
logger = logging.getLogger(__name__)


async def get_all_tasks(
    db: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    tasks = await find_all_tasks(db, limit, offset)
    return {"tasks": [dict(task._mapping) for task in tasks], "limit": limit, "offset": offset}


async def get_task_result(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    task = await find_task_by_redis_id(db, task_id)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du décodage du résultat",
        ) from e

    if isinstance(result_json, dict) and result_json.get("error"):
        logger.error("Erreur de traitement pour la tâche %s: %s", task_id, result_json["error"])
        raise HTTPException(
            status_code=500, detail="Une erreur est survenue lors du traitement de la tâche"
        )

    status_val = result_json.get("status") if isinstance(result_json, dict) else None

    if status_val in ("en attente", "pending"):
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "completed": False,
                "status": "pending",
                "total_images": result_json.get("total_images", 0),
                "processed_images": result_json.get("processed_images", 0),
                "message": "Tâche en attente ou en cours",
            },
        )

    if status_val == "in_progress":
        return {
            "completed": False,
            "status": "in_progress",
            "total_images": result_json.get("total_images", 0),
            "processed_images": result_json.get("processed_images", 0),
            "result": result_json.get("descriptions"),
        }

    # "completed" ou ancien format {"epub_path", "descriptions"} sans status
    return {"completed": True, "status": "completed", "result": result_json}
