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
    UserRole,
)

@pytest.fixture
def setup(db, factory):
    kategori = {
        jenis: factory.add(Kategori(nama=nama, jenis=jenis))
        for nama, jenis in [
            ("Green Bean", KategoriType.GREEN_BEAN),
            ("Single Origin", KategoriType.ROASTED_BEAN),
            ("Alat Seduh", KategoriType.PERALATAN),
        ]
    }
    green = factory.add(Produk(
        sku="GB-ARB-GAYO", nama="Green Bean Gayo", kategori=kategori[KategoriType.GREEN_BEAN],
        satuan=ProdukUnit.KG, jenis_kopi=CoffeeType.ARABIKA, harga_beli=110000, harga_jual=145000,
    ))
    biji = factory.add(Produk(
        sku="BK-ARB-GAYO-200", nama="Arabika Gayo 200 g", kategori=kategori[KategoriType.ROASTED_BEAN],
        satuan=ProdukUnit.PACK, berat_gram=200, jenis_kopi=CoffeeType.ARABIKA,
        harga_beli=65000, harga_jual=95000,
    ))
    alat = factory.add(Produk(
        sku="AL-V60-02", nama="Dripper V60 02", kategori=kategori[KategoriType.PERALATAN],
        satuan=ProdukUnit.PCS, harga_beli=120000, harga_jual=165000,
    ))
    gudang = factory.add(Lokasi(kode="GU-01", nama="Gudang Utama Roastery", jenis=LokasiType.GUDANG_UTAMA))
    outlet = factory.outlet()
    admin = factory.user("admin@example.com")
    manager_gudang = factory.user("gudang@example.com", UserRole.MANAGER_GUDANG, lokasi=gudang)
    manager_outlet = factory.user("outlet@example.com", UserRole.MANAGER_OUTLET, lokasi=outlet)
    factory.user("kurir@example.com", UserRole.DELIVERYMAN)
    db.commit()
    return {
        "kategori": kategori, "green": green, "biji": biji, "alat": alat,
        "gudang": gudang, "outlet": outlet, "admin": admin,
        "manager_gudang": manager_gudang, "manager_outlet": manager_outlet,
    }

def payload(setup, **changes):
    base = {
        "jenis": "masuk",
        "tanggal": Clock.today().isoformat(),
        "alasan": "retur",
        "keterangan": "Retur pelanggan",
        "items": [{"produk_id": setup["biji"].id, "jumlah": 5}],
    }
    return base | changes

def balance(db, lokasi_id: int, produk_id: int) -> int | None:
    return db.scalar(select(Stok.jumlah).where(Stok.lokasi_id == lokasi_id, Stok.produk_id == produk_id))

def test_draft_create_update_and_delete(setup, login_as):
    client = login_as("outlet@example.com")
    created = client.post("/api/transaksi", json=payload(setup))
    assert created.status_code == 201
    data = created.json()
    assert data["kode"].startswith("BM-") and data["status"] == "draf"
    assert (data["lokasi"]["kode"], data["jumlah_item"], data["diposting_oleh"]) == ("OT-01", 1, None)
    # ubah draf mengganti baris detail termasuk produk yang sama tanpa bentrok UNIQUE
    updated_body = payload(
        setup, keterangan=" ", catatan="Dicek ulang",
        items=[{"produk_id": setup["biji"].id, "jumlah": 8}, {"produk_id": setup["alat"].id, "jumlah": 2}],
    )
    updated = client.put(f"/api/transaksi/{data['id']}", json=updated_body)
    assert updated.status_code == 200
    detail = updated.json()
    assert (detail["keterangan"], detail["catatan"], detail["jumlah_item"]) == (None, "Dicek ulang", 2)
    assert [(i["produk"]["sku"], i["jumlah"]) for i in detail["items"]] == [
        ("BK-ARB-GAYO-200", 8), ("AL-V60-02", 2)]
    # jenis tidak bisa diubah sesudah draf dibuat
    wrong_jenis = client.put(f"/api/transaksi/{data['id']}", json=payload(setup, jenis="keluar", alasan="sampel"))
    assert wrong_jenis.status_code == 409
    assert wrong_jenis.json()["errors"] == {"jenis": "Jenis transaksi tidak bisa diubah"}
    assert client.delete(f"/api/transaksi/{data['id']}").status_code == 204
    assert client.get(f"/api/transaksi/{data['id']}").status_code == 404

