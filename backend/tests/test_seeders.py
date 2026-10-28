from dataclasses import replace

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.limiter import rate_limiter
from app.models import CoffeeType, Kategori, Lokasi, Produk, User, UserStatus
from app.seeders.__main__ import SeedCommand
from app.seeders.base import DEMO_PASSWORD
from app.seeders.database_seeder import DatabaseSeeder

EXPECTED = {"lokasi": 6, "users": 8, "kategori": 7, "supplier": 6, "customer": 8, "produk": 42}

@pytest.fixture
def seeded(db):
    return DatabaseSeeder(db).run()

def test_counts_match_design(seeded):
    assert seeded == EXPECTED

def test_rerun_resets_data_and_ids(db, seeded):
    assert DatabaseSeeder(db).run() == EXPECTED
    assert db.scalar(select(func.min(Lokasi.id))) == 1
    assert db.scalar(select(Lokasi.kode).where(Lokasi.id == 1)) == "GU-01"

def test_products_follow_category_rules(db, seeded):
    rows = db.execute(select(Produk, Kategori.jenis).join(Produk.kategori)).all()
    for produk, jenis in rows:
        if jenis == "green_bean":
            assert (produk.satuan, produk.berat_gram, produk.tingkat_sangrai) == ("kg", None, None)
            assert produk.jenis_kopi is not None
        elif jenis == "roasted_bean":
            assert produk.satuan == "pack" and produk.berat_gram in (100, 200, 250, 500, 1000)
            assert produk.tingkat_sangrai is not None and produk.jenis_kopi is not None
        else:
            assert (produk.berat_gram, produk.tingkat_sangrai, produk.jenis_kopi) == (None, None, None)
        assert 0 < produk.harga_beli < produk.harga_jual
    assert {p.jenis_kopi for p, _ in rows} - {None} == {item.value for item in CoffeeType}

def test_every_demo_account_can_login(client, seeded, db):
    users = db.scalars(select(User).order_by(User.id)).all()
    for user in users:
        # akun demo lebih banyak dari batas login 5 per menit
        rate_limiter.reset()
        response = client.post("/api/auth/login", json={"email": user.email, "password": DEMO_PASSWORD})
        expected = 200 if user.status == UserStatus.AKTIF else 403
        assert response.status_code == expected, user.email
        client.cookies.clear()
    roles = {u.role for u in users if u.status == UserStatus.AKTIF}
    assert roles == {"admin", "manager_gudang", "manager_outlet", "deliveryman"}

def test_remote_database_needs_confirmation(db, capsys):
    remote = replace(settings, database_url="postgresql+psycopg://app:rahasia@ep-contoh.neon.tech/neondb")
    calls = []
    command = SeedCommand(remote, lambda: calls.append("dipanggil"))
    assert command.run([]) == 1
    output = capsys.readouterr().out
    assert calls == [] and "--yes" in output and "rahasia" not in output

def test_local_database_seeded_without_flag(db, capsys):
    assert SeedCommand(settings, lambda: db).run([]) == 0
    output = capsys.readouterr().out
    assert "produk" in output and DEMO_PASSWORD in output
    assert db.scalar(select(func.count()).select_from(User)) == 8
