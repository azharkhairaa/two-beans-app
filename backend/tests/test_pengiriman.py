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
    Pengiriman,
    PengirimanDetail,
    PengirimanStatus,
    Permintaan,
    PermintaanDetail,
    PermintaanStatus,
    Produk,
    ProdukUnit,
    Stok,
    StokMutasi,
    UserRole,
    UserStatus,
)

@pytest.fixture
def setup(db, factory):
    kategori_biji = factory.add(
        Kategori(nama="Single Origin", jenis=KategoriType.ROASTED_BEAN)
    )
    kategori_alat = factory.add(
        Kategori(nama="Alat Seduh", jenis=KategoriType.PERALATAN)
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
    gudang = factory.add(
        Lokasi(
            kode="GU-01",
            nama="Gudang Utama Roastery",
            jenis=LokasiType.GUDANG_UTAMA,
            alamat="Jl. Roastery No. 1",
        )
    )
    cabang = factory.add(
        Lokasi(
            kode="GC-01",
            nama="Gudang Cabang Selatan",
            jenis=LokasiType.GUDANG_CABANG,
            alamat="Jl. Cabang No. 2",
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
    kurir1 = factory.user("kurir1@example.com", UserRole.DELIVERYMAN)
    kurir2 = factory.user("kurir2@example.com", UserRole.DELIVERYMAN)
    db.commit()
    return {
        "biji": biji,
        "alat": alat,
        "gudang": gudang,
        "cabang": cabang,
        "outlet": outlet,
        "admin": admin,
        "manager_gudang": manager_gudang,
        "manager_cabang": manager_cabang,
        "manager_outlet": manager_outlet,
        "kurir1": kurir1,
        "kurir2": kurir2,
    }

def payload(setup, **changes):
    base = {
        "lokasi_tujuan_id": setup["outlet"].id,
        "tanggal_kirim": Clock.today().isoformat(),
        "catatan": "Kirim pagi",
        "items": [{"produk_id": setup["biji"].id, "jumlah_dikirim": 10}],
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
    created = client.post("/api/pengiriman", json=payload(setup))
    assert created.status_code == 201
    data = created.json()
    assert data["kode"].startswith("KR-") and data["status"] == "draf"
    assert (data["lokasi_asal"]["kode"], data["lokasi_tujuan"]["kode"]) == (
        "GU-01",
        "OT-01",
    )
    assert (data["jumlah_item"], data["nilai_dikirim"]) == (1, 10 * 65000)

    updated = client.put(
        f"/api/pengiriman/{data['id']}",
        json=payload(
            setup,
            deliveryman_id=setup["kurir1"].id,
            kendaraan_jenis="mobil_box",
            kendaraan_nomor="  d 1234   abc ",
            items=[
                {"produk_id": setup["biji"].id, "jumlah_dikirim": 12},
                {"produk_id": setup["alat"].id, "jumlah_dikirim": 2},
            ],
        ),
    )
    assert updated.status_code == 200
    detail = updated.json()
    assert detail["kendaraan_nomor"] == "D 1234 ABC"
    assert detail["deliveryman"]["id"] == setup["kurir1"].id
    assert detail["nilai_dikirim"] == 12 * 65000 + 2 * 120000
    assert [(row["produk"]["sku"], row["jumlah_dikirim"]) for row in detail["items"]] == [
        ("BK-ARB-GAYO-200", 12),
        ("AL-V60-02", 2),
    ]

    assert client.delete(f"/api/pengiriman/{data['id']}").status_code == 204
    assert client.get(f"/api/pengiriman/{data['id']}").status_code == 404

def test_delete_draft_linked_to_permintaan_cancels_and_reopens_permintaan(
    db, factory, setup, login_as
):
    permintaan = factory.add(
        Permintaan(
            kode="PM-261028-0001",
            status=PermintaanStatus.DISETUJUI,
            lokasi_peminta_id=setup["outlet"].id,
            lokasi_sumber_id=setup["gudang"].id,
            tanggal_butuh=Clock.today(),
            diajukan_oleh_id=setup["manager_outlet"].id,
            diproses_oleh_id=setup["manager_gudang"].id,
            diproses_pada=Clock.now(),
            detail=[
                PermintaanDetail(
                    produk_id=setup["biji"].id,
                    jumlah_diminta=10,
                    jumlah_disetujui=8,
                )
            ],
        )
    )
    pengiriman = factory.add(
        Pengiriman(
            kode="KR-261028-0001",
            status=PengirimanStatus.DRAF,
            lokasi_asal_id=setup["gudang"].id,
            lokasi_tujuan_id=setup["outlet"].id,
            permintaan_id=permintaan.id,
            tanggal_kirim=Clock.today(),
            dibuat_oleh_id=setup["manager_gudang"].id,
            detail=[
                PengirimanDetail(produk_id=setup["biji"].id, jumlah_dikirim=8)
            ],
        )
    )
    db.commit()

    client = login_as("gudang@example.com")
    assert client.delete(f"/api/pengiriman/{pengiriman.id}").status_code == 204
    db.expire_all()
    refreshed_kr = db.get(Pengiriman, pengiriman.id)
    refreshed_pm = db.get(Permintaan, permintaan.id)
    assert refreshed_kr.status == PengirimanStatus.DIBATALKAN
    assert refreshed_pm.status == PermintaanStatus.DIAJUKAN
    assert refreshed_pm.diproses_oleh_id is None and refreshed_pm.diproses_pada is None
    assert refreshed_pm.detail[0].jumlah_disetujui is None

def test_kirim_and_terima_updates_stock_and_completes_permintaan(
    db, factory, setup, login_as, client
):
    gudang, outlet, biji, alat = (
        setup["gudang"],
        setup["outlet"],
        setup["biji"],
        setup["alat"],
    )
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=30))
    factory.add(Stok(lokasi_id=gudang.id, produk_id=alat.id, jumlah=5))
    permintaan = factory.add(
        Permintaan(
            kode="PM-261028-0002",
            status=PermintaanStatus.DISETUJUI,
            lokasi_peminta_id=outlet.id,
            lokasi_sumber_id=gudang.id,
            tanggal_butuh=Clock.today(),
            diajukan_oleh_id=setup["manager_outlet"].id,
            diproses_oleh_id=setup["manager_gudang"].id,
            diproses_pada=Clock.now(),
            detail=[
                PermintaanDetail(
                    produk_id=biji.id, jumlah_diminta=10, jumlah_disetujui=10
                ),
                PermintaanDetail(
                    produk_id=alat.id, jumlah_diminta=3, jumlah_disetujui=3
                ),
            ],
        )
    )
    pengiriman = factory.add(
        Pengiriman(
            kode="KR-261028-0002",
            status=PengirimanStatus.DRAF,
            lokasi_asal_id=gudang.id,
            lokasi_tujuan_id=outlet.id,
            permintaan_id=permintaan.id,
            tanggal_kirim=Clock.today(),
            dibuat_oleh_id=setup["manager_gudang"].id,
            detail=[
                PengirimanDetail(produk_id=biji.id, jumlah_dikirim=10),
                PengirimanDetail(produk_id=alat.id, jumlah_dikirim=3),
            ],
        )
    )
    db.commit()

    gudang_client = login_as("gudang@example.com")
    sent = gudang_client.post(
        f"/api/pengiriman/{pengiriman.id}/kirim",
        json={
            "deliveryman_id": setup["kurir1"].id,
            "kendaraan_jenis": "mobil_box",
            "kendaraan_nomor": "d 8899 zz",
        },
    )
    assert sent.status_code == 200
    sent_data = sent.json()
    assert sent_data["status"] == "dikirim"
    assert sent_data["kendaraan_nomor"] == "D 8899 ZZ"
    assert sent_data["dikirim_oleh"]["id"] == setup["manager_gudang"].id
    assert sent_data["dikirim_pada"] is not None
    db.expire_all()
    assert (balance(db, gudang.id, biji.id), balance(db, gudang.id, alat.id)) == (20, 2)
    assert balance(db, outlet.id, biji.id) is None

    client.cookies.clear()
    outlet_client = login_as("outlet@example.com")
    received = outlet_client.post(
        f"/api/pengiriman/{pengiriman.id}/terima",
        json={
            "catatan_penerimaan": "Diterima sore hari",
            "items": [
                {
                    "produk_id": biji.id,
                    "jumlah_diterima": 9,
                    "catatan": "1 pack sobek saat bongkar",
                },
                {"produk_id": alat.id, "jumlah_diterima": 3},
            ],
        },
    )
    assert received.status_code == 200
    rec_data = received.json()
    assert rec_data["status"] == "diterima"
    assert rec_data["diterima_oleh"]["id"] == setup["manager_outlet"].id
    assert rec_data["diterima_pada"] is not None
    assert [
        (row["produk"]["sku"], row["jumlah_diterima"], row["selisih"], row["catatan"])
        for row in rec_data["items"]
    ] == [
        ("BK-ARB-GAYO-200", 9, 1, "1 pack sobek saat bongkar"),
        ("AL-V60-02", 3, 0, None),
    ]
    db.expire_all()
    assert (balance(db, outlet.id, biji.id), balance(db, outlet.id, alat.id)) == (9, 3)
    assert db.get(Permintaan, permintaan.id).status == PermintaanStatus.SELESAI
    mutasi = db.execute(
        select(StokMutasi.lokasi_id, StokMutasi.jenis, StokMutasi.perubahan)
        .where(StokMutasi.produk_id == biji.id)
        .order_by(StokMutasi.id)
    ).all()
    assert mutasi == [(gudang.id, "kirim", -10), (outlet.id, "terima", 9)]

def test_kirim_insufficient_stock_rolls_back(db, factory, setup, login_as):
    gudang, biji, alat = setup["gudang"], setup["biji"], setup["alat"]
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=10))
    factory.add(Stok(lokasi_id=gudang.id, produk_id=alat.id, jumlah=1))
    db.commit()

    client = login_as("gudang@example.com")
    draft = client.post(
        "/api/pengiriman",
        json=payload(
            setup,
            deliveryman_id=setup["kurir1"].id,
            kendaraan_jenis="pickup",
            kendaraan_nomor="B 1234 CD",
            items=[
                {"produk_id": biji.id, "jumlah_dikirim": 5},
                {"produk_id": alat.id, "jumlah_dikirim": 3},
            ],
        ),
    ).json()
    res = client.post(f"/api/pengiriman/{draft['id']}/kirim")
    assert res.status_code == 409
    assert res.json()["errors"] == {
        "items.1.jumlah_dikirim": "Stok AL-V60-02 di Gudang Utama Roastery tersisa 1 pcs"
    }
    db.expire_all()
    assert (balance(db, gudang.id, biji.id), balance(db, gudang.id, alat.id)) == (10, 1)
    assert client.get(f"/api/pengiriman/{draft['id']}").json()["status"] == "draf"

