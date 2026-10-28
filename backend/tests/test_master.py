from datetime import UTC, datetime, timedelta

import pytest

from app.core.clock import Clock
from app.models import (
    Customer,
    CustomerType,
    Kategori,
    KategoriType,
    Lokasi,
    LokasiType,
    Pembelian,
    Penjualan,
    PenjualanDetail,
    PenjualanStatus,
    Stok,
    Supplier,
    UserRole,
)

LOKASI = {"jenis": "outlet", "kode": "ot-04", "nama": "Outlet Dago", "alamat": "Jl. Dago 1",
          "telepon": "0812-3456 7890", "aktif": True}

@pytest.fixture
def setup(db, factory):
    # gudang utama, satu outlet dengan manager, admin dan deliveryman
    gudang = factory.add(Lokasi(kode="GU-01", nama="Gudang Utama Roastery", jenis=LokasiType.GUDANG_UTAMA))
    outlet = factory.outlet()
    admin = factory.user("admin@example.com")
    manager = factory.user("manager@example.com", UserRole.MANAGER_OUTLET, lokasi=outlet)
    factory.user("kurir@example.com", UserRole.DELIVERYMAN)
    db.commit()
    return {"gudang": gudang, "outlet": outlet, "admin": admin, "manager": manager}

def test_admin_crud_lokasi(setup, login_as):
    client = login_as("admin@example.com")
    created = client.post("/api/lokasi", json=LOKASI)
    assert created.status_code == 201
    data = created.json()
    assert (data["kode"], data["telepon"], data["ringkasan"]) == (
        "OT-04", "081234567890", {"sku_ada": 0, "menipis": 0, "habis": 0, "nilai": 0})
    updated = client.put(f"/api/lokasi/{data['id']}", json=LOKASI | {"nama": "Outlet Dago Atas", "alamat": " "})
    assert updated.status_code == 200 and (updated.json()["nama"], updated.json()["alamat"]) == ("Outlet Dago Atas", None)
    assert client.delete(f"/api/lokasi/{data['id']}").status_code == 204
    response = client.get(f"/api/lokasi/{data['id']}")
    assert (response.status_code, response.json()) == (404, {"detail": "Lokasi tidak ditemukan"})

def test_lokasi_validation_messages(setup, login_as):
    client = login_as("admin@example.com")
    body = LOKASI | {"kode": "GC-04", "telepon": "12345", "role": "x"}
    assert client.post("/api/lokasi", json=body).json()["errors"] == {
        "kode": "Kode outlet diawali OT-",
        "telepon": "Format telepon seperti 081234567890 atau +6281234567890",
        "role": "Field tidak dikenal",
    }

@pytest.mark.parametrize("body, field, message", [
    (LOKASI | {"kode": "OT-01"}, "kode", "Kode lokasi sudah dipakai"),
    (LOKASI | {"nama": "OUTLET PUSAT KOTA"}, "nama", "Nama lokasi sudah dipakai"),
    (LOKASI | {"jenis": "gudang_utama", "kode": "GU-02"}, "jenis", "Gudang utama sudah ada"),
])
def test_lokasi_duplicates_409(setup, login_as, body, field, message):
    response = login_as("admin@example.com").post("/api/lokasi", json=body)
    assert response.status_code == 409 and response.json()["errors"] == {field: message}

def test_lokasi_state_rules(setup, login_as):
    client = login_as("admin@example.com")
    gudang = setup["gudang"]
    body = {"jenis": "gudang_utama", "kode": "GU-01", "nama": gudang.nama, "aktif": False}
    response = client.put(f"/api/lokasi/{gudang.id}", json=body)
    assert response.status_code == 409 and response.json()["errors"] == {"aktif": "Gudang utama tidak bisa dinonaktifkan"}
    outlet = setup["outlet"]
    body = {"jenis": "gudang_cabang", "kode": "GC-01", "nama": outlet.nama}
    response = client.put(f"/api/lokasi/{outlet.id}", json=body)
    assert response.status_code == 409 and "sudah punya riwayat" in response.json()["detail"]

