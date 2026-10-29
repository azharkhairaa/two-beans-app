from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError

from app.core.database import database
from app.core.errors import InsufficientStock
from app.models import (
    Kategori,
    KategoriType,
    Lokasi,
    LokasiType,
    Produk,
    ProdukUnit,
    Stok,
    StokMutasi,
    StokMutasiType,
    Transaksi,
    TransaksiType,
    User,
    UserRole,
)
from app.services.mutasi_stok import MutasiStok, MutationSource, StockChange

@pytest.fixture
def setup(db, factory):
    gudang = factory.add(Lokasi(kode="GU-01", nama="Gudang Utama Roastery", jenis=LokasiType.GUDANG_UTAMA))
    outlet = factory.outlet()
    biji = factory.produk()
    alat = factory.add(Produk(sku="AL-V60-02", nama="Dripper V60 02", satuan=ProdukUnit.PCS, harga_beli=120000,
                              kategori=factory.add(Kategori(nama="Alat Seduh", jenis=KategoriType.PERALATAN))))
    admin = factory.user("admin@example.com")
    manager = factory.user("manager@example.com", UserRole.MANAGER_OUTLET, lokasi=outlet)
    db.commit()
    return {"gudang": gudang, "outlet": outlet, "biji": biji, "alat": alat, "admin": admin, "manager": manager}

def transaksi(factory, setup, jenis, alasan, nomor):
    prefix = {TransaksiType.MASUK: "BM", TransaksiType.KELUAR: "BK", TransaksiType.PENYESUAIAN: "PS"}[jenis]
    return factory.add(Transaksi(kode=f"{prefix}-261028-{nomor:04d}", jenis=jenis, tanggal=date(2026, 10, 28),
                                 lokasi_id=setup["gudang"].id, alasan=alasan, dibuat_oleh_id=setup["admin"].id))

def apply(db, setup, document, jenis, changes):
    mutasi = MutasiStok(db, setup["admin"])
    result = mutasi.apply([StockChange(lokasi, produk, delta, f"items.{i}.jumlah")
                           for i, (lokasi, produk, delta) in enumerate(changes)],
                          MutationSource(jenis, document.id))
    db.commit()
    return result

def balance(db, lokasi, produk) -> int | None:
    return db.scalar(select(Stok.jumlah).where(Stok.lokasi_id == lokasi.id, Stok.produk_id == produk.id))

def test_ledger_records_running_balance(db, factory, setup):
    gudang, biji = setup["gudang"], setup["biji"]
    masuk = transaksi(factory, setup, TransaksiType.MASUK, "retur", 1)
    keluar = transaksi(factory, setup, TransaksiType.KELUAR, "sampel", 2)
    opname = transaksi(factory, setup, TransaksiType.PENYESUAIAN, "opname", 3)
    apply(db, setup, masuk, StokMutasiType.MASUK, [(gudang.id, biji.id, 40)])
    apply(db, setup, keluar, StokMutasiType.KELUAR, [(gudang.id, biji.id, -15)])
    apply(db, setup, opname, StokMutasiType.PENYESUAIAN, [(gudang.id, biji.id, -2)])
    rows = db.execute(select(StokMutasi.perubahan, StokMutasi.stok_sebelum, StokMutasi.stok_sesudah)
                      .order_by(StokMutasi.id)).all()
    assert rows == [(40, 0, 40), (-15, 40, 25), (-2, 25, 23)]
    assert balance(db, gudang, biji) == 23

def test_negative_balance_rejected_without_any_change(db, factory, setup):
    gudang, biji, alat = setup["gudang"], setup["biji"], setup["alat"]
    apply(db, setup, transaksi(factory, setup, TransaksiType.MASUK, "retur", 1), StokMutasiType.MASUK,
          [(gudang.id, biji.id, 10), (gudang.id, alat.id, 3)])
    keluar = transaksi(factory, setup, TransaksiType.KELUAR, "pemakaian", 2)
    db.commit()
    with pytest.raises(InsufficientStock) as error:
        apply(db, setup, keluar, StokMutasiType.KELUAR,
              [(gudang.id, biji.id, -4), (gudang.id, alat.id, -5), (setup["outlet"].id, biji.id, -1)])
    assert error.value.message == "Stock tidak cukup untuk 2 produk"
    assert error.value.errors == {
        "items.1.jumlah": "Stock AL-V60-02 di Gudang Utama Roastery tersisa 3 pcs",
        "items.2.jumlah": "Stock BK-ARB-GAYO-200 di Outlet Pusat Kota tersisa 0 pack",
    }
    # baris pertama yang cukup pun tidak berubah dan baris stok outlet tidak ikut tercipta
    db.expire_all()
    assert (balance(db, gudang, biji), balance(db, gudang, alat)) == (10, 3)
    assert balance(db, setup["outlet"], biji) is None
    assert db.scalar(select(func.count()).select_from(StokMutasi)) == 2

def test_stock_equals_last_ledger_balance(db, factory, setup):
    gudang, outlet, biji = setup["gudang"], setup["outlet"], setup["biji"]
    for nomor, delta in enumerate([25, -5, 7, -10], start=1):
        jenis = TransaksiType.MASUK if delta > 0 else TransaksiType.KELUAR
        document = transaksi(factory, setup, jenis, "retur" if delta > 0 else "sampel", nomor)
        apply(db, setup, document, StokMutasiType(jenis.value), [(gudang.id, biji.id, delta), (outlet.id, biji.id, 0)])
    last = db.scalar(select(StokMutasi.stok_sesudah).where(StokMutasi.lokasi_id == gudang.id)
                     .order_by(StokMutasi.id.desc()).limit(1))
    assert balance(db, gudang, biji) == last == 17
    # perubahan 0 dilewati sehingga outlet tidak punya baris stok maupun mutasi
    assert balance(db, outlet, biji) is None

