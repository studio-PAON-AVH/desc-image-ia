import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv()


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
        """GET / retourne le message de bienvenue."""
        response = client.get("/")

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
        response = client.get("/health", headers={"Origin": "http://localhost:7001"})

        assert response.headers.get("access-control-allow-origin") == "http://localhost:7001"

    @pytest.mark.unit
    def test_cors_unknown_origin_not_allowed(self, client):
        """Une origine non autorisée ne reçoit pas le header CORS."""
        response = client.get("/health", headers={"Origin": "http://malicious.com"})

        assert "access-control-allow-origin" not in response.headers


class TestRoutersRegistered:

    @pytest.fixture
    def app(self, mocker):
        mock_broker = MagicMock()
        mock_broker.is_worker_process = False
        mocker.patch("backend.main.broker", mock_broker)

        from backend.main import app
        return app

    @pytest.mark.unit
    def test_epub_router_registered(self, app):
        """Le router epub est bien enregistré sous /api/epub."""
        paths = [route.path for route in app.routes]
        assert any(p.startswith("/api/epub") for p in paths)

    @pytest.mark.unit
    def test_task_router_registered(self, app):
        """Le router task est bien enregistré sous /api/task."""
        paths = [route.path for route in app.routes]
        assert any(p.startswith("/api/task") for p in paths)

    @pytest.mark.unit
    def test_description_router_registered(self, app):
        """Le router description est bien enregistré sous /api/description."""
        paths = [route.path for route in app.routes]
        assert any(p.startswith("/api/description") for p in paths)

    @pytest.mark.unit
    def test_auth_router_registered(self, app):
        """Le router auth est bien enregistré sous /api/auth."""
        paths = [route.path for route in app.routes]
        assert any(p.startswith("/api/auth") for p in paths)


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
