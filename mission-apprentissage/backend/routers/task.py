from fastapi import APIRouter, status, Depends
from ..controllers.task_controller import get_all_tasks, get_task_result
from ..middlewares.auth_middleware import is_admin

router = APIRouter()

router.add_api_route("/admin", get_all_tasks, dependencies=[Depends(is_admin)], methods=["GET"], status_code=status.HTTP_200_OK)
router.add_api_route("/{task_id}", get_task_result, methods=["GET"], status_code=status.HTTP_200_OK)