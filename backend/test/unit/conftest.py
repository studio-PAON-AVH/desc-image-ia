# tests/conftest.py
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from dotenv import load_dotenv

# Valeurs minimales pour que backend.core.settings puisse être importé sans .env
os.environ.setdefault("SECRET_KEY", "test-secret-key-unit")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_USER", "user")
os.environ.setdefault("POSTGRES_PASSWORD", "pass")
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("POSTGRES_SSL", "disable")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("URL_SALESFORCE_CPU_LARGE", "http://localhost:8001/describe")
os.environ.setdefault("URL_FLORANCE_2_LARGE", "http://localhost:8002/describe")
os.environ.setdefault("URL_GIT_LARGE", "http://localhost:8003/describe")
os.environ.setdefault("FASTAPI_URL", "http://localhost:8000")
os.environ.setdefault("URL_FRONT", "http://localhost:5173")
os.environ.setdefault("DEBUG", "true")

# Charge le .env réel — n'écrase pas les valeurs déjà définies ci-dessus.
load_dotenv()


@pytest.fixture
def mock_session():
    """Session SQLAlchemy mockée (base AsyncMock) — tests unitaires des repositories."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def session(mocker):
    """Session SQLAlchemy mockée (base MagicMock) — tests unitaires des services."""
    mock = mocker.MagicMock()
    mock.add = mocker.MagicMock(return_value=None)
    mock.commit = mocker.AsyncMock(return_value=None)
    mock.refresh = mocker.AsyncMock(return_value=None)
    mock.execute = mocker.AsyncMock(return_value=None)
    return mock
