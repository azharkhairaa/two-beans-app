from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.errors import Conflict
from app.main import app
from app.models import (
    Lokasi,
    LokasiType,
    Transaksi,
    TransaksiType,
    UserRole,
    UserSession,
    UserStatus,
)
from app.schemas.user import UserUpdate
from app.services.user_service import UserService
from tests.conftest import PASSWORD

@pytest.fixture
def setup(db, factory):
    gudang = factory.add(Lokasi(kode="GU-01", nama="Gudang Utama Roastery", jenis=LokasiType.GUDANG_UTAMA))
    outlet = factory.outlet()
    users = {
        "admin": factory.user("admin@example.com"),
        "manager": factory.user("manager@example.com", UserRole.MANAGER_OUTLET, lokasi=outlet),
        "kurir": factory.user("kurir@example.com", UserRole.DELIVERYMAN),
        "calon": factory.user("calon@example.com", role=None, status=UserStatus.MENUNGGU),
    }
    db.commit()
    return {"gudang": gudang, "outlet": outlet, **users}

@pytest.fixture
def other_client():
    # browser kedua milik user yang diubah admin
    with TestClient(app, headers={"Origin": "http://testserver"}) as test_client:
        yield test_client

def test_approve_pending_account(setup, login_as, other_client):
    admin = login_as("admin@example.com")
    body = {"role": "manager_outlet", "lokasi_id": setup["outlet"].id, "status": "aktif"}
    response = admin.patch(f"/api/users/{setup['calon'].id}", json=body)
    assert response.status_code == 200
    data = response.json()
    assert (data["role"], data["status"], data["lokasi"]["kode"]) == ("manager_outlet", "aktif", "OT-01")
    login = other_client.post("/api/auth/login", json={"email": "calon@example.com", "password": PASSWORD})
    assert login.status_code == 200

@pytest.mark.parametrize("body, errors", [
    ({"status": "aktif"}, {"role": "Wajib diisi saat mengaktifkan akun"}),
    ({"role": "manager_gudang", "status": "aktif"}, {"lokasi_id": "Wajib diisi untuk manager"}),
    ({"role": "manager_outlet", "lokasi_id": 999, "status": "aktif"}, {"lokasi_id": "Lokasi tidak ditemukan"}),
    ({"role": "manager_gudang", "lokasi_id": "outlet", "status": "aktif"},
     {"lokasi_id": "Manager gudang harus ditempatkan di gudang utama atau cabang"}),
    ({"role": "manager_outlet", "lokasi_id": "gudang", "status": "aktif"},
     {"lokasi_id": "Manager outlet harus ditempatkan di outlet"}),
    ({"status": "menunggu"}, {"status": "Pilihan tidak valid"}),
    ({}, {"body": "Isi minimal satu dari role, lokasi_id atau status"}),
])
def test_approval_rules(setup, login_as, body, errors):
    if isinstance(body.get("lokasi_id"), str):
        body = body | {"lokasi_id": setup[body["lokasi_id"]].id}
    response = login_as("admin@example.com").patch(f"/api/users/{setup['calon'].id}", json=body)
    assert response.status_code == 422 and response.json()["errors"] == errors

def test_admin_and_deliveryman_not_bound_to_lokasi(setup, login_as):
    response = login_as("admin@example.com").patch(
        f"/api/users/{setup['manager'].id}", json={"role": "deliveryman", "lokasi_id": setup["outlet"].id})
    assert response.status_code == 200 and (response.json()["role"], response.json()["lokasi"]) == ("deliveryman", None)

@pytest.mark.parametrize("body", [{"status": "nonaktif"}, {"role": "manager_gudang", "lokasi_id": "gudang"}])
def test_change_revokes_sessions(db, setup, login_as, other_client, body):
    other_client.post("/api/auth/login", json={"email": "manager@example.com", "password": PASSWORD})
    assert other_client.get("/api/auth/me").status_code == 200
    if "lokasi_id" in body:
        body = body | {"lokasi_id": setup["gudang"].id}
    assert login_as("admin@example.com").patch(f"/api/users/{setup['manager'].id}", json=body).status_code == 200
    assert other_client.get("/api/auth/me").status_code == 401
    user_id = setup["manager"].id
    assert db.scalar(select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id)) == 0

def test_cannot_change_or_delete_self(setup, login_as):
    admin = login_as("admin@example.com")
    response = admin.patch(f"/api/users/{setup['admin'].id}", json={"role": "deliveryman"})
    assert (response.status_code, response.json()) == (
        409, {"detail": "Peran, lokasi atau status akun sendiri tidak bisa diubah"})
    response = admin.delete(f"/api/users/{setup['admin'].id}")
    assert (response.status_code, response.json()) == (409, {"detail": "Akun sendiri tidak bisa dihapus"})

def test_last_active_admin_is_protected(db, setup):
    # lewat API admin selalu mengubah orang lain, jadi aturan ini diuji langsung di service
    service = UserService(db)
    with pytest.raises(Conflict, match="Minimal satu admin aktif"):
        service.change(setup["admin"], UserUpdate(status="nonaktif"), actor=setup["kurir"])
    with pytest.raises(Conflict, match="Minimal satu admin aktif"):
        service.delete_user(setup["admin"], actor=setup["kurir"])

def test_delete_pending_and_user_with_history(db, factory, setup, login_as):
    factory.add(Transaksi(kode="BM-261028-0001", jenis=TransaksiType.MASUK, tanggal=date(2026, 10, 28),
                          lokasi_id=setup["outlet"].id, alasan="retur", dibuat_oleh_id=setup["manager"].id))
    db.commit()
    admin = login_as("admin@example.com")
    # menolak akun menunggu = menghapusnya, sesi tidak menghalangi karena ON DELETE CASCADE
    assert admin.delete(f"/api/users/{setup['calon'].id}").status_code == 204
    response = admin.delete(f"/api/users/{setup['manager'].id}")
    assert response.status_code == 409
    assert response.json()["detail"] == "User masih dipakai 1 transaksi. Nonaktifkan saja bila tidak dipakai lagi"

def test_list_pending_first_and_filters(setup, login_as, client):
    admin = login_as("admin@example.com")
    data = admin.get("/api/users").json()
    assert data["data"][0]["email"] == "calon@example.com" and data["meta"]["total"] == 4
    assert [u["email"] for u in admin.get("/api/users", params={"role": "deliveryman"}).json()["data"]] == [
        "kurir@example.com"]
    assert admin.get("/api/users", params={"lokasi_id": setup["outlet"].id}).json()["meta"]["total"] == 1
    assert admin.get("/api/users", params={"q": "MANAGER@"}).json()["meta"]["total"] == 1
    client.cookies.clear()
    manager = login_as("manager@example.com")
    assert manager.get("/api/users").status_code == 403
    assert manager.get("/api/users/deliveryman").json() == [{"id": setup["kurir"].id, "nama": "User Uji"}]
