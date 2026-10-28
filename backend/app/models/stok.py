from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.lokasi import Lokasi
    from app.models.produk import Produk

class StokStatus(StrEnum):
    AMAN = "aman"
    MENIPIS = "menipis"
    HABIS = "habis"

class Stok(Base):
    # many-to-many lokasi dan produk yang punya data sendiri (jumlah, stok minimum, rak)
    __tablename__ = "stok"
    __table_args__ = (
        CheckConstraint("jumlah >= 0", name="jumlah"),
        CheckConstraint("stok_minimum >= 0", name="stok_minimum"),
        CheckConstraint("rak IS NULL OR rak ~ '^[A-Z]{1,2}-[0-9]{2}$'", name="rak"),
    )

    lokasi_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"), primary_key=True
    )
    produk_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("produk.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    jumlah: Mapped[int] = mapped_column(server_default=text("0"))
    stok_minimum: Mapped[int] = mapped_column(server_default=text("0"))
    rak: Mapped[str | None] = mapped_column(String(10))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lokasi: Mapped["Lokasi"] = relationship(back_populates="stok")
    produk: Mapped["Produk"] = relationship(back_populates="stok")

    @property
    def status_stok(self) -> StokStatus:
        # BR-16, nilai turunan yang tidak disimpan
        if self.jumlah == 0:
            return StokStatus.HABIS
        if self.jumlah <= self.stok_minimum:
            return StokStatus.MENIPIS
        return StokStatus.AMAN
