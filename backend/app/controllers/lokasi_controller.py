from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User
from app.policies.access import current_user
from app.policies.lokasi_policy import LokasiPolicy
from app.schemas.common import ActiveFilter
from app.schemas.lokasi import LokasiInput, LokasiResponse
from app.services.lokasi_service import LokasiService

class LokasiController:
    def index(
        self, aktif: ActiveFilter = ActiveFilter.ALL,
        user: User = Depends(current_user), db: Session = Depends(get_db),
    ) -> list[LokasiResponse]:
        return LokasiService(db).summaries(aktif, LokasiPolicy(user))

    def show(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> LokasiResponse:
        return LokasiService(db).detail(id, LokasiPolicy(user))

    def store(
        self, body: LokasiInput, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> LokasiResponse:
        service = LokasiService(db)
        return service.detail(service.create(body).id, LokasiPolicy(user))

    def update(
        self, id: int, body: LokasiInput,
        user: User = Depends(current_user), db: Session = Depends(get_db),
    ) -> LokasiResponse:
        service = LokasiService(db)
        service.update(service.get_or_404(id), body)
        return service.detail(id, LokasiPolicy(user))

    def destroy(self, id: int, db: Session = Depends(get_db)) -> None:
        service = LokasiService(db)
        service.delete(service.get_or_404(id))
