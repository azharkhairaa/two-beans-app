from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, contains_eager

from app.core.errors import Forbidden, NotFound
from app.models import (
    Kategori,
    KategoriType,
    Lokasi,
    LokasiType,
    Pembelian,
    Pengiriman,
    Penjualan,
    Produk,
    Stok,
    StokMutasi,
    StokStatus,
    Transaksi,
    User,
)
from app.policies.lokasi_policy import LokasiPolicy
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.lokasi import LokasiSummary
from app.schemas.stok import KartuStokItem, StokItem, StokPage, StokProduk, StokSettingInput
from app.services.base import CrudService

class StokSort(StrEnum):
    NAMA = "nama"
    JUMLAH = "jumlah"
    NILAI = "nilai"

@dataclass(frozen=True)
class StokFilter:
    lokasi_id: int | None = None
    q: str | None = None
    kategori_id: int | None = None
    jenis: KategoriType | None = None
    status_stok: StokStatus | None = None
    sort: StokSort = StokSort.NAMA
    arah: SortDirection = SortDirection.ASC

class StokService:
    # daftar stok per lokasi, pengaturan stok minimum dan rak serta kartu stok
    STATUS = {
        StokStatus.HABIS: Stok.jumlah == 0,
        StokStatus.MENIPIS: and_(Stok.jumlah > 0, Stok.jumlah <= Stok.stok_minimum),
        StokStatus.AMAN: Stok.jumlah > Stok.stok_minimum,
    }

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.policy = LokasiPolicy(user)

    def lokasi(self, lokasi_id: int | None) -> Lokasi:
        # tanpa lokasi_id manager melihat lokasinya dan admin melihat gudang utama
        if lokasi_id is None:
            lokasi_id = self.user.lokasi_id or self.db.scalar(
                select(Lokasi.id).where(Lokasi.jenis == LokasiType.GUDANG_UTAMA)
            )
        lokasi = self.db.get(Lokasi, lokasi_id) if lokasi_id else None
        if lokasi is None:
            raise NotFound("Lokasi tidak ditemukan")
        return lokasi

    def search(self, filters: StokFilter, params: PageParams) -> StokPage:
        lokasi = self.lokasi(filters.lokasi_id)
        query = (
            select(Stok)
            .join(Stok.produk)
            .join(Produk.kategori)
            .options(contains_eager(Stok.produk).contains_eager(Produk.kategori))
            .where(Stok.lokasi_id == lokasi.id)
        )
        if filters.q:
            columns = (Produk.sku, Produk.nama)
            matches = (CrudService.contains(column, filters.q) for column in columns)
            query = query.where(or_(*matches))
        if filters.kategori_id:
            query = query.where(Produk.kategori_id == filters.kategori_id)
        if filters.jenis:
            query = query.where(Kategori.jenis == filters.jenis)
        if filters.status_stok:
            query = query.where(self.STATUS[filters.status_stok])
        column = self.sort_column(filters.sort)
        order = column.desc() if filters.arah == SortDirection.DESC else column.asc()
        page = self.paginate(query.order_by(order, Produk.nama), params, self.to_item, scalars=True)
        return StokPage(data=page.data, meta=page.meta, lokasi=LokasiSummary.model_validate(lokasi))

    @staticmethod
    def sort_column(sort: StokSort) -> ColumnElement:
        if sort == StokSort.JUMLAH:
            return Stok.jumlah
        if sort == StokSort.NILAI:
            return Stok.jumlah * Produk.harga_beli
        return Produk.nama

    def update_setting(self, lokasi_id: int, produk_id: int, data: StokSettingInput) -> StokItem:
        lokasi = self.lokasi(lokasi_id)
        if self.db.get(Produk, produk_id) is None:
            raise NotFound("Produk tidak ditemukan")
        if not self.policy.can_manage(lokasi.id):
            raise Forbidden("Stok minimum dan rak hanya bisa diatur di lokasi sendiri")
        # baris stok dibuat bila produk belum pernah ada di lokasi ini
        self.db.execute(
            insert(Stok).values(lokasi_id=lokasi.id, produk_id=produk_id).on_conflict_do_nothing()
        )
        stok = self.db.get(Stok, (lokasi.id, produk_id), populate_existing=True)
        stok.stok_minimum = data.stok_minimum
        stok.rak = data.rak
        self.db.commit()
        self.db.refresh(stok)
        return self.to_item(stok)

    def kartu_stok(self, produk_id: int, lokasi_id: int, params: PageParams) -> Page:
        if self.db.get(Produk, produk_id) is None:
            raise NotFound("Produk tidak ditemukan")
        lokasi = self.lokasi(lokasi_id)
        dokumen = func.coalesce(Transaksi.kode, Pengiriman.kode, Pembelian.kode, Penjualan.kode)
        query = (
            select(StokMutasi, User.name, dokumen)
            .join(User, User.id == StokMutasi.user_id)
            .outerjoin(Transaksi, Transaksi.id == StokMutasi.transaksi_id)
            .outerjoin(Pengiriman, Pengiriman.id == StokMutasi.pengiriman_id)
            .outerjoin(Pembelian, Pembelian.id == StokMutasi.pembelian_id)
            .outerjoin(Penjualan, Penjualan.id == StokMutasi.penjualan_id)
            .where(StokMutasi.produk_id == produk_id, StokMutasi.lokasi_id == lokasi.id)
            .order_by(StokMutasi.id.desc())
        )
        return self.paginate(query, params, self.to_kartu)

    def paginate(
        self, query: Select, params: PageParams, convert: Callable, scalars: bool = False
    ) -> Page:
        total = self.db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        query = query.limit(params.per_page).offset(params.offset)
        rows = self.db.scalars(query).all() if scalars else self.db.execute(query).all()
        items = [convert(row) if scalars else convert(*row) for row in rows]
        return Page.of(items, total, params)

    @staticmethod
    def to_item(stok: Stok) -> StokItem:
        produk = stok.produk
        return StokItem(
            produk=StokProduk(
                id=produk.id, sku=produk.sku, nama=produk.nama, satuan=produk.satuan,
                kategori=produk.kategori.nama, jenis=produk.kategori.jenis,
                harga_beli=produk.harga_beli,
            ),
            jumlah=stok.jumlah, stok_minimum=stok.stok_minimum, rak=stok.rak,
            status_stok=stok.status_stok, nilai=stok.jumlah * produk.harga_beli,
            updated_at=stok.updated_at,
        )

    @staticmethod
    def to_kartu(mutasi: StokMutasi, oleh: str, dokumen: str) -> KartuStokItem:
        return KartuStokItem(
            id=mutasi.id, jenis=mutasi.jenis, dokumen=dokumen, perubahan=mutasi.perubahan,
            stok_sebelum=mutasi.stok_sebelum, stok_sesudah=mutasi.stok_sesudah, oleh=oleh,
            created_at=mutasi.created_at,
        )
