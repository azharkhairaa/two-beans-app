from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.clock import Clock
from app.core.errors import NotFound, ValidationFailed
from app.models import (
    Lokasi,
    LokasiType,
    Pengiriman,
    PengirimanDetail,
    PengirimanStatus,
    Permintaan,
    PermintaanDetail,
    PermintaanStatus,
    Produk,
    Stok,
    User,
)
from app.policies.dokumen_policy import PermintaanPolicy
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.pengiriman import PengirimanLokasi, UserRef
from app.schemas.permintaan import (
    PengirimanRef,
    PermintaanDetailResponse,
    PermintaanInput,
    PermintaanItemInput,
    PermintaanItemResponse,
    PermintaanProduk,
    PermintaanSetujuiInput,
    PermintaanSummary,
    PermintaanTolakInput,
)
from app.services.base import CrudService, DokumenService

class PermintaanSort(StrEnum):
    CREATED_AT = "created_at"
    TANGGAL_BUTUH = "tanggal_butuh"
    KODE = "kode"


@dataclass(frozen=True)
class PermintaanFilter:
    lokasi_peminta_id: int | None = None
    status: PermintaanStatus | None = None
    dari: date | None = None
    sampai: date | None = None
    q: str | None = None
    sort: PermintaanSort = PermintaanSort.CREATED_AT
    arah: SortDirection = SortDirection.DESC


