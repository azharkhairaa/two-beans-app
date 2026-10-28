from dataclasses import replace

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.limiter import rate_limiter
from app.models import (
    CoffeeType,
    Kategori,
    Lokasi,
    Pembelian,
    Pengiriman,
    Penjualan,
    Permintaan,
    Produk,
    Stok,
    StokMutasi,
    Transaksi,
    User,
    UserStatus,
)
from app.seeders.__main__ import SeedCommand
from app.seeders.base import DEMO_PASSWORD
from app.seeders.database_seeder import DatabaseSeeder

EXPECTED = {
    "customer": 8,
    "kategori": 7,
    "lokasi": 6,
    "supplier": 6,
    "produk": 42,
    "users": 8,
    "pembelian": 12,
    "penjualan": 60,
    "permintaan": 15,
    "stok": 109,
    "transaksi": 40,
    "pembelian_detail": 41,
    "pengiriman": 25,
    "penjualan_detail": 118,
    "permintaan_detail": 51,
    "transaksi_detail": 92,
    "pengiriman_detail": 77,
    "stok_mutasi": 385,
}

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


def test_stok_matches_ledger_and_demo_states_exist(db, seeded):
    stok_rows = db.scalars(select(Stok)).all()
    statuses = {row.status_stok.value for row in stok_rows}
    assert statuses == {"aman", "menipis", "habis"}

    for row in stok_rows:
        last_after = db.scalar(
            select(StokMutasi.stok_sesudah)
            .where(
                StokMutasi.lokasi_id == row.lokasi_id,
                StokMutasi.produk_id == row.produk_id,
            )
            .order_by(StokMutasi.id.desc())
            .limit(1)
        )
        total_delta = db.scalar(
            select(func.coalesce(func.sum(StokMutasi.perubahan), 0)).where(
                StokMutasi.lokasi_id == row.lokasi_id,
                StokMutasi.produk_id == row.produk_id,
            )
        )
        assert row.jumlah == total_delta
        assert row.jumlah == (last_after or 0)

    assert "dipesan" in set(db.scalars(select(Pembelian.status)).all())
    assert {"diajukan", "disetujui", "ditolak", "selesai"} <= set(
        db.scalars(select(Permintaan.status)).all()
    )
    assert {"draf", "dikirim", "diterima"} <= set(
        db.scalars(select(Pengiriman.status)).all()
    )
    assert {"draf", "diposting"} == set(db.scalars(select(Transaksi.status)).all())
    assert {"draf", "diposting"} == set(db.scalars(select(Penjualan.status)).all())
