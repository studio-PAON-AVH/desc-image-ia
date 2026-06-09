import json
import logging
import os
import tempfile
from fastapi import HTTPException, Depends, status
from typing import Annotated
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from ..core.database.config import get_session, AsyncSession, User, Task
from ..tasks.service import (
    validate_task_descriptions, 
    get_task_descriptions
)
from .service import add_descriptions
from ..auth.middleware import get_current_user
from ..core.redis.redis import redis_server_dev
from .schemas import DescriptionValidationRequest, AddDescriptionsRequest

logger = logging.getLogger(__name__)

r = redis_server_dev()


async def validate_descriptions(
    task_id: str,
    validation_data: DescriptionValidationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    # Vérifier que la tâche appartient à l'utilisateur
    result = await session.execute(
        select(Task).where(Task.task_id_redis == task_id, Task.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche non trouvée")

    try:
        result = await validate_task_descriptions(
            session, task_id, validation_data.validated_descriptions
        )
        return {
            "success": True,
            "message": "Descriptions validées et alternatives supprimées",
            "validated_count": len(validation_data.validated_descriptions),
        }
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur d'intégrité lors de la validation",
        ) from e
    except Exception as e:
        logger.exception("Erreur lors de la validation des descriptions pour la tâche %s", task_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la validation des descriptions",
        ) from e


async def get_descriptions(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    # Vérifier que la tâche appartient à l'utilisateur
    result = await session.execute(
        select(Task).where(Task.task_id_redis == task_id, Task.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche non trouvée")

    try:
        result = await get_task_descriptions(session, task_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche non trouvée")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Erreur lors de la récupération des descriptions pour la tâche %s", task_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des descriptions",
        ) from e


async def add_descriptions_to_epub(
    request: AddDescriptionsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Task)
        .options(selectinload(Task.epubs))
        .where(Task.task_id_redis == request.task_id_redis, Task.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche non trouvée")

    raw = r.get(request.task_id_redis)
    if raw is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tâche introuvable dans le cache"
        )
    task_data = json.loads(raw)
    epub_path = task_data.get("epub_path")
    if not epub_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chemin du fichier EPUB introuvable dans le cache",
        )

    if not os.path.exists(epub_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fichier EPUB introuvable sur le serveur"
        )

    original_filename = task.epubs[0].file_name if task.epubs else "output.epub"
    name, _ = os.path.splitext(original_filename)
    output_filename = f"{name}_modified.epub"

    downloads_dir = os.path.join(os.getenv("UPLOAD_TEMP_DIR", tempfile.gettempdir()), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    output_path = os.path.join(downloads_dir, output_filename)

    try:
        await add_descriptions(session, request.task_id_redis, epub_path, output_path)
    except Exception as e:
        logger.exception(
            "Erreur lors de l'ajout des descriptions pour la tâche %s", request.task_id_redis
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la génération du fichier EPUB modifié",
        ) from e

    return {"download_url": f"/downloads/{output_filename}"}
