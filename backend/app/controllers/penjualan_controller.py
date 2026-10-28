from datetime import date

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import PenjualanStatus, User
from app.policies.access import current_user
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.penjualan import (
    PenjualanDetailResponse,
    PenjualanInput,
    PenjualanSummary,
)
from app.services.penjualan_service import PenjualanFilter, PenjualanService, PenjualanSort

class PenjualanController:
    def index(
        self,
        lokasi_id: int | None = None,
        customer_id: int | None = None,
        status: PenjualanStatus | None = None,
        dari: date | None = None,
        sampai: date | None = None,
        q: str | None = Query(None, max_length=100, description="Cari di kode atau catatan"),
        sort: PenjualanSort = PenjualanSort.TANGGAL,
        arah: SortDirection = SortDirection.DESC,
        params: PageParams = Depends(),
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> Page[PenjualanSummary]:
        filters = PenjualanFilter(lokasi_id, customer_id, status, dari, sampai, q, sort, arah)
        return PenjualanService(db, user).search(filters, params)

    def show(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> PenjualanDetailResponse:
        return PenjualanService(db, user).detail(id)

    def store(
        self,
        body: PenjualanInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PenjualanDetailResponse:
        return PenjualanService(db, user).create(body)

    def update(
        self,
        id: int,
        body: PenjualanInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PenjualanDetailResponse:
        return PenjualanService(db, user).update(id, body)

    def destroy(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> None:
        PenjualanService(db, user).delete(id)

    def posting(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> PenjualanDetailResponse:
        return PenjualanService(db, user).posting(id)
