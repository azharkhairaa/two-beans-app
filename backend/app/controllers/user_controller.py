from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import User, UserRole, UserStatus
from app.policies.access import current_user
from app.schemas.common import OptionResponse, Page, PageParams
from app.schemas.user import UserItem, UserUpdate
from app.services.user_service import UserFilter, UserService

class UserController:
    def index(
        self,
        q: str | None = Query(None, max_length=100, description="Cari di nama atau email"),
        role: UserRole | None = None,
        status: UserStatus | None = None,
        lokasi_id: int | None = None,
        params: PageParams = Depends(),
        db: Session = Depends(get_db),
    ) -> Page[UserItem]:
        return UserService(db).search(UserFilter(q, role, status, lokasi_id), params)

    def deliveryman(self, db: Session = Depends(get_db)) -> list[OptionResponse]:
        return [OptionResponse(id=u.id, nama=u.name) for u in UserService(db).deliverymen()]

    def update(
        self, id: int, body: UserUpdate,
        actor: User = Depends(current_user), db: Session = Depends(get_db),
    ) -> UserItem:
        service = UserService(db)
        return UserItem.model_validate(service.change(service.get_or_404(id), body, actor))

    def destroy(
        self, id: int, actor: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> None:
        service = UserService(db)
        service.delete_user(service.get_or_404(id), actor)
