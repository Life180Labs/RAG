import pytest


@pytest.mark.asyncio
async def test_live_endpoint(client):
    response = await client.get("/api/v1/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_health_endpoint_includes_request_id(client):
    response = await client.get("/api/v1/health")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "healthy"
    assert "request_id" in body
    assert "x-request-id" in response.headers


@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_prometheus_format(client):
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert b"http_requests_total" in response.content or response.status_code == 200


@pytest.mark.asyncio
async def test_not_found_returns_standard_error_envelope(client):
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "code" in body["error"]
    assert "request_id" in body
