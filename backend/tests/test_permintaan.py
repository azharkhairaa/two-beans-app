from datetime import datetime, timedelta

import pytest
from sqlalchemy import event

from app.core.clock import Clock
from app.core.database import database
from app.models import (
    CoffeeType,
    Kategori,
    KategoriType,
    Lokasi,
    LokasiType,
    Produk,
    ProdukUnit,
    Stok,
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
    kosong = factory.add(
        Produk(
            sku="AL-KETTLE-01",
            nama="Gooseneck Kettle",
            kategori=kategori_alat,
            satuan=ProdukUnit.PCS,
            harga_beli=250000,
            harga_jual=340000,
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
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=25))
    factory.add(Stok(lokasi_id=gudang.id, produk_id=alat.id, jumlah=4))

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
        "kosong": kosong,
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
        "tanggal_butuh": (Clock.today() + timedelta(days=2)).isoformat(),
        "catatan": "Stok akhir pekan",
        "items": [{"produk_id": setup["biji"].id, "jumlah_diminta": 10}],
    }
    return base | changes

def test_create_update_and_batal_permintaan(setup, login_as):
    client = login_as("outlet@example.com")
    created = client.post("/api/permintaan", json=payload(setup))
    assert created.status_code == 201
    data = created.json()
    assert data["kode"].startswith("PM-") and data["status"] == "diajukan"
    assert (data["lokasi_peminta"]["kode"], data["lokasi_sumber"]["kode"]) == (
        "OT-01",
        "GU-01",
    )
    assert data["items"][0]["produk"]["stok_sumber"] == 25

    updated = client.put(
        f"/api/permintaan/{data['id']}",
        json=payload(
            setup,
            catatan="Tambahan dripper",
            items=[
                {"produk_id": setup["biji"].id, "jumlah_diminta": 12},
                {"produk_id": setup["alat"].id, "jumlah_diminta": 3},
            ],
        ),
    )
    assert updated.status_code == 200
    detail = updated.json()
    assert detail["catatan"] == "Tambahan dripper" and detail["jumlah_item"] == 2

    cancelled = client.post(f"/api/permintaan/{data['id']}/batal")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "dibatalkan"
    for res in (
        client.put(f"/api/permintaan/{data['id']}", json=payload(setup)),
        client.post(f"/api/permintaan/{data['id']}/batal"),
    ):
        assert (res.status_code, res.json()) == (
            409,
            {"detail": "Permintaan sudah dibatalkan"},
        )

def test_setujui_partial_creates_draft_pengiriman_and_full_cycle_to_selesai(
    setup, login_as, client
):
    outlet_client = login_as("outlet@example.com")
    pm = outlet_client.post(
        "/api/permintaan",
        json=payload(
            setup,
            items=[
                {"produk_id": setup["biji"].id, "jumlah_diminta": 10},
                {"produk_id": setup["alat"].id, "jumlah_diminta": 4},
            ],
        ),
    ).json()

    client.cookies.clear()
    gudang_client = login_as("gudang@example.com")
    approved = gudang_client.post(
        f"/api/permintaan/{pm['id']}/setujui",
        json={
            "tanggal_kirim": Clock.today().isoformat(),
            "items": [
                {"produk_id": setup["biji"].id, "jumlah_disetujui": 8},
                {"produk_id": setup["alat"].id, "jumlah_disetujui": 0},
            ],
        },
    )
    assert approved.status_code == 200
    pm_data = approved.json()
    assert pm_data["status"] == "disetujui"
    assert pm_data["diproses_oleh"]["id"] == setup["manager_gudang"].id
    assert pm_data["pengiriman"]["kode"].startswith("KR-")
    assert pm_data["pengiriman"]["status"] == "draf"

    kr_id = pm_data["pengiriman"]["id"]
    kr_detail = gudang_client.get(f"/api/pengiriman/{kr_id}").json()
    # baris yang disetujui 0 tidak masuk ke draf pengiriman
    assert [(row["produk"]["sku"], row["jumlah_dikirim"]) for row in kr_detail["items"]] == [
        ("BK-ARB-GAYO-200", 8)
    ]

    assert (
        gudang_client.post(
            f"/api/pengiriman/{kr_id}/kirim",
            json={
                "deliveryman_id": setup["kurir"].id,
                "kendaraan_jenis": "mobil_box",
                "kendaraan_nomor": "D 1234 ABC",
            },
        ).status_code
        == 200
    )

    client.cookies.clear()
    outlet_client = login_as("outlet@example.com")
    assert (
        outlet_client.post(
            f"/api/pengiriman/{kr_id}/terima",
            json={"items": [{"produk_id": setup["biji"].id, "jumlah_diterima": 8}]},
        ).status_code
        == 200
    )

    final_pm = outlet_client.get(f"/api/permintaan/{pm['id']}").json()
    assert final_pm["status"] == "selesai"
    assert final_pm["pengiriman"]["status"] == "diterima"

