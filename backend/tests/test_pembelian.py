from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.clock import Clock
from app.models import (
    CoffeeType,
    Kategori,
    KategoriType,
    Lokasi,
    LokasiType,
    Produk,
    ProdukUnit,
    Stok,
    StokMutasi,
    Supplier,
    UserRole,
)

@pytest.fixture
def setup(db, factory):
    kategori_green = factory.add(
        Kategori(nama="Green Bean", jenis=KategoriType.GREEN_BEAN)
    )
    kategori_biji = factory.add(
        Kategori(nama="Single Origin", jenis=KategoriType.ROASTED_BEAN)
    )
    kategori_alat = factory.add(
        Kategori(nama="Alat Seduh", jenis=KategoriType.PERALATAN)
    )
    green = factory.add(
        Produk(
            sku="GB-ARB-GAYO",
            nama="Green Bean Gayo",
            kategori=kategori_green,
            satuan=ProdukUnit.KG,
            jenis_kopi=CoffeeType.ARABIKA,
            harga_beli=110000,
            harga_jual=145000,
        )
    )
    biji = factory.add(
        Produk(
            sku="BK-ARB-GAYO-200",
            nama="Arabika Gayo 200 g",
            kategori=kategori_biji,
            satuan=ProdukUnit.PACK,
            berat_gram=200,
            jenis_kopi=CoffeeType.ARABIKA,
            harga_beli=65000,
            harga_jual=95000,
        )
    )
    alat = factory.add(
        Produk(
            sku="AL-V60-02",
            nama="Dripper V60 02",
            kategori=kategori_alat,
            satuan=ProdukUnit.PCS,
            harga_beli=120000,
            harga_jual=165000,
        )
    )
    supplier = factory.add(
        Supplier(
            nama="Koperasi Gayo Highland",
            kontak="Pak Hendra",
            telepon="081234567890",
        )
    )
    gudang = factory.add(
        Lokasi(
            kode="GU-01",
            nama="Gudang Utama Roastery",
            jenis=LokasiType.GUDANG_UTAMA,
        )
    )
    cabang = factory.add(
        Lokasi(
            kode="GC-01",
            nama="Gudang Cabang Selatan",
            jenis=LokasiType.GUDANG_CABANG,
        )
    )
    outlet = factory.outlet()
    admin = factory.user("admin@example.com")
    manager_gudang = factory.user(
        "gudang@example.com", UserRole.MANAGER_GUDANG, lokasi=gudang
    )
    manager_cabang = factory.user(
        "cabang@example.com", UserRole.MANAGER_GUDANG, lokasi=cabang
    )
    manager_outlet = factory.user(
        "outlet@example.com", UserRole.MANAGER_OUTLET, lokasi=outlet
    )
    kurir = factory.user("kurir@example.com", UserRole.DELIVERYMAN)
    db.commit()
    return {
        "green": green,
        "biji": biji,
        "alat": alat,
        "supplier": supplier,
        "gudang": gudang,
        "cabang": cabang,
        "outlet": outlet,
        "admin": admin,
        "manager_gudang": manager_gudang,
        "manager_cabang": manager_cabang,
        "manager_outlet": manager_outlet,
        "kurir": kurir,
    }

def payload(setup, **changes):
    base = {
        "supplier_id": setup["supplier"].id,
        "tanggal_perkiraan": (Clock.today() + timedelta(days=5)).isoformat(),
        "catatan": "Panen baru",
        "items": [
            {
                "produk_id": setup["green"].id,
                "jumlah": 50,
                "harga_satuan": 118000,
            }
        ],
    }
    return base | changes

def balance(db, lokasi_id: int, produk_id: int) -> int | None:
    return db.scalar(
        select(Stok.jumlah).where(
            Stok.lokasi_id == lokasi_id, Stok.produk_id == produk_id
        )
    )

def test_draft_create_update_and_delete(setup, login_as):
    client = login_as("gudang@example.com")
    created = client.post("/api/pembelian", json=payload(setup))
    assert created.status_code == 201
    data = created.json()
    assert data["kode"].startswith("PO-") and data["status"] == "draf"
    assert data["lokasi"]["kode"] == "GU-01"
    assert data["total_pesanan"] == 50 * 118000
    assert data["total_diterima"] is None

    updated = client.put(
        f"/api/pembelian/{data['id']}",
        json=payload(
            setup,
            catatan="Tambah dripper",
            items=[
                {
                    "produk_id": setup["green"].id,
                    "jumlah": 40,
                    "harga_satuan": 115000,
                },
                {
                    "produk_id": setup["alat"].id,
                    "jumlah": 5,
                    "harga_satuan": 125000,
                },
            ],
        ),
    )
    assert updated.status_code == 200
    detail = updated.json()
    assert detail["jumlah_item"] == 2
    assert detail["total_pesanan"] == 40 * 115000 + 5 * 125000

    assert client.delete(f"/api/pembelian/{data['id']}").status_code == 204
    assert client.get(f"/api/pembelian/{data['id']}").status_code == 404

