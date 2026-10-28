from dataclasses import dataclass

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import joinedload

from app.core.errors import Conflict, ValidationFailed
from app.core.session import SessionManager, session_manager
from app.models import Lokasi, LokasiType, User, UserRole, UserStatus
from app.schemas.common import Page, PageParams
from app.schemas.user import UserItem, UserUpdate
from app.services.base import CrudService

@dataclass(frozen=True)
class UserFilter:
    q: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    lokasi_id: int | None = None

class UserRules:
    # jenis lokasi yang boleh ditempati tiap peran manager
    LOKASI_TYPES = {
        UserRole.MANAGER_GUDANG: (LokasiType.GUDANG_UTAMA, LokasiType.GUDANG_CABANG),
        UserRole.MANAGER_OUTLET: (LokasiType.OUTLET,),
    }
    MESSAGES = {
        UserRole.MANAGER_GUDANG: "Manager gudang harus ditempatkan di gudang utama atau cabang",
        UserRole.MANAGER_OUTLET: "Manager outlet harus ditempatkan di outlet",
    }

    def check(
        self, role: str | None, status: str, lokasi: Lokasi | None, lokasi_given: bool
    ) -> dict[str, str]:
        errors: dict[str, str] = {}
        if status == UserStatus.AKTIF and role is None:
            errors["role"] = "Wajib diisi saat mengaktifkan akun"
        if role in self.LOKASI_TYPES:
            if lokasi is None:
                missing = "Lokasi tidak ditemukan" if lokasi_given else "Wajib diisi untuk manager"
                errors["lokasi_id"] = missing
            elif not lokasi.aktif:
                errors["lokasi_id"] = "Lokasi sudah nonaktif"
            elif lokasi.jenis not in self.LOKASI_TYPES[role]:
                errors["lokasi_id"] = self.MESSAGES[role]
        return errors

class UserService(CrudService[User]):
    model = User
    label = "User"
    rules = UserRules()

    def __init__(self, db, sessions: SessionManager = session_manager):
        super().__init__(db)
        self.sessions = sessions

    @property
    def can_deactivate(self) -> bool:
        # user dinonaktifkan lewat kolom status, bukan aktif
        return True

    def search(self, filters: UserFilter, params: PageParams) -> Page:
        # akun menunggu tampil paling atas supaya admin segera memprosesnya
        query = select(User).options(joinedload(User.lokasi))
        if filters.q:
            matches = (self.contains(User.name, filters.q), self.contains(User.email, filters.q))
            query = query.where(or_(*matches))
        if filters.role:
            query = query.where(User.role == filters.role)
        if filters.status:
            query = query.where(User.status == filters.status)
        if filters.lokasi_id:
            query = query.where(User.lokasi_id == filters.lokasi_id)
        pending_first = case((User.status == UserStatus.MENUNGGU, 0), else_=1)
        return self.paginate(query.order_by(pending_first, User.name, User.id), params, UserItem)

    def deliverymen(self) -> list[User]:
        query = select(User).where(
            User.role == UserRole.DELIVERYMAN, User.status == UserStatus.AKTIF
        )
        return list(self.db.scalars(query.order_by(User.name)))

    def change(self, user: User, data: UserUpdate, actor: User) -> User:
        message = "Peran, lokasi atau status akun sendiri tidak bisa diubah"
        self.ensure_not_self(user, actor, message)
        role = data.role if "role" in data.model_fields_set else user.role
        status = data.status if data.status is not None else user.status
        lokasi_id = data.lokasi_id if "lokasi_id" in data.model_fields_set else user.lokasi_id
        # admin dan deliveryman tidak terikat lokasi, lokasi_id yang dikirim diabaikan
        if role not in self.rules.LOKASI_TYPES:
            lokasi_id = None
        lokasi = self.db.get(Lokasi, lokasi_id) if lokasi_id else None
        errors = self.rules.check(role, status, lokasi, lokasi_id is not None)
        if errors:
            raise ValidationFailed(errors=errors)
        if role != UserRole.ADMIN or status != UserStatus.AKTIF:
            self.ensure_other_admin(user)
        changed = (role, lokasi_id, status) != (user.role, user.lokasi_id, user.status)
        user.role, user.lokasi_id, user.status = role, lokasi_id, status
        # BR-24: hak akses baru langsung berlaku karena semua sesi lama dicabut
        if changed:
            self.sessions.revoke_all(self.db, user.id)
        return self.save(user)

    def delete_user(self, user: User, actor: User) -> None:
        self.ensure_not_self(user, actor, "Akun sendiri tidak bisa dihapus")
        self.ensure_other_admin(user)
        self.delete(user)

    @staticmethod
    def ensure_not_self(user: User, actor: User, message: str) -> None:
        if user.id == actor.id:
            raise Conflict(message)

    def ensure_other_admin(self, user: User) -> None:
        # BR-21: minimal satu admin aktif selalu ada
        if user.role != UserRole.ADMIN or user.status != UserStatus.AKTIF:
            return
        others = self.db.scalar(
            select(func.count()).where(
                User.role == UserRole.ADMIN, User.status == UserStatus.AKTIF, User.id != user.id
            )
        )
        if not others:
            raise Conflict("Minimal satu admin aktif harus ada")
