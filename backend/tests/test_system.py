import pytest

from app.core.database import Database, get_db
from app.main import app
from app.routes.api import ROUTES

@pytest.fixture
def database_down():
    # port 1 tidak dipakai PostgreSQL, koneksi langsung ditolak
    down = Database("postgresql+psycopg://localhost:1/two_beans_test")
    app.dependency_overrides[get_db] = down.session
    yield
    app.dependency_overrides.pop(get_db)
    down.engine.dispose()

def test_health_database_connected(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "koneksi database ok"}

def test_health_database_down_503(client, database_down):
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json() == {"status": "gangguan", "database": "koneksi database putus"}

def test_all_routes_have_summary_and_tag(client):
    paths = client.get("/openapi.json").json()["paths"]
    operations = [op for path in paths.values() for op in path.values()]
    assert len(operations) == len(ROUTES)
    assert all(op["summary"] and op["tags"] for op in operations)

def test_swagger_available_and_redoc_disabled(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 404
