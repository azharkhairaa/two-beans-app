from datetime import UTC, date, datetime

import pytest

from app.models import (
    Kategori,
    KategoriType,
    KendaraanType,
    Lokasi,
    LokasiType,
    Pengiriman,
    PengirimanDetail,
    PengirimanStatus,
    Produk,
    ProdukUnit,
    Stok,
    UserRole,
)

@pytest.fixture
def setup(db, factory):
    kategori = {
        jenis: factory.add(Kategori(nama=nama, jenis=jenis))
        for nama, jenis in [("Green Bean", KategoriType.GREEN_BEAN), ("Single Origin", KategoriType.ROASTED_BEAN),
                            ("Alat Seduh", KategoriType.PERALATAN)]
    }
    gudang = factory.add(Lokasi(kode="GU-01", nama="Gudang Utama Roastery", jenis=LokasiType.GUDANG_UTAMA))
    outlet = factory.outlet()
    admin = factory.user("admin@example.com")
    factory.user("manager@example.com", UserRole.MANAGER_OUTLET, lokasi=outlet)
    kurir = factory.user("kurir@example.com", UserRole.DELIVERYMAN)
    db.commit()
    return {"kategori": kategori, "gudang": gudang, "outlet": outlet, "admin": admin, "kurir": kurir}

def body(setup, jenis=KategoriType.ROASTED_BEAN, **changes):
    data = {"sku": "bk-arb-gayo-200", "nama": "Arabika Gayo 200 g", "kategori_id": setup["kategori"][jenis].id,
            "satuan": "pack", "berat_gram": 200, "tingkat_sangrai": "medium", "jenis_kopi": "arabika",
            "harga_beli": 65000, "harga_jual": 95000}
    return data | changes

def test_create_roasted_bean(setup, login_as):
    response = login_as("admin@example.com").post("/api/produk", json=body(setup, merek=" "))
    assert response.status_code == 201
    data = response.json()
    assert (data["sku"], data["merek"], data["kategori"]["jenis"]) == ("BK-ARB-GAYO-200", None, "roasted_bean")
    assert (data["stok"], data["total_stok"], data["total_nilai"], data["dalam_perjalanan"]) == ([], 0, 0, 0)

@pytest.mark.parametrize("jenis, changes, errors", [
    (KategoriType.GREEN_BEAN, {"satuan": "pack", "jenis_kopi": None}, {
        "satuan": "Green bean memakai satuan kg",
        "berat_gram": "Hanya untuk roasted bean",
        "tingkat_sangrai": "Hanya untuk roasted bean",
        "jenis_kopi": "Wajib diisi untuk green bean dan roasted bean",
    }),
    (KategoriType.ROASTED_BEAN, {"satuan": "kg", "berat_gram": None, "jenis_kopi": ""}, {
        "satuan": "Roasted bean memakai satuan pack",
        "berat_gram": "Wajib diisi untuk roasted bean",
        "jenis_kopi": "Wajib diisi untuk green bean dan roasted bean",
    }),
    (KategoriType.ROASTED_BEAN, {"berat_gram": 300}, {"berat_gram": "Pilih 100, 200, 250, 500 atau 1000 gram"}),
    (KategoriType.PERALATAN, {"satuan": "pcs"}, {
        "berat_gram": "Hanya untuk roasted bean",
        "tingkat_sangrai": "Hanya untuk roasted bean",
        "jenis_kopi": "Hanya untuk green bean dan roasted bean",
    }),
])
def test_category_rules(setup, login_as, jenis, changes, errors):
    response = login_as("admin@example.com").post("/api/produk", json=body(setup, jenis, **changes))
    assert response.status_code == 422 and response.json()["errors"] == errors

def test_valid_green_bean_and_peralatan(setup, login_as):
    client = login_as("admin@example.com")
    green = body(setup, KategoriType.GREEN_BEAN, sku="GB-ARB-GAYO", satuan="kg", berat_gram=None, tingkat_sangrai=None)
    alat = body(setup, KategoriType.PERALATAN, sku="AL-V60-02", satuan="pcs", berat_gram=None,
                tingkat_sangrai=None, jenis_kopi=None)
    assert client.post("/api/produk", json=green).status_code == 201
    assert client.post("/api/produk", json=alat).status_code == 201

def test_stok_field_and_loose_types_rejected(setup, login_as):
    client = login_as("admin@example.com")
    response = client.post("/api/produk", json=body(setup, stok=99, harga_beli="65000", kategori_id=999))
    assert response.status_code == 422
    assert response.json()["errors"] == {"stok": "Field tidak dikenal", "harga_beli": "Harus bilangan bulat"}
    response = client.post("/api/produk", json=body(setup, kategori_id=999))
    assert response.json()["errors"] == {"kategori_id": "Kategori tidak ditemukan"}

def test_duplicate_sku_and_manager_cannot_write(setup, login_as, client):
    admin = login_as("admin@example.com")
    assert admin.post("/api/produk", json=body(setup)).status_code == 201
    response = admin.post("/api/produk", json=body(setup, sku="BK-ARB-GAYO-200 ", nama="Produk Lain"))
    assert response.status_code == 409 and response.json()["errors"] == {"sku": "SKU sudah dipakai produk lain"}
    client.cookies.clear()
    manager = login_as("manager@example.com")
    assert manager.get("/api/produk").status_code == 200
    assert manager.post("/api/produk", json=body(setup, sku="BK-BARU")).status_code == 403

