import json
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.limiter import RateLimiter, rate_limiter
from app.main import app, create_app
from app.routes.api import Access, Route

VERCEL_JSON = Path(__file__).resolve().parents[2] / "vercel.json"

class LimitedController:
    def ping(self, request: Request) -> dict:
        return {"status": "ok"}

@pytest.fixture
def bare_client():
    # tanpa Origin bawaan, seperti request dari luar browser
    with TestClient(app) as test_client:
        yield test_client

def make_request(headers: dict[str, str]) -> Request:
    raw = [(key.lower().encode(), value.encode()) for key, value in headers.items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "client": ("10.0.0.1", 5000)})

def test_api_response_has_security_headers(client):
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert headers["cache-control"] == "no-store"

def test_api_csp_same_as_static_pages(client):
    config = json.loads(VERCEL_JSON.read_text())
    pages = {h["key"]: h["value"] for block in config["headers"] for h in block["headers"]}
    assert client.get("/api/health").headers["content-security-policy"] == pages["Content-Security-Policy"]

def test_docs_without_csp_so_swagger_ui_loads(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "content-security-policy" not in response.headers
    assert response.headers["x-frame-options"] == "DENY"

def test_post_without_origin_rejected(bare_client):
    response = bare_client.post("/api/health")
    assert response.status_code == 403
    assert response.json() == {"detail": "Origin tidak diizinkan"}
    assert response.headers["x-content-type-options"] == "nosniff"

@pytest.mark.parametrize("headers", [
    {"Origin": "https://evil.example"},
    {"Origin": "http://testserver.evil.example"},
    {"Origin": "null", "Referer": "http://testserver/produk"},
    {"Referer": "https://evil.example/form"},
])
def test_foreign_origin_rejected(bare_client, headers):
    assert bare_client.delete("/api/health", headers=headers).status_code == 403

@pytest.mark.parametrize("headers", [{"Origin": "http://testserver"}, {"Referer": "http://testserver/produk/5"}])
def test_allowed_origin_passes_guard(bare_client, headers):
    # lolos OriginGuard lalu dijawab router, health hanya menerima GET
    assert bare_client.post("/api/health", headers=headers).status_code == 405

def test_get_not_checked(bare_client):
    assert bare_client.get("/api/health").status_code == 200

def test_rate_limit_returns_429_with_retry_after():
    limited = LimitedController()
    routes = [Route("GET", "/limited", limited.ping, Access.PUBLIC, "Contoh rate limit", rate_limit="2/minute")]
    rate_limiter.reset()
    with TestClient(create_app(routes)) as client:
        assert [client.get("/api/limited").status_code for _ in range(2)] == [200, 200]
        response = client.get("/api/limited")
    assert response.status_code == 429
    assert response.json() == {"detail": "Terlalu banyak percobaan. Coba lagi dalam 1 menit"}
    assert response.headers["retry-after"] == "60"

def test_client_address_uses_x_real_ip_only_on_vercel():
    request = make_request({"X-Real-IP": "203.0.113.7"})
    assert RateLimiter(serverless=True).client_address(request) == "203.0.113.7"
    assert RateLimiter(serverless=False).client_address(request) == "10.0.0.1"
