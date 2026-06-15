import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client(mocker):
    mock_broker = MagicMock()
    mock_broker.is_worker_process = False
    mock_broker.startup = AsyncMock()
    mock_broker.shutdown = AsyncMock()
    mocker.patch("backend.main.broker", mock_broker)

    from backend.main import app

    with TestClient(app) as c:
        yield c


class TestMainEndpoints:
    @pytest.mark.unit
    def test_root_returns_welcome_message(self, client):
        """GET /api retourne le message de bienvenue."""
        response = client.get("/api")

        assert response.status_code == 200
        assert response.json() == {"message": "Bienvenue sur l'API de description d'images EPUB"}

    @pytest.mark.unit
    def test_health_returns_healthy(self, client):
        """GET /health retourne le statut healthy."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @pytest.mark.unit
    def test_unknown_route_returns_404(self, client):
        """Une route inexistante retourne 404."""
        response = client.get("/inexistant")

        assert response.status_code == 404


class TestCORSMiddleware:
    @pytest.mark.unit
    def test_cors_allowed_origin(self, client):
        """Une origine autorisée reçoit le header CORS."""
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})

        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    @pytest.mark.unit
    def test_cors_unknown_origin_not_allowed(self, client):
        """Une origine non autorisée ne reçoit pas le header CORS."""
        response = client.get("/health", headers={"Origin": "http://malicious.com"})

        assert "access-control-allow-origin" not in response.headers


class TestLifespan:
    @pytest.mark.unit
    def test_broker_startup_called_on_start(self, mocker):
        """broker.startup() est appelé au démarrage si pas worker process."""
        mock_broker = MagicMock()
        mock_broker.is_worker_process = False
        mock_broker.startup = AsyncMock()
        mock_broker.shutdown = AsyncMock()
        mocker.patch("backend.main.broker", mock_broker)

        from backend.main import app

        with TestClient(app):
            mock_broker.startup.assert_called_once()

    @pytest.mark.unit
    def test_broker_shutdown_called_on_stop(self, mocker):
        """broker.shutdown() est appelé à l'arrêt si pas worker process."""
        mock_broker = MagicMock()
        mock_broker.is_worker_process = False
        mock_broker.startup = AsyncMock()
        mock_broker.shutdown = AsyncMock()
        mocker.patch("backend.main.broker", mock_broker)

        from backend.main import app

        with TestClient(app):
            pass

        mock_broker.shutdown.assert_called_once()

    @pytest.mark.unit
    def test_broker_not_started_when_worker_process(self, mocker):
        """broker.startup() n'est pas appelé si is_worker_process est True."""
        mock_broker = MagicMock()
        mock_broker.is_worker_process = True
        mock_broker.startup = AsyncMock()
        mock_broker.shutdown = AsyncMock()
        mocker.patch("backend.main.broker", mock_broker)

        from backend.main import app

        with TestClient(app):
            mock_broker.startup.assert_not_called()
