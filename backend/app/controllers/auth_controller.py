from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.limiter import rate_limiter
from app.core.session import session_manager
from app.models import UserSession
from app.policies.access import active_session
from app.schemas.auth import AuthResponse, LoginRequest, MessageResponse, RegisterRequest
from app.services.auth_service import AuthService

class AuthController:
    def register(
        self, body: RegisterRequest, request: Request, db: Session = Depends(get_db)
    ) -> MessageResponse:
        AuthService(db).register(body)
        return MessageResponse(
            pesan="Pendaftaran terkirim. Akun bisa dipakai setelah disetujui admin."
        )

    def login(
        self, body: LoginRequest, request: Request, response: Response,
        db: Session = Depends(get_db),
    ) -> AuthResponse:
        ip_address = rate_limiter.client_address(request)
        token, session = AuthService(db).login(body, ip_address, request.headers.get("user-agent"))
        session_manager.set_cookie(response, token)
        return AuthResponse.of(session)

    def logout(
        self, response: Response,
        session: UserSession = Depends(active_session), db: Session = Depends(get_db),
    ) -> None:
        AuthService(db).logout(session)
        session_manager.clear_cookie(response)

    def me(self, session: UserSession = Depends(active_session)) -> AuthResponse:
        # dipanggil saat halaman dimuat ulang untuk memulihkan profil dan token CSRF
        return AuthResponse.of(session)
