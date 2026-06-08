from fastapi import APIRouter, status
from ..controllers.epub_controller import upload_epub

router = APIRouter()

router.add_api_route("/upload-epub", upload_epub, methods=["POST"], status_code=status.HTTP_201_CREATED)