def test_lokasi_in_use_cannot_be_deleted(setup, login_as):
    response = login_as("admin@example.com").delete(f"/api/lokasi/{setup['outlet'].id}")
    assert response.status_code == 409
    assert response.json() == {"detail": "Lokasi masih dipakai 1 user. Nonaktifkan saja bila tidak dipakai lagi"}

def test_lokasi_summary_and_active_filter(db, factory, setup, login_as):
    produk = factory.produk()
    outlet = setup["outlet"]
    factory.add(Stok(lokasi_id=outlet.id, produk_id=produk.id, jumlah=5, stok_minimum=10))
    factory.add(Lokasi(kode="OT-09", nama="Outlet Tutup", jenis=LokasiType.OUTLET, aktif=False))
    db.commit()
    client = login_as("manager@example.com")
    rows = {row["kode"]: row for row in client.get("/api/lokasi").json()}
    assert rows["OT-01"]["ringkasan"] == {"sku_ada": 1, "menipis": 1, "habis": 0, "nilai": 5 * 65000}
    assert "OT-09" in rows
    assert [row["kode"] for row in client.get("/api/lokasi", params={"aktif": "true"}).json()] == ["GU-01", "OT-01"]

def test_lokasi_access_by_role(setup, login_as, client):
    assert client.get("/api/lokasi").status_code == 401
    manager = login_as("manager@example.com")
    assert manager.get("/api/lokasi").status_code == 200
    response = manager.post("/api/lokasi", json=LOKASI)
    assert (response.status_code, response.json()) == (403, {"detail": "Fitur ini khusus admin"})
    client.cookies.clear()
    assert login_as("kurir@example.com").get("/api/lokasi").status_code == 403

def test_kategori_counts_and_rules(db, factory, setup, login_as):
    produk = factory.produk()
    kosong = factory.add(Kategori(nama="Grinder", jenis=KategoriType.PERALATAN))
    db.commit()
    client = login_as("admin@example.com")
    counts = {row["nama"]: row["jumlah_produk"] for row in client.get("/api/kategori").json()}
    assert counts == {"Arabika Single Origin": 1, "Grinder": 0}
    kategori_id = produk.kategori_id
    response = client.put(f"/api/kategori/{kategori_id}", json={"nama": "Arabika Single Origin", "jenis": "peralatan"})
    assert response.status_code == 409 and "sudah berisi produk" in response.json()["errors"]["jenis"]
    response = client.delete(f"/api/kategori/{kategori_id}")
    assert (response.status_code, response.json()) == (409, {"detail": "Kategori masih dipakai 1 produk"})
    response = client.post("/api/kategori", json={"nama": "grinder", "jenis": "peralatan"})
    assert response.status_code == 409 and response.json()["errors"] == {"nama": "Nama kategori sudah dipakai"}
    assert client.delete(f"/api/kategori/{kosong.id}").status_code == 204

def test_supplier_search_pagination_and_sort(db, factory, setup, login_as):
    for i in range(12):
        factory.add(Supplier(nama=f"Supplier {i:02d}", kontak="Bagian 100%" if i == 3 else None, aktif=i != 5))
    db.commit()
    client = login_as("admin@example.com")
    page = client.get("/api/supplier", params={"per_page": 5, "page": 3}).json()
    assert page["meta"] == {"page": 3, "per_page": 5, "total": 12, "total_pages": 3} and len(page["data"]) == 2
    # tanda % dicari sebagai teks biasa, bukan wildcard
    assert [s["nama"] for s in client.get("/api/supplier", params={"q": "100%"}).json()["data"]] == ["Supplier 03"]
    assert client.get("/api/supplier", params={"aktif": "false"}).json()["meta"]["total"] == 1
    first = client.get("/api/supplier", params={"sort": "nama", "arah": "desc"}).json()["data"][0]
    assert first["nama"] == "Supplier 11"
    options = client.get("/api/supplier/opsi").json()
    assert len(options) == 11 and set(options[0]) == {"id", "nama"}
    assert client.get("/api/supplier", params={"sort": "harga"}).json()["errors"] == {"sort": "Pilihan tidak valid"}

