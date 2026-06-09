from fastapi import APIRouter, status, Depends
from .controller import validate_descriptions, get_descriptions, add_descriptions_to_epub
from ..auth.middleware import get_current_user

router = APIRouter()

router.add_api_route(
    "/{task_id}",
    get_descriptions,
    dependencies=[Depends(get_current_user)],
    methods=["GET"],
    status_code=status.HTTP_200_OK,
)
router.add_api_route(
    "/{task_id}/validate",
    validate_descriptions,
    dependencies=[Depends(get_current_user)],
    methods=["POST"],
    status_code=status.HTTP_200_OK,
)
router.add_api_route(
    "/add_descriptions",
    add_descriptions_to_epub,
    dependencies=[Depends(get_current_user)],
    methods=["POST"],
    status_code=status.HTTP_200_OK,
)
