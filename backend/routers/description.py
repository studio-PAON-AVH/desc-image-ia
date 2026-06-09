from fastapi import APIRouter, status
from ..controllers.description_controller import validate_descriptions, get_descriptions, add_descriptions_to_epub

router = APIRouter()

router.add_api_route("/{task_id}", get_descriptions, methods=["GET"], status_code=status.HTTP_200_OK)
router.add_api_route("/{task_id}/validate", validate_descriptions, methods=["POST"], status_code=status.HTTP_200_OK)
router.add_api_route("/add_descriptions", add_descriptions_to_epub, methods=["POST"], status_code=status.HTTP_200_OK)