def test_cancel_draft_pengiriman_reopens_permintaan_for_reapproval(
    setup, login_as, client
):
    outlet_client = login_as("outlet@example.com")
    pm = outlet_client.post("/api/permintaan", json=payload(setup)).json()

    client.cookies.clear()
    gudang_client = login_as("gudang@example.com")
    first = gudang_client.post(
        f"/api/permintaan/{pm['id']}/setujui",
        json={
            "tanggal_kirim": Clock.today().isoformat(),
            "items": [{"produk_id": setup["biji"].id, "jumlah_disetujui": 6}],
        },
    ).json()
    kr1_id = first["pengiriman"]["id"]

    # batalkan draf pengiriman pertama lalu setujui ulang permintaan
    assert gudang_client.delete(f"/api/pengiriman/{kr1_id}").status_code == 204
    reopened = gudang_client.get(f"/api/permintaan/{pm['id']}").json()
    assert reopened["status"] == "diajukan" and reopened["pengiriman"] is None

    second = gudang_client.post(
        f"/api/permintaan/{pm['id']}/setujui",
        json={
            "tanggal_kirim": Clock.today().isoformat(),
            "items": [{"produk_id": setup["biji"].id, "jumlah_disetujui": 10}],
        },
    )
    assert second.status_code == 200
    assert second.json()["status"] == "disetujui"
    assert second.json()["pengiriman"]["id"] != kr1_id

def test_tolak_permintaan_requires_reason(setup, login_as, client):
    outlet_client = login_as("outlet@example.com")
    pm = outlet_client.post("/api/permintaan", json=payload(setup)).json()

    client.cookies.clear()
    gudang_client = login_as("gudang@example.com")
    pendek = gudang_client.post(
        f"/api/permintaan/{pm['id']}/tolak", json={"alasan_penolakan": "ab"}
    )
    assert pendek.status_code == 422 and pendek.json()["errors"] == {
        "alasan_penolakan": "Minimal 3 karakter"
    }

    rejected = gudang_client.post(
        f"/api/permintaan/{pm['id']}/tolak",
        json={"alasan_penolakan": "Stok diprioritaskan untuk cabang"},
    )
    assert rejected.status_code == 200
    data = rejected.json()
    assert data["status"] == "ditolak"
    assert data["alasan_penolakan"] == "Stok diprioritaskan untuk cabang"
    assert data["diproses_oleh"]["id"] == setup["manager_gudang"].id

def test_validation_rules_for_create_and_setujui(setup, login_as):
    admin = login_as("admin@example.com")
    assert admin.post("/api/permintaan", json=payload(setup)).json()["errors"] == {
        "lokasi_peminta_id": "Wajib diisi untuk admin"
    }
    dari_gudang_utama = admin.post(
        "/api/permintaan",
        json=payload(setup, lokasi_peminta_id=setup["gudang"].id),
    )
    assert dari_gudang_utama.status_code == 422 and dari_gudang_utama.json()[
        "errors"
    ] == {
        "lokasi_peminta_id": "Permintaan hanya bisa diajukan dari gudang cabang atau outlet"
    }

    # produk tanpa stok di gudang utama ditolak 422 (BR-08)
    stok_kosong = admin.post(
        "/api/permintaan",
        json=payload(
            setup,
            lokasi_peminta_id=setup["outlet"].id,
            items=[
                {"produk_id": setup["biji"].id, "jumlah_diminta": 5},
                {"produk_id": setup["kosong"].id, "jumlah_diminta": 1},
            ],
        ),
    )
    assert stok_kosong.status_code == 422 and stok_kosong.json()["errors"] == {
        "items.1.produk_id": "Stok di gudang utama kosong"
    }

    # ajukan permintaan valid dengan jumlah_diminta > stok_gudang_utama untuk uji batas setujui
    pm = admin.post(
        "/api/permintaan",
        json=payload(
            setup,
            lokasi_peminta_id=setup["outlet"].id,
            items=[
                {"produk_id": setup["biji"].id, "jumlah_diminta": 10},
                {"produk_id": setup["alat"].id, "jumlah_diminta": 6},
            ],
        ),
    ).json()

    # jumlah_disetujui melebihi jumlah_diminta dan melebihi stok gudang utama (alat stok=4)
    melebihi = admin.post(
        f"/api/permintaan/{pm['id']}/setujui",
        json={
            "tanggal_kirim": Clock.today().isoformat(),
            "items": [
                {"produk_id": setup["biji"].id, "jumlah_disetujui": 12},
                {"produk_id": setup["alat"].id, "jumlah_disetujui": 5},
            ],
        },
    )
    assert melebihi.status_code == 422 and melebihi.json()["errors"] == {
        "items.0.jumlah_disetujui": "Maksimal sebesar jumlah diminta (10)",
        "items.1.jumlah_disetujui": "Melebihi stok gudang utama (4 pcs)",
    }

    # semua baris disetujui 0 ditolak 422 (BR-09)
    semua_nol = admin.post(
        f"/api/permintaan/{pm['id']}/setujui",
        json={
            "tanggal_kirim": Clock.today().isoformat(),
            "items": [
                {"produk_id": setup["biji"].id, "jumlah_disetujui": 0},
                {"produk_id": setup["alat"].id, "jumlah_disetujui": 0},
            ],
        },
    )
    assert semua_nol.status_code == 422 and semua_nol.json()["errors"] == {
        "items": (
            "Minimal satu produk harus disetujui lebih dari 0. "
            "Gunakan aksi tolak bila tidak ada yang disetujui"
        )
    }