def test_posting_masuk_keluar_and_penyesuaian_plus_minus(db, setup, login_as):
    client = login_as("gudang@example.com")
    gudang, green, biji, alat = setup["gudang"], setup["green"], setup["biji"], setup["alat"]
    masuk = client.post("/api/transaksi", json=payload(
        setup, jenis="masuk", alasan="hasil_roasting", items=[{"produk_id": biji.id, "jumlah": 20}],
    )).json()
    posted_masuk = client.post(f"/api/transaksi/{masuk['id']}/posting")
    assert posted_masuk.status_code == 200
    assert posted_masuk.json()["status"] == "diposting" and posted_masuk.json()["diposting_pada"] is not None
    assert balance(db, gudang.id, biji.id) == 20

    keluar = client.post("/api/transaksi", json=payload(
        setup, jenis="keluar", alasan="sampel", items=[{"produk_id": biji.id, "jumlah": 6}],
    )).json()
    assert client.post(f"/api/transaksi/{keluar['id']}/posting").status_code == 200
    assert balance(db, gudang.id, biji.id) == 14

    # penyesuaian boleh positif dan negatif dalam satu dokumen
    opname = client.post("/api/transaksi", json=payload(
        setup, jenis="penyesuaian", alasan="opname",
        items=[{"produk_id": biji.id, "jumlah": -4}, {"produk_id": alat.id, "jumlah": 3},
               {"produk_id": green.id, "jumlah": 10}],
    )).json()
    assert opname["kode"].startswith("PS-")
    assert client.post(f"/api/transaksi/{opname['id']}/posting").status_code == 200
    db.expire_all()
    assert (balance(db, gudang.id, biji.id), balance(db, gudang.id, alat.id), balance(db, gudang.id, green.id)) == (
        10, 3, 10)
    rows = db.execute(
        select(StokMutasi.jenis, StokMutasi.perubahan, StokMutasi.stok_sesudah)
        .where(StokMutasi.produk_id == biji.id)
        .order_by(StokMutasi.id)
    ).all()
    assert rows == [("masuk", 20, 20), ("keluar", -6, 14), ("penyesuaian", -4, 10)]

def test_posting_insufficient_stock_rolls_back(db, factory, setup, login_as):
    gudang, biji, alat = setup["gudang"], setup["biji"], setup["alat"]
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=10))
    factory.add(Stok(lokasi_id=gudang.id, produk_id=alat.id, jumlah=2))
    db.commit()
    client = login_as("gudang@example.com")
    draft = client.post("/api/transaksi", json=payload(
        setup, jenis="keluar", alasan="pemakaian",
        items=[{"produk_id": biji.id, "jumlah": 4}, {"produk_id": alat.id, "jumlah": 5}],
    )).json()
    response = client.post(f"/api/transaksi/{draft['id']}/posting")
    assert response.status_code == 409
    assert response.json()["errors"] == {
        "items.1.jumlah": "Stock AL-V60-02 di Gudang Utama Roastery tersisa 2 pcs",
    }
    db.expire_all()
    assert (balance(db, gudang.id, biji.id), balance(db, gudang.id, alat.id)) == (10, 2)
    assert client.get(f"/api/transaksi/{draft['id']}").json()["status"] == "draf"

def test_final_transaction_rejects_update_delete_and_repost_409(setup, login_as):
    client = login_as("outlet@example.com")
    draft = client.post("/api/transaksi", json=payload(setup)).json()
    assert client.post(f"/api/transaksi/{draft['id']}/posting").status_code == 200
    expected = (409, {"detail": "Transaksi sudah diposting"})
    for response in (
        client.put(f"/api/transaksi/{draft['id']}", json=payload(setup, keterangan="Ubah")),
        client.delete(f"/api/transaksi/{draft['id']}"),
        client.post(f"/api/transaksi/{draft['id']}/posting"),
    ):
        assert (response.status_code, response.json()) == expected

