from datetime import date

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import PermintaanStatus, User
from app.policies.access import current_user
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.permintaan import (
    PermintaanDetailResponse,
    PermintaanInput,
    PermintaanSetujuiInput,
    PermintaanSummary,
    PermintaanTolakInput,
)
from app.services.permintaan_service import PermintaanFilter, PermintaanService, PermintaanSort

class PermintaanController:
    def index(
        self,
        lokasi_peminta_id: int | None = None,
        status: PermintaanStatus | None = None,
        dari: date | None = None,
        sampai: date | None = None,
        q: str | None = Query(None, max_length=100, description="Cari di kode atau catatan"),
        sort: PermintaanSort = PermintaanSort.CREATED_AT,
        arah: SortDirection = SortDirection.DESC,
        params: PageParams = Depends(),
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> Page[PermintaanSummary]:
        filters = PermintaanFilter(lokasi_peminta_id, status, dari, sampai, q, sort, arah)
        return PermintaanService(db, user).search(filters, params)

    def show(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> PermintaanDetailResponse:
        return PermintaanService(db, user).detail(id)

    def store(
        self,
        body: PermintaanInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PermintaanDetailResponse:
        return PermintaanService(db, user).create(body)

    def update(
        self,
        id: int,
        body: PermintaanInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PermintaanDetailResponse:
        return PermintaanService(db, user).update(id, body)

    def batal(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> PermintaanDetailResponse:
        return PermintaanService(db, user).batal(id)

    def setujui(
        self,
        id: int,
        body: PermintaanSetujuiInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PermintaanDetailResponse:
        return PermintaanService(db, user).setujui(id, body)

    def tolak(
        self,
        id: int,
        body: PermintaanTolakInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PermintaanDetailResponse:
        return PermintaanService(db, user).tolak(id, body)
