import uuid
import json
import tempfile
import shutil
import os

from fastapi import UploadFile, HTTPException, File, Depends, status
from ..services.epub_service import save_epub, save_task
from ..middlewares.epub_middleware import already_exists
from ..middlewares.auth_middleware import get_current_user
from ..redis.redis import redis_server_dev
from ..database import get_session, AsyncSession, User
from ..worker.worker import process_epub_describe

r = redis_server_dev()


async def upload_epub(current_user: User = Depends(get_current_user), upload: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    if not upload.filename.endswith(".epub"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le fichier doit être un .epub")

    if await already_exists(upload.filename, session):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce fichier existe déjà")

    temp_dir = os.getenv("UPLOAD_TEMP_DIR", tempfile.gettempdir())
    tpm_path = tempfile.NamedTemporaryFile(delete=False, suffix=".epub", dir=temp_dir).name
    with open(tpm_path, "wb") as output:
        shutil.copyfileobj(upload.file, output)

    task_id = str(uuid.uuid4())
    r.set(task_id, json.dumps({"status": "en attente", "epub_path": tpm_path}, ensure_ascii=False))
    task = await save_task(session, task_id, current_user.id)
    epub = await save_epub(session, task.id, upload.filename)
    await process_epub_describe.kiq(tpm_path, task_id, task.id, epub.id)
    return {"task_id": task_id}