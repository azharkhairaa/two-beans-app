from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, check_values

if TYPE_CHECKING:
    from app.models.lokasi import Lokasi
    from app.models.user_session import UserSession

class UserRole(StrEnum):
    ADMIN = "admin"
    MANAGER_GUDANG = "manager_gudang"
    MANAGER_OUTLET = "manager_outlet"
    DELIVERYMAN = "deliveryman"

class UserStatus(StrEnum):
    MENUNGGU = "menunggu"
    AKTIF = "aktif"
    NONAKTIF = "nonaktif"

class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        check_values("role", UserRole, nullable=True),
        check_values("status", UserStatus),
        # akun yang sudah disetujui wajib punya role, manager wajib punya lokasi
        CheckConstraint("status = 'menunggu' OR role IS NOT NULL", name="role_wajib"),
        CheckConstraint(
            "role NOT IN ('manager_gudang', 'manager_outlet') OR lokasi_id IS NOT NULL",
            name="lokasi_manager",
        ),
        CheckConstraint("email = lower(email)", name="email_lower"),
        CheckConstraint("failed_logins >= 0", name="failed_logins"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(10), server_default=UserStatus.MENUNGGU.value)
    lokasi_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"), index=True
    )
    failed_logins: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lokasi: Mapped["Lokasi | None"] = relationship(back_populates="users")
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", passive_deletes=True
    )
