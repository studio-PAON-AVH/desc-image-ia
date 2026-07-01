import os
import tempfile
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from .epub.router import router as epub_router
from .tasks.router import router as task_router
from .descriptions.router import router as description_router
from .auth.router import router as auth_router
from .broker import broker
from .core.observability.setup import setup_observability

@asynccontextmanager
async def lifespan(_: FastAPI):
    if not broker.is_worker_process:
        await broker.startup()
    yield
    if not broker.is_worker_process:
        await broker.shutdown()

app = FastAPI(lifespan=lifespan)
setup_observability("desc-image-api", app=app)

SERVE_FRONTEND = os.getenv("SERVE_FRONTEND", "false").lower() == "true"
FRONTEND_DIR = os.getenv("FRONTEND_DIR", "/app/frontend_dist")

class SPAStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise

DOWNLOADS_DIR = os.path.join(os.getenv("UPLOAD_TEMP_DIR", tempfile.gettempdir()), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

URL_FRONT = os.getenv("URL_FRONT")

origins = [
    URL_FRONT
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(epub_router, prefix="/api/epub", tags=["epub"])
app.include_router(task_router, prefix="/api/task", tags=["task"])
app.include_router(description_router, prefix="/api/description", tags=["description"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


@app.get("/api")
def read_api ():
    return {"message": "Bienvenue sur l'API de description d'images EPUB"}

app.mount("/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if SERVE_FRONTEND and os.path.isdir(FRONTEND_DIR):
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")  