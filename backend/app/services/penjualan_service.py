from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.core.clock import Clock
from app.core.errors import ValidationFailed
from app.models import (
    Customer,
    Lokasi,
    Penjualan,
    PenjualanDetail,
    PenjualanStatus,
    Produk,
    StokMutasiType,
)
from app.policies.dokumen_policy import DokumenPolicy
from app.schemas.common import LokasiKontakRef, Page, PageParams, SortDirection
from app.schemas.penjualan import (
    CustomerRef,
    PenjualanDetailResponse,
    PenjualanInput,
    PenjualanItemResponse,
    PenjualanProduk,
    PenjualanSummary,
)
from app.services.base import DokumenService, SqlMoney
from app.services.mutasi_stok import MutasiStok, MutationSource, StockChange

class PenjualanSort(StrEnum):
    TANGGAL = "tanggal"
    KODE = "kode"
    TOTAL = "total"

@dataclass(frozen=True)
class PenjualanFilter:
    lokasi_id: int | None = None
    customer_id: int | None = None
    status: PenjualanStatus | None = None
    dari: date | None = None
    sampai: date | None = None
    q: str | None = None
    sort: PenjualanSort = PenjualanSort.TANGGAL
    arah: SortDirection = SortDirection.DESC

class PenjualanRules:
    # BR-26: penjualan dari gudang wajib memilih customer aktif, di outlet boleh kosong
    @staticmethod
    def requires_customer(lokasi: Lokasi) -> bool:
        return lokasi.jenis in DokumenPolicy.WAREHOUSE_TYPES

