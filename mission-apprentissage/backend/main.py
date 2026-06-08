import logging 
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.epub import router as epub_router
from .routers.task import router as task_router
from .routers.description import router as description_router
from .routers.auth import router as auth_router

app = FastAPI()
log = logging.getLogger("uvicorn.error")

origins = [
    "http://localhost",
    "http://localhost:7001",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:7001",
    "http://127.0.0.1:8080",
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