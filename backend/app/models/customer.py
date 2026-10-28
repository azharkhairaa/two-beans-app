from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Identity, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, check_values

if TYPE_CHECKING:
    from app.models.penjualan import Penjualan

class CustomerType(StrEnum):
    KAFE = "kafe"
    RESELLER = "reseller"
    PERORANGAN = "perorangan"
    LAINNYA = "lainnya"

class Customer(TimestampMixin, Base):
    __tablename__ = "customer"
    __table_args__ = (
        check_values("jenis", CustomerType),
        CheckConstraint(r"telepon IS NULL OR telepon ~ '^\+?[0-9]{9,15}$'", name="telepon"),
        CheckConstraint("email IS NULL OR email = lower(email)", name="email_lower"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    nama: Mapped[str] = mapped_column(String(100))
    jenis: Mapped[str] = mapped_column(String(12))
    kontak: Mapped[str | None] = mapped_column(String(100))
    telepon: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(254))
    alamat: Mapped[str | None] = mapped_column(String(500))
    aktif: Mapped[bool] = mapped_column(server_default=text("true"))

    # FK RESTRICT dijaga database, ORM tidak mengosongkan FK anak saat induk dihapus
    penjualan: Mapped[list["Penjualan"]] = relationship(
        back_populates="customer", passive_deletes="all"
    )

Index("uq_customer_nama_lower", func.lower(Customer.nama), unique=True)
