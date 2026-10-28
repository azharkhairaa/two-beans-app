from sqlalchemy import Select, func, select

from app.core.errors import Conflict
from app.models import Lokasi, LokasiType, Produk, Stok
from app.schemas.common import ActiveFilter
from app.schemas.lokasi import LokasiInput, LokasiResponse
from app.services.base import CrudService

class LokasiService(CrudService[Lokasi]):
    model = Lokasi
    label = "Lokasi"

    def summary_query(self) -> Select:
        # ringkasan stok per lokasi (Desain Database 8.2), nilai = jumlah x harga beli
        return (
            select(
                Lokasi,
                func.count().filter(Stok.jumlah > 0).label("sku_ada"),
                func.count()
                .filter(Stok.jumlah > 0, Stok.jumlah <= Stok.stok_minimum)
                .label("menipis"),
                func.count().filter(Stok.jumlah == 0).label("habis"),
                func.coalesce(func.sum(Stok.jumlah * Produk.harga_beli), 0).label("nilai"),
            )
            .outerjoin(Stok, Stok.lokasi_id == Lokasi.id)
            .outerjoin(Produk, Produk.id == Stok.produk_id)
            .group_by(Lokasi.id)
        )

    def summaries(self, aktif: ActiveFilter) -> list[LokasiResponse]:
        query = self.active_filter(self.summary_query(), Lokasi.aktif, aktif).order_by(Lokasi.kode)
        return [LokasiResponse.of(*row) for row in self.db.execute(query)]

    def detail(self, item_id: int) -> LokasiResponse:
        self.get_or_404(item_id)
        row = self.db.execute(self.summary_query().where(Lokasi.id == item_id)).one()
        return LokasiResponse.of(*row)

    def update(self, lokasi: Lokasi, data: LokasiInput) -> Lokasi:
        if data.jenis != lokasi.jenis and self.usage(lokasi):
            message = "Jenis lokasi tidak bisa diubah karena lokasi sudah punya riwayat"
            raise Conflict(message, {"jenis": message})
        if LokasiType.GUDANG_UTAMA in (lokasi.jenis, data.jenis) and not data.aktif:
            message = "Gudang utama tidak bisa dinonaktifkan"
            raise Conflict(message, {"aktif": message})
        return super().update(lokasi, data)
