from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import KategoriType, StokStatus, User
from app.policies.access import current_user
from app.schemas.dashboard import DashboardResponse, MonitoringResponse, TrenResponse
from app.schemas.stok import StokStatusFilter
from app.services.dashboard_service import DashboardService
from app.services.monitoring_service import MonitoringFilter, MonitoringService

class DashboardController:
    def index(
        self,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> DashboardResponse:
        return DashboardService(db, user).summary()

    def monitoring(
        self,
        kategori_id: int | None = None,
        jenis: KategoriType | None = None,
        status_stok: StokStatusFilter = None,
        q: str | None = Query(None, max_length=100, description="Cari di SKU, nama atau merek"),
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> MonitoringResponse:
        resolved_status = StokStatus(status_stok) if status_stok in StokStatus else None
        filters = MonitoringFilter(kategori_id, jenis, resolved_status, q)
        return MonitoringService(db, user).matriks(filters)

    def tren(
        self,
        hari: int = Query(30, ge=7, le=90, description="Rentang hari tren mutasi (7 sampai 90)"),
        lokasi_id: int | None = None,
        user: User = Depends(current_user),
        db: Session = Depends(get_db),
    ) -> TrenResponse:
        return MonitoringService(db, user).tren(hari=hari, lokasi_id=lokasi_id)