def test_pesan_and_terima_updates_stock_and_harga_beli(db, setup, login_as):
    client = login_as("gudang@example.com")
    gudang, green, alat = setup["gudang"], setup["green"], setup["alat"]
    po = client.post(
        "/api/pembelian",
        json=payload(
            setup,
            items=[
                {"produk_id": green.id, "jumlah": 50, "harga_satuan": 118000},
                {"produk_id": alat.id, "jumlah": 5, "harga_satuan": 125000},
            ],
        ),
    ).json()

    ordered = client.post(
        f"/api/pembelian/{po['id']}/pesan",
        json={
            "tanggal_pesan": Clock.today().isoformat(),
            "tanggal_perkiraan": (Clock.today() + timedelta(days=3)).isoformat(),
        },
    )
    assert ordered.status_code == 200
    ordered_data = ordered.json()
    assert ordered_data["status"] == "dipesan"
    assert ordered_data["dipesan_oleh"]["id"] == setup["manager_gudang"].id
    # sesudah dipesan tidak bisa diubah, dihapus atau dipesan ulang
    for res in (
        client.put(f"/api/pembelian/{po['id']}", json=payload(setup)),
        client.delete(f"/api/pembelian/{po['id']}"),
        client.post(f"/api/pembelian/{po['id']}/pesan"),
    ):
        assert (res.status_code, res.json()) == (
            409,
            {"detail": "Pembelian sudah dipesan"},
        )

    received = client.post(
        f"/api/pembelian/{po['id']}/terima",
        json={
            "items": [
                {"produk_id": green.id, "jumlah_diterima": 48},
                {"produk_id": alat.id, "jumlah_diterima": 5},
            ]
        },
    )
    assert received.status_code == 200
    rec_data = received.json()
    assert rec_data["status"] == "diterima"
    assert rec_data["total_diterima"] == 48 * 118000 + 5 * 125000
    db.expire_all()
    assert (balance(db, gudang.id, green.id), balance(db, gudang.id, alat.id)) == (
        48,
        5,
    )
    # BR-12: harga_beli produk diperbarui ke harga_satuan pembelian terakhir
    assert db.get(Produk, green.id).harga_beli == 118000
    assert db.get(Produk, alat.id).harga_beli == 125000
    mutasi = db.execute(
        select(StokMutasi.produk_id, StokMutasi.jenis, StokMutasi.perubahan)
        .where(StokMutasi.pembelian_id == po["id"])
        .order_by(StokMutasi.id)
    ).all()
    assert mutasi == [(green.id, "pembelian", 48), (alat.id, "pembelian", 5)]

def test_batal_from_draf_and_from_dipesan(setup, login_as):
    client = login_as("admin@example.com")
    po_draf = client.post("/api/pembelian", json=payload(setup)).json()
    res_draf = client.post(f"/api/pembelian/{po_draf['id']}/batal")
    assert res_draf.status_code == 200 and res_draf.json()["status"] == "dibatalkan"

    po_pesan = client.post("/api/pembelian", json=payload(setup)).json()
    assert client.post(f"/api/pembelian/{po_pesan['id']}/pesan").status_code == 200
    res_pesan = client.post(f"/api/pembelian/{po_pesan['id']}/batal")
    assert res_pesan.status_code == 200 and res_pesan.json()["status"] == "dibatalkan"

    for res in (
        client.post(f"/api/pembelian/{po_pesan['id']}/batal"),
        client.post(
            f"/api/pembelian/{po_pesan['id']}/terima",
            json={"items": [{"produk_id": setup["green"].id, "jumlah_diterima": 10}]},
        ),
    ):
        assert (res.status_code, res.json()) == (
            409,
            {"detail": "Pembelian sudah dibatalkan"},
        )

def test_validation_rules_for_roasted_bean_supplier_and_terima(
    db, factory, setup, login_as
):
    supplier_nonaktif = factory.add(
        Supplier(nama="Supplier Lama", aktif=False)
    )
    db.commit()

    client = login_as("gudang@example.com")
    # BR-11: roasted_bean ditolak 422 di pembelian
    tolak_biji = client.post(
        "/api/pembelian",
        json=payload(
            setup,
            supplier_id=supplier_nonaktif.id,
            items=[
                {
                    "produk_id": setup["biji"].id,
                    "jumlah": 10,
                    "harga_satuan": 65000,
                }
            ],
        ),
    )
    assert tolak_biji.status_code == 422 and tolak_biji.json()["errors"] == {
        "supplier_id": "Supplier sudah tidak aktif",
        "items.0.produk_id": (
            "Produk roasted bean diproduksi sendiri dan tidak bisa dibeli dari supplier"
        ),
    }

    po = client.post("/api/pembelian", json=payload(setup)).json()
    # terima sebelum dipesan ditolak 409
    belum_pesan = client.post(
        f"/api/pembelian/{po['id']}/terima",
        json={"items": [{"produk_id": setup["green"].id, "jumlah_diterima": 50}]},
    )
    assert (belum_pesan.status_code, belum_pesan.json()) == (
        409,
        {"detail": "Pembelian masih berstatus draf"},
    )

    assert client.post(f"/api/pembelian/{po['id']}/pesan").status_code == 200
    lebih = client.post(
        f"/api/pembelian/{po['id']}/terima",
        json={"items": [{"produk_id": setup["green"].id, "jumlah_diterima": 55}]},
    )
    assert lebih.status_code == 422 and lebih.json()["errors"] == {
        "items.0.jumlah_diterima": "Maksimal sebesar jumlah dipesan (50)"
    }

    nol = client.post(
        f"/api/pembelian/{po['id']}/terima",
        json={"items": [{"produk_id": setup["green"].id, "jumlah_diterima": 0}]},
    )
    assert nol.status_code == 422 and nol.json()["errors"] == {
        "items": (
            "Minimal satu produk harus diterima lebih dari 0. "
            "Gunakan aksi batal bila pesanan tidak jadi diterima"
        )
    }

def test_role_and_location_access(setup, login_as, client):
    for email in ("cabang@example.com", "outlet@example.com", "kurir@example.com"):
        user_client = login_as(email)
        assert user_client.get("/api/pembelian").status_code == 403
        assert user_client.post("/api/pembelian", json=payload(setup)).status_code == 403
        client.cookies.clear()
