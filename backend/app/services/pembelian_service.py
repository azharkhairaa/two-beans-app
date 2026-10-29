from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.clock import Clock
from app.core.errors import ValidationFailed
from app.models import (
    KategoriType,
    Pembelian,
    PembelianDetail,
    PembelianStatus,
    Produk,
    StokMutasiType,
    Supplier,
    User,
)
from app.policies.dokumen_policy import PembelianPolicy
from app.schemas.common import LokasiKontakRef, Page, PageParams, SortDirection, UserRef
from app.schemas.pembelian import (
    PembelianDetailResponse,
    PembelianInput,
    PembelianItemInput,
    PembelianItemResponse,
    PembelianPesanInput,
    PembelianProduk,
    PembelianSummary,
    PembelianTerimaInput,
    SupplierRef,
)
from app.services.base import CrudService, DetailMatcher, DokumenService
from app.services.mutasi_stok import MutasiStok, MutationSource, StockChange

class PembelianSort(StrEnum):
    CREATED_AT = "created_at"
    TANGGAL_PESAN = "tanggal_pesan"
    KODE = "kode"

@dataclass(frozen=True)
class PembelianFilter:
    supplier_id: int | None = None
    status: PembelianStatus | None = None
    dari: date | None = None
    sampai: date | None = None
    q: str | None = None
    sort: PembelianSort = PembelianSort.CREATED_AT
    arah: SortDirection = SortDirection.DESC

