import pytest
from sqlalchemy import select

from app.core.clock import Clock
from app.models import (
    CoffeeType,
    Customer,
    CustomerType,
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
    kategori_biji = factory.add(
        Kategori(nama="Single Origin", jenis=KategoriType.ROASTED_BEAN)
    )
    kategori_alat = factory.add(
        Kategori(nama="Alat Seduh", jenis=KategoriType.PERALATAN)
    )
    kategori_bahan = factory.add(
        Kategori(nama="Bahan Bar", jenis=KategoriType.HABIS_PAKAI)
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
    tanpa_harga_jual = factory.add(
        Produk(
            sku="HP-CUP-01",
            nama="Paper Cup Internal",
            kategori=kategori_bahan,
            satuan=ProdukUnit.PACK,
            harga_beli=25000,
            harga_jual=0,
        )
    )
    customer = factory.add(
        Customer(
            nama="Kafe Senja",
            jenis=CustomerType.KAFE,
            telepon="081298765432",
            alamat="Jl. Contoh No. 10",
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
        "biji": biji,
        "alat": alat,
        "tanpa_harga_jual": tanpa_harga_jual,
        "customer": customer,
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
        "tanggal": Clock.today().isoformat(),
        "catatan": "Pembelian eceran",
        "items": [{"produk_id": setup["biji"].id, "jumlah": 2}],
    }
    return base | changes


def balance(db, lokasi_id: int, produk_id: int) -> int | None:
    return db.scalar(
        select(Stok.jumlah).where(
            Stok.lokasi_id == lokasi_id, Stok.produk_id == produk_id
        )
    )


def test_outlet_sale_without_customer_and_default_harga_jual(setup, login_as):
    client = login_as("outlet@example.com")
    created = client.post(
        "/api/penjualan",
        json=payload(
            setup,
            items=[
                {"produk_id": setup["biji"].id, "jumlah": 2},
                {
                    "produk_id": setup["alat"].id,
                    "jumlah": 1,
                    "harga_satuan": 150000,
                },
            ],
        ),
    )
    assert created.status_code == 201
    data = created.json()
    assert data["kode"].startswith("PJ-") and data["status"] == "draf"
    assert data["customer"] is None and data["nama_customer"] == "Umum"
    assert [(row["produk"]["sku"], row["harga_satuan"], row["subtotal"]) for row in data["items"]] == [
        ("BK-ARB-GAYO-200", 95000, 190000),
        ("AL-V60-02", 150000, 150000),
    ]
    assert data["total"] == 340000

    updated = client.put(
        f"/api/penjualan/{data['id']}",
        json=payload(
            setup,
            customer_id=setup["customer"].id,
            items=[{"produk_id": setup["biji"].id, "jumlah": 3}],
        ),
    )
    assert updated.status_code == 200
    assert updated.json()["nama_customer"] == "Kafe Senja"
    assert updated.json()["total"] == 3 * 95000

    assert client.delete(f"/api/penjualan/{data['id']}").status_code == 204
    assert client.get(f"/api/penjualan/{data['id']}").status_code == 404


def test_posting_reduces_stock_and_records_mutasi_penjualan(
    db, factory, setup, login_as
):
    gudang, biji, alat = setup["gudang"], setup["biji"], setup["alat"]
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=30))
    factory.add(Stok(lokasi_id=gudang.id, produk_id=alat.id, jumlah=5))
    db.commit()

    client = login_as("gudang@example.com")
    pj = client.post(
        "/api/penjualan",
        json=payload(
            setup,
            customer_id=setup["customer"].id,
            catatan="Harga reseller 10 pack",
            items=[
                {"produk_id": biji.id, "jumlah": 10, "harga_satuan": 85000},
                {"produk_id": alat.id, "jumlah": 2},
            ],
        ),
    ).json()

    posted = client.post(f"/api/penjualan/{pj['id']}/posting")
    assert posted.status_code == 200
    post_data = posted.json()
    assert post_data["status"] == "diposting" and post_data["diposting_pada"] is not None
    assert post_data["total"] == 10 * 85000 + 2 * 165000
    db.expire_all()
    assert (balance(db, gudang.id, biji.id), balance(db, gudang.id, alat.id)) == (
        20,
        3,
    )
    mutasi = db.execute(
        select(StokMutasi.produk_id, StokMutasi.jenis, StokMutasi.perubahan)
        .where(StokMutasi.penjualan_id == pj["id"])
        .order_by(StokMutasi.id)
    ).all()
    assert mutasi == [(biji.id, "penjualan", -10), (alat.id, "penjualan", -2)]

    # sesudah diposting tidak bisa diubah, dihapus atau diposting ulang
    for res in (
        client.put(
            f"/api/penjualan/{pj['id']}",
            json=payload(setup, customer_id=setup["customer"].id),
        ),
        client.delete(f"/api/penjualan/{pj['id']}"),
        client.post(f"/api/penjualan/{pj['id']}/posting"),
    ):
        assert (res.status_code, res.json()) == (
            409,
            {"detail": "Penjualan sudah diposting"},
        )


def test_posting_insufficient_stock_rolls_back(db, factory, setup, login_as):
    outlet, biji, alat = setup["outlet"], setup["biji"], setup["alat"]
    factory.add(Stok(lokasi_id=outlet.id, produk_id=biji.id, jumlah=5))
    factory.add(Stok(lokasi_id=outlet.id, produk_id=alat.id, jumlah=1))
    db.commit()

    client = login_as("outlet@example.com")
    pj = client.post(
        "/api/penjualan",
        json=payload(
            setup,
            items=[
                {"produk_id": biji.id, "jumlah": 3},
                {"produk_id": alat.id, "jumlah": 2},
            ],
        ),
    ).json()
    res = client.post(f"/api/penjualan/{pj['id']}/posting")
    assert res.status_code == 409
    assert res.json()["errors"] == {
        "items.1.jumlah": "Stok AL-V60-02 di Outlet Pusat Kota tersisa 1 pcs"
    }
    db.expire_all()
    assert (balance(db, outlet.id, biji.id), balance(db, outlet.id, alat.id)) == (5, 1)
    assert client.get(f"/api/penjualan/{pj['id']}").json()["status"] == "draf"


def test_validation_rules_warehouse_customer_and_zero_price(
    db, factory, setup, login_as, client
):
    customer_off = factory.add(
        Customer(nama="Kafe Tutup", jenis=CustomerType.KAFE, aktif=False)
    )
    db.commit()

    # penjualan dari gudang utama dan gudang cabang wajib memilih customer (BR-26)
    for email in ("gudang@example.com", "cabang@example.com"):
        wh_client = login_as(email)
        tanpa_cust = wh_client.post("/api/penjualan", json=payload(setup))
        assert tanpa_cust.status_code == 422 and tanpa_cust.json()["errors"] == {
            "customer_id": "Penjualan dari gudang wajib memilih customer"
        }
        client.cookies.clear()

    outlet_client = login_as("outlet@example.com")
    # customer nonaktif ditolak 422
    nonaktif = outlet_client.post(
        "/api/penjualan", json=payload(setup, customer_id=customer_off.id)
    )
    assert nonaktif.status_code == 422 and nonaktif.json()["errors"] == {
        "customer_id": "Customer sudah tidak aktif"
    }

    # harga_satuan = 0 ditolak schema 422
    harga_nol = outlet_client.post(
        "/api/penjualan",
        json=payload(
            setup,
            items=[{"produk_id": setup["biji"].id, "jumlah": 1, "harga_satuan": 0}],
        ),
    )
    assert harga_nol.status_code == 422 and harga_nol.json()["errors"] == {
        "items.0.harga_satuan": "Minimal 1"
    }

    # produk dengan harga_jual = 0 tanpa harga_satuan ditolak service 422
    standar_nol = outlet_client.post(
        "/api/penjualan",
        json=payload(
            setup,
            items=[{"produk_id": setup["tanpa_harga_jual"].id, "jumlah": 1}],
        ),
    )
    assert standar_nol.status_code == 422 and standar_nol.json()["errors"] == {
        "items.0.harga_satuan": "Produk belum memiliki harga jual standar, isi harga satuan"
    }


def test_location_scope_and_sorting_by_total(setup, login_as, client):
    assert login_as("kurir@example.com").get("/api/penjualan").status_code == 403
    client.cookies.clear()

    gudang_client = login_as("gudang@example.com")
    pj_gudang = gudang_client.post(
        "/api/penjualan",
        json=payload(
            setup,
            customer_id=setup["customer"].id,
            items=[{"produk_id": setup["biji"].id, "jumlah": 10, "harga_satuan": 85000}],
        ),
    ).json()
    client.cookies.clear()

    outlet_client = login_as("outlet@example.com")
    pj_outlet = outlet_client.post("/api/penjualan", json=payload(setup)).json()
    assert [row["id"] for row in outlet_client.get("/api/penjualan").json()["data"]] == [
        pj_outlet["id"]
    ]
    for res in (
        outlet_client.get(f"/api/penjualan/{pj_gudang['id']}"),
        outlet_client.put(f"/api/penjualan/{pj_gudang['id']}", json=payload(setup)),
        outlet_client.delete(f"/api/penjualan/{pj_gudang['id']}"),
        outlet_client.post(f"/api/penjualan/{pj_gudang['id']}/posting"),
        outlet_client.post(
            "/api/penjualan", json=payload(setup, lokasi_id=setup["gudang"].id)
        ),
    ):
        assert (res.status_code, res.json()) == (
            404,
            {"detail": "Penjualan tidak ditemukan"},
        )

    client.cookies.clear()
    admin = login_as("admin@example.com")
    asc = admin.get("/api/penjualan", params={"sort": "total", "arah": "asc"}).json()
    desc = admin.get("/api/penjualan", params={"sort": "total", "arah": "desc"}).json()
    assert [row["id"] for row in asc["data"]] == [pj_outlet["id"], pj_gudang["id"]]
    assert [row["id"] for row in desc["data"]] == [pj_gudang["id"], pj_outlet["id"]]
