from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.clock import Clock
from app.core.errors import NotFound, ValidationFailed
from app.models import (
    Lokasi,
    Pengiriman,
    PengirimanDetail,
    PengirimanStatus,
    Permintaan,
    PermintaanStatus,
    Produk,
    StokMutasiType,
    User,
    UserRole,
    UserStatus,
)
from app.policies.dokumen_policy import PengirimanPolicy
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.pengiriman import (
    PengirimanDetailResponse,
    PengirimanInput,
    PengirimanItemInput,
    PengirimanItemResponse,
    PengirimanKirimInput,
    PengirimanLokasi,
    PengirimanProduk,
    PengirimanSummary,
    PengirimanTerimaInput,
    PermintaanRef,
    UserRef,
)
from app.services.base import CrudService, DokumenService
from app.services.mutasi_stok import MutasiStok, MutationSource, StockChange

class PengirimanSort(StrEnum):
    TANGGAL_KIRIM = "tanggal_kirim"
    KODE = "kode"
    CREATED_AT = "created_at"

@dataclass(frozen=True)
class PengirimanFilter:
    lokasi_asal_id: int | None = None
    lokasi_tujuan_id: int | None = None
    status: PengirimanStatus | None = None
    deliveryman_id: int | None = None
    dari: date | None = None
    sampai: date | None = None
    q: str | None = None
    sort: PengirimanSort = PengirimanSort.TANGGAL_KIRIM
    arah: SortDirection = SortDirection.DESC