class PembelianService(DokumenService[Pembelian]):
    model = Pembelian
    label = "Pembelian"

    def __init__(self, db: Session, user: User):
        super().__init__(db, user)
        # semua aksi pembelian khusus pengelola, jadi 403 muncul sebelum dokumen dicari (404/409)
        PembelianPolicy(user).ensure_can_manage()

    def can_access(self, obj: Pembelian) -> bool:
        # pembelian tidak dibatasi lokasi, hak kelola sudah diperiksa saat service dibuat
        return True

    def search(self, filters: PembelianFilter, params: PageParams) -> Page:
        query = select(Pembelian).options(
            joinedload(Pembelian.supplier),
            joinedload(Pembelian.lokasi),
            joinedload(Pembelian.dibuat_oleh),
            joinedload(Pembelian.dipesan_oleh),
            joinedload(Pembelian.diterima_oleh),
            selectinload(Pembelian.detail),
        )
        if filters.supplier_id:
            query = query.where(Pembelian.supplier_id == filters.supplier_id)
        if filters.status:
            query = query.where(Pembelian.status == filters.status)
        if filters.dari:
            query = query.where(
                func.coalesce(Pembelian.tanggal_pesan, CrudService.local_date(Pembelian.created_at))
                >= filters.dari
            )
        if filters.sampai:
            query = query.where(
                func.coalesce(Pembelian.tanggal_pesan, CrudService.local_date(Pembelian.created_at))
                <= filters.sampai
            )
        query = self.apply_search(query, (Pembelian.kode, Pembelian.catatan), filters.q)
        query = self.apply_sort(query, getattr(Pembelian, filters.sort.value), filters.arah)
        return self.paginate(query, params, self.to_summary)

    def detail(self, item_id: int) -> PembelianDetailResponse:
        pembelian = self.get_or_404(
            item_id,
            joinedload(Pembelian.supplier),
            joinedload(Pembelian.lokasi),
            joinedload(Pembelian.dibuat_oleh),
            joinedload(Pembelian.dipesan_oleh),
            joinedload(Pembelian.diterima_oleh),
            selectinload(Pembelian.detail)
            .joinedload(PembelianDetail.produk)
            .joinedload(Produk.kategori),
        )
        return self.to_detail(pembelian)

    def create(self, data: PembelianInput) -> PembelianDetailResponse:
        gudang_utama = self.resolve_gudang_utama()
        self.validate_draft(data)
        pembelian = Pembelian(
            kode=self.next_code("PO"),
            status=PembelianStatus.DRAF,
            supplier_id=data.supplier_id,
            lokasi_id=gudang_utama.id,
            tanggal_perkiraan=data.tanggal_perkiraan,
            catatan=data.catatan,
            dibuat_oleh_id=self.user.id,
            detail=self.build_details(data.items),
        )
        self.db.add(pembelian)
        self.db.commit()
        return self.detail(pembelian.id)

    def update(self, item_id: int, data: PembelianInput) -> PembelianDetailResponse:
        pembelian = self.get_or_404(item_id, for_update=True)
        self.ensure_status(pembelian, PembelianStatus.DRAF)
        self.validate_draft(data)
        pembelian.supplier_id = data.supplier_id
        pembelian.tanggal_perkiraan = data.tanggal_perkiraan
        pembelian.catatan = data.catatan
        self.replace_details(pembelian, self.build_details(data.items))
        self.db.commit()
        return self.detail(pembelian.id)

    def delete(self, item_id: int) -> None:
        pembelian = self.get_or_404(item_id, for_update=True)
        self.ensure_status(pembelian, PembelianStatus.DRAF)
        self.db.delete(pembelian)
        self.db.commit()

    def pesan(
        self, item_id: int, data: PembelianPesanInput | None = None
    ) -> PembelianDetailResponse:
        pembelian = self.get_or_404(item_id, for_update=True)
        self.ensure_status(pembelian, PembelianStatus.DRAF)
        tanggal_pesan = (
            data.tanggal_pesan
            if data is not None and data.tanggal_pesan is not None
            else Clock.today()
        )
        if data is not None and "tanggal_perkiraan" in data.model_fields_set:
            pembelian.tanggal_perkiraan = data.tanggal_perkiraan
        errors: dict[str, str] = {}
        supplier = self.db.get(Supplier, pembelian.supplier_id)
        if supplier is None or not supplier.aktif:
            errors["supplier_id"] = "Supplier sudah tidak aktif"
        if (
            pembelian.tanggal_perkiraan is not None
            and pembelian.tanggal_perkiraan < tanggal_pesan
        ):
            errors["tanggal_perkiraan"] = (
                "Tanggal perkiraan tiba tidak boleh sebelum tanggal pesan"
            )
        if errors:
            raise ValidationFailed(errors=errors)
        pembelian.status = PembelianStatus.DIPESAN
        pembelian.tanggal_pesan = tanggal_pesan
        pembelian.dipesan_oleh_id = self.user.id
        self.db.commit()
        return self.detail(pembelian.id)

    def batal(self, item_id: int) -> PembelianDetailResponse:
        pembelian = self.get_or_404(item_id, for_update=True)
        self.ensure_status(pembelian, PembelianStatus.DRAF, PembelianStatus.DIPESAN)
        pembelian.status = PembelianStatus.DIBATALKAN
        self.db.commit()
        return self.detail(pembelian.id)

    def terima(self, item_id: int, data: PembelianTerimaInput) -> PembelianDetailResponse:
        pembelian = self.get_or_404(item_id, for_update=True)
        self.ensure_status(pembelian, PembelianStatus.DIPESAN)
        received_map = self.validate_terima(pembelian, data)
        changes: list[StockChange] = []
        for index, row in enumerate(pembelian.detail):
            jumlah_diterima = received_map[row.produk_id]
            row.jumlah_diterima = jumlah_diterima
            changes.append(
                StockChange(
                    lokasi_id=pembelian.lokasi_id,
                    produk_id=row.produk_id,
                    delta=jumlah_diterima,
                    field=f"items.{index}.jumlah_diterima",
                )
            )
        MutasiStok(self.db, self.user).apply(
            changes, MutationSource(StokMutasiType.PEMBELIAN, pembelian.id)
        )
        for row in pembelian.detail:
            if row.jumlah_diterima and row.jumlah_diterima > 0:
                # BR-12: harga beli produk diperbarui ke harga satuan pembelian terakhir
                row.produk.harga_beli = row.harga_satuan
        if data.catatan is not None:
            pembelian.catatan = data.catatan
        pembelian.status = PembelianStatus.DITERIMA
        pembelian.diterima_oleh_id = self.user.id
        pembelian.diterima_pada = Clock.now()
        self.db.commit()
        return self.detail(pembelian.id)

    def validate_draft(self, data: PembelianInput) -> None:
        products, product_errors = self.check_products(data.items)
        errors: dict[str, str] = {}
        supplier = self.db.get(Supplier, data.supplier_id)
        if supplier is None:
            errors["supplier_id"] = "Supplier tidak ditemukan"
        elif not supplier.aktif:
            errors["supplier_id"] = "Supplier sudah tidak aktif"
        errors.update(product_errors)
        for index, item in enumerate(data.items):
            produk = products.get(item.produk_id)
            if produk is None:
                continue
            # BR-11: pembelian ke supplier tidak boleh berisi produk roasted_bean
            if produk.kategori.jenis == KategoriType.ROASTED_BEAN:
                errors[f"items.{index}.produk_id"] = (
                    "Produk roasted bean diproduksi sendiri dan tidak bisa dibeli dari supplier"
                )
        if errors:
            raise ValidationFailed(errors=errors)

    def validate_terima(self, pembelian: Pembelian, data: PembelianTerimaInput) -> dict[int, int]:
        matcher = DetailMatcher(self.label, pembelian.detail)
        for field, item, row in matcher.pairs(data.items):
            if item.jumlah_diterima > row.jumlah:
                matcher.errors[f"{field}.jumlah_diterima"] = (
                    f"Maksimal sebesar jumlah dipesan ({row.jumlah})"
                )
        received_map = {
            produk_id: item.jumlah_diterima for produk_id, item in matcher.matched.items()
        }
        if not matcher.complete:
            matcher.errors.setdefault("items", "Semua produk di pembelian wajib dikonfirmasi")
        elif received_map and all(jumlah == 0 for jumlah in received_map.values()):
            matcher.errors["items"] = (
                "Minimal satu produk harus diterima lebih dari 0. "
                "Gunakan aksi batal bila pesanan tidak jadi diterima"
            )
        matcher.raise_if_invalid()
        return received_map

    @staticmethod
    def build_details(items: list[PembelianItemInput]) -> list[PembelianDetail]:
        return [
            PembelianDetail(
                produk_id=item.produk_id,
                jumlah=item.jumlah,
                harga_satuan=item.harga_satuan,
            )
            for item in items
        ]

    @staticmethod
    def to_summary(pembelian: Pembelian) -> PembelianSummary:
        total_pesanan = sum(row.jumlah * row.harga_satuan for row in pembelian.detail)
        total_diterima = (
            sum((row.jumlah_diterima or 0) * row.harga_satuan for row in pembelian.detail)
            if pembelian.status == PembelianStatus.DITERIMA
            else None
        )
        return PembelianSummary(
            id=pembelian.id,
            kode=pembelian.kode,
            status=pembelian.status,
            supplier=SupplierRef.model_validate(pembelian.supplier),
            lokasi=LokasiKontakRef.model_validate(pembelian.lokasi),
            tanggal_pesan=pembelian.tanggal_pesan,
            tanggal_perkiraan=pembelian.tanggal_perkiraan,
            catatan=pembelian.catatan,
            jumlah_item=len(pembelian.detail),
            total_pesanan=total_pesanan,
            total_diterima=total_diterima,
            dibuat_oleh=UserRef.model_validate(pembelian.dibuat_oleh),
            dipesan_oleh=(
                UserRef.model_validate(pembelian.dipesan_oleh)
                if pembelian.dipesan_oleh
                else None
            ),
            diterima_oleh=(
                UserRef.model_validate(pembelian.diterima_oleh)
                if pembelian.diterima_oleh
                else None
            ),
            diterima_pada=pembelian.diterima_pada,
            created_at=pembelian.created_at,
            updated_at=pembelian.updated_at,
        )

    @classmethod
    def to_detail(cls, pembelian: Pembelian) -> PembelianDetailResponse:
        summary = cls.to_summary(pembelian).model_dump()
        items = [
            PembelianItemResponse(
                id=row.id,
                produk=PembelianProduk.of(row.produk, harga_beli=row.produk.harga_beli),
                jumlah=row.jumlah,
                harga_satuan=row.harga_satuan,
                subtotal=row.jumlah * row.harga_satuan,
                jumlah_diterima=row.jumlah_diterima,
                subtotal_diterima=(
                    row.jumlah_diterima * row.harga_satuan
                    if row.jumlah_diterima is not None
                    else None
                ),
            )
            for row in pembelian.detail
        ]
        return PembelianDetailResponse(**summary, items=items)
