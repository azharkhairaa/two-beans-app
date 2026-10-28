import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Response
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, settings
from app.models import User, UserSession, UserStatus

class SessionManager:
    # sesi server-side: cookie membawa token acak, database hanya menyimpan HMAC-SHA256-nya
    COOKIE = "twobeans_sesi"
    TOUCH_INTERVAL = timedelta(minutes=5)

    def __init__(self, config: Settings):
        self.key = config.secret_key.encode()
        self.idle = timedelta(minutes=config.session_idle_minutes)
        self.max_age = timedelta(hours=config.session_max_hours)
        self.cookie_secure = config.cookie_secure

    @staticmethod
    def now() -> datetime:
        return datetime.now(UTC)

    def token_hash(self, token: str) -> str:
        # SECRET_KEY diganti berarti semua sesi lama otomatis tidak berlaku
        return hmac.new(self.key, token.encode(), hashlib.sha256).hexdigest()

    def create(
        self, db: Session, user: User, ip_address: str | None, user_agent: str | None
    ) -> tuple[str, UserSession]:
        # token baru setiap login sehingga session fixation tidak mungkin, commit di pemanggil
        token = secrets.token_urlsafe(32)
        now = self.now()
        session = UserSession(
            user=user,
            token_hash=self.token_hash(token),
            csrf_token=secrets.token_urlsafe(32),
            ip_address=ip_address,
            user_agent=(user_agent or "")[:255] or None,
            created_at=now,
            last_seen_at=now,
            expires_at=now + self.max_age,
        )
        db.add(session)
        return token, session

    def resolve(self, db: Session, token: str) -> UserSession | None:
        # sesi, user dan lokasinya diambil dalam satu query
        query = (
            select(UserSession)
            .options(joinedload(UserSession.user).joinedload(User.lokasi))
            .where(UserSession.token_hash == self.token_hash(token))
        )
        session = db.scalar(query)
        if session is None:
            return None
        if self.expired(session) or session.user.status != UserStatus.AKTIF:
            self.revoke(db, session)
            return None
        return session

    def expired(self, session: UserSession) -> bool:
        now = self.now()
        return now >= session.expires_at or now - session.last_seen_at > self.idle

    def touch(self, db: Session, session: UserSession) -> None:
        # last_seen_at cukup diperbarui paling sering sekali per 5 menit
        now = self.now()
        if now - session.last_seen_at >= self.TOUCH_INTERVAL:
            session.last_seen_at = now
            db.commit()

    def revoke(self, db: Session, session: UserSession) -> None:
        db.delete(session)
        db.commit()

    def revoke_all(self, db: Session, user_id: int, keep: UserSession | None = None) -> None:
        # dipakai saat ubah password atau admin mengubah akun, commit di pemanggil
        query = delete(UserSession).where(UserSession.user_id == user_id)
        if keep is not None:
            query = query.where(UserSession.id != keep.id)
        db.execute(query)

    def purge_expired(self, db: Session, user_id: int) -> None:
        now = self.now()
        db.execute(
            delete(UserSession).where(
                UserSession.user_id == user_id,
                or_(UserSession.expires_at <= now, UserSession.last_seen_at < now - self.idle),
            )
        )

    def set_cookie(self, response: Response, token: str) -> None:
        # HttpOnly menutup akses JavaScript, SameSite=Strict menahan cookie dari situs lain
        response.set_cookie(
            self.COOKIE, token, max_age=int(self.max_age.total_seconds()), path="/",
            secure=self.cookie_secure, httponly=True, samesite="strict",
        )

    def clear_cookie(self, response: Response) -> None:
        response.delete_cookie(
            self.COOKIE, path="/", secure=self.cookie_secure, httponly=True, samesite="strict"
        )

session_manager = SessionManager(settings)
