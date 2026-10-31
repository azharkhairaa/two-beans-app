import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.clock import Clock
from app.core.config import settings
from app.core.limiter import rate_limiter
from app.core.security import PasswordHasher, password_hasher
from app.core.session import SessionManager, session_manager
from app.models import User, UserRole, UserSession, UserStatus
from tests.conftest import PASSWORD

REGISTER = {"name": "Calon Manager", "email": "Calon.Manager@Example.com", "password": "kopi2026",
            "password_confirmation": "kopi2026"}

def login(client, email, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})

def only_session(db) -> UserSession:
    db.expire_all()
    return db.scalars(select(UserSession)).one()

def test_register_creates_pending_account_without_session(client, db):
    response = client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 201
    assert response.json() == {"pesan": "Registrasi terkirim. Akun bisa dipakai setelah disetujui admin."}
    user = db.scalars(select(User)).one()
    assert (user.email, user.status, user.role, user.lokasi_id) == ("calon.manager@example.com", "menunggu", None, None)
    assert user.password_hash != "kopi2026" and password_hasher.verify("kopi2026", user.password_hash)
    assert "set-cookie" not in response.headers

def test_register_validation_messages(client):
    body = REGISTER | {"email": "bukan-email", "password": "kopikopi", "password_confirmation": "beda",
                       "role": "admin"}
    assert client.post("/api/auth/register", json=body).json()["errors"] == {
        "email": "Format email tidak valid",
        "password": "Harus berisi huruf dan angka",
        "role": "Field tidak dikenal",
    }
    body = REGISTER | {"password_confirmation": "kopi2027"}
    assert client.post("/api/auth/register", json=body).json()["errors"] == {
        "password_confirmation": "Konfirmasi password tidak sama",
    }

def test_register_password_limits_in_characters_and_bytes(client):
    def password_error(password):
        return client.post("/api/auth/register", json=REGISTER | {"password": password}).json()["errors"]["password"]
    assert password_error("kopi1") == "Minimal 8 karakter"
    # 7 karakter tetap ditolak walaupun 8 byte
    assert password_error("kopié12") == "Minimal 8 karakter"
    assert password_error("kopi1" * 15) == "Maksimal 72 karakter"
    # 39 karakter tetapi 73 byte, melewati batas bcrypt
    assert password_error("kopi1" + "é" * 34) == "Terlalu panjang, huruf beraksen dihitung lebih dari satu karakter"

def test_register_duplicate_email_ignoring_case(client, db, factory):
    factory.user("calon.manager@example.com")
    db.commit()
    response = client.post("/api/auth/register", json=REGISTER)
    assert response.status_code == 409
    assert response.json()["errors"] == {"email": "Email sudah terdaftar"}

def test_login_sets_hardened_cookie_and_returns_profile(client, db, factory):
    outlet = factory.outlet()
    factory.user("manager@example.com", UserRole.MANAGER_OUTLET, lokasi=outlet)
    db.commit()
    response = login(client, "Manager@Example.com")
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    for part in ("twobeans_sesi=", "HttpOnly", "Max-Age=43200", "Path=/", "SameSite=strict"):
        assert part in cookie
    data = response.json()
    assert data["user"]["role"] == "manager_outlet" and data["user"]["lokasi"]["kode"] == "OT-01"
    assert data["user"]["last_login_at"].endswith("Z") and len(data["csrf_token"]) >= 40
    session = only_session(db)
    token = client.cookies["twobeans_sesi"]
    assert session.token_hash == session_manager.token_hash(token) != token
    assert session.csrf_token == data["csrf_token"]

