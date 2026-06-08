from fastapi import HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional, Annotated
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from ..database import get_session, AsyncSession
from ..services.task_service import validate_task_descriptions, get_task_descriptions
from ..middlewares.auth_middleware import get_current_user
from ..database import User, Task, get_session

class DescriptionValidation(BaseModel):
    image_index: int
    text: str
    model: Optional[str] = None
    is_written_by_ai: bool
    is_written_by_human: bool

class DescriptionValidationRequest(BaseModel):
    validated_descriptions: List[DescriptionValidation]

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