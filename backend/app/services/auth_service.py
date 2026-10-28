import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import Conflict, Forbidden, NotAuthenticated
from app.core.security import PasswordHasher, password_hasher
from app.core.session import SessionManager, session_manager
from app.models import User, UserSession, UserStatus
from app.schemas.auth import LoginRequest, RegisterRequest

log = logging.getLogger("uvicorn.error")

class AuthService:
    STATUS_MESSAGES = {
        UserStatus.MENUNGGU: "Akun belum disetujui admin",
        UserStatus.NONAKTIF: "Akun dinonaktifkan. Hubungi admin",
    }

    def __init__(
        self,
        db: Session,
        hasher: PasswordHasher = password_hasher,
        sessions: SessionManager = session_manager,
    ):
        self.db = db
        self.hasher = hasher
        self.sessions = sessions

    def register(self, data: RegisterRequest) -> User:
        if self.db.scalar(select(User.id).where(User.email == data.email)) is not None:
            raise Conflict("Email sudah terdaftar", {"email": "Email sudah terdaftar"})
        # akun baru menunggu admin memberi peran dan lokasi, belum mendapat sesi
        user = User(name=data.name, email=data.email, password_hash=self.hasher.hash(data.password))
        self.db.add(user)
        self.db.commit()
        return user

    def login(
        self, data: LoginRequest, ip_address: str, user_agent: str | None
    ) -> tuple[str, UserSession]:
        user = self.db.scalar(
            select(User).options(joinedload(User.lokasi)).where(User.email == data.email)
        )
        # pesan sama untuk email tidak terdaftar dan password salah supaya email tidak bisa ditebak
        if not self.hasher.verify(data.password, user.password_hash if user else None):
            log.warning("login gagal: %s dari %s", self.mask(data.email), ip_address)
            raise NotAuthenticated("Email atau password salah")
        if user.status in self.STATUS_MESSAGES:
            raise Forbidden(self.STATUS_MESSAGES[user.status])
        self.sessions.purge_expired(self.db, user.id)
        token, session = self.sessions.create(self.db, user, ip_address, user_agent)
        user.last_login_at = session.created_at
        self.db.commit()
        return token, session

    def logout(self, session: UserSession) -> None:
        self.sessions.revoke(self.db, session)

    @staticmethod
    def mask(email: str) -> str:
        # email di log disamarkan, cukup untuk mengenali pola serangan
        local, _, domain = email.partition("@")
        return f"{local[:2]}***@{domain}"
