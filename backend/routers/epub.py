from fastapi import APIRouter, status
from ..controllers.epub_controller import upload_epub, download_epub

router = APIRouter()

router.add_api_route("/upload-epub", upload_epub, methods=["POST"], status_code=status.HTTP_201_CREATED)
router.add_api_route("/download-epub/{file_name}", download_epub, methods=["GET"], status_code=status.HTTP_200_OK)