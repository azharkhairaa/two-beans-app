import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

# TEST_DATABASE_URL ditulis di .env, value lain ditimpa supaya test tidak bergantung .env
load_dotenv()
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://localhost:5432/two_beans_test")
if not (make_url(TEST_DATABASE_URL).database or "").endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL harus menunjuk database berakhiran _test")

os.environ.update({
    "APP_ENV": "test",
    "DATABASE_URL": TEST_DATABASE_URL,
    "SECRET_KEY": "kunci-uji-yang-panjang-dan-acak-0123456789abcdef",
    "ALLOWED_ORIGINS": "http://testserver",
    "COOKIE_SECURE": "false",
    "BCRYPT_ROUNDS": "4",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import database  # noqa: E402
from app.core.limiter import rate_limiter  # noqa: E402
from app.core.security import password_hasher  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Base,
    CoffeeType,
    Kategori,
    KategoriType,
    Lokasi,
    LokasiType,
    Produk,
    ProdukUnit,
    User,
    UserRole,
    UserStatus,
)

PASSWORD = "rahasia123"

@pytest.fixture(scope="session", autouse=True)
def schema():
    # skema test dari model, isinya sama dengan hasil migration (dicek dengan bandingkan_skema.py)
    Base.metadata.drop_all(database.engine)
    Base.metadata.create_all(database.engine)
    yield
    Base.metadata.drop_all(database.engine)

@pytest.fixture
def db():
    with database.session_factory() as session:
        yield session
    # data dihapus sesudah setiap test supaya urutan test tidak berpengaruh
    with database.engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())

@pytest.fixture(autouse=True)
def reset_rate_limit():
    # hitungan rate limit disimpan di memori proses, setiap test mulai dari nol
    rate_limiter.reset()

@pytest.fixture
def client():
    # Origin bawaan meniru browser sehingga request pengubah data lolos OriginGuard
    with TestClient(app, headers={"Origin": "http://testserver"}) as test_client:
        yield test_client

class ModelFactory:
    # data contoh untuk test, objek langsung di-flush supaya id terisi

    def __init__(self, db):
        self.db = db

    def add(self, obj):
        self.db.add(obj)
        self.db.flush()
        return obj

    def outlet(self, kode="OT-01", nama="Outlet Pusat Kota") -> Lokasi:
        return self.add(Lokasi(kode=kode, nama=nama, jenis=LokasiType.OUTLET))

    def manager(self, lokasi: Lokasi) -> User:
        return self.add(User(name="Manager Outlet", email="manager.outlet@example.com", password_hash="x",
                             role=UserRole.MANAGER_OUTLET, status=UserStatus.AKTIF, lokasi=lokasi))

    def user(self, email: str, role: str | None = UserRole.ADMIN, status: str = UserStatus.AKTIF,
             lokasi: Lokasi | None = None) -> User:
        return self.add(User(name="User Uji", email=email, password_hash=password_hasher.hash(PASSWORD),
                             role=role, status=status, lokasi=lokasi))

    def produk(self) -> Produk:
        kategori = self.add(Kategori(nama="Arabika Single Origin", jenis=KategoriType.ROASTED_BEAN))
        return self.add(Produk(sku="BK-ARB-GAYO-200", nama="Arabika Gayo 200 g", kategori=kategori,
                               satuan=ProdukUnit.PACK, berat_gram=200, jenis_kopi=CoffeeType.ARABIKA,
                               harga_beli=65000, harga_jual=95000))

@pytest.fixture
def factory(db):
    return ModelFactory(db)

@pytest.fixture
def login_as(client):
    # login lewat API lalu token CSRF dipasang di header bawaan client
    def login(email: str):
        response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
        return client
    return login
