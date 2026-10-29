from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.core.clock import Clock
from app.core.errors import Conflict, ValidationFailed
from app.models import (
    TRANSAKSI_REASONS,
    KategoriType,
    Produk,
    StokMutasiType,
    Transaksi,
    TransaksiDetail,
    TransaksiStatus,
    TransaksiType,
)
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.lokasi import LokasiSummary
from app.schemas.transaksi import (
    TransaksiDetailResponse,
    TransaksiInput,
    TransaksiItemInput,
    TransaksiItemResponse,
    TransaksiProduk,
    TransaksiSummary,
    TransaksiUpdate,
)
from app.services.base import DokumenService
from app.services.mutasi_stok import MutasiStok, MutationSource, StockChange

class TransaksiSort(StrEnum):
    TANGGAL = "tanggal"
    KODE = "kode"
    CREATED_AT = "created_at"

@dataclass(frozen=True)
class TransaksiFilter:
    lokasi_id: int | None = None
    jenis: TransaksiType | None = None
    status: TransaksiStatus | None = None
    alasan: str | None = None
    dari: date | None = None
    sampai: date | None = None
    q: str | None = None
    sort: TransaksiSort = TransaksiSort.TANGGAL
    arah: SortDirection = SortDirection.DESC

class TransaksiRules:
    # BR-13: alasan harus sesuai jenis transaksi, roasting khusus green bean dan hasil roasting
    # khusus biji kopi sangrai. Penjualan punya dokumen sendiri
    def check(
        self, data: TransaksiUpdate, jenis: str, products: dict[int, Produk]
    ) -> dict[str, str]:
        errors: dict[str, str] = {}
        allowed = TRANSAKSI_REASONS[TransaksiType(jenis)]
        if data.alasan == "penjualan":
            errors["alasan"] = "Penjualan dicatat lewat dokumen penjualan, bukan transaksi keluar"
        elif data.alasan not in allowed:
            choices = ", ".join(allowed)
            errors["alasan"] = f"Alasan transaksi {jenis} harus salah satu dari {choices}"
        for index, item in enumerate(data.items):
            if jenis == TransaksiType.PENYESUAIAN:
                if item.jumlah == 0:
                    errors[f"items.{index}.jumlah"] = "Jumlah penyesuaian tidak boleh 0"
            elif item.jumlah < 1:
                errors[f"items.{index}.jumlah"] = "Minimal 1"
            produk = products.get(item.produk_id)
            if produk is None:
                continue
            kategori_jenis = produk.kategori.jenis
            if (
                jenis == TransaksiType.KELUAR
                and data.alasan == "roasting"
                and kategori_jenis != KategoriType.GREEN_BEAN
            ):
                errors[f"items.{index}.produk_id"] = (
                    "Alasan roasting hanya untuk produk green bean"
                )
            elif (
                jenis == TransaksiType.MASUK
                and data.alasan == "hasil_roasting"
                and kategori_jenis != KategoriType.ROASTED_BEAN
            ):
                errors[f"items.{index}.produk_id"] = (
                    "Alasan hasil roasting hanya untuk produk roasted bean"
                )
        return errors