class PenjualanService(DokumenService[Penjualan]):
    model = Penjualan
    label = "Penjualan"
    rules = PenjualanRules()

    def search(self, filters: PenjualanFilter, params: PageParams) -> Page:
        query = self.restrict(
            select(Penjualan).options(
                joinedload(Penjualan.lokasi),
                joinedload(Penjualan.customer),
                joinedload(Penjualan.dibuat_oleh),
                joinedload(Penjualan.diposting_oleh),
                selectinload(Penjualan.detail),
            )
        )
        if filters.lokasi_id:
            query = query.where(Penjualan.lokasi_id == filters.lokasi_id)
        if filters.customer_id:
            query = query.where(Penjualan.customer_id == filters.customer_id)
        if filters.status:
            query = query.where(Penjualan.status == filters.status)
        if filters.dari:
            query = query.where(Penjualan.tanggal >= filters.dari)
        if filters.sampai:
            query = query.where(Penjualan.tanggal <= filters.sampai)
        query = self.apply_search(query, (Penjualan.kode, Penjualan.catatan), filters.q)
        if filters.sort == PenjualanSort.TOTAL:
            column = (
                select(
                    SqlMoney.total(PenjualanDetail.jumlah, PenjualanDetail.harga_satuan)
                )
                .where(PenjualanDetail.penjualan_id == Penjualan.id)
                .correlate(Penjualan)
                .scalar_subquery()
            )
        else:
            column = getattr(Penjualan, filters.sort.value)
        query = self.apply_sort(query, column, filters.arah)
        return self.paginate(query, params, self.to_summary)

    def detail(self, item_id: int) -> PenjualanDetailResponse:
        penjualan = self.get_or_404(
            item_id,
            joinedload(Penjualan.lokasi),
            joinedload(Penjualan.customer),
            joinedload(Penjualan.dibuat_oleh),
            joinedload(Penjualan.diposting_oleh),
            selectinload(Penjualan.detail)
            .joinedload(PenjualanDetail.produk)
            .joinedload(Produk.kategori),
        )
        return self.to_detail(penjualan)

    def create(self, data: PenjualanInput) -> PenjualanDetailResponse:
        lokasi = self.resolve_lokasi(data.lokasi_id)
        details = self.validate_and_build_details(data, lokasi)
        penjualan = Penjualan(
            kode=self.next_code("PJ", data.tanggal),
            status=PenjualanStatus.DRAF,
            tanggal=data.tanggal,
            lokasi_id=lokasi.id,
            customer_id=data.customer_id,
            catatan=data.catatan,
            dibuat_oleh_id=self.user.id,
            detail=details,
        )
        self.db.add(penjualan)
        self.db.commit()
        return self.detail(penjualan.id)

    def update(self, item_id: int, data: PenjualanInput) -> PenjualanDetailResponse:
        penjualan = self.get_or_404(item_id, for_update=True)
        self.ensure_status(penjualan, PenjualanStatus.DRAF)
        if data.lokasi_id is not None:
            lokasi = self.resolve_lokasi(data.lokasi_id)
        else:
            lokasi = self.db.get(Lokasi, penjualan.lokasi_id)
        details = self.validate_and_build_details(data, lokasi)
        penjualan.lokasi_id = lokasi.id
        penjualan.tanggal = data.tanggal
        penjualan.customer_id = data.customer_id
        penjualan.catatan = data.catatan
        self.replace_details(penjualan, details)
        self.db.commit()
        return self.detail(penjualan.id)

    def delete(self, item_id: int) -> None:
        penjualan = self.get_or_404(item_id, for_update=True)
        self.ensure_status(penjualan, PenjualanStatus.DRAF)
        self.db.delete(penjualan)
        self.db.commit()

    def posting(self, item_id: int) -> PenjualanDetailResponse:
        penjualan = self.get_or_404(item_id, for_update=True)
        self.ensure_status(penjualan, PenjualanStatus.DRAF)
        changes = [
            StockChange(
                lokasi_id=penjualan.lokasi_id,
                produk_id=row.produk_id,
                delta=-row.jumlah,
                field=f"items.{index}.jumlah",
            )
            for index, row in enumerate(penjualan.detail)
        ]
        MutasiStok(self.db, self.user).apply(
            changes, MutationSource(StokMutasiType.PENJUALAN, penjualan.id)
        )
        penjualan.status = PenjualanStatus.DIPOSTING
        penjualan.diposting_oleh_id = self.user.id
        penjualan.diposting_pada = Clock.now()
        self.db.commit()
        return self.detail(penjualan.id)

    def validate_and_build_details(
        self, data: PenjualanInput, lokasi: Lokasi
    ) -> list[PenjualanDetail]:
        products, product_errors = self.check_products(data.items)
        errors: dict[str, str] = {}
        if data.customer_id is None:
            if self.rules.requires_customer(lokasi):
                errors["customer_id"] = "Penjualan dari gudang wajib memilih customer"
        else:
            customer = self.db.get(Customer, data.customer_id)
            if customer is None:
                errors["customer_id"] = "Customer tidak ditemukan"
            elif not customer.aktif:
                errors["customer_id"] = "Customer sudah tidak aktif"
        errors.update(product_errors)

        details: list[PenjualanDetail] = []
        for index, item in enumerate(data.items):
            produk = products.get(item.produk_id)
            if produk is None:
                continue
            # BR-27: harga satuan terisi dari harga_jual produk bila tidak dikirim, minimal Rp1
            harga_satuan = (
                item.harga_satuan if item.harga_satuan is not None else produk.harga_jual
            )
            if harga_satuan <= 0:
                errors[f"items.{index}.harga_satuan"] = (
                    "Produk belum memiliki harga jual standar, isi harga satuan"
                )
                continue
            details.append(
                PenjualanDetail(
                    produk_id=item.produk_id,
                    jumlah=item.jumlah,
                    harga_satuan=harga_satuan,
                )
            )
        if errors:
            raise ValidationFailed(errors=errors)
        return details

    @staticmethod
    def to_summary(penjualan: Penjualan) -> PenjualanSummary:
        total = sum(row.jumlah * row.harga_satuan for row in penjualan.detail)
        return PenjualanSummary(
            id=penjualan.id,
            kode=penjualan.kode,
            status=penjualan.status,
            tanggal=penjualan.tanggal,
            lokasi=LokasiKontakRef.model_validate(penjualan.lokasi),
            customer=(
                CustomerRef.model_validate(penjualan.customer) if penjualan.customer else None
            ),
            nama_customer=penjualan.customer.nama if penjualan.customer else "Umum",
            catatan=penjualan.catatan,
            jumlah_item=len(penjualan.detail),
            total=total,
            dibuat_oleh=penjualan.dibuat_oleh.name,
            diposting_oleh=(
                penjualan.diposting_oleh.name if penjualan.diposting_oleh else None
            ),
            diposting_pada=penjualan.diposting_pada,
            created_at=penjualan.created_at,
            updated_at=penjualan.updated_at,
        )

    @classmethod
    def to_detail(cls, penjualan: Penjualan) -> PenjualanDetailResponse:
        summary = cls.to_summary(penjualan).model_dump()
        items = [
            PenjualanItemResponse(
                id=row.id,
                produk=PenjualanProduk.of(row.produk, harga_jual=row.produk.harga_jual),
                jumlah=row.jumlah,
                harga_satuan=row.harga_satuan,
                subtotal=row.jumlah * row.harga_satuan,
            )
            for row in penjualan.detail
        ]
        return PenjualanDetailResponse(**summary, items=items)