class PermintaanService(DokumenService[Permintaan]):
    model = Permintaan
    label = "Permintaan"

    def __init__(self, db: Session, user: User):
        super().__init__(db, user)
        self.permintaan_policy = PermintaanPolicy(user)

    def can_access(self, obj: Permintaan) -> bool:
        return self.permintaan_policy.can_read(obj)

    def search(self, filters: PermintaanFilter, params: PageParams) -> Page:
        query = self.permintaan_policy.restrict(
            select(Permintaan).options(
                joinedload(Permintaan.lokasi_peminta),
                joinedload(Permintaan.lokasi_sumber),
                joinedload(Permintaan.pengiriman),
                joinedload(Permintaan.diajukan_oleh),
                joinedload(Permintaan.diproses_oleh),
                selectinload(Permintaan.detail),
            )
        )
        if filters.lokasi_peminta_id:
            query = query.where(Permintaan.lokasi_peminta_id == filters.lokasi_peminta_id)
        if filters.status:
            query = query.where(Permintaan.status == filters.status)
        if filters.dari:
            query = query.where(func.date(Permintaan.created_at) >= filters.dari)
        if filters.sampai:
            query = query.where(func.date(Permintaan.created_at) <= filters.sampai)
        if filters.q:
            columns = (Permintaan.kode, Permintaan.catatan)
            query = query.where(
                or_(*(CrudService.contains(column, filters.q) for column in columns))
            )
        column = getattr(Permintaan, filters.sort.value)
        desc = filters.arah == SortDirection.DESC
        order = (
            (column.desc(), Permintaan.id.desc()) if desc else (column.asc(), Permintaan.id.asc())
        )
        return self.paginate(query.order_by(*order), params, self.to_summary)

    def detail(self, item_id: int) -> PermintaanDetailResponse:
        query = (
            select(Permintaan)
            .options(
                joinedload(Permintaan.lokasi_peminta),
                joinedload(Permintaan.lokasi_sumber),
                joinedload(Permintaan.pengiriman),
                joinedload(Permintaan.diajukan_oleh),
                joinedload(Permintaan.diproses_oleh),
                selectinload(Permintaan.detail)
                .joinedload(PermintaanDetail.produk)
                .joinedload(Produk.kategori),
            )
            .where(Permintaan.id == item_id)
        )
        permintaan = self.db.scalar(query)
        if permintaan is None or not self.can_access(permintaan):
            raise NotFound("Permintaan tidak ditemukan")
        stok_map = self.load_stock_map(
            permintaan.lokasi_sumber_id, {row.produk_id for row in permintaan.detail}
        )
        return self.to_detail(permintaan, stok_map)

    def create(self, data: PermintaanInput) -> PermintaanDetailResponse:
        lokasi_peminta = self.resolve_lokasi(data.lokasi_peminta_id, field="lokasi_peminta_id")
        self.permintaan_policy.ensure_can_create(lokasi_peminta)
        lokasi_sumber = self.resolve_gudang_utama()
        self.validate_request(data, lokasi_peminta, lokasi_sumber)
        permintaan = Permintaan(
            kode=self.next_code("PM"),
            status=PermintaanStatus.DIAJUKAN,
            lokasi_peminta_id=lokasi_peminta.id,
            lokasi_sumber_id=lokasi_sumber.id,
            tanggal_butuh=data.tanggal_butuh,
            catatan=data.catatan,
            diajukan_oleh_id=self.user.id,
            detail=self.build_details(data.items),
        )
        self.db.add(permintaan)
        self.db.commit()
        return self.detail(permintaan.id)

    def update(self, item_id: int, data: PermintaanInput) -> PermintaanDetailResponse:
        permintaan = self.get_or_404(item_id, for_update=True)
        self.permintaan_policy.ensure_can_edit_or_cancel(permintaan)
        self.ensure_status(permintaan, PermintaanStatus.DIAJUKAN)
        if data.lokasi_peminta_id is not None:
            lokasi_peminta = self.resolve_lokasi(
                data.lokasi_peminta_id, field="lokasi_peminta_id"
            )
        else:
            lokasi_peminta = self.db.get(Lokasi, permintaan.lokasi_peminta_id)
        lokasi_sumber = self.db.get(Lokasi, permintaan.lokasi_sumber_id)
        self.validate_request(data, lokasi_peminta, lokasi_sumber)
        permintaan.lokasi_peminta_id = lokasi_peminta.id
        permintaan.tanggal_butuh = data.tanggal_butuh
        permintaan.catatan = data.catatan
        self.replace_details(permintaan, self.build_details(data.items))
        self.db.commit()
        return self.detail(permintaan.id)

    def batal(self, item_id: int) -> PermintaanDetailResponse:
        permintaan = self.get_or_404(item_id, for_update=True)
        self.permintaan_policy.ensure_can_edit_or_cancel(permintaan)
        self.ensure_status(permintaan, PermintaanStatus.DIAJUKAN)
        permintaan.status = PermintaanStatus.DIBATALKAN
        self.db.commit()
        return self.detail(permintaan.id)

    def setujui(self, item_id: int, data: PermintaanSetujuiInput) -> PermintaanDetailResponse:
        permintaan = self.get_or_404(item_id, for_update=True)
        self.permintaan_policy.ensure_can_process(permintaan)
        self.ensure_status(permintaan, PermintaanStatus.DIAJUKAN)
        approved_map = self.validate_setujui(permintaan, data)
        for row in permintaan.detail:
            row.jumlah_disetujui = approved_map[row.produk_id]
        permintaan.status = PermintaanStatus.DISETUJUI
        permintaan.diproses_oleh_id = self.user.id
        permintaan.diproses_pada = Clock.now()
        pengiriman = Pengiriman(
            kode=self.next_code("KR", data.tanggal_kirim),
            status=PengirimanStatus.DRAF,
            lokasi_asal_id=permintaan.lokasi_sumber_id,
            lokasi_tujuan_id=permintaan.lokasi_peminta_id,
            permintaan_id=permintaan.id,
            tanggal_kirim=data.tanggal_kirim,
            catatan=data.catatan if data.catatan is not None else permintaan.catatan,
            dibuat_oleh_id=self.user.id,
            detail=[
                PengirimanDetail(produk_id=row.produk_id, jumlah_dikirim=row.jumlah_disetujui)
                for row in permintaan.detail
                if row.jumlah_disetujui and row.jumlah_disetujui > 0
            ],
        )
        self.db.add(pengiriman)
        self.db.commit()
        return self.detail(permintaan.id)

    def tolak(self, item_id: int, data: PermintaanTolakInput) -> PermintaanDetailResponse:
        permintaan = self.get_or_404(item_id, for_update=True)
        self.permintaan_policy.ensure_can_process(permintaan)
        self.ensure_status(permintaan, PermintaanStatus.DIAJUKAN)
        permintaan.status = PermintaanStatus.DITOLAK
        permintaan.diproses_oleh_id = self.user.id
        permintaan.diproses_pada = Clock.now()
        permintaan.alasan_penolakan = data.alasan_penolakan
        self.db.commit()
        return self.detail(permintaan.id)

    def resolve_gudang_utama(self) -> Lokasi:
        gudang_utama = self.db.scalar(
            select(Lokasi).where(
                Lokasi.jenis == LokasiType.GUDANG_UTAMA, Lokasi.aktif.is_(True)
            )
        )
        if gudang_utama is None:
            raise ValidationFailed(errors={"lokasi_sumber_id": "Gudang utama tidak ditemukan"})
        return gudang_utama

    def load_stock_map(self, lokasi_id: int, produk_ids: set[int]) -> dict[int, int]:
        if not produk_ids:
            return {}
        rows = self.db.execute(
            select(Stok.produk_id, Stok.jumlah).where(
                Stok.lokasi_id == lokasi_id, Stok.produk_id.in_(produk_ids)
            )
        ).all()
        return dict(rows)

    def validate_request(
        self, data: PermintaanInput, lokasi_peminta: Lokasi, lokasi_sumber: Lokasi
    ) -> None:
        products, product_errors = self.check_products(data.items)
        errors: dict[str, str] = {}
        if lokasi_peminta.jenis not in PermintaanPolicy.REQUESTER_TYPES:
            errors["lokasi_peminta_id"] = (
                "Permintaan hanya bisa diajukan dari gudang cabang atau outlet"
            )
        errors.update(product_errors)
        stok_map = self.load_stock_map(lokasi_sumber.id, set(products))
        for index, item in enumerate(data.items):
            if item.produk_id not in products:
                continue
            if stok_map.get(item.produk_id, 0) <= 0:
                errors[f"items.{index}.produk_id"] = "Stok di gudang utama kosong"
        if errors:
            raise ValidationFailed(errors=errors)

    def validate_setujui(
        self, permintaan: Permintaan, data: PermintaanSetujuiInput
    ) -> dict[int, int]:
        detail_by_produk = {row.produk_id: row for row in permintaan.detail}
        stok_map = self.load_stock_map(permintaan.lokasi_sumber_id, set(detail_by_produk))
        errors: dict[str, str] = {}
        approved_map: dict[int, int] = {}
        for index, item in enumerate(data.items):
            row = detail_by_produk.get(item.produk_id)
            if row is None:
                errors[f"items.{index}.produk_id"] = "Produk tidak ada di permintaan ini"
                continue
            if item.produk_id in approved_map:
                errors[f"items.{index}.produk_id"] = (
                    "Produk tidak boleh duplikat dalam satu dokumen"
                )
                continue
            approved_map[item.produk_id] = item.jumlah_disetujui
            stok_tersedia = stok_map.get(item.produk_id, 0)
            if item.jumlah_disetujui > row.jumlah_diminta:
                errors[f"items.{index}.jumlah_disetujui"] = (
                    f"Maksimal sebesar jumlah diminta ({row.jumlah_diminta})"
                )
            elif item.jumlah_disetujui > stok_tersedia:
                errors[f"items.{index}.jumlah_disetujui"] = (
                    f"Melebihi stok gudang utama ({stok_tersedia} {row.produk.satuan})"
                )
        if set(detail_by_produk) != set(approved_map):
            errors.setdefault("items", "Semua produk di permintaan wajib diputuskan")
        elif approved_map and all(jumlah == 0 for jumlah in approved_map.values()):
            errors["items"] = (
                "Minimal satu produk harus disetujui lebih dari 0. "
                "Gunakan aksi tolak bila tidak ada yang disetujui"
            )
        if errors:
            raise ValidationFailed(errors=errors)
        return approved_map

    @staticmethod
    def build_details(items: list[PermintaanItemInput]) -> list[PermintaanDetail]:
        return [
            PermintaanDetail(produk_id=item.produk_id, jumlah_diminta=item.jumlah_diminta)
            for item in items
        ]

    @staticmethod
    def to_summary(permintaan: Permintaan) -> PermintaanSummary:
        return PermintaanSummary(
            id=permintaan.id,
            kode=permintaan.kode,
            status=permintaan.status,
            lokasi_peminta=PengirimanLokasi.model_validate(permintaan.lokasi_peminta),
            lokasi_sumber=PengirimanLokasi.model_validate(permintaan.lokasi_sumber),
            tanggal_butuh=permintaan.tanggal_butuh,
            catatan=permintaan.catatan,
            alasan_penolakan=permintaan.alasan_penolakan,
            jumlah_item=len(permintaan.detail),
            pengiriman=(
                PengirimanRef.model_validate(permintaan.pengiriman)
                if permintaan.pengiriman
                else None
            ),
            diajukan_oleh=UserRef.model_validate(permintaan.diajukan_oleh),
            diproses_oleh=(
                UserRef.model_validate(permintaan.diproses_oleh)
                if permintaan.diproses_oleh
                else None
            ),
            diproses_pada=permintaan.diproses_pada,
            created_at=permintaan.created_at,
            updated_at=permintaan.updated_at,
        )

    @classmethod
    def to_detail(
        cls, permintaan: Permintaan, stok_map: dict[int, int]
    ) -> PermintaanDetailResponse:
        summary = cls.to_summary(permintaan).model_dump()
        items = [
            PermintaanItemResponse(
                id=row.id,
                produk=PermintaanProduk(
                    id=row.produk.id,
                    sku=row.produk.sku,
                    nama=row.produk.nama,
                    satuan=row.produk.satuan,
                    jenis=row.produk.kategori.jenis,
                    harga_beli=row.produk.harga_beli,
                    stok_sumber=stok_map.get(row.produk_id, 0),
                ),
                jumlah_diminta=row.jumlah_diminta,
                jumlah_disetujui=row.jumlah_disetujui,
            )
            for row in permintaan.detail
        ]
        return PermintaanDetailResponse(**summary, items=items)
