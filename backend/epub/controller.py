import uuid
import json
import tempfile
import os

from fastapi import UploadFile, HTTPException, File, Depends, status
from fastapi.responses import FileResponse
from .service import save_epub, save_task
from .middleware import already_exists
from ..auth.middleware import get_current_user
from ..core.redis.redis import redis_server_dev
from ..core.database.config import get_session, AsyncSession, User
from ..worker.worker import process_epub_describe

r = redis_server_dev()

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 Mo
EPUB_MAGIC_BYTES = b"PK\x03\x04"


async def upload_epub(
    current_user: User = Depends(get_current_user),
    upload: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    if not upload.filename.endswith(".epub"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Le fichier doit être un .epub"
        )

    if await already_exists(upload.filename, session):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce fichier existe déjà")

    content = await upload.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fichier trop volumineux (max 50 Mo)",
        )

    if not content.startswith(EPUB_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Le fichier n'est pas un EPUB valide"
        )

    temp_dir = os.getenv("UPLOAD_TEMP_DIR", tempfile.gettempdir())
    tmp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".epub", dir=temp_dir).name
    with open(tmp_path, "wb") as output:
        output.write(content)
        
    task_id = str(uuid.uuid4())
    r.set(task_id, json.dumps({"status": "en attente", "epub_path": tmp_path}, ensure_ascii=False))
    task = await save_task(session, task_id, current_user.id)
    epub = await save_epub(session, task.id, upload.filename)
    await process_epub_describe.kiq(tmp_path, task_id, task.id, epub.id)
    return {"task_id": task_id}


async def download_epub(file_name: str):
    downloads_dir = os.path.realpath(
        os.path.join(os.getenv("UPLOAD_TEMP_DIR", tempfile.gettempdir()), "downloads")
    )
    file_path = os.path.realpath(os.path.join(downloads_dir, file_name))

    if not file_path.startswith(downloads_dir + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Nom de fichier invalide"
        )

    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier non trouvé")

    return FileResponse(
        path=file_path,
        media_type="application/epub+zip",
        filename=file_name,
    )
