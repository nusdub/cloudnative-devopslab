from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_contains_service_metadata() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["purpose"] == "sre-cicd-observability-lab"


def test_healthz_is_ok() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_is_ready_by_default() -> None:
    client.post("/api/fault", json={"enabled": False})
    response = client.get("/readyz")
    assert response.status_code == 200


def test_create_order_success() -> None:
    client.post("/api/fault", json={"enabled": False})
    response = client.post("/api/orders", json={"item": "book", "quantity": 2, "region": "cn-east"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["order_id"].startswith("ord-")
    assert payload["item"] == "book"


def test_fault_mode_returns_500_and_not_ready() -> None:
    response = client.post("/api/fault", json={"enabled": True})
    assert response.status_code == 200
    assert response.json() == {"fault_mode": True}

    order_response = client.post("/api/orders", json={"item": "book"})
    assert order_response.status_code == 500

    ready_response = client.get("/readyz")
    assert ready_response.status_code == 503

    client.post("/api/fault", json={"enabled": False})


def test_metrics_endpoint_exposes_prometheus_format() -> None:
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    assert "app_build_info" in response.text


def test_version_endpoint_exposes_release_provenance() -> None:
    response = client.get("/api/version")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "cloudnative-devopslab"
    assert "git_sha" in payload
    assert "image_digest" in payload
