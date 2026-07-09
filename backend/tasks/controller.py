from fastapi import HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from ..core.redis.redis import redis_server_dev
from ..core.database.config import User, get_session
import json
import logging
from ..auth.middleware import get_current_user
from ..core.task_coordination import processed_key
from .repository import find_all_tasks, find_task_by_redis_id
from .service import (
    CANCELLABLE_STATUSES,
    build_task_progress_payload,
    cancel_task as _cancel_task_processing,
)

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
        processed_raw = redis_dev.get(processed_key(task_id))
        processed_images = (
            int(processed_raw)
            if processed_raw is not None
            else result_json.get("processed_images", 0)
        )
        payload = await build_task_progress_payload(db, task_id)
        return {
            "completed": False,
            "status": "in_progress",
            "total_images": result_json.get("total_images", 0),
            "processed_images": processed_images,
            "result": payload or {"images": {}, "total_images": result_json.get("total_images", 0)},
        }

    if status_val == "completed":
        payload = await build_task_progress_payload(db, task_id)
        return {
            "completed": True,
            "status": "completed",
            "result": payload if payload is not None else result_json,
        }

    # ancien format {"epub_path", "descriptions"} sans status (tâches pré-migration)
    return {"completed": True, "status": "completed", "result": result_json}


async def cancel_task(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_session)],
):
    task = await find_task_by_redis_id(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche non trouvée")
    if task.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès interdit")
    if task.status not in CANCELLABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La tâche n'est plus annulable (déjà terminée, en échec ou déjà annulée)",
        )

    await _cancel_task_processing(db, redis_dev, task)
    return {"task_id": task_id, "status": "cancelled"}
