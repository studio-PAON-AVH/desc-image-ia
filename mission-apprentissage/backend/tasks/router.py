from fastapi import APIRouter, status, Depends
from .controller import get_all_tasks, get_task_result
from ..auth.middleware import is_admin, get_current_user

router = APIRouter()

router.add_api_route(
    "/admin",
    get_all_tasks,
    dependencies=[Depends(is_admin)],
    methods=["GET"],
    status_code=status.HTTP_200_OK,
)
router.add_api_route(
    "/{task_id}",
    get_task_result,
    dependencies=[Depends(get_current_user)],
    methods=["GET"],
    status_code=status.HTTP_200_OK,
)
