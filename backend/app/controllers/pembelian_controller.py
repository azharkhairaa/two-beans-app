from datetime import date

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import PembelianStatus, User
from app.policies.access import current_user
from app.schemas.common import Page, PageParams, SortDirection
from app.schemas.pembelian import (
    PembelianDetailResponse,
    PembelianInput,
    PembelianPesanInput,
    PembelianSummary,
    PembelianTerimaInput,
)
from app.services.pembelian_service import PembelianFilter, PembelianService, PembelianSort

class PembelianController:
    def index(
        self,
        supplier_id: int | None = None,
        status: PembelianStatus | None = None,
        dari: date | None = None,
        sampai: date | None = None,
        q: str | None = Query(None, max_length=100, description="Cari di kode atau catatan"),
        sort: PembelianSort = PembelianSort.CREATED_AT,
        arah: SortDirection = SortDirection.DESC,
        params: PageParams = Depends(),
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> Page[PembelianSummary]:
        filters = PembelianFilter(supplier_id, status, dari, sampai, q, sort, arah)
        return PembelianService(db, user).search(filters, params)

    def show(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> PembelianDetailResponse:
        return PembelianService(db, user).detail(id)

    def store(
        self,
        body: PembelianInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PembelianDetailResponse:
        return PembelianService(db, user).create(body)

    def update(
        self,
        id: int,
        body: PembelianInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PembelianDetailResponse:
        return PembelianService(db, user).update(id, body)

    def destroy(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> None:
        PembelianService(db, user).delete(id)

    def pesan(
        self,
        id: int,
        body: PembelianPesanInput | None = None,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PembelianDetailResponse:
        return PembelianService(db, user).pesan(id, body)

    def terima(
        self,
        id: int,
        body: PembelianTerimaInput,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> PembelianDetailResponse:
        return PembelianService(db, user).terima(id, body)

    def batal(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> PembelianDetailResponse:
        return PembelianService(db, user).batal(id)
