import secrets
from collections.abc import Iterable

from fastapi import Depends, Request
from fastapi.security import APIKeyCookie, APIKeyHeader
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import Forbidden, NotAuthenticated
from app.core.session import SessionManager, session_manager
from app.models import User, UserRole, UserSession

# skema keamanan ini juga memunculkan tombol Authorize di Swagger untuk header CSRF
session_cookie = APIKeyCookie(name=SessionManager.COOKIE, auto_error=False)
csrf_header = APIKeyHeader(
    name="X-CSRF-Token", auto_error=False,
    description="Token dari response login atau GET /api/auth/me",
)

class SessionGuard:
    # dependency sesi aktif: cookie valid, CSRF untuk method pengubah data, lalu sentuh last_seen_at
    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    def __init__(self, sessions: SessionManager):
        self.sessions = sessions

    def __call__(
        self,
        request: Request,
        token: str | None = Depends(session_cookie),
        csrf_token: str | None = Depends(csrf_header),
        db: Session = Depends(get_db),
    ) -> UserSession:
        session = self.sessions.resolve(db, token) if token else None
        if session is None:
            raise NotAuthenticated()
        if request.method not in self.SAFE_METHODS and not self.csrf_valid(csrf_token, session):
            raise Forbidden("Token CSRF tidak valid")
        self.sessions.touch(db, session)
        return session

    @staticmethod
    def csrf_valid(sent: str | None, session: UserSession) -> bool:
        # compare_digest supaya waktu pembandingan tidak membocorkan isi token
        return secrets.compare_digest((sent or "").encode(), session.csrf_token.encode())

active_session = SessionGuard(session_manager)

def current_user(session: UserSession = Depends(active_session)) -> User:
    return session.user

class RoleGuard:
    # dependency peran, user di luar daftar ditolak 403
    def __init__(self, roles: Iterable[str], message: str):
        self.roles = frozenset(roles)
        self.message = message

    def __call__(self, user: User = Depends(current_user)) -> User:
        if user.role not in self.roles:
            raise Forbidden(self.message)
        return user

require_manager = RoleGuard(
    (UserRole.ADMIN, UserRole.MANAGER_GUDANG, UserRole.MANAGER_OUTLET),
    "Fitur ini khusus manager dan admin",
)
require_admin = RoleGuard((UserRole.ADMIN,), "Fitur ini khusus admin")
