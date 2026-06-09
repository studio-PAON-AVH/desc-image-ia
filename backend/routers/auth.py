from fastapi import APIRouter, status, Depends
from ..controllers.auth_controller import create_new_user, login_for_access_token, create_admin_user, get_current_user_info, get_current_user_tasks, refresh_access_token, logout
from ..middlewares.auth_middleware import is_admin

router = APIRouter()

router.add_api_route("/admin/register", create_admin_user, dependencies=[Depends(is_admin)] ,methods=["POST"], status_code=status.HTTP_201_CREATED, response_model=None)
router.add_api_route("/register", create_new_user, methods=["POST"], status_code=status.HTTP_201_CREATED, response_model=None)
router.add_api_route("/login", login_for_access_token, methods=["POST"], status_code=status.HTTP_200_OK, response_model=None)
router.add_api_route("/users/me", get_current_user_info, methods=["GET"], status_code=status.HTTP_200_OK, response_model=None)
router.add_api_route("/users/me/tasks", get_current_user_tasks, methods=["GET"], status_code=status.HTTP_200_OK, response_model=None)
router.add_api_route("/refresh", refresh_access_token, methods=["POST"], status_code=status.HTTP_200_OK, response_model=None)
router.add_api_route("/logout", logout, methods=["POST"], status_code=status.HTTP_200_OK, response_model=None)
