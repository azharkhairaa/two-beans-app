import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import create_app
from app.models import Lokasi, LokasiType, Penjualan, User, UserRole
from app.policies.access import current_user
from app.policies.lokasi_policy import LokasiPolicy
from app.routes.api import ROUTES, Access, Route
from tests.conftest import PASSWORD

class SampleController:
    def whoami(self, user: User = Depends(current_user)) -> dict:
        return {"email": user.email}

sample = SampleController()
SAMPLE_ROUTES = [
    *ROUTES,
    Route("GET", "/sample/login", sample.whoami, Access.LOGIN, "Contoh login"),
    Route("GET", "/sample/manager", sample.whoami, Access.MANAGER, "Contoh manager"),
    Route("GET", "/sample/admin", sample.whoami, Access.ADMIN, "Contoh admin"),
]

@pytest.fixture
def sample_client():
    with TestClient(create_app(SAMPLE_ROUTES), headers={"Origin": "http://testserver"}) as client:
        yield client

@pytest.fixture
def accounts(db, factory):
    gudang = factory.add(Lokasi(kode="GC-01", nama="Gudang Cabang Dago", jenis=LokasiType.GUDANG_CABANG))
    factory.user("admin@example.com")
    factory.user("gudang@example.com", UserRole.MANAGER_GUDANG, lokasi=gudang)
    factory.user("kurir@example.com", UserRole.DELIVERYMAN)
    db.commit()

@pytest.mark.parametrize("email, expected", [
    ("admin@example.com", {"login": 200, "manager": 200, "admin": 200}),
    ("gudang@example.com", {"login": 200, "manager": 200, "admin": 403}),
    ("kurir@example.com", {"login": 200, "manager": 403, "admin": 403}),
])
def test_role_levels(sample_client, accounts, email, expected):
    sample_client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    actual = {level: sample_client.get(f"/api/sample/{level}").status_code for level in expected}
    assert actual == expected

def test_role_messages(sample_client, accounts):
    sample_client.post("/api/auth/login", json={"email": "kurir@example.com", "password": PASSWORD})
    assert sample_client.get("/api/sample/manager").json() == {"detail": "Fitur ini khusus manager dan admin"}
    assert sample_client.get("/api/sample/admin").json() == {"detail": "Fitur ini khusus admin"}

def test_protected_route_without_login_401(sample_client):
    assert sample_client.get("/api/sample/admin").status_code == 401

def test_lokasi_policy_admin_and_manager():
    admin = User(role=UserRole.ADMIN, lokasi_id=None)
    manager = User(role=UserRole.MANAGER_OUTLET, lokasi_id=4)
    kurir = User(role=UserRole.DELIVERYMAN, lokasi_id=None)
    assert LokasiPolicy(admin).can_manage(9)
    assert LokasiPolicy(manager).can_manage(4) and not LokasiPolicy(manager).can_manage(9)
    assert not LokasiPolicy(kurir).can_manage(4)

def test_lokasi_policy_restricts_list_query():
    query = select(Penjualan)
    assert LokasiPolicy(User(role=UserRole.ADMIN)).restrict(query, Penjualan.lokasi_id) is query
    restricted = LokasiPolicy(User(role=UserRole.MANAGER_OUTLET, lokasi_id=4)).restrict(query, Penjualan.lokasi_id)
    assert "WHERE penjualan.lokasi_id = " in str(restricted)
    nothing = LokasiPolicy(User(role=UserRole.DELIVERYMAN)).restrict(query, Penjualan.lokasi_id)
    assert "WHERE false" in str(nothing)
