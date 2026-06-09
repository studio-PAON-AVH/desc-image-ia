import os
import tempfile
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .epub.router import router as epub_router
from .tasks.router import router as task_router
from .descriptions.router import router as description_router
from .auth.router import router as auth_router
from .broker import broker

@asynccontextmanager
async def lifespan(_: FastAPI):
    if not broker.is_worker_process:
        await broker.startup()
    yield
    if not broker.is_worker_process:
        await broker.shutdown()

app = FastAPI(lifespan=lifespan)

DOWNLOADS_DIR = os.path.join(os.getenv("UPLOAD_TEMP_DIR", tempfile.gettempdir()), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
app.mount("/downloads", StaticFiles(directory=DOWNLOADS_DIR), name="downloads")

VPS_HOST = os.getenv("VPS_HOST")

origins = [
    "http://localhost:5173",
    "http://localhost:3000"
]

if VPS_HOST:
    origins += [
        f"https://{VPS_HOST}", 
        f"http://{VPS_HOST}"
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


@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API de description d'images EPUB"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
