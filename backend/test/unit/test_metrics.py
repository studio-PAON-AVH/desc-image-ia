# tests/test_metrics.py
from fastapi.testclient import TestClient


def test_metrics_endpoint_exists():
    """GET /metrics expose les métriques Prometheus."""
    from backend.main import app

    response = TestClient(app).get("/metrics")
    assert response.status_code == 200
    assert b"python" in response.content or b"http" in response.content