def test_detail_stock_per_lokasi_and_in_transit(db, factory, setup, login_as):
    produk = factory.produk()
    gudang, outlet = setup["gudang"], setup["outlet"]
    factory.add(Stok(lokasi_id=gudang.id, produk_id=produk.id, jumlah=40, stok_minimum=30, rak="A-01"))
    factory.add(Stok(lokasi_id=outlet.id, produk_id=produk.id, jumlah=24, stok_minimum=30))
    factory.add(Pengiriman(
        kode="KR-261028-0001", status=PengirimanStatus.DIKIRIM, lokasi_asal=gudang, lokasi_tujuan=outlet,
        deliveryman=setup["kurir"], kendaraan_jenis=KendaraanType.MOTOR, kendaraan_nomor="D 1234 ABC",
        tanggal_kirim=date(2026, 10, 28), dibuat_oleh=setup["admin"], dikirim_oleh=setup["admin"],
        dikirim_pada=datetime.now(UTC), detail=[PengirimanDetail(produk=produk, jumlah_dikirim=10)],
    ))
    db.commit()
    data = login_as("admin@example.com").get(f"/api/produk/{produk.id}").json()
    assert [(s["lokasi"]["kode"], s["status_stok"], s["nilai"]) for s in data["stok"]] == [
        ("GU-01", "aman", 40 * 65000), ("OT-01", "menipis", 24 * 65000)]
    assert (data["total_stok"], data["total_nilai"], data["dalam_perjalanan"]) == (64, 64 * 65000, 10)
    # manager outlet tetap melihat jumlah semua lokasi, nilai rupiah hanya lokasinya sendiri
    data = login_as("manager@example.com").get(f"/api/produk/{produk.id}").json()
    assert [(s["lokasi"]["kode"], s["jumlah"], s["nilai"], s["rak"]) for s in data["stok"]] == [
        ("GU-01", 40, None, None), ("OT-01", 24, 24 * 65000, None)]
    assert (data["total_stok"], data["total_nilai"]) == (64, None)

def test_list_filters_and_options(db, factory, setup, login_as):
    kategori = setup["kategori"]
    rows = [("GB-ROB-01", "Green Bean Robusta", KategoriType.GREEN_BEAN, ProdukUnit.KG, None, "robusta", 80000, True),
            ("BK-LIB-200", "Liberika Jambi 200 g", KategoriType.ROASTED_BEAN, ProdukUnit.PACK, 200, "liberika", 88000, True),
            ("BK-EXC-200", "Excelsa Lama", KategoriType.ROASTED_BEAN, ProdukUnit.PACK, 200, "excelsa", 85000, False),
            ("AL-V60-02", "Dripper V60", KategoriType.PERALATAN, ProdukUnit.PCS, None, None, 165000, True)]
    produk = {}
    for sku, nama, jenis, satuan, berat, kopi, harga, aktif in rows:
        produk[sku] = factory.add(Produk(sku=sku, nama=nama, kategori=kategori[jenis], satuan=satuan, berat_gram=berat,
                                         jenis_kopi=kopi, harga_jual=harga, aktif=aktif))
    factory.add(Stok(lokasi_id=setup["outlet"].id, produk_id=produk["BK-LIB-200"].id, jumlah=7))
    db.commit()
    client = login_as("manager@example.com")

    def skus(**params):
        return [p["sku"] for p in client.get("/api/produk", params=params).json()["data"]]

    assert skus() == ["AL-V60-02", "GB-ROB-01", "BK-LIB-200"]
    assert skus(jenis="roasted_bean", aktif="semua") == ["BK-EXC-200", "BK-LIB-200"]
    assert skus(jenis_kopi="robusta") == ["GB-ROB-01"]
    assert skus(q="jambi") == ["BK-LIB-200"]
    assert skus(sort="harga_jual", arah="desc") == ["AL-V60-02", "BK-LIB-200", "GB-ROB-01"]
    options = client.get("/api/produk/opsi", params={"lokasi_id": setup["outlet"].id, "jenis": "roasted_bean"}).json()
    assert [(o["sku"], o["jenis"], o["stok"]) for o in options] == [("BK-LIB-200", "roasted_bean", 7)]
    assert all(o["stok"] is None for o in client.get("/api/produk/opsi").json())

def test_delete_unused_and_used_produk(db, factory, setup, login_as):
    produk = factory.produk()
    kosong = factory.add(Produk(sku="AL-KOSONG", nama="Alat Kosong", kategori=setup["kategori"][KategoriType.PERALATAN],
                                satuan=ProdukUnit.PCS))
    factory.add(Stok(lokasi_id=setup["outlet"].id, produk_id=produk.id, jumlah=0))
    db.commit()
    client = login_as("admin@example.com")
    assert client.delete(f"/api/produk/{kosong.id}").status_code == 204
    response = client.delete(f"/api/produk/{produk.id}")
    assert response.status_code == 409
    assert response.json() == {"detail": "Produk masih dipakai 1 catatan stok lokasi. Nonaktifkan saja bila tidak dipakai lagi"}