def test_supplier_used_by_pembelian_cannot_be_deleted(db, factory, setup, login_as):
    supplier = factory.add(Supplier(nama="CV Biji Hijau Nusantara"))
    factory.add(Pembelian(kode="PO-261028-0001", supplier=supplier, lokasi_id=setup["gudang"].id,
                          dibuat_oleh_id=setup["admin"].id))
    db.commit()
    response = login_as("admin@example.com").delete(f"/api/supplier/{supplier.id}")
    assert response.status_code == 409 and response.json()["detail"].startswith("Supplier masih dipakai 1 pembelian")

def test_manager_manages_customer_but_cannot_delete(setup, login_as):
    client = login_as("manager@example.com")
    body = {"nama": "Kafe Teras", "jenis": "kafe", "email": "Halo@Teras.Example", "telepon": "+62 812 3456 7890"}
    created = client.post("/api/customer", json=body)
    assert created.status_code == 201
    data = created.json()
    assert (data["email"], data["telepon"]) == ("halo@teras.example", "+6281234567890")
    updated = client.put(f"/api/customer/{data['id']}", json=body | {"jenis": "reseller", "aktif": False})
    assert updated.status_code == 200 and (updated.json()["jenis"], updated.json()["aktif"]) == ("reseller", False)
    assert client.delete(f"/api/customer/{data['id']}").status_code == 403
    client.cookies.clear()
    assert login_as("admin@example.com").delete(f"/api/customer/{data['id']}").status_code == 204

def test_customer_total_30_days_and_usage(db, factory, setup, login_as):
    customer = factory.add(Customer(nama="Kafe Senja", jenis=CustomerType.KAFE))
    produk = factory.produk()
    today = Clock.today()

    def penjualan(nomor, tanggal, status):
        posted = status == PenjualanStatus.DIPOSTING
        factory.add(Penjualan(
            kode=f"PJ-261028-{nomor:04d}", tanggal=tanggal, lokasi=setup["outlet"], customer=customer,
            status=status, dibuat_oleh=setup["manager"],
            diposting_oleh=setup["manager"] if posted else None, diposting_pada=datetime.now(UTC) if posted else None,
            detail=[PenjualanDetail(produk=produk, jumlah=2, harga_satuan=50000)],
        ))

    penjualan(1, today, PenjualanStatus.DIPOSTING)
    penjualan(2, today - timedelta(days=40), PenjualanStatus.DIPOSTING)
    penjualan(3, today, PenjualanStatus.DRAF)
    db.commit()
    client = login_as("admin@example.com")
    assert client.get(f"/api/customer/{customer.id}").json()["total_pembelian_30_hari"] == 100000
    response = client.delete(f"/api/customer/{customer.id}")
    assert response.status_code == 409 and response.json()["detail"].startswith("Customer masih dipakai 3 penjualan")

def test_customer_filters_and_options(db, factory, setup, login_as):
    factory.add(Customer(nama="Kafe Senja", jenis=CustomerType.KAFE))
    factory.add(Customer(nama="Toko Oleh-oleh", jenis=CustomerType.RESELLER))
    factory.add(Customer(nama="Kafe Tutup", jenis=CustomerType.KAFE, aktif=False))
    db.commit()
    client = login_as("manager@example.com")
    kafe = client.get("/api/customer", params={"jenis": "kafe"}).json()
    assert [c["nama"] for c in kafe["data"]] == ["Kafe Senja", "Kafe Tutup"]
    options = client.get("/api/customer/opsi").json()
    assert [(c["nama"], c["jenis"]) for c in options] == [("Kafe Senja", "kafe"), ("Toko Oleh-oleh", "reseller")]
    assert set(options[0]) == {"id", "nama", "jenis"}
