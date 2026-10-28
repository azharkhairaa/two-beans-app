from datetime import date

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import PengirimanStatus, User
from app.policies.access import current_user
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.pengiriman import (
    PengirimanDetailResponse,
    PengirimanInput,
    PengirimanKirimInput,
    PengirimanSummary,
    PengirimanTerimaInput,
)
from app.services.pengiriman_service import PengirimanFilter, PengirimanService, PengirimanSort

class PengirimanController:
    def index(
        self,
        lokasi_asal_id: int | None = None,
        lokasi_tujuan_id: int | None = None,
        status: PengirimanStatus | None = None,
        deliveryman_id: int | None = None,
        dari: date | None = None,
        sampai: date | None = None,
        q: str | None = Query(None, max_length=100, description="Cari di kode atau catatan"),
        sort: PengirimanSort = PengirimanSort.TANGGAL_KIRIM,
        arah: SortDirection = SortDirection.DESC,
        params: PageParams = Depends(),
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> Page[PengirimanSummary]:
        filters = PengirimanFilter(
            lokasi_asal_id, lokasi_tujuan_id, status, deliveryman_id, dari, sampai, q, sort, arah
        )
        return PengirimanService(db, user).search(filters, params)

    def show(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> PengirimanDetailResponse:
        return PengirimanService(db, user).detail(id)

    def store(
        self,
        body: PengirimanInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PengirimanDetailResponse:
        return PengirimanService(db, user).create(body)

    def update(
        self,
        id: int,
        body: PengirimanInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PengirimanDetailResponse:
        return PengirimanService(db, user).update(id, body)

    def destroy(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> None:
        PengirimanService(db, user).delete(id)

    def kirim(
        self,
        id: int,
        body: PengirimanKirimInput | None = None,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PengirimanDetailResponse:
        return PengirimanService(db, user).kirim(id, body)

    def terima(
        self,
        id: int,
        body: PengirimanTerimaInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PengirimanDetailResponse:
        return PengirimanService(db, user).terima(id, body)
