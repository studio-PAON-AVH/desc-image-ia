import uuid
import json
import tempfile
import shutil
import os

from fastapi import UploadFile, HTTPException, BackgroundTasks, File, Depends, status
from ..services.epub_service import (
    save_epub,
    save_task,
    save_images,
    save_image_descriptions,
    extract_images_epub,
    get_image_describe
)
from ..middlewares.epub_middleware import already_exists
from ..redis.redis import redis_server_dev
from ..database import get_session, AsyncSession, async_session

r = redis_server_dev()

async def upload_epub(background_tasks: BackgroundTasks, upload: UploadFile = File(...), session: AsyncSession = Depends(get_session)):
    if not upload.filename.endswith(".epub"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le fichier doit être un .epub")

    if await already_exists(upload.filename, session):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ce fichier existe déjà")

    tpm_path = tempfile.NamedTemporaryFile(delete=False, suffix=".epub").name
    with open(tpm_path, "wb") as output:
        shutil.copyfileobj(upload.file, output)

    task_id = str(uuid.uuid4())
    r.set(task_id, json.dumps({"status": "en attente"}, ensure_ascii=False))
    task = await save_task(session, task_id)
    epub = await save_epub(session, task.id, upload.filename)
    background_tasks.add_task(process_epub_describe, tpm_path, task_id, task.id, epub.id)
    return {"task_id": task_id}
    
async def process_epub_describe(epub_path: str, task_id: str, db_task_id: int, epub_id: int):
    try:
        # Extraction des images
        image_paths, temp_folder = extract_images_epub(epub_path)

        # Sauvegarder les images en base
        async with async_session() as session:
            images = await save_images(session, db_task_id, epub_id, image_paths)

        # Encoder et envoyer aux modèles
        import base64
        img_list = []
        for img_path in image_paths:
            with open(img_path, "rb") as f:
                img_bs64 = base64.b64encode(f.read()).decode("utf-8")
                img_list.append(img_bs64)

        description = await get_image_describe(img_list)

        # Sauvegarder les descriptions en base
        async with async_session() as session:
            model_mapping = {
                "salesforce_blip": 1,
                "florence2": 2,
                "git_large": 3
            }
            await save_image_descriptions(session, images, description, model_mapping)

        # Mettre à jour Redis
        r.set(task_id, json.dumps(description, ensure_ascii=False))

        # Nettoyer
        if temp_folder:
            shutil.rmtree(temp_folder)

    except Exception as e:
        r.set(task_id, json.dumps({"error": str(e)}, ensure_ascii=False))
    finally:
        if os.path.exists(epub_path):
            os.remove(epub_path)