from fastapi import HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from ..database import get_session, AsyncSession
from ..services.task_service import validate_task_descriptions, get_task_descriptions

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
    session: AsyncSession = Depends(get_session)
):
    """Valide les descriptions choisies pour une image et supprime les alternatives non validées"""
    try:
        result = await validate_task_descriptions(
            session,
            task_id,
            validation_data.validated_descriptions
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tâche non trouvée"
            )
        return {
            "success": True,
            "message": "Descriptions validées et alternatives supprimées",
            "validated_count": len(validation_data.validated_descriptions)
        }
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Erreur d'intégrité lors de la validation"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la validation: {str(e)}"
        )

async def get_descriptions(
    task_id: str,
    session: AsyncSession = Depends(get_session)
):
    """Récupère les descriptions pour les images d'une tâche"""
    try:
        result = await get_task_descriptions(session, task_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tâche non trouvée"
            )
        return result

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des descriptions: {str(e)}"
        )