def test_validation_rules_for_draft_kirim_and_terima(db, factory, setup, login_as):
    gudang, outlet, biji, alat = (
        setup["gudang"],
        setup["outlet"],
        setup["biji"],
        setup["alat"],
    )
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=20))
    factory.add(Stok(lokasi_id=gudang.id, produk_id=alat.id, jumlah=5))
    kurir_nonaktif = factory.user(
        "kurir.off@example.com", UserRole.DELIVERYMAN, status=UserStatus.NONAKTIF
    )
    db.commit()

    admin = login_as("admin@example.com")
    # admin wajib mengisi lokasi_asal_id dan lokasi_asal harus berupa gudang
    assert admin.post("/api/pengiriman", json=payload(setup)).json()["errors"] == {
        "lokasi_asal_id": "Wajib diisi untuk admin"
    }
    asal_outlet = admin.post(
        "/api/pengiriman",
        json=payload(
            setup, lokasi_asal_id=outlet.id, lokasi_tujuan_id=setup["cabang"].id
        ),
    )
    assert asal_outlet.status_code == 422 and asal_outlet.json()["errors"] == {
        "lokasi_asal_id": "Lokasi asal pengiriman harus berupa gudang"
    }
    # tanggal masa lalu dan pelat nomor salah ditolak schema 422
    schema_salah = admin.post(
        "/api/pengiriman",
        json=payload(
            setup,
            lokasi_asal_id=gudang.id,
            tanggal_kirim=(Clock.today() - timedelta(days=1)).isoformat(),
            kendaraan_nomor="SALAH-123",
        ),
    )
    assert schema_salah.status_code == 422 and schema_salah.json()["errors"] == {
        "tanggal_kirim": "Tanggal tidak boleh sebelum hari ini",
        "kendaraan_nomor": "Format nomor kendaraan seperti D 1234 ABC atau B 9012",
    }
    # tujuan sama dengan asal dan deliveryman nonaktif ditolak service 422
    tujuan_sama = admin.post(
        "/api/pengiriman",
        json=payload(
            setup,
            lokasi_asal_id=gudang.id,
            lokasi_tujuan_id=gudang.id,
            deliveryman_id=kurir_nonaktif.id,
        ),
    )
    assert tujuan_sama.status_code == 422 and tujuan_sama.json()["errors"] == {
        "lokasi_tujuan_id": "Lokasi tujuan harus berbeda dari lokasi asal",
        "deliveryman_id": "Deliveryman sudah tidak aktif",
    }
    # produk ganda di satu pengiriman dijawab 409
    duplikat = admin.post(
        "/api/pengiriman",
        json=payload(
            setup,
            lokasi_asal_id=gudang.id,
            items=[
                {"produk_id": biji.id, "jumlah_dikirim": 2},
                {"produk_id": biji.id, "jumlah_dikirim": 3},
            ],
        ),
    )
    assert duplikat.status_code == 409 and duplikat.json()["errors"] == {
        "items": "Produk tidak boleh ganda dalam satu dokumen"
    }

    # kirim tanpa data pengantaran ditolak 422
    draft = admin.post(
        "/api/pengiriman",
        json=payload(
            setup,
            lokasi_asal_id=gudang.id,
            items=[
                {"produk_id": biji.id, "jumlah_dikirim": 5},
                {"produk_id": alat.id, "jumlah_dikirim": 2},
            ],
        ),
    ).json()
    kirim_kosong = admin.post(f"/api/pengiriman/{draft['id']}/kirim")
    assert kirim_kosong.status_code == 422 and kirim_kosong.json()["errors"] == {
        "deliveryman_id": "Wajib diisi saat mengirim",
        "kendaraan_jenis": "Wajib diisi saat mengirim",
        "kendaraan_nomor": "Wajib diisi saat mengirim",
    }

    # kirim valid lalu uji validasi terima
    assert (
        admin.post(
            f"/api/pengiriman/{draft['id']}/kirim",
            json={
                "deliveryman_id": setup["kurir1"].id,
                "kendaraan_jenis": "van",
                "kendaraan_nomor": "D 1111 AA",
            },
        ).status_code
        == 200
    )

    terima_kurang_item = admin.post(
        f"/api/pengiriman/{draft['id']}/terima",
        json={"items": [{"produk_id": biji.id, "jumlah_diterima": 4}]},
    )
    assert terima_kurang_item.status_code == 422
    assert terima_kurang_item.json()["errors"] == {
        "items.0.catatan": "Catatan wajib diisi bila jumlah diterima kurang dari jumlah dikirim",
        "items": "Semua produk di pengiriman wajib dikonfirmasi",
    }

    terima_lebih = admin.post(
        f"/api/pengiriman/{draft['id']}/terima",
        json={
            "items": [
                {"produk_id": biji.id, "jumlah_diterima": 6},
                {"produk_id": alat.id, "jumlah_diterima": 2},
            ]
        },
    )
    assert terima_lebih.status_code == 422 and terima_lebih.json()["errors"] == {
        "items.0.jumlah_diterima": "Maksimal sebesar jumlah dikirim (5)"
    }