def test_login_failure_same_message_and_logged(client, db, factory, caplog):
    factory.user("admin@example.com")
    db.commit()
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        wrong_password = login(client, "admin@example.com", "salah12345")
        unknown_email = login(client, "tidak.ada@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {"detail": "Email atau password salah"}
    assert "login gagal: ad***@example.com" in caplog.text and "admin@example.com" not in caplog.text

@pytest.mark.parametrize("status, message", [
    (UserStatus.MENUNGGU, "Akun belum disetujui admin"),
    (UserStatus.NONAKTIF, "Akun dinonaktifkan. Hubungi admin"),
])
def test_login_rejects_inactive_account(client, db, factory, status, message):
    factory.user("akun@example.com", role=None if status == UserStatus.MENUNGGU else UserRole.ADMIN, status=status)
    db.commit()
    response = login(client, "akun@example.com")
    assert (response.status_code, response.json()) == (403, {"detail": message})
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0

def test_login_rate_limited_per_ip(client):
    statuses = [login(client, "admin@example.com", "salah12345").status_code for _ in range(6)]
    assert statuses == [401] * 5 + [429]

def test_me_restores_profile_and_csrf(client, db, factory):
    factory.user("admin@example.com")
    db.commit()
    token = login(client, "admin@example.com").json()["csrf_token"]
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["csrf_token"] == token and response.json()["user"]["email"] == "admin@example.com"

def test_me_without_session_401(client):
    response = client.get("/api/auth/me")
    assert (response.status_code, response.json()) == (401, {"detail": "Belum login atau sesi sudah berakhir"})

def test_logout_requires_csrf_then_revokes_session(client, db, factory):
    factory.user("admin@example.com")
    db.commit()
    csrf = login(client, "admin@example.com").json()["csrf_token"]
    response = client.post("/api/auth/logout", headers={"X-CSRF-Token": "token-palsu"})
    assert (response.status_code, response.json()) == (403, {"detail": "Token CSRF tidak valid"})
    assert client.get("/api/auth/me").status_code == 200
    response = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 204
    assert 'twobeans_sesi=""' in response.headers["set-cookie"] and "Max-Age=0" in response.headers["set-cookie"]
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0
    assert client.get("/api/auth/me").status_code == 401

def test_session_expires_after_idle_limit(client, db, factory):
    factory.user("admin@example.com")
    db.commit()
    login(client, "admin@example.com")
    session = only_session(db)
    session.last_seen_at = datetime.now(UTC) - timedelta(minutes=61)
    db.commit()
    assert client.get("/api/auth/me").status_code == 401
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0

def test_session_expires_after_absolute_limit(client, db, factory):
    factory.user("admin@example.com")
    db.commit()
    login(client, "admin@example.com")
    now = datetime.now(UTC)
    session = only_session(db)
    session.created_at, session.expires_at, session.last_seen_at = now - timedelta(hours=13), now - timedelta(hours=1), now
    db.commit()
    assert client.get("/api/auth/me").status_code == 401

def test_deactivated_user_loses_session(client, db, factory):
    user = factory.user("admin@example.com")
    db.commit()
    login(client, "admin@example.com")
    user.status = UserStatus.NONAKTIF
    db.commit()
    assert client.get("/api/auth/me").status_code == 401

def test_last_seen_updated_at_most_every_five_minutes(client, db, factory):
    factory.user("admin@example.com")
    db.commit()
    login(client, "admin@example.com")
    recent = datetime.now(UTC) - timedelta(minutes=1)
    session = only_session(db)
    session.last_seen_at = recent
    db.commit()
    client.get("/api/auth/me")
    assert only_session(db).last_seen_at == recent
    session = only_session(db)
    session.last_seen_at = datetime.now(UTC) - timedelta(minutes=10)
    db.commit()
    client.get("/api/auth/me")
    assert datetime.now(UTC) - only_session(db).last_seen_at < timedelta(minutes=1)

def test_each_login_gets_new_token_and_purges_expired(client, db, factory):
    user = factory.user("admin@example.com")
    now = datetime.now(UTC)
    factory.add(UserSession(user=user, token_hash="0" * 64, csrf_token="lama", created_at=now - timedelta(hours=13),
                            last_seen_at=now - timedelta(hours=2), expires_at=now - timedelta(hours=1)))
    db.commit()
    login(client, "admin@example.com")
    first = client.cookies["twobeans_sesi"]
    client.cookies.clear()
    login(client, "admin@example.com")
    assert client.cookies["twobeans_sesi"] != first
    db.expire_all()
    assert "0" * 64 not in db.scalars(select(UserSession.token_hash)).all()

def test_password_hasher_limits():
    hasher = PasswordHasher(rounds=4)
    stored = hasher.hash("kopi2026")
    assert hasher.verify("kopi2026", stored) and not hasher.verify("kopi2027", stored)
    assert not hasher.verify("kopi2026", None)
    long_password = "k" * 72
    assert hasher.verify(long_password, hasher.hash(long_password))
    assert not hasher.verify(long_password + "x", hasher.hash(long_password))

def test_secret_key_change_invalidates_token():
    other = SessionManager(replace(settings, secret_key="kunci-lain-yang-juga-panjang-sekali-0123456789"))
    assert other.token_hash("token") != session_manager.token_hash("token")

def test_account_locked_for_15_minutes_after_five_failed_logins(client, db, factory):
    user = factory.user("terkunci@example.com")
    db.commit()
    now = datetime.now(UTC)

    with Clock.at(now):
        # 5 kali gagal dari IP berbeda agar menguji kunci akun, bukan rate limit IP
        for idx in range(5):
            res = client.post(
                "/api/auth/login",
                json={"email": "terkunci@example.com", "password": "salahpassword1"},
                headers={"x-real-ip": f"10.0.0.{idx + 1}"},
            )
            assert res.status_code == 401

        db.expire_all()
        locked_user = db.get(User, user.id)
        assert locked_user.failed_logins == 5
        assert locked_user.locked_until == now + timedelta(minutes=15)

        # reset hitungan rate limit IP agar percobaan ke-6 menguji kunci akun di database
        rate_limiter.reset()
        res_locked = client.post(
            "/api/auth/login",
            json={"email": "terkunci@example.com", "password": PASSWORD},
        )
        assert res_locked.status_code == 429
        assert "15 menit" in res_locked.json()["detail"]
        assert res_locked.headers["Retry-After"] == "900"

    # sesudah lewat 15 menit, login dengan password benar berhasil dan mereset failed_logins
    with Clock.at(now + timedelta(minutes=16)):
        rate_limiter.reset()
        res_ok = client.post(
            "/api/auth/login",
            json={"email": "terkunci@example.com", "password": PASSWORD},
        )
        assert res_ok.status_code == 200
        db.expire_all()
        unlocked_user = db.get(User, user.id)
        assert unlocked_user.failed_logins == 0
        assert unlocked_user.locked_until is None

def test_change_password_updates_hash_and_revokes_other_sessions(client, db, factory):
    user = factory.user("admin@example.com")
    now = datetime.now(UTC)
    # sesi perangkat lain milik user yang sama
    other_session = factory.add(
        UserSession(
            user=user,
            token_hash="a" * 64,
            csrf_token="csrf-perangkat-lain",
            created_at=now - timedelta(minutes=10),
            last_seen_at=now - timedelta(minutes=2),
            expires_at=now + timedelta(hours=11),
        )
    )
    db.commit()
    other_session_id = other_session.id

    csrf = login(client, "admin@example.com").json()["csrf_token"]
    headers = {"X-CSRF-Token": csrf}

    # password saat ini salah -> 422
    wrong_curr = client.put(
        "/api/auth/password",
        json={
            "current_password": "salahpassword1",
            "new_password": "passwordbaru2026",
            "new_password_confirmation": "passwordbaru2026",
        },
        headers=headers,
    )
    assert wrong_curr.status_code == 422
    assert wrong_curr.json()["errors"] == {"current_password": "Password saat ini salah"}

    # konfirmasi tidak sama -> 422
    mismatch = client.put(
        "/api/auth/password",
        json={
            "current_password": PASSWORD,
            "new_password": "passwordbaru2026",
            "new_password_confirmation": "beda2026",
        },
        headers=headers,
    )
    assert mismatch.status_code == 422
    assert mismatch.json()["errors"] == {
        "new_password_confirmation": "Konfirmasi password tidak sama"
    }

    # password baru sama dengan password saat ini -> 422
    same_pw = client.put(
        "/api/auth/password",
        json={
            "current_password": PASSWORD,
            "new_password": PASSWORD,
            "new_password_confirmation": PASSWORD,
        },
        headers=headers,
    )
    assert same_pw.status_code == 422
    assert same_pw.json()["errors"] == {
        "new_password": "Password baru harus berbeda dari password saat ini"
    }

    # ubah password berhasil -> 204, sesi aktif tetap jalan dan sesi lain tercabut
    ok = client.put(
        "/api/auth/password",
        json={
            "current_password": PASSWORD,
            "new_password": "passwordbaru2026",
            "new_password_confirmation": "passwordbaru2026",
        },
        headers=headers,
    )
    assert ok.status_code == 204
    assert client.get("/api/auth/me").status_code == 200

    db.expire_all()
    assert db.get(UserSession, other_session_id) is None
    assert db.scalar(select(func.count()).select_from(UserSession)) == 1
    updated_user = db.get(User, user.id)
    assert password_hasher.verify("passwordbaru2026", updated_user.password_hash)
    assert not password_hasher.verify(PASSWORD, updated_user.password_hash)
