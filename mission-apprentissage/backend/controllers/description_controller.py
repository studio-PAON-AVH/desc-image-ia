import json
import os
from fastapi import HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Annotated
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from fastapi.responses import FileResponse
from ..database import get_session, AsyncSession
from ..services.task_service import validate_task_descriptions, get_task_descriptions
from ..services.description_service import add_descriptions
from ..middlewares.auth_middleware import get_current_user
from ..database import User, Task, get_session
from ..redis.redis import redis_server_dev

r = redis_server_dev()

class DescriptionValidation(BaseModel):
    image_index: int
    text: str
    model: Optional[str] = None
    is_written_by_ai: bool
    is_written_by_human: bool

class DescriptionValidationRequest(BaseModel):
    validated_descriptions: List[DescriptionValidation]

class AddDescriptionsRequest(BaseModel):
    task_id_redis: str

async def validate_descriptions(
    task_id: str,
    validation_data: DescriptionValidationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session)
):
    # Vérifier que la tâche appartient à l'utilisateur
    result = await session.execute(select(Task).where(Task.task_id_redis == task_id, Task.user_id == current_user.id))
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
            "validated_count": len(validation_data.validated_descriptions)
        }
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erreur d'intégrité lors de la validation")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur lors de la validation: {str(e)}")

async def get_descriptions(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session)
):
    # Vérifier que la tâche appartient à l'utilisateur
    result = await session.execute(select(Task).where(Task.task_id_redis == task_id, Task.user_id == current_user.id))
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur lors de la récupération des descriptions: {str(e)}")

async def add_descriptions_to_epub(
    request: AddDescriptionsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Task).where(Task.task_id_redis == request.task_id_redis, Task.user_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tâche non trouvée")

    task_data = json.loads(r.get(request.task_id_redis))
    epub_path = task_data["epub_path"]

    original_filename = task.epubs[0].file_name if task.epubs else "output.epub"
    name, _ = os.path.splitext(original_filename)
    output_filename = f"{name}_modified.epub"

    downloads_dir = os.path.join(os.getenv("UPLOAD_TEMP_DIR", "/tmp"), "downloads")
    output_path = os.path.join(downloads_dir, output_filename)

    await add_descriptions(session, request.task_id_redis, epub_path, output_path)

    return FileResponse(
        path=output_path, 
        media_type="application/epub+zip", 
        filename=output_filename
    )
    