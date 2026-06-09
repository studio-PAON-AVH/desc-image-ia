import os
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response

# ── Valeurs fixes (ne dépendent pas des containers) ──────────────────────────
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("UPLOAD_TEMP_DIR", "/tmp")
os.environ.setdefault("URL_SALESFORCE_CPU_LARGE", "http://localhost:8001/describe")
os.environ.setdefault("URL_FLORANCE_2_LARGE", "http://localhost:8002/describe")
os.environ.setdefault("URL_GIT_LARGE", "http://localhost:8003/describe")
os.environ.setdefault("BATCH_SIZE", "5")
os.environ.setdefault("BATCH_MAX", "50")

# Placeholders remplacés par les testcontainers avant toute connexion réelle.
# Les modules applicatifs (database.py, broker.py, redis.py) lisent ces vars
# à l'import — leurs connexions sont toutes mockées ou overridées dans les tests.
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")

import redis as redis_lib
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient

# Base = métadonnées SQLAlchemy uniquement, pas de connexion à l'import
from backend.core.database.config import Base, get_session


# ── containers (session-scoped) ───────────────────────────────────────────────
# Démarre PostgreSQL et Redis via Docker une seule fois pour toute la session.
# Les env vars sont mises à jour avec les vrais host/port des containers.
@pytest.fixture(scope="session", autouse=True)
def containers():
    # En CI avec services GitHub Actions, les containers sont déjà lancés
    if os.getenv("USE_SERVICE_CONTAINERS") == "true":
        yield
        return

    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer

    pg = PostgresContainer(
        "postgres:16",
        username="test",
        password="test",
        dbname="test_db",
    )
    rd = RedisContainer("redis:7")

    pg.start()
    rd.start()

    os.environ["POSTGRES_HOST"] = pg.get_container_host_ip()
    os.environ["POSTGRES_PORT"] = str(pg.get_exposed_port(5432))
    os.environ["POSTGRES_USER"] = pg.username
    os.environ["POSTGRES_PASSWORD"] = pg.password
    os.environ["POSTGRES_DB"] = pg.dbname
    os.environ["REDIS_HOST"] = rd.get_container_host_ip()
    os.environ["REDIS_PORT"] = str(rd.get_exposed_port(6379))

    yield

    pg.stop()
    rd.stop()


# ── helpers ───────────────────────────────────────────────────────────────────


def _build_db_url() -> str:
    """URL asyncpg construite depuis les env vars (lues après démarrage des containers)."""
    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    host = os.environ["POSTGRES_HOST"]
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ["POSTGRES_DB"]
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def _build_redis_client() -> redis_lib.Redis:
    """Client Redis pointant vers le container de test."""
    return redis_lib.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.environ["REDIS_PORT"]),
        db=1,
    )


# ── setup_database (session-scoped, sync) ─────────────────────────────────────
# Crée toutes les tables après démarrage du container PostgreSQL.
# Sync (via asyncio.run) pour être compatible avec les fixtures sync et async.
@pytest.fixture(scope="session", autouse=True)
def setup_database(containers):
    async def _create():
        engine = create_async_engine(_build_db_url(), echo=False, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    async def _drop():
        engine = create_async_engine(_build_db_url(), echo=False, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_create())
    yield
    asyncio.run(_drop())


# ── async_session (function-scoped) ──────────────────────────────────────────
# Session fraîche par test pour vérifier directement en DB.
# NullPool : connexion créée dans l'event loop du test, pas de partage.
@pytest_asyncio.fixture
async def async_session(setup_database):
    engine = create_async_engine(_build_db_url(), echo=False, poolclass=NullPool)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


# ── mock_ml_response ──────────────────────────────────────────────────────────
@pytest.fixture
def mock_ml_response():
    return {
        "results": [
            {
                "success": True,
                "english_description": "A test image",
                "french_description": "Une image de test",
                "generation_time": 0.1,
            }
        ]
    }


# ── client (function-scoped) ──────────────────────────────────────────────────
# TestClient FastAPI avec :
#   - get_session overridé → connexion vers le container PostgreSQL de test
#   - broker taskiq mocké (pas de connexion Redis réelle pour les tasks)
#   - epub_controller.r et task_controller.redis_dev patchés → container Redis de test
#   - appels HTTP vers les modèles ML mockés
@pytest.fixture
def client(setup_database, mock_ml_response):
    from backend.main import app

    db_url = _build_db_url()
    override_engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
    override_factory = async_sessionmaker(
        override_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_session():
        async with override_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    test_redis = _build_redis_client()

    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ml_response

    with (
        patch("backend.main.broker") as mock_broker,
        patch("backend.epub.controller.process_epub_describe") as mock_task,
        patch("backend.epub.controller.r", test_redis),
        patch("backend.tasks.controller.redis_dev", test_redis),
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response),
        patch("pyrate_limiter.Limiter.try_acquire_async", new_callable=AsyncMock, return_value=True),
    ):
        mock_broker.is_worker_process = False
        mock_broker.startup = AsyncMock()
        mock_broker.shutdown = AsyncMock()
        mock_task.kiq = AsyncMock()

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