def test_role_and_location_isolation(setup, login_as, client):
    # deliveryman ditolak 403
    assert login_as("kurir@example.com").get("/api/permintaan").status_code == 403
    client.cookies.clear()

    # manager gudang utama tidak bisa mengajukan permintaan untuk dirinya sendiri
    gudang_client = login_as("gudang@example.com")
    assert gudang_client.post("/api/permintaan", json=payload(setup)).status_code == 403
    client.cookies.clear()

    outlet_client = login_as("outlet@example.com")
    pm_outlet = outlet_client.post("/api/permintaan", json=payload(setup)).json()
    client.cookies.clear()

    cabang_client = login_as("cabang@example.com")
    pm_cabang = cabang_client.post("/api/permintaan", json=payload(setup)).json()
    # cabang hanya melihat miliknya dan mendapat 404 untuk permintaan outlet
    assert [row["id"] for row in cabang_client.get("/api/permintaan").json()["data"]] == [
        pm_cabang["id"]
    ]
    assert cabang_client.get(f"/api/permintaan/{pm_outlet['id']}").status_code == 404
    # cabang tidak bisa menyetujui atau menolak permintaannya sendiri (403)
    assert (
        cabang_client.post(
            f"/api/permintaan/{pm_cabang['id']}/setujui",
            json={
                "tanggal_kirim": Clock.today().isoformat(),
                "items": [{"produk_id": setup["biji"].id, "jumlah_disetujui": 5}],
            },
        ).status_code
        == 403
    )
    assert (
        cabang_client.post(
            f"/api/permintaan/{pm_cabang['id']}/tolak",
            json={"alasan_penolakan": "Batal"},
        ).status_code
        == 403
    )

    # gudang utama melihat semua permintaan tetapi tidak boleh mengubah atau membatalkannya (403)
    client.cookies.clear()
    gudang_client = login_as("gudang@example.com")
    assert gudang_client.get("/api/permintaan").json()["meta"]["total"] == 2
    assert (
        gudang_client.put(
            f"/api/permintaan/{pm_outlet['id']}", json=payload(setup)
        ).status_code
        == 403
    )
    assert (
        gudang_client.post(f"/api/permintaan/{pm_outlet['id']}/batal").status_code
        == 403
    )

def test_draft_from_permintaan_keeps_destination_and_approved_quantity(
    setup, login_as, client
):
    outlet_client = login_as("outlet@example.com")
    pm = outlet_client.post("/api/permintaan", json=payload(setup)).json()

    client.cookies.clear()
    gudang_client = login_as("gudang@example.com")
    approved = gudang_client.post(
        f"/api/permintaan/{pm['id']}/setujui",
        json={
            "tanggal_kirim": Clock.today().isoformat(),
            "items": [{"produk_id": setup["biji"].id, "jumlah_disetujui": 6}],
        },
    ).json()
    kr_id = approved["pengiriman"]["id"]

    def update(tujuan, items):
        body = {
            "lokasi_tujuan_id": tujuan.id,
            "tanggal_kirim": Clock.today().isoformat(),
            "items": items,
        }
        return gudang_client.put(f"/api/pengiriman/{kr_id}", json=body)

    # draf tidak bisa dialihkan ke lokasi lain, ditambah produk lain atau melebihi persetujuan
    moved = update(setup["cabang"], [{"produk_id": setup["biji"].id, "jumlah_dikirim": 20}])
    assert moved.status_code == 422
    assert set(moved.json()["errors"]) == {"lokasi_tujuan_id", "items.0.jumlah_dikirim"}
    extra = update(setup["outlet"], [{"produk_id": setup["alat"].id, "jumlah_dikirim": 1}])
    assert extra.json()["errors"] == {
        "items.0.produk_id": f"Produk tidak ada di permintaan {pm['kode']}"
    }
    smaller = update(setup["outlet"], [{"produk_id": setup["biji"].id, "jumlah_dikirim": 5}])
    assert smaller.status_code == 200 and smaller.json()["items"][0]["jumlah_dikirim"] == 5

@pytest.fixture
def utc_session():
    # meniru Neon yang zona waktu sesi databasenya UTC
    def set_utc(dbapi_connection, *_):
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")

    event.listen(database.engine, "checkout", set_utc)
    yield
    event.remove(database.engine, "checkout", set_utc)
    database.engine.dispose()

def test_date_filter_uses_wib_creation_date(setup, login_as, utc_session):
    outlet_client = login_as("outlet@example.com")
    # 06.30 WIB tanggal 2 masih tanggal 1 di UTC
    with Clock.at(datetime(2026, 10, 2, 6, 30, tzinfo=Clock.ZONE)):
        assert outlet_client.post("/api/permintaan", json=payload(setup)).status_code == 201
    for day, total in (("2026-10-02", 1), ("2026-10-01", 0)):
        res = outlet_client.get("/api/permintaan", params={"dari": day, "sampai": day})
        assert res.json()["meta"]["total"] == total
