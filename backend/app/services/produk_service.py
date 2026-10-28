from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import func, or_, select
from sqlalchemy.orm import contains_eager, joinedload

from app.core.errors import ValidationFailed
from app.models import (
    Kategori,
    KategoriType,
    Pengiriman,
    PengirimanDetail,
    PengirimanStatus,
    Produk,
    ProdukUnit,
    Stok,
)
from app.schemas.common import ActiveFilter, Page, PageParams, SortDirection
from app.schemas.produk import (
    LokasiRef,
    ProdukDetail,
    ProdukInput,
    ProdukOption,
    ProdukResponse,
    StokLokasi,
)
from app.services.base import CrudService

class ProdukRules:
    # BR-18: satuan, berat, tingkat sangrai dan jenis kopi mengikuti jenis kategori
    WEIGHTS = (100, 200, 250, 500, 1000)
    COFFEE = (KategoriType.GREEN_BEAN, KategoriType.ROASTED_BEAN)

    def check(self, data: ProdukInput, jenis: str) -> dict[str, str]:
        errors: dict[str, str] = {}
        if jenis == KategoriType.GREEN_BEAN and data.satuan != ProdukUnit.KG:
            errors["satuan"] = "Green bean memakai satuan kg"
        if jenis == KategoriType.ROASTED_BEAN:
            if data.satuan != ProdukUnit.PACK:
                errors["satuan"] = "Roasted bean memakai satuan pack"
            if data.berat_gram is None:
                errors["berat_gram"] = "Wajib diisi untuk roasted bean"
            elif data.berat_gram not in self.WEIGHTS:
                errors["berat_gram"] = "Pilih 100, 200, 250, 500 atau 1000 gram"
        else:
            if data.berat_gram is not None:
                errors["berat_gram"] = "Hanya untuk roasted bean"
            if data.tingkat_sangrai is not None:
                errors["tingkat_sangrai"] = "Hanya untuk roasted bean"
        if jenis in self.COFFEE and data.jenis_kopi is None:
            errors["jenis_kopi"] = "Wajib diisi untuk green bean dan roasted bean"
        if jenis not in self.COFFEE and data.jenis_kopi is not None:
            errors["jenis_kopi"] = "Hanya untuk green bean dan roasted bean"
        return errors

class ProdukSort(StrEnum):
    NAMA = "nama"
    SKU = "sku"
    HARGA_BELI = "harga_beli"
    HARGA_JUAL = "harga_jual"
    UPDATED_AT = "updated_at"

@dataclass(frozen=True)
class ProdukFilter:
    q: str | None = None
    kategori_id: int | None = None
    jenis: KategoriType | None = None
    jenis_kopi: str | None = None
    aktif: ActiveFilter = ActiveFilter.TRUE
    sort: ProdukSort = ProdukSort.NAMA
    arah: SortDirection = SortDirection.ASC

class ProdukService(CrudService[Produk]):
    model = Produk
    label = "Produk"
    rules = ProdukRules()

    def create(self, data: ProdukInput) -> Produk:
        self.validate(data)
        return super().create(data)

    def update(self, produk: Produk, data: ProdukInput) -> Produk:
        self.validate(data)
        return super().update(produk, data)

    def validate(self, data: ProdukInput) -> None:
        kategori = self.db.get(Kategori, data.kategori_id)
        if kategori is None:
            raise ValidationFailed(errors={"kategori_id": "Kategori tidak ditemukan"})
        errors = self.rules.check(data, kategori.jenis)
        if errors:
            raise ValidationFailed(errors=errors)

    def search(self, filters: ProdukFilter, params: PageParams) -> Page:
        query = select(Produk).join(Produk.kategori).options(contains_eager(Produk.kategori))
        query = self.active_filter(query, Produk.aktif, filters.aktif)
        if filters.q:
            columns = (Produk.sku, Produk.nama, Produk.merek)
            query = query.where(or_(*(self.contains(column, filters.q) for column in columns)))
        if filters.kategori_id:
            query = query.where(Produk.kategori_id == filters.kategori_id)
        if filters.jenis:
            query = query.where(Kategori.jenis == filters.jenis)
        if filters.jenis_kopi:
            query = query.where(Produk.jenis_kopi == filters.jenis_kopi)
        column = getattr(Produk, filters.sort.value)
        order = column.desc() if filters.arah == SortDirection.DESC else column.asc()
        return self.paginate(query.order_by(order, Produk.id), params, ProdukResponse)

    def detail(self, item_id: int) -> ProdukDetail:
        produk = self.get_or_404(item_id)
        rows = self.db.scalars(
            select(Stok).options(joinedload(Stok.lokasi)).where(Stok.produk_id == produk.id)
        ).all()
        stok = [
            StokLokasi(
                lokasi=LokasiRef.model_validate(row.lokasi), jumlah=row.jumlah,
                stok_minimum=row.stok_minimum, rak=row.rak, status_stok=row.status_stok,
                nilai=row.jumlah * produk.harga_beli,
            )
            for row in sorted(rows, key=lambda row: row.lokasi.kode)
        ]
        dalam_perjalanan = self.db.scalar(
            select(func.coalesce(func.sum(PengirimanDetail.jumlah_dikirim), 0))
            .join(Pengiriman, Pengiriman.id == PengirimanDetail.pengiriman_id)
            .where(
                PengirimanDetail.produk_id == produk.id,
                Pengiriman.status == PengirimanStatus.DIKIRIM,
            )
        )
        data = ProdukResponse.model_validate(produk).model_dump()
        return ProdukDetail(
            **data, stok=stok, total_stok=sum(s.jumlah for s in stok),
            total_nilai=sum(s.nilai for s in stok), dalam_perjalanan=dalam_perjalanan,
        )

    def options(self, lokasi_id: int | None, jenis: KategoriType | None) -> list[ProdukOption]:
        query = (
            select(Produk, Kategori.jenis, Stok.jumlah)
            .join(Produk.kategori)
            .outerjoin(Stok, (Stok.produk_id == Produk.id) & (Stok.lokasi_id == lokasi_id))
            .where(Produk.aktif)
            .order_by(Produk.nama)
        )
        if jenis:
            query = query.where(Kategori.jenis == jenis)
        return [
            ProdukOption(
                id=produk.id, sku=produk.sku, nama=produk.nama, satuan=produk.satuan,
                jenis=kategori_jenis,
                harga_beli=produk.harga_beli, harga_jual=produk.harga_jual,
                stok=(jumlah or 0) if lokasi_id else None,
            )
            for produk, kategori_jenis, jumlah in self.db.execute(query)
        ]
