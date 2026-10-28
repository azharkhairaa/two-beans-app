import logging
import math
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.clock import Clock
from app.core.errors import (
    Conflict,
    Forbidden,
    NotAuthenticated,
    TooManyRequests,
    ValidationFailed,
)
from app.core.security import PasswordHasher, password_hasher
from app.core.session import SessionManager, session_manager
from app.models import User, UserSession, UserStatus
from app.schemas.auth import LoginRequest, PasswordChangeRequest, RegisterRequest

log = logging.getLogger("uvicorn.error")


class AuthService:
    MAX_FAILED_LOGINS = 5
    LOCK_DURATION = timedelta(minutes=15)

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
        now = Clock.now()
        user = self.db.scalar(
            select(User).options(joinedload(User.lokasi)).where(User.email == data.email)
        )
        # cek kunci akun sementara sebelum verifikasi lanjut
        if user is not None and user.locked_until is not None:
            if user.locked_until > now:
                remaining = max(1, int((user.locked_until - now).total_seconds()))
                rounded = max(60, math.ceil(remaining / 60) * 60)
                raise TooManyRequests.retry_after(rounded)
            user.failed_logins = 0
            user.locked_until = None

        # pesan sama untuk email tidak terdaftar dan password salah supaya email tidak bisa ditebak
        if not self.hasher.verify(data.password, user.password_hash if user else None):
            if user is not None:
                user.failed_logins = int(user.failed_logins or 0) + 1
                if user.failed_logins >= self.MAX_FAILED_LOGINS:
                    user.locked_until = now + self.LOCK_DURATION
                    log.warning(
                        "akun dikunci 15 menit: %s dari %s", self.mask(data.email), ip_address
                    )
                self.db.commit()
            log.warning("login gagal: %s dari %s", self.mask(data.email), ip_address)
            raise NotAuthenticated("Email atau password salah")

        if user.status in self.STATUS_MESSAGES:
            raise Forbidden(self.STATUS_MESSAGES[user.status])

        user.failed_logins = 0
        user.locked_until = None
        self.sessions.purge_expired(self.db, user.id)
        token, session = self.sessions.create(self.db, user, ip_address, user_agent)
        user.last_login_at = session.created_at
        self.db.commit()
        return token, session

    def change_password(self, session: UserSession, data: PasswordChangeRequest) -> None:
        user = session.user
        if not self.hasher.verify(data.current_password, user.password_hash):
            raise ValidationFailed(
                "Password saat ini salah",
                {"current_password": "Password saat ini salah"},
            )
        if data.current_password == data.new_password:
            raise ValidationFailed(
                "Password baru harus berbeda dari password saat ini",
                {"new_password": "Password baru harus berbeda dari password saat ini"},
            )
        user.password_hash = self.hasher.hash(data.new_password)
        user.failed_logins = 0
        user.locked_until = None
        # cabut semua sesi perangkat lain milik user, sesi aktif saat ini tetap dipertahankan
        self.sessions.revoke_all(self.db, user.id, keep=session)
        self.db.commit()

    def logout(self, session: UserSession) -> None:
        self.sessions.revoke(self.db, session)

    @staticmethod
    def mask(email: str) -> str:
        # email di log disamarkan, cukup untuk mengenali pola serangan
        local, _, domain = email.partition("@")
        return f"{local[:2]}***@{domain}"
