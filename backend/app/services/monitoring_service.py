from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.clock import Clock
from app.core.errors import NotFound
from app.models import (
    Kategori,
    KategoriType,
    Lokasi,
    Produk,
    Stok,
    StokMutasi,
    StokStatus,
    User,
    UserRole,
)
from app.policies.lokasi_policy import LokasiPolicy
from app.schemas.dashboard import (
    MonitoringBaris,
    MonitoringLokasiHeader,
    MonitoringProdukInfo,
    MonitoringResponse,
    MonitoringSel,
    MonitoringTotalLokasi,
    TrenHariItem,
    TrenResponse,
)
from app.services.base import CrudService

@dataclass(frozen=True)
class MonitoringFilter:
    kategori_id: int | None = None
    jenis: KategoriType | None = None
    status_stok: StokStatus | None = None
    q: str | None = None

class MonitoringService:
    # matriks stok produk per lokasi dan tren mutasi harian untuk halaman monitoring
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.lokasi_policy = LokasiPolicy(user)

    def matriks(self, filters: MonitoringFilter) -> MonitoringResponse:
        lokasi_rows = self.db.scalars(
            select(Lokasi).where(Lokasi.aktif.is_(True)).order_by(Lokasi.kode)
        ).all()
        lokasi_headers = [
            MonitoringLokasiHeader(
                id=lokasi.id, kode=lokasi.kode, nama=lokasi.nama, jenis=lokasi.jenis
            )
            for lokasi in lokasi_rows
        ]
        lokasi_ids = [lokasi.id for lokasi in lokasi_rows]

        produk_query = (
            select(Produk)
            .join(Kategori, Kategori.id == Produk.kategori_id)
            .options(joinedload(Produk.kategori))
            # produk nonaktif yang masih punya stok tetap tampil agar nilainya sama dengan dashboard
            .where(
                or_(
                    Produk.aktif.is_(True),
                    Produk.id.in_(select(Stok.produk_id).where(Stok.jumlah > 0)),
                )
            )
            .order_by(Produk.sku)
        )
        if filters.kategori_id:
            produk_query = produk_query.where(Produk.kategori_id == filters.kategori_id)
        if filters.jenis:
            produk_query = produk_query.where(Kategori.jenis == filters.jenis)
        if filters.q:
            columns = (Produk.sku, Produk.nama, Produk.merek)
            produk_query = produk_query.where(
                or_(*(CrudService.contains(column, filters.q) for column in columns))
            )
        produk_rows = self.db.scalars(produk_query).all()
        produk_ids = [produk.id for produk in produk_rows]

        stok_map: dict[tuple[int, int], Stok] = {}
        if lokasi_ids and produk_ids:
            stok_rows = self.db.scalars(
                select(Stok).where(
                    Stok.lokasi_id.in_(lokasi_ids),
                    Stok.produk_id.in_(produk_ids),
                )
            ).all()
            stok_map = {(stok.lokasi_id, stok.produk_id): stok for stok in stok_rows}

        baris_list: list[MonitoringBaris] = []
        nilai_per_lokasi = {lokasi.id: 0 for lokasi in lokasi_rows}
        show_values = self.lokasi_policy.sees_all_values
        detail_lokasi = {
            lokasi.id for lokasi in lokasi_rows if self.lokasi_policy.can_see_detail(lokasi.id)
        }

        for produk in produk_rows:
            sel_list: list[MonitoringSel] = []
            recorded_statuses: set[str] = set()
            total_produk = 0
            for lokasi in lokasi_rows:
                stok = stok_map.get((lokasi.id, produk.id))
                if stok is not None:
                    jumlah = stok.jumlah
                    minimum = stok.stok_minimum
                    rak = stok.rak
                    status = stok.status_stok.value
                    recorded_statuses.add(status)
                else:
                    jumlah = 0
                    minimum = 0
                    rak = None
                    status = StokStatus.HABIS.value
                total_produk += jumlah
                sel_list.append(
                    MonitoringSel(
                        lokasi_id=lokasi.id,
                        jumlah=jumlah,
                        stok_minimum=minimum,
                        rak=rak if lokasi.id in detail_lokasi else None,
                        status_stok=status,
                        nilai=jumlah * produk.harga_beli if show_values else None,
                    )
                )

            # filter status hanya mencocokkan stok yang tercatat, sel kosong tidak dihitung habis
            if (
                filters.status_stok is not None
                and filters.status_stok.value not in recorded_statuses
            ):
                continue

            for sel in sel_list:
                nilai_per_lokasi[sel.lokasi_id] += sel.nilai or 0

            baris_list.append(
                MonitoringBaris(
                    produk=MonitoringProdukInfo(
                        id=produk.id,
                        sku=produk.sku,
                        nama=produk.nama,
                        satuan=produk.satuan,
                        jenis=produk.kategori.jenis,
                        kategori_nama=produk.kategori.nama,
                        harga_beli=produk.harga_beli if show_values else None,
                    ),
                    sel=sel_list,
                    total=total_produk,
                    nilai=total_produk * produk.harga_beli if show_values else None,
                )
            )

        # jumlah unit per lokasi tidak dijumlahkan karena satuannya berbeda (pack, pcs, kg)
        total_per_lokasi = [
            MonitoringTotalLokasi(
                lokasi_id=lokasi.id,
                kode=lokasi.kode,
                nama=lokasi.nama,
                nilai=nilai_per_lokasi[lokasi.id] if show_values else None,
            )
            for lokasi in lokasi_rows
        ]
        return MonitoringResponse(
            lokasi=lokasi_headers,
            baris=baris_list,
            total_per_lokasi=total_per_lokasi,
            total_nilai=sum(nilai_per_lokasi.values()) if show_values else None,
            nilai_terlihat=show_values,
        )

    def tren(self, hari: int = 30, lokasi_id: int | None = None) -> TrenResponse:
        if self.user.role == UserRole.ADMIN:
            resolved_lokasi_id = lokasi_id
            if resolved_lokasi_id is not None and self.db.get(Lokasi, resolved_lokasi_id) is None:
                raise NotFound("Lokasi tidak ditemukan")
        else:
            if self.user.lokasi_id is None:
                raise NotFound("Lokasi tidak ditemukan")
            if lokasi_id is not None and not self.lokasi_policy.can_manage(lokasi_id):
                raise NotFound("Lokasi tidak ditemukan")
            resolved_lokasi_id = self.user.lokasi_id

        today = Clock.today()
        start_date = today - timedelta(days=hari - 1)
        wib_date = CrudService.local_date(StokMutasi.created_at)

        query = (
            select(
                wib_date.label("tanggal"),
                func.coalesce(
                    func.sum(StokMutasi.perubahan).filter(StokMutasi.perubahan > 0), 0
                ).label("masuk"),
                func.coalesce(
                    -func.sum(StokMutasi.perubahan).filter(StokMutasi.perubahan < 0), 0
                ).label("keluar"),
            )
            .where(wib_date.between(start_date, today))
            .group_by(wib_date)
            .order_by(wib_date)
        )
        if resolved_lokasi_id is not None:
            query = query.where(StokMutasi.lokasi_id == resolved_lokasi_id)

        by_date = {
            row.tanggal: (int(row.masuk or 0), int(row.keluar or 0))
            for row in self.db.execute(query).all()
        }

        data: list[TrenHariItem] = []
        for offset in range(hari):
            day = start_date + timedelta(days=offset)
            masuk, keluar = by_date.get(day, (0, 0))
            data.append(TrenHariItem(tanggal=day, masuk=masuk, keluar=keluar))

        return TrenResponse(hari=hari, lokasi_id=resolved_lokasi_id, data=data)
