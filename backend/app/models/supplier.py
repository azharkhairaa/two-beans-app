from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Identity, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.pembelian import Pembelian

class Supplier(TimestampMixin, Base):
    __tablename__ = "supplier"
    __table_args__ = (
        CheckConstraint(r"telepon IS NULL OR telepon ~ '^\+?[0-9]{9,15}$'", name="telepon"),
        CheckConstraint("email IS NULL OR email = lower(email)", name="email_lower"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    nama: Mapped[str] = mapped_column(String(100))
    kontak: Mapped[str | None] = mapped_column(String(100))
    telepon: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(254))
    alamat: Mapped[str | None] = mapped_column(String(500))
    aktif: Mapped[bool] = mapped_column(server_default=text("true"))

    # FK RESTRICT dijaga database, ORM tidak mengosongkan FK anak saat induk dihapus
    pembelian: Mapped[list["Pembelian"]] = relationship(
        back_populates="supplier", passive_deletes="all"
    )

Index("uq_supplier_nama_lower", func.lower(Supplier.nama), unique=True)