@pytest.mark.parametrize("changes, expected_errors", [
    ({"jenis": "keluar", "alasan": "penjualan"}, {
        "alasan": "Penjualan dicatat lewat dokumen penjualan, bukan transaksi keluar",
    }),
    ({"jenis": "masuk", "alasan": "roasting"}, {
        "alasan": "Alasan transaksi masuk harus salah satu dari hasil_roasting, retur, lainnya",
    }),
    ({"jenis": "keluar", "alasan": "roasting"}, {
        "items.0.produk_id": "Alasan roasting hanya untuk produk green bean",
    }),
    ({"jenis": "masuk", "alasan": "hasil_roasting", "use_green": True}, {
        "items.0.produk_id": "Alasan hasil roasting hanya untuk produk roasted bean",
    }),
])
def test_reason_and_roasting_category_rules(setup, login_as, changes, expected_errors):
    changes = dict(changes)
    produk = setup["green"] if changes.pop("use_green", False) else setup["biji"]
    body = payload(setup, items=[{"produk_id": produk.id, "jumlah": 3}], **changes)
    response = login_as("gudang@example.com").post("/api/transaksi", json=body)
    assert response.status_code == 422 and response.json()["errors"] == expected_errors

def test_valid_roasting_workflow(setup, login_as):
    client = login_as("gudang@example.com")
    masuk_gb = client.post("/api/transaksi", json=payload(
        setup, jenis="masuk", alasan="lainnya", items=[{"produk_id": setup["green"].id, "jumlah": 10}],
    )).json()
    assert client.post(f"/api/transaksi/{masuk_gb['id']}/posting").status_code == 200
    roasting = client.post("/api/transaksi", json=payload(
        setup, jenis="keluar", alasan="roasting", items=[{"produk_id": setup["green"].id, "jumlah": 5}],
    )).json()
    assert client.post(f"/api/transaksi/{roasting['id']}/posting").status_code == 200
    hasil = client.post("/api/transaksi", json=payload(
        setup, jenis="masuk", alasan="hasil_roasting", items=[{"produk_id": setup["biji"].id, "jumlah": 20}],
    )).json()
    assert client.post(f"/api/transaksi/{hasil['id']}/posting").status_code == 200

