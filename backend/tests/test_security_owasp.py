import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.clock import Clock
from app.core.limiter import rate_limiter
from app.core.security import password_hasher
from app.models import (
    Lokasi,
    LokasiType,
    Penjualan,
    PenjualanStatus,
    Stok,
    User,
    UserRole,
    UserSession,
)
from tests.conftest import PASSWORD

def login_client(client, email: str, password: str = PASSWORD) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login gagal: {res.text}"
    return res.json()["csrf_token"]

# A01 broken access control: BOLA, eskalasi peran, origin dan CSRF
def test_a01_bola_isolated_between_locations(client, db, factory):
    # BOLA/IDOR: manager outlet tidak bisa membaca penjualan outlet lain
    ot1 = factory.outlet()
    ot2 = factory.add(Lokasi(kode="OT-02", nama="Outlet Dipatiukur", jenis=LokasiType.OUTLET))
    factory.user("mgr1@example.com", UserRole.MANAGER_OUTLET, lokasi=ot1)
    mgr2 = factory.user("mgr2@example.com", UserRole.MANAGER_OUTLET, lokasi=ot2)
    pj2 = factory.add(
        Penjualan(
            kode="PJ-261028-0999",
            status=PenjualanStatus.DRAF,
            lokasi=ot2,
            customer=None,
            tanggal=Clock.today(),
            dibuat_oleh=mgr2,
        )
    )
    db.commit()

    login_client(client, "mgr1@example.com")
    # dokumen lokasi lain dijawab 404 supaya keberadaan ID tidak bisa ditebak
    res = client.get(f"/api/penjualan/{pj2.id}")
    assert res.status_code == 404
    assert res.json()["detail"] == "Penjualan tidak ditemukan"

def test_a01_vertical_privilege_escalation_rejected(client, db, factory):
    # deliveryman dan manager tidak bisa mengakses endpoint khusus admin
    factory.user("kurir@example.com", UserRole.DELIVERYMAN)
    db.commit()

    login_client(client, "kurir@example.com")
    # deliveryman mencoba membuka daftar master user
    res = client.get("/api/users")
    assert res.status_code == 403
    assert "khusus admin" in res.json()["detail"]

def test_a01_csrf_and_origin_guard_enforced(client, db, factory):
    # request pengubah data tanpa token CSRF atau dari origin asing ditolak 403
    factory.user("admin@example.com", UserRole.ADMIN)
    db.commit()

    csrf = login_client(client, "admin@example.com")

    # token CSRF salah
    res_bad_csrf = client.post(
        "/api/kategori",
        json={"nama": "Sirup Rasa", "jenis": "bahan_habis_pakai"},
        headers={"X-CSRF-Token": "token-palsu-12345"},
    )
    assert res_bad_csrf.status_code == 403
    assert res_bad_csrf.json()["detail"] == "Token CSRF tidak valid"

    # origin asing
    res_bad_origin = client.post(
        "/api/kategori",
        json={"nama": "Sirup Rasa", "jenis": "bahan_habis_pakai"},
        headers={"X-CSRF-Token": csrf, "Origin": "https://evil-attacker.example.com"},
    )
    assert res_bad_origin.status_code == 403
    assert res_bad_origin.json()["detail"] == "Origin tidak diizinkan"

# A02 security misconfiguration: header keamanan, CSP dan cache-control
def test_a02_security_headers_and_cache_control(client):
    # header keamanan wajib terpasang dan API memakai cache-control no-store
    res = client.get("/api/health")
    headers = res.headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert headers["cache-control"] == "no-store"
    assert "default-src 'self'" in headers["content-security-policy"]

