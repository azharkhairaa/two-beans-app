from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import KategoriType, StokStatus, User
from app.policies.access import current_user
from app.schemas.common import PageParams, SortDirection
from app.schemas.stok import StokItem, StokPage, StokSettingInput
from app.services.stok_service import StokFilter, StokService, StokSort

class StokController:
    def index(
        self,
        lokasi_id: int | None = Query(None, description="Bawaan lokasi user, admin gudang utama"),
        q: str | None = Query(None, max_length=100, description="Cari di SKU atau nama"),
        kategori_id: int | None = None,
        jenis: KategoriType | None = None,
        status_stok: StokStatus | None = None,
        sort: StokSort = StokSort.NAMA,
        arah: SortDirection = SortDirection.ASC,
        params: PageParams = Depends(),
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> StokPage:
        filters = StokFilter(lokasi_id, q, kategori_id, jenis, status_stok, sort, arah)
        return StokService(db, user).search(filters, params)

    def update(
        self, lokasi_id: int, produk_id: int, body: StokSettingInput,
        user: User = Depends(current_user), db: Session = Depends(get_db),
    ) -> StokItem:
        return StokService(db, user).update_setting(lokasi_id, produk_id, body)