def test_date_quantity_and_reference_validation(db, factory, setup, login_as):
    today = Clock.today()
    nonaktif_produk = factory.add(Produk(
        sku="AL-NONAKTIF", nama="Alat Lama", kategori=setup["kategori"][KategoriType.PERALATAN],
        satuan=ProdukUnit.PCS, aktif=False,
    ))
    nonaktif_lokasi = factory.add(Lokasi(kode="OT-09", nama="Outlet Tutup", jenis=LokasiType.OUTLET, aktif=False))
    db.commit()
    admin = login_as("admin@example.com")

    besok = admin.post("/api/transaksi", json=payload(
        setup, lokasi_id=setup["gudang"].id, tanggal=(today + timedelta(days=1)).isoformat(),
    ))
    assert besok.status_code == 422 and besok.json()["errors"] == {
        "tanggal": "Tanggal tidak boleh melewati hari ini",
    }
    kadaluarsa = admin.post("/api/transaksi", json=payload(
        setup, lokasi_id=setup["gudang"].id, tanggal=(today - timedelta(days=366)).isoformat(),
    ))
    assert kadaluarsa.status_code == 422 and kadaluarsa.json()["errors"] == {
        "tanggal": "Tanggal tidak boleh lebih tua dari 365 hari",
    }
    tanpa_lokasi = admin.post("/api/transaksi", json=payload(setup))
    assert tanpa_lokasi.json()["errors"] == {"lokasi_id": "Wajib diisi untuk admin"}
    lokasi_tutup = admin.post("/api/transaksi", json=payload(setup, lokasi_id=nonaktif_lokasi.id))
    assert lokasi_tutup.json()["errors"] == {"lokasi_id": "Lokasi sudah tidak aktif"}

    baris_salah = admin.post("/api/transaksi", json=payload(
        setup, lokasi_id=setup["gudang"].id, jenis="masuk",
        items=[{"produk_id": setup["biji"].id, "jumlah": 0},
               {"produk_id": nonaktif_produk.id, "jumlah": 2},
               {"produk_id": 9999, "jumlah": -1}],
    ))
    assert baris_salah.status_code == 422 and baris_salah.json()["errors"] == {
        "items.0.jumlah": "Minimal 1",
        "items.1.produk_id": "Produk sudah tidak aktif",
        "items.2.produk_id": "Produk tidak ditemukan",
        "items.2.jumlah": "Minimal 1",
    }
    opname_nol = admin.post("/api/transaksi", json=payload(
        setup, lokasi_id=setup["gudang"].id, jenis="penyesuaian", alasan="opname",
        items=[{"produk_id": setup["biji"].id, "jumlah": 0}],
    ))
    assert opname_nol.json()["errors"] == {"items.0.jumlah": "Jumlah penyesuaian tidak boleh 0"}

    duplikat = admin.post("/api/transaksi", json=payload(
        setup, lokasi_id=setup["gudang"].id,
        items=[{"produk_id": setup["biji"].id, "jumlah": 1}, {"produk_id": setup["biji"].id, "jumlah": 2}],
    ))
    assert duplikat.status_code == 409 and duplikat.json()["errors"] == {
        "items": "Produk tidak boleh ganda dalam satu dokumen",
    }
    asing = admin.post("/api/transaksi", json=payload(setup, lokasi_id=setup["gudang"].id, status="diposting"))
    assert asing.status_code == 422 and asing.json()["errors"] == {"status": "Field tidak dikenal"}

def test_location_scope_filters_and_role_access(setup, login_as, client):
    assert client.get("/api/transaksi").status_code == 401
    assert login_as("kurir@example.com").get("/api/transaksi").status_code == 403
    client.cookies.clear()

    gudang_client = login_as("gudang@example.com")
    tx_gudang = gudang_client.post("/api/transaksi", json=payload(
        setup, keterangan="Stok gudang", tanggal=(Clock.today() - timedelta(days=2)).isoformat(),
    )).json()
    client.cookies.clear()

    outlet_client = login_as("outlet@example.com")
    tx_outlet = outlet_client.post("/api/transaksi", json=payload(setup, keterangan="Stok outlet")).json()
    # manager hanya melihat lokasinya sendiri dan mendapat 404 untuk transaksi lokasi lain (BR-14)
    daftar = outlet_client.get("/api/transaksi").json()
    assert [row["id"] for row in daftar["data"]] == [tx_outlet["id"]]
    assert outlet_client.get("/api/transaksi", params={"lokasi_id": setup["gudang"].id}).json()["data"] == []
    for response in (
        outlet_client.get(f"/api/transaksi/{tx_gudang['id']}"),
        outlet_client.put(f"/api/transaksi/{tx_gudang['id']}", json=payload(setup)),
        outlet_client.delete(f"/api/transaksi/{tx_gudang['id']}"),
        outlet_client.post(f"/api/transaksi/{tx_gudang['id']}/posting"),
        outlet_client.post("/api/transaksi", json=payload(setup, lokasi_id=setup["gudang"].id)),
    ):
        assert (response.status_code, response.json()) == (404, {"detail": "Transaksi tidak ditemukan"})

    client.cookies.clear()
    admin = login_as("admin@example.com")
    assert admin.get("/api/transaksi").json()["meta"]["total"] == 2
    filtered = admin.get("/api/transaksi", params={"q": "gudang", "sampai": (Clock.today() - timedelta(days=1)).isoformat()}).json()
    assert [row["id"] for row in filtered["data"]] == [tx_gudang["id"]]
