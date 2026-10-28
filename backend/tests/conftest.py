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
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

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

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