def test_role_and_location_access_and_status_transitions(
    db, factory, setup, login_as, client
):
    gudang, cabang, outlet, biji = (
        setup["gudang"],
        setup["cabang"],
        setup["outlet"],
        setup["biji"],
    )
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=30))
    db.commit()

    # manager outlet tidak boleh membuat pengiriman
    outlet_client = login_as("outlet@example.com")
    assert outlet_client.post("/api/pengiriman", json=payload(setup)).status_code == 403
    client.cookies.clear()

    # gudang utama membuat dua pengiriman: kurir1 ke outlet dan kurir2 ke cabang
    gudang_client = login_as("gudang@example.com")
    kr_outlet = gudang_client.post(
        "/api/pengiriman",
        json=payload(
            setup,
            lokasi_tujuan_id=outlet.id,
            deliveryman_id=setup["kurir1"].id,
            kendaraan_jenis="motor",
            kendaraan_nomor="D 2222 BB",
        ),
    ).json()
    kr_cabang = gudang_client.post(
        "/api/pengiriman",
        json=payload(
            setup,
            lokasi_tujuan_id=cabang.id,
            deliveryman_id=setup["kurir2"].id,
            kendaraan_jenis="pickup",
            kendaraan_nomor="D 3333 CC",
        ),
    ).json()

    # manager lokasi tujuan bisa membaca draf tetapi tidak bisa mengubah/menghapus/mengirim (403)
    # dan belum bisa menerima sebelum dikirim (409)
    client.cookies.clear()
    outlet_client = login_as("outlet@example.com")
    assert outlet_client.get(f"/api/pengiriman/{kr_outlet['id']}").status_code == 200
    assert (
        outlet_client.put(
            f"/api/pengiriman/{kr_outlet['id']}", json=payload(setup)
        ).status_code
        == 403
    )
    assert (
        outlet_client.delete(f"/api/pengiriman/{kr_outlet['id']}").status_code == 403
    )
    assert (
        outlet_client.post(f"/api/pengiriman/{kr_outlet['id']}/kirim").status_code
        == 403
    )
    belum_dikirim = outlet_client.post(
        f"/api/pengiriman/{kr_outlet['id']}/terima",
        json={"items": [{"produk_id": biji.id, "jumlah_diterima": 10}]},
    )
    assert (belum_dikirim.status_code, belum_dikirim.json()) == (
        409,
        {"detail": "Pengiriman masih berstatus draf"},
    )
    # pengiriman ke cabang tidak terlihat oleh manager outlet (404)
    assert outlet_client.get(f"/api/pengiriman/{kr_cabang['id']}").status_code == 404
    assert [row["id"] for row in outlet_client.get("/api/pengiriman").json()["data"]] == [
        kr_outlet["id"]
    ]

    # gudang asal mengirim kr_outlet tetapi tidak boleh ikut menerimanya (403)
    client.cookies.clear()
    gudang_client = login_as("gudang@example.com")
    assert (
        gudang_client.post(f"/api/pengiriman/{kr_outlet['id']}/kirim").status_code
        == 200
    )
    assert (
        gudang_client.post(
            f"/api/pengiriman/{kr_outlet['id']}/terima",
            json={"items": [{"produk_id": biji.id, "jumlah_diterima": 10}]},
        ).status_code
        == 403
    )
    # sesudah dikirim tidak bisa diubah, dihapus atau dikirim ulang (409)
    for res in (
        gudang_client.put(f"/api/pengiriman/{kr_outlet['id']}", json=payload(setup)),
        gudang_client.delete(f"/api/pengiriman/{kr_outlet['id']}"),
        gudang_client.post(f"/api/pengiriman/{kr_outlet['id']}/kirim"),
    ):
        assert (res.status_code, res.json()) == (
            409,
            {"detail": "Pengiriman sudah dikirim"},
        )

    # deliveryman hanya melihat pengiriman tugasnya dan tidak punya aksi tulis
    client.cookies.clear()
    kurir1_client = login_as("kurir1@example.com")
    daftar_kurir = kurir1_client.get("/api/pengiriman").json()
    assert [row["id"] for row in daftar_kurir["data"]] == [kr_outlet["id"]]
    detail_kurir = kurir1_client.get(f"/api/pengiriman/{kr_outlet['id']}")
    assert detail_kurir.status_code == 200
    # harga beli dan nilai barang tidak dikirim ke deliveryman
    assert daftar_kurir["data"][0]["nilai_dikirim"] is None
    assert detail_kurir.json()["nilai_dikirim"] is None
    assert {row["produk"]["harga_beli"] for row in detail_kurir.json()["items"]} == {None}
    assert "nilai_dikirim" not in kurir1_client.get("/api/dashboard").json()["pengiriman_aktif"][0]
    assert kurir1_client.get(f"/api/pengiriman/{kr_cabang['id']}").status_code == 404
    for res in (
        kurir1_client.post("/api/pengiriman", json=payload(setup)),
        kurir1_client.put(f"/api/pengiriman/{kr_outlet['id']}", json=payload(setup)),
        kurir1_client.delete(f"/api/pengiriman/{kr_outlet['id']}"),
        kurir1_client.post(f"/api/pengiriman/{kr_outlet['id']}/kirim"),
        kurir1_client.post(
            f"/api/pengiriman/{kr_outlet['id']}/terima",
            json={"items": [{"produk_id": biji.id, "jumlah_diterima": 10}]},
        ),
    ):
        assert res.status_code == 403
