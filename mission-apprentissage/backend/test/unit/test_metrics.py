# tests/test_metrics.py
def test_metrics_endpoint_exists(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_USER", "test")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test")
    monkeypatch.setenv("POSTGRES_DB", "test")
    monkeypatch.setenv("POSTGRES_SSL", "disable")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("URL_SALESFORCE_CPU_LARGE", "http://localhost:8001")
    monkeypatch.setenv("URL_FLORANCE_2_LARGE", "http://localhost:8002")
    monkeypatch.setenv("URL_GIT_LARGE", "http://localhost:8003")
    monkeypatch.setenv("FASTAPI_URL", "http://localhost:8000")
    monkeypatch.setenv("VPS_HOST", "")
    monkeypatch.setenv("DEBUG", "true")

    from backend.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert b"python" in response.content or b"http" in response.content
