from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import CoffeeType, KategoriType, User
from app.policies.access import current_user
from app.schemas.common import ActiveFilter, Page, PageParams, SortDirection
from app.schemas.produk import ProdukDetail, ProdukInput, ProdukOption, ProdukResponse
from app.schemas.stok import KartuStokItem
from app.services.produk_service import ProdukFilter, ProdukService, ProdukSort
from app.services.stok_service import StokService

class ProdukController:
    def index(
        self,
        q: str | None = Query(None, max_length=100, description="Cari di SKU, nama atau merek"),
        kategori_id: int | None = None,
        jenis: KategoriType | None = None,
        jenis_kopi: CoffeeType | None = None,
        aktif: ActiveFilter = ActiveFilter.TRUE,
        sort: ProdukSort = ProdukSort.NAMA,
        arah: SortDirection = SortDirection.ASC,
        params: PageParams = Depends(),
        db: Session = Depends(get_db),
    ) -> Page[ProdukResponse]:
        filters = ProdukFilter(q, kategori_id, jenis, jenis_kopi, aktif, sort, arah)
        return ProdukService(db).search(filters, params)

    def options(
        self,
        lokasi_id: int | None = Query(None, description="Sertakan stok di lokasi ini"),
        jenis: KategoriType | None = None,
        db: Session = Depends(get_db),
    ) -> list[ProdukOption]:
        return ProdukService(db).options(lokasi_id, jenis)

    def show(self, id: int, db: Session = Depends(get_db)) -> ProdukDetail:
        return ProdukService(db).detail(id)

    def store(self, body: ProdukInput, db: Session = Depends(get_db)) -> ProdukDetail:
        service = ProdukService(db)
        return service.detail(service.create(body).id)

    def update(self, id: int, body: ProdukInput, db: Session = Depends(get_db)) -> ProdukDetail:
        service = ProdukService(db)
        service.update(service.get_or_404(id), body)
        return service.detail(id)

    def destroy(self, id: int, db: Session = Depends(get_db)) -> None:
        service = ProdukService(db)
        service.delete(service.get_or_404(id))

    def kartu_stok(
        self, id: int,
        lokasi_id: int = Query(..., description="Lokasi yang kartu stoknya dibuka"),
        params: PageParams = Depends(),
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> Page[KartuStokItem]:
        # riwayat mutasi terbaru di atas, setiap baris menyebut dokumen sumber dan user
        return StokService(db, user).kartu_stok(id, lokasi_id, params)