def test_stok_list_defaults_filters_and_sort(db, factory, setup, login_as, client):
    gudang, outlet, biji, alat = setup["gudang"], setup["outlet"], setup["biji"], setup["alat"]
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=40, stok_minimum=30, rak="A-01"))
    factory.add(Stok(lokasi_id=gudang.id, produk_id=alat.id, jumlah=0, stok_minimum=2))
    factory.add(Stok(lokasi_id=outlet.id, produk_id=biji.id, jumlah=5, stok_minimum=10))
    db.commit()
    admin = login_as("admin@example.com")
    data = admin.get("/api/stok").json()
    assert data["lokasi"]["kode"] == "GU-01" and data["meta"]["total"] == 2
    assert [(s["produk"]["sku"], s["status_stok"], s["nilai"]) for s in data["data"]] == [
        ("BK-ARB-GAYO-200", "aman", 40 * 65000), ("AL-V60-02", "habis", 0)]
    habis = admin.get("/api/stok", params={"status_stok": "habis"}).json()["data"]
    assert [s["produk"]["sku"] for s in habis] == ["AL-V60-02"]
    by_value = admin.get("/api/stok", params={"sort": "nilai", "arah": "desc"}).json()["data"]
    assert by_value[0]["produk"]["sku"] == "BK-ARB-GAYO-200"
    client.cookies.clear()
    manager = login_as("manager@example.com")
    own = manager.get("/api/stok").json()
    assert own["lokasi"]["kode"] == "OT-01" and own["data"][0]["status_stok"] == "menipis"
    assert manager.get("/api/stok", params={"lokasi_id": gudang.id}).json()["meta"]["total"] == 2

def test_stok_setting_only_own_lokasi(setup, login_as):
    manager = login_as("manager@example.com")
    outlet, gudang, alat = setup["outlet"], setup["gudang"], setup["alat"]
    response = manager.put(f"/api/stok/{outlet.id}/{alat.id}", json={"stok_minimum": 4, "rak": " b-02 "})
    assert response.status_code == 200
    assert (response.json()["jumlah"], response.json()["stok_minimum"], response.json()["rak"]) == (0, 4, "B-02")
    response = manager.put(f"/api/stok/{gudang.id}/{alat.id}", json={"stok_minimum": 4})
    assert (response.status_code, response.json()) == (
        403, {"detail": "Stock minimum dan rak hanya bisa diatur di lokasi sendiri"})
    response = manager.put(f"/api/stok/{outlet.id}/{alat.id}", json={"stok_minimum": "4", "rak": "rak1", "jumlah": 9})
    assert response.json()["errors"] == {
        "stok_minimum": "Harus bilangan bulat", "rak": "Format rak seperti A-01 atau BC-12", "jumlah": "Field tidak dikenal"}
    assert manager.put(f"/api/stok/{outlet.id}/999", json={"stok_minimum": 1}).status_code == 404

def test_kartu_stok_lists_ledger_with_document_and_user(db, factory, setup, login_as):
    gudang, biji = setup["gudang"], setup["biji"]
    apply(db, setup, transaksi(factory, setup, TransaksiType.MASUK, "retur", 1), StokMutasiType.MASUK,
          [(gudang.id, biji.id, 12)])
    apply(db, setup, transaksi(factory, setup, TransaksiType.KELUAR, "sampel", 2), StokMutasiType.KELUAR,
          [(gudang.id, biji.id, -2)])
    manager = login_as("manager@example.com")
    data = manager.get(f"/api/produk/{biji.id}/kartu-stok", params={"lokasi_id": gudang.id}).json()
    assert [(k["dokumen"], k["jenis"], k["perubahan"], k["stok_sesudah"], k["oleh"]) for k in data["data"]] == [
        ("BK-261028-0002", "keluar", -2, 10, "User Uji"), ("BM-261028-0001", "masuk", 12, 12, "User Uji")]
    response = manager.get(f"/api/produk/{biji.id}/kartu-stok")
    assert response.json()["errors"] == {"lokasi_id": "Wajib diisi"}

def test_concurrent_mutation_waits_for_row_lock(db, factory, setup):
    # transaksi kedua tertahan kunci FOR UPDATE transaksi pertama sampai commit (mencegah lost update)
    gudang, biji = setup["gudang"], setup["biji"]
    factory.add(Stok(lokasi_id=gudang.id, produk_id=biji.id, jumlah=10))
    document = transaksi(factory, setup, TransaksiType.KELUAR, "sampel", 1)
    db.commit()
    source = MutationSource(StokMutasiType.KELUAR, document.id)
    MutasiStok(db, setup["admin"]).apply([StockChange(gudang.id, biji.id, -3, "items.0.jumlah")], source)
    with database.session_factory() as other:
        other.execute(text("SET lock_timeout = '200ms'"))
        actor = other.get(User, setup["admin"].id)
        with pytest.raises(OperationalError) as error:
            MutasiStok(other, actor).apply([StockChange(gudang.id, biji.id, -3, "items.0.jumlah")], source)
        assert error.value.orig.sqlstate == "55P03"
    db.commit()
    assert balance(db, gudang, biji) == 7
