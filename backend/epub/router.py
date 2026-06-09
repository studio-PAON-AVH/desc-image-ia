from fastapi import APIRouter, Depends, status
from .controller import upload_epub, download_epub
from ..auth.middleware import get_current_user

router = APIRouter()

router.add_api_route(
    "/upload-epub",
    upload_epub,
    methods=["POST"],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_user)],
)
router.add_api_route(
    "/download-epub/{file_name}",
    download_epub,
    methods=["GET"],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(get_current_user)],
)
