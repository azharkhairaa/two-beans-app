from datetime import date

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import TransaksiStatus, TransaksiType, User
from app.policies.access import current_user
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.transaksi import (
    TransaksiDetailResponse,
    TransaksiInput,
    TransaksiSummary,
    TransaksiUpdate,
)
from app.services.transaksi_service import TransaksiFilter, TransaksiService, TransaksiSort

class TransaksiController:
    def index(
        self,
        lokasi_id: int | None = None,
        jenis: TransaksiType | None = None,
        status: TransaksiStatus | None = None,
        alasan: str | None = Query(None, max_length=30),
        dari: date | None = None,
        sampai: date | None = None,
        q: str | None = Query(None, max_length=100, description="Cari di kode atau keterangan"),
        sort: TransaksiSort = TransaksiSort.TANGGAL,
        arah: SortDirection = SortDirection.DESC,
        params: PageParams = Depends(),
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> Page[TransaksiSummary]:
        filters = TransaksiFilter(lokasi_id, jenis, status, alasan, dari, sampai, q, sort, arah)
        return TransaksiService(db, user).search(filters, params)

    def show(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> TransaksiDetailResponse:
        return TransaksiService(db, user).detail(id)

    def store(
        self,
        body: TransaksiInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> TransaksiDetailResponse:
        return TransaksiService(db, user).create(body)

    def update(
        self,
        id: int,
        body: TransaksiUpdate,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> TransaksiDetailResponse:
        return TransaksiService(db, user).update(id, body)

    def destroy(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> None:
        TransaksiService(db, user).delete(id)

    def posting(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> TransaksiDetailResponse:
        return TransaksiService(db, user).posting(id)
