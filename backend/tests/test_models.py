from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import (
    DOCUMENT_NUMBER_SEQUENCE,
    Base,
    Customer,
    CustomerType,
    Lokasi,
    LokasiType,
    Penjualan,
    PenjualanDetail,
    StokMutasi,
    StokMutasiType,
    User,
    UserStatus,
)

def constraint_violated(error) -> str:
    return error.value.orig.diag.constraint_name

def test_metadata_has_19_tables():
    assert len(Base.metadata.tables) == 19

def test_constraint_names_follow_naming_convention():
    tables = Base.metadata.tables.values()
    names = {c.name for t in tables for c in t.constraints} | {i.name for t in tables for i in t.indexes}
    for name in ("pk_stok", "fk_users_lokasi_id_lokasi", "uq_produk_sku", "ck_users_role",
                 "ck_stok_mutasi_satu_sumber", "uq_penjualan_detail_penjualan_id_produk_id",
                 "ix_stok_mutasi_lokasi_produk", "uq_lokasi_satu_gudang_utama"):
        assert name in names

def test_server_defaults_filled_by_database(db, factory):
    lokasi = factory.outlet()
    user = factory.add(User(name="Calon User", email="calon@example.com", password_hash="x"))
    db.refresh(lokasi)
    db.refresh(user)
    assert lokasi.aktif is True and lokasi.created_at is not None
    assert (user.status, user.role, user.failed_logins) == ("menunggu", None, 0)

def test_only_one_gudang_utama(factory):
    factory.add(Lokasi(kode="GU-01", nama="Gudang Utama Roastery", jenis=LokasiType.GUDANG_UTAMA))
    with pytest.raises(IntegrityError) as error:
        factory.add(Lokasi(kode="GU-02", nama="Gudang Utama Kedua", jenis=LokasiType.GUDANG_UTAMA))
    assert constraint_violated(error) == "uq_lokasi_satu_gudang_utama"

def test_lokasi_name_unique_ignoring_case(factory):
    factory.outlet("OT-01", "Outlet Kampus")
    with pytest.raises(IntegrityError) as error:
        factory.outlet("OT-02", "OUTLET KAMPUS")
    assert constraint_violated(error) == "uq_lokasi_nama_lower"

def test_lokasi_code_prefix_must_match_type(factory):
    with pytest.raises(IntegrityError) as error:
        factory.add(Lokasi(kode="GC-01", nama="Salah Kode", jenis=LokasiType.OUTLET))
    assert constraint_violated(error) == "ck_lokasi_kode_jenis"

def test_active_user_must_have_role(factory):
    with pytest.raises(IntegrityError) as error:
        factory.add(User(name="Tanpa Peran", email="x@example.com", password_hash="x", status=UserStatus.AKTIF))
    assert constraint_violated(error) == "ck_users_role_wajib"

def test_stok_mutasi_needs_exactly_one_source(factory):
    outlet = factory.outlet()
    user = factory.manager(outlet)
    produk = factory.produk()
    with pytest.raises(IntegrityError) as error:
        factory.add(StokMutasi(lokasi_id=outlet.id, produk_id=produk.id, jenis=StokMutasiType.MASUK,
                               perubahan=5, stok_sebelum=0, stok_sesudah=5, user_id=user.id))
    assert constraint_violated(error) == "ck_stok_mutasi_satu_sumber"

def test_penjualan_customer_optional_and_detail_deleted_with_document(db, factory):
    outlet = factory.outlet()
    manager = factory.manager(outlet)
    produk = factory.produk()
    kafe = factory.add(Customer(nama="Kafe Senja", jenis=CustomerType.KAFE))
    umum = factory.add(Penjualan(kode="PJ-261028-0001", tanggal=date(2026, 10, 28), lokasi=outlet,
                                 dibuat_oleh=manager,
                                 detail=[PenjualanDetail(produk=produk, jumlah=5, harga_satuan=produk.harga_jual)]))
    langganan = factory.add(Penjualan(kode="PJ-261028-0002", tanggal=date(2026, 10, 28), lokasi=outlet,
                                      customer=kafe, dibuat_oleh=manager,
                                      detail=[PenjualanDetail(produk=produk, jumlah=10, harga_satuan=85000)]))
    db.commit()
    assert umum.customer is None and umum.status == "draf"
    assert [p.kode for p in kafe.penjualan] == [langganan.kode]
    db.delete(umum)
    db.commit()
    assert db.scalar(select(func.count()).select_from(PenjualanDetail)) == 1

def test_document_number_sequence_increments(db):
    pertama = db.scalar(DOCUMENT_NUMBER_SEQUENCE.next_value())
    kedua = db.scalar(DOCUMENT_NUMBER_SEQUENCE.next_value())
    assert kedua == pertama + 1