class PengirimanService(DokumenService[Pengiriman]):
    model = Pengiriman
    label = "Pengiriman"

    def __init__(self, db: Session, user: User):
        super().__init__(db, user)
        self.pengiriman_policy = PengirimanPolicy(user)

    def can_access(self, obj: Pengiriman) -> bool:
        return self.pengiriman_policy.can_read(obj)

    def search(self, filters: PengirimanFilter, params: PageParams) -> Page:
        query = self.pengiriman_policy.restrict(
            select(Pengiriman).options(
                joinedload(Pengiriman.lokasi_asal),
                joinedload(Pengiriman.lokasi_tujuan),
                joinedload(Pengiriman.permintaan),
                joinedload(Pengiriman.deliveryman),
                joinedload(Pengiriman.dibuat_oleh),
                joinedload(Pengiriman.dikirim_oleh),
                joinedload(Pengiriman.diterima_oleh),
                selectinload(Pengiriman.detail).joinedload(PengirimanDetail.produk),
            )
        )
        if filters.lokasi_asal_id:
            query = query.where(Pengiriman.lokasi_asal_id == filters.lokasi_asal_id)
        if filters.lokasi_tujuan_id:
            query = query.where(Pengiriman.lokasi_tujuan_id == filters.lokasi_tujuan_id)
        if filters.status:
            query = query.where(Pengiriman.status == filters.status)
        if filters.deliveryman_id:
            query = query.where(Pengiriman.deliveryman_id == filters.deliveryman_id)
        if filters.dari:
            query = query.where(Pengiriman.tanggal_kirim >= filters.dari)
        if filters.sampai:
            query = query.where(Pengiriman.tanggal_kirim <= filters.sampai)
        if filters.q:
            columns = (Pengiriman.kode, Pengiriman.catatan)
            query = query.where(
                or_(*(CrudService.contains(column, filters.q) for column in columns))
            )
        column = getattr(Pengiriman, filters.sort.value)
        desc = filters.arah == SortDirection.DESC
        order = (
            (column.desc(), Pengiriman.id.desc()) if desc else (column.asc(), Pengiriman.id.asc())
        )
        return self.paginate(query.order_by(*order), params, self.to_summary)

    def detail(self, item_id: int) -> PengirimanDetailResponse:
        query = (
            select(Pengiriman)
            .options(
                joinedload(Pengiriman.lokasi_asal),
                joinedload(Pengiriman.lokasi_tujuan),
                joinedload(Pengiriman.permintaan),
                joinedload(Pengiriman.deliveryman),
                joinedload(Pengiriman.dibuat_oleh),
                joinedload(Pengiriman.dikirim_oleh),
                joinedload(Pengiriman.diterima_oleh),
                selectinload(Pengiriman.detail)
                .joinedload(PengirimanDetail.produk)
                .joinedload(Produk.kategori),
            )
            .where(Pengiriman.id == item_id)
        )
        pengiriman = self.db.scalar(query)
        if pengiriman is None or not self.can_access(pengiriman):
            raise NotFound("Pengiriman tidak ditemukan")
        return self.to_detail(pengiriman)

    def create(self, data: PengirimanInput) -> PengirimanDetailResponse:
        self.pengiriman_policy.ensure_can_create()
        lokasi_asal = self.resolve_lokasi(data.lokasi_asal_id, field="lokasi_asal_id")
        self.validate_draft(data, lokasi_asal)
        pengiriman = Pengiriman(
            kode=self.next_code("KR", data.tanggal_kirim),
            status=PengirimanStatus.DRAF,
            lokasi_asal_id=lokasi_asal.id,
            lokasi_tujuan_id=data.lokasi_tujuan_id,
            tanggal_kirim=data.tanggal_kirim,
            deliveryman_id=data.deliveryman_id,
            kendaraan_jenis=data.kendaraan_jenis,
            kendaraan_nomor=data.kendaraan_nomor,
            catatan=data.catatan,
            dibuat_oleh_id=self.user.id,
            detail=self.build_details(data.items),
        )
        self.db.add(pengiriman)
        self.db.commit()
        return self.detail(pengiriman.id)

    def update(self, item_id: int, data: PengirimanInput) -> PengirimanDetailResponse:
        pengiriman = self.get_or_404(item_id, for_update=True)
        self.pengiriman_policy.ensure_can_send(pengiriman)
        self.ensure_status(pengiriman, PengirimanStatus.DRAF)
        if data.lokasi_asal_id is not None:
            lokasi_asal = self.resolve_lokasi(data.lokasi_asal_id, field="lokasi_asal_id")
        else:
            lokasi_asal = self.db.get(Lokasi, pengiriman.lokasi_asal_id)
        self.validate_draft(data, lokasi_asal)
        pengiriman.lokasi_asal_id = lokasi_asal.id
        pengiriman.lokasi_tujuan_id = data.lokasi_tujuan_id
        pengiriman.tanggal_kirim = data.tanggal_kirim
        pengiriman.deliveryman_id = data.deliveryman_id
        pengiriman.kendaraan_jenis = data.kendaraan_jenis
        pengiriman.kendaraan_nomor = data.kendaraan_nomor
        pengiriman.catatan = data.catatan
        self.replace_details(pengiriman, self.build_details(data.items))
        self.db.commit()
        return self.detail(pengiriman.id)

    def delete(self, item_id: int) -> None:
        pengiriman = self.get_or_404(item_id, for_update=True)
        self.pengiriman_policy.ensure_can_send(pengiriman)
        self.ensure_status(pengiriman, PengirimanStatus.DRAF)
        if pengiriman.permintaan_id is None:
            self.db.delete(pengiriman)
        else:
            # draf dari permintaan tidak dihapus tetapi dibatalkan dan permintaan kembali diajukan
            permintaan = self.db.get(Permintaan, pengiriman.permintaan_id)
            pengiriman.status = PengirimanStatus.DIBATALKAN
            pengiriman.permintaan_id = None
            if permintaan is not None:
                permintaan.status = PermintaanStatus.DIAJUKAN
                permintaan.diproses_oleh_id = None
                permintaan.diproses_pada = None
                for row in permintaan.detail:
                    row.jumlah_disetujui = None
        self.db.commit()

    def kirim(
        self, item_id: int, data: PengirimanKirimInput | None = None
    ) -> PengirimanDetailResponse:
        pengiriman = self.get_or_404(item_id, for_update=True)
        self.pengiriman_policy.ensure_can_send(pengiriman)
        self.ensure_status(pengiriman, PengirimanStatus.DRAF)
        if data is not None:
            if "deliveryman_id" in data.model_fields_set:
                pengiriman.deliveryman_id = data.deliveryman_id
            if "kendaraan_jenis" in data.model_fields_set:
                pengiriman.kendaraan_jenis = data.kendaraan_jenis
            if "kendaraan_nomor" in data.model_fields_set:
                pengiriman.kendaraan_nomor = data.kendaraan_nomor
        self.validate_kirim(pengiriman)
        changes = [
            StockChange(
                lokasi_id=pengiriman.lokasi_asal_id,
                produk_id=row.produk_id,
                delta=-row.jumlah_dikirim,
                field=f"items.{index}.jumlah_dikirim",
            )
            for index, row in enumerate(pengiriman.detail)
        ]
        MutasiStok(self.db, self.user).apply(
            changes, MutationSource(StokMutasiType.KIRIM, pengiriman.id)
        )
        pengiriman.status = PengirimanStatus.DIKIRIM
        pengiriman.dikirim_oleh_id = self.user.id
        pengiriman.dikirim_pada = Clock.now()
        self.db.commit()
        return self.detail(pengiriman.id)

    def terima(self, item_id: int, data: PengirimanTerimaInput) -> PengirimanDetailResponse:
        pengiriman = self.get_or_404(item_id, for_update=True)
        self.pengiriman_policy.ensure_can_receive(pengiriman)
        self.ensure_status(pengiriman, PengirimanStatus.DIKIRIM)
        received_map = self.validate_terima(pengiriman, data)
        changes: list[StockChange] = []
        for index, row in enumerate(pengiriman.detail):
            item_in = received_map[row.produk_id]
            row.jumlah_diterima = item_in.jumlah_diterima
            row.catatan = item_in.catatan
            changes.append(
                StockChange(
                    lokasi_id=pengiriman.lokasi_tujuan_id,
                    produk_id=row.produk_id,
                    delta=row.jumlah_diterima,
                    field=f"items.{index}.jumlah_diterima",
                )
            )
        MutasiStok(self.db, self.user).apply(
            changes, MutationSource(StokMutasiType.TERIMA, pengiriman.id)
        )
        pengiriman.status = PengirimanStatus.DITERIMA
        pengiriman.diterima_oleh_id = self.user.id
        pengiriman.diterima_pada = Clock.now()
        pengiriman.catatan_penerimaan = data.catatan_penerimaan
        if pengiriman.permintaan_id is not None:
            permintaan = self.db.get(Permintaan, pengiriman.permintaan_id)
            if permintaan is not None:
                permintaan.status = PermintaanStatus.SELESAI
        self.db.commit()
        return self.detail(pengiriman.id)

    def validate_draft(self, data: PengirimanInput, lokasi_asal: Lokasi) -> None:
        _, product_errors = self.check_products(data.items)
        errors: dict[str, str] = {}
        if lokasi_asal.jenis not in PengirimanPolicy.WAREHOUSE_TYPES:
            errors["lokasi_asal_id"] = "Lokasi asal pengiriman harus berupa gudang"
        tujuan = self.db.get(Lokasi, data.lokasi_tujuan_id)
        if tujuan is None:
            errors["lokasi_tujuan_id"] = "Lokasi tujuan tidak ditemukan"
        elif not tujuan.aktif:
            errors["lokasi_tujuan_id"] = "Lokasi tujuan sudah tidak aktif"
        elif tujuan.id == lokasi_asal.id:
            errors["lokasi_tujuan_id"] = "Lokasi tujuan harus berbeda dari lokasi asal"
        if data.deliveryman_id is not None:
            self.check_deliveryman(data.deliveryman_id, errors)
        errors.update(product_errors)
        if errors:
            raise ValidationFailed(errors=errors)

    def validate_kirim(self, pengiriman: Pengiriman) -> None:
        errors: dict[str, str] = {}
        if pengiriman.deliveryman_id is None:
            errors["deliveryman_id"] = "Wajib diisi saat mengirim"
        else:
            self.check_deliveryman(pengiriman.deliveryman_id, errors)
        if pengiriman.kendaraan_jenis is None:
            errors["kendaraan_jenis"] = "Wajib diisi saat mengirim"
        if not pengiriman.kendaraan_nomor:
            errors["kendaraan_nomor"] = "Wajib diisi saat mengirim"
        if errors:
            raise ValidationFailed(errors=errors)

    def check_deliveryman(self, deliveryman_id: int, errors: dict[str, str]) -> None:
        kurir = self.db.get(User, deliveryman_id)
        if kurir is None or kurir.role != UserRole.DELIVERYMAN:
            errors["deliveryman_id"] = "Deliveryman tidak ditemukan"
        elif kurir.status != UserStatus.AKTIF:
            errors["deliveryman_id"] = "Deliveryman sudah tidak aktif"

    @staticmethod
    def validate_terima(pengiriman: Pengiriman, data: PengirimanTerimaInput) -> dict[int, object]:
        detail_by_produk = {row.produk_id: row for row in pengiriman.detail}
        errors: dict[str, str] = {}
        received_map: dict[int, object] = {}
        for index, item in enumerate(data.items):
            row = detail_by_produk.get(item.produk_id)
            if row is None:
                errors[f"items.{index}.produk_id"] = "Produk tidak ada di pengiriman ini"
                continue
            if item.produk_id in received_map:
                errors[f"items.{index}.produk_id"] = (
                    "Produk tidak boleh duplikat dalam satu dokumen"
                )
                continue
            received_map[item.produk_id] = item
            if item.jumlah_diterima > row.jumlah_dikirim:
                errors[f"items.{index}.jumlah_diterima"] = (
                    f"Maksimal sebesar jumlah dikirim ({row.jumlah_dikirim})"
                )
            elif item.jumlah_diterima < row.jumlah_dikirim and not item.catatan:
                errors[f"items.{index}.catatan"] = (
                    "Catatan wajib diisi bila jumlah diterima kurang dari jumlah dikirim"
                )
        if set(detail_by_produk) != set(received_map):
            errors.setdefault("items", "Semua produk di pengiriman wajib dikonfirmasi")
        if errors:
            raise ValidationFailed(errors=errors)
        return received_map

    @staticmethod
    def build_details(items: list[PengirimanItemInput]) -> list[PengirimanDetail]:
        return [
            PengirimanDetail(produk_id=item.produk_id, jumlah_dikirim=item.jumlah_dikirim)
            for item in items
        ]

    @staticmethod
    def to_summary(pengiriman: Pengiriman) -> PengirimanSummary:
        nilai_dikirim = sum(
            row.jumlah_dikirim * row.produk.harga_beli for row in pengiriman.detail
        )
        return PengirimanSummary(
            id=pengiriman.id,
            kode=pengiriman.kode,
            status=pengiriman.status,
            lokasi_asal=PengirimanLokasi.model_validate(pengiriman.lokasi_asal),
            lokasi_tujuan=PengirimanLokasi.model_validate(pengiriman.lokasi_tujuan),
            permintaan=(
                PermintaanRef.model_validate(pengiriman.permintaan)
                if pengiriman.permintaan
                else None
            ),
            deliveryman=(
                UserRef.model_validate(pengiriman.deliveryman) if pengiriman.deliveryman else None
            ),
            kendaraan_jenis=pengiriman.kendaraan_jenis,
            kendaraan_nomor=pengiriman.kendaraan_nomor,
            tanggal_kirim=pengiriman.tanggal_kirim,
            catatan=pengiriman.catatan,
            catatan_penerimaan=pengiriman.catatan_penerimaan,
            jumlah_item=len(pengiriman.detail),
            nilai_dikirim=nilai_dikirim,
            dibuat_oleh=UserRef.model_validate(pengiriman.dibuat_oleh),
            dikirim_oleh=(
                UserRef.model_validate(pengiriman.dikirim_oleh)
                if pengiriman.dikirim_oleh
                else None
            ),
            dikirim_pada=pengiriman.dikirim_pada,
            diterima_oleh=(
                UserRef.model_validate(pengiriman.diterima_oleh)
                if pengiriman.diterima_oleh
                else None
            ),
            diterima_pada=pengiriman.diterima_pada,
            created_at=pengiriman.created_at,
            updated_at=pengiriman.updated_at,
        )

    @classmethod
    def to_detail(cls, pengiriman: Pengiriman) -> PengirimanDetailResponse:
        summary = cls.to_summary(pengiriman).model_dump()
        items = [
            PengirimanItemResponse(
                id=row.id,
                produk=PengirimanProduk(
                    id=row.produk.id,
                    sku=row.produk.sku,
                    nama=row.produk.nama,
                    satuan=row.produk.satuan,
                    jenis=row.produk.kategori.jenis,
                    harga_beli=row.produk.harga_beli,
                ),
                jumlah_dikirim=row.jumlah_dikirim,
                jumlah_diterima=row.jumlah_diterima,
                selisih=(
                    row.jumlah_dikirim - row.jumlah_diterima
                    if row.jumlah_diterima is not None
                    else None
                ),
                catatan=row.catatan,
            )
            for row in pengiriman.detail
        ]
        return PengirimanDetailResponse(**summary, items=items)