class TransaksiService(DokumenService[Transaksi]):
    model = Transaksi
    label = "Transaksi"
    rules = TransaksiRules()
    PREFIX = {
        TransaksiType.MASUK: "BM",
        TransaksiType.KELUAR: "BK",
        TransaksiType.PENYESUAIAN: "PS",
    }

    def search(self, filters: TransaksiFilter, params: PageParams) -> Page:
        query = self.restrict(
            select(Transaksi).options(
                joinedload(Transaksi.lokasi),
                joinedload(Transaksi.dibuat_oleh),
                joinedload(Transaksi.diposting_oleh),
                selectinload(Transaksi.detail),
            )
        )
        if filters.lokasi_id:
            query = query.where(Transaksi.lokasi_id == filters.lokasi_id)
        if filters.jenis:
            query = query.where(Transaksi.jenis == filters.jenis)
        if filters.status:
            query = query.where(Transaksi.status == filters.status)
        if filters.alasan:
            query = query.where(Transaksi.alasan == filters.alasan)
        if filters.dari:
            query = query.where(Transaksi.tanggal >= filters.dari)
        if filters.sampai:
            query = query.where(Transaksi.tanggal <= filters.sampai)
        query = self.apply_search(query, (Transaksi.kode, Transaksi.keterangan), filters.q)
        query = self.apply_sort(query, getattr(Transaksi, filters.sort.value), filters.arah)
        return self.paginate(query, params, self.to_summary)

    def detail(self, item_id: int) -> TransaksiDetailResponse:
        transaksi = self.get_or_404(
            item_id,
            joinedload(Transaksi.lokasi),
            joinedload(Transaksi.dibuat_oleh),
            joinedload(Transaksi.diposting_oleh),
            selectinload(Transaksi.detail)
            .joinedload(TransaksiDetail.produk)
            .joinedload(Produk.kategori),
        )
        return self.to_detail(transaksi)

    def create(self, data: TransaksiInput) -> TransaksiDetailResponse:
        lokasi = self.resolve_lokasi(data.lokasi_id)
        self.validate(data, data.jenis)
        transaksi = Transaksi(
            kode=self.next_code(self.PREFIX[data.jenis]),
            jenis=data.jenis,
            status=TransaksiStatus.DRAF,
            tanggal=data.tanggal,
            lokasi_id=lokasi.id,
            alasan=data.alasan,
            keterangan=data.keterangan,
            catatan=data.catatan,
            dibuat_oleh_id=self.user.id,
            detail=self.build_details(data.items),
        )
        self.db.add(transaksi)
        self.db.commit()
        return self.detail(transaksi.id)

    def update(self, item_id: int, data: TransaksiUpdate) -> TransaksiDetailResponse:
        transaksi = self.get_or_404(item_id, for_update=True)
        self.ensure_status(transaksi, TransaksiStatus.DRAF)
        if data.jenis is not None and data.jenis != transaksi.jenis:
            message = "Jenis transaksi tidak bisa diubah"
            raise Conflict(message, {"jenis": message})
        if data.lokasi_id is not None:
            transaksi.lokasi_id = self.resolve_lokasi(data.lokasi_id).id
        self.validate(data, transaksi.jenis)
        transaksi.tanggal = data.tanggal
        transaksi.alasan = data.alasan
        transaksi.keterangan = data.keterangan
        transaksi.catatan = data.catatan
        self.replace_details(transaksi, self.build_details(data.items))
        self.db.commit()
        return self.detail(transaksi.id)

    def delete(self, item_id: int) -> None:
        transaksi = self.get_or_404(item_id, for_update=True)
        self.ensure_status(transaksi, TransaksiStatus.DRAF)
        self.db.delete(transaksi)
        self.db.commit()

    def posting(self, item_id: int) -> TransaksiDetailResponse:
        transaksi = self.get_or_404(item_id, for_update=True)
        self.ensure_status(transaksi, TransaksiStatus.DRAF)
        sign = -1 if transaksi.jenis == TransaksiType.KELUAR else 1
        changes = [
            StockChange(
                lokasi_id=transaksi.lokasi_id,
                produk_id=row.produk_id,
                delta=sign * row.jumlah,
                field=f"items.{index}.jumlah",
            )
            for index, row in enumerate(transaksi.detail)
        ]
        source = MutationSource(StokMutasiType(transaksi.jenis), transaksi.id)
        MutasiStok(self.db, self.user).apply(changes, source)
        transaksi.status = TransaksiStatus.DIPOSTING
        transaksi.diposting_oleh_id = self.user.id
        transaksi.diposting_pada = Clock.now()
        self.db.commit()
        return self.detail(transaksi.id)

    def validate(self, data: TransaksiUpdate, jenis: str) -> None:
        products, product_errors = self.check_products(data.items)
        errors = product_errors | self.rules.check(data, jenis, products)
        if errors:
            raise ValidationFailed(errors=errors)

    @staticmethod
    def build_details(items: list[TransaksiItemInput]) -> list[TransaksiDetail]:
        return [TransaksiDetail(produk_id=item.produk_id, jumlah=item.jumlah) for item in items]

    @staticmethod
    def to_summary(transaksi: Transaksi) -> TransaksiSummary:
        return TransaksiSummary(
            id=transaksi.id,
            kode=transaksi.kode,
            jenis=transaksi.jenis,
            status=transaksi.status,
            tanggal=transaksi.tanggal,
            lokasi=LokasiSummary.model_validate(transaksi.lokasi),
            alasan=transaksi.alasan,
            keterangan=transaksi.keterangan,
            catatan=transaksi.catatan,
            jumlah_item=len(transaksi.detail),
            dibuat_oleh=transaksi.dibuat_oleh.name,
            diposting_oleh=transaksi.diposting_oleh.name if transaksi.diposting_oleh else None,
            diposting_pada=transaksi.diposting_pada,
            created_at=transaksi.created_at,
            updated_at=transaksi.updated_at,
        )

    @classmethod
    def to_detail(cls, transaksi: Transaksi) -> TransaksiDetailResponse:
        summary = cls.to_summary(transaksi).model_dump()
        items = [
            TransaksiItemResponse(
                id=row.id,
                produk=TransaksiProduk.of(row.produk, harga_beli=row.produk.harga_beli),
                jumlah=row.jumlah,
            )
            for row in transaksi.detail
        ]
        return TransaksiDetailResponse(**summary, items=items)