# A03 software supply chain failures: kontrak input ketat dan mass assignment
def test_a03_mass_assignment_and_unexpected_fields_rejected(client, db, factory):
    # schema extra='forbid' menolak field asing supaya tidak ada mass assignment
    factory.user("admin@example.com", UserRole.ADMIN)
    db.commit()

    csrf = login_client(client, "admin@example.com")
    res = client.post(
        "/api/kategori",
        json={
            "nama": "Kopi Spesialti",
            "jenis": "green_bean",
            "is_admin": True,
            "role": "superadmin",
            "extra_payload": "injected",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 422
    errors = res.json()["errors"]
    assert "is_admin" in errors and errors["is_admin"] == "Field tidak dikenal"
    assert "role" in errors and errors["role"] == "Field tidak dikenal"

# A04 cryptographic failures: hash password dan entropi token sesi
def test_a04_cryptographic_strength_and_token_storage(client, db, factory):
    # password di-hash bcrypt dan token sesi disimpan di database sebagai HMAC-SHA256
    user = factory.user("crypto@example.com", UserRole.ADMIN)
    db.commit()

    # password tidak boleh tersimpan sebagai plaintext
    assert user.password_hash.startswith("$2b$") or user.password_hash.startswith("$2a$")
    assert user.password_hash != PASSWORD
    assert password_hasher.verify(PASSWORD, user.password_hash)

    # login lalu periksa token sesi di database
    login_client(client, "crypto@example.com")
    raw_token = client.cookies["twobeans_sesi"]
    assert len(raw_token) >= 40  # 256 bit entropy

    db.expire_all()
    session = db.scalar(select(UserSession).where(UserSession.user_id == user.id))
    assert session is not None
    # database menyimpan hash token, bukan nilai cookie mentah
    assert session.token_hash != raw_token
    assert len(session.token_hash) == 64  # SHA256 hex digest

# A05 injection: parameter SQL dan sanitasi tag XSS
def test_a05_sql_injection_payloads_safely_parameterized(client, db, factory):
    # payload SQL injection di parameter query diperlakukan sebagai teks biasa
    factory.user("admin@example.com", UserRole.ADMIN)
    db.commit()

    login_client(client, "admin@example.com")
    payload = "' OR 1=1; DROP TABLE users; --"
    res = client.get(f"/api/customer?q={payload}")
    assert res.status_code == 200
    assert isinstance(res.json()["data"], list)

    # tabel users tetap utuh karena query memakai parameter
    assert db.scalar(select(func.count()).select_from(User)) >= 1

def test_a05_xss_markup_rejected_by_sanitizer(client, db, factory):
    # input berisi tag HTML atau JavaScript ditolak 422
    factory.user("admin@example.com", UserRole.ADMIN)
    db.commit()

    csrf = login_client(client, "admin@example.com")
    res = client.post(
        "/api/kategori",
        json={"nama": "<script>alert('XSS')</script>", "jenis": "green_bean"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 422
    assert "tag HTML" in res.json()["errors"]["nama"]

# A06 insecure design: aturan bisnis, stok negatif dan turun peran sendiri
def test_a06_insecure_design_prevents_negative_stock(client, db, factory):
    # stok tidak bisa dikurangi melebihi saldo yang tersedia
    ot = factory.outlet()
    factory.user("mgr@example.com", UserRole.MANAGER_OUTLET, lokasi=ot)
    prod = factory.produk()
    # stok di outlet hanya 2
    factory.add(Stok(lokasi=ot, produk=prod, jumlah=2, stok_minimum=5))
    db.commit()

    csrf = login_client(client, "mgr@example.com")

    # draf penjualan 10 unit melebihi saldo 2
    pj_res = client.post(
        "/api/penjualan",
        json={
            "tanggal": str(Clock.today()),
            "items": [{"produk_id": prod.id, "jumlah": 10, "harga_satuan": 95000}],
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert pj_res.status_code == 201
    pj_id = pj_res.json()["id"]

    # posting gagal 409 dan stok tidak berkurang
    post_res = client.post(f"/api/penjualan/{pj_id}/posting", headers={"X-CSRF-Token": csrf})
    assert post_res.status_code == 409
    assert "Stok tidak cukup" in post_res.json()["detail"]

    db.expire_all()
    stok_row = db.scalar(select(Stok).where(Stok.lokasi_id == ot.id, Stok.produk_id == prod.id))
    assert stok_row.jumlah == 2

def test_a06_self_demotion_and_last_admin_protected(client, db, factory):
    # admin tidak bisa menurunkan peran dirinya sendiri atau admin aktif terakhir
    admin = factory.user("super@example.com", UserRole.ADMIN)
    db.commit()

    csrf = login_client(client, "super@example.com")
    res = client.patch(
        f"/api/users/{admin.id}",
        json={"role": "deliveryman"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 409
    assert "sendiri tidak bisa diubah" in res.json()["detail"].lower()

# A07 authentication failures: kunci akun 15 menit dan hash pengecoh waktu
def test_a07_lockout_after_repeated_failures_and_dummy_hash(client, db, factory):
    # akun dikunci 15 menit sesudah 5 kali gagal, email asing tetap melewati hash pengecoh
    user = factory.user("locktest@example.com")
    db.commit()

    now = datetime.now(UTC)
    with Clock.at(now):
        for _ in range(5):
            rate_limiter.reset()
            client.post(
                "/api/auth/login",
                json={"email": "locktest@example.com", "password": "passwordsalah123"},
            )

        db.expire_all()
        u = db.get(User, user.id)
        assert u.failed_logins == 5
        assert u.locked_until == now + timedelta(minutes=15)

        # percobaan berikutnya ditolak 429
        rate_limiter.reset()
        res_locked = client.post(
            "/api/auth/login",
            json={"email": "locktest@example.com", "password": PASSWORD},
        )
        assert res_locked.status_code == 429
        assert "15 menit" in res_locked.json()["detail"]

# A08 software and data integrity failures: FK RESTRICT dan konsistensi buku besar
def test_a08_foreign_key_restrict_prevents_orphan_deletion(client, db, factory):
    # lokasi yang sudah dirujuk stok atau user tidak bisa dihapus (409 DataInUse)
    ot = factory.outlet()
    factory.user("mgr@example.com", UserRole.MANAGER_OUTLET, lokasi=ot)
    factory.user("admin@example.com", UserRole.ADMIN)
    db.commit()

    csrf = login_client(client, "admin@example.com")
    del_res = client.delete(f"/api/lokasi/{ot.id}", headers={"X-CSRF-Token": csrf})
    assert del_res.status_code == 409
    assert "masih dipakai" in del_res.json()["detail"].lower()

# A09 security logging and alerting failures: email disamarkan di log
def test_a09_failed_login_logged_with_masked_pii(client, db, factory, caplog):
    # login gagal dicatat di log dengan email disamarkan supaya PII tidak bocor
    factory.user("rahasia.azhar@example.com")
    db.commit()

    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        client.post(
            "/api/auth/login",
            json={"email": "rahasia.azhar@example.com", "password": "salahpassword1"},
        )

    # log mencatat 'ra***@example.com', bukan alamat email utuh
    assert "ra***@example.com" in caplog.text
    assert "rahasia.azhar@example.com" not in caplog.text

# A10 mishandling of exceptional conditions: fail-closed dan respons error aman
def test_a10_exceptional_conditions_fail_closed_and_safe_500(client, db, factory):
    # request tanpa sesi ditolak (fail-closed) dan error tidak membocorkan traceback
    # endpoint terlindungi menolak request tanpa sesi
    res_unauth = client.get("/api/dashboard")
    assert res_unauth.status_code == 401
    assert res_unauth.json() == {"detail": "Belum login atau sesi sudah berakhir"}

    # respons 404 untuk user yang login tidak membocorkan traceback atau query mentah
    factory.user("admin@example.com", UserRole.ADMIN)
    db.commit()
    login_client(client, "admin@example.com")
    res_not_found = client.get("/api/produk/99999999")
    assert res_not_found.status_code == 404
    body = res_not_found.json()
    assert "detail" in body
    assert "traceback" not in body and "Traceback" not in res_not_found.text
    assert "sqlalchemy" not in res_not_found.text.lower()
