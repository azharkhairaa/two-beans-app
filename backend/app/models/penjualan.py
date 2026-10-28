from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, check_values

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.lokasi import Lokasi
    from app.models.produk import Produk
    from app.models.user import User

class PenjualanStatus(StrEnum):
    DRAF = "draf"
    DIPOSTING = "diposting"

class Penjualan(TimestampMixin, Base):
    __tablename__ = "penjualan"
    __table_args__ = (
        check_values("status", PenjualanStatus),
        CheckConstraint(r"kode ~ '^PJ-[0-9]{6}-[0-9]{4,}$'", name="kode_format"),
        CheckConstraint(
            "(status = 'draf' AND diposting_oleh_id IS NULL AND diposting_pada IS NULL) "
            "OR (status = 'diposting' AND diposting_oleh_id IS NOT NULL "
            "AND diposting_pada IS NOT NULL)",
            name="data_posting",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    kode: Mapped[str] = mapped_column(String(20), unique=True)
    status: Mapped[str] = mapped_column(String(10), server_default=PenjualanStatus.DRAF.value)
    tanggal: Mapped[date] = mapped_column(Date, index=True)
    lokasi_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"), index=True
    )
    # kosong berarti pembeli umum, hanya boleh untuk outlet (dijaga service)
    customer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("customer.id", ondelete="RESTRICT"), index=True
    )
    catatan: Mapped[str | None] = mapped_column(String(500))
    dibuat_oleh_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diposting_oleh_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diposting_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lokasi: Mapped["Lokasi"] = relationship()
    customer: Mapped["Customer | None"] = relationship(back_populates="penjualan")
    detail: Mapped[list["PenjualanDetail"]] = relationship(
        back_populates="penjualan", cascade="all, delete-orphan", passive_deletes=True,
        order_by="PenjualanDetail.id",
    )
    dibuat_oleh: Mapped["User"] = relationship(foreign_keys=[dibuat_oleh_id])
    diposting_oleh: Mapped["User | None"] = relationship(foreign_keys=[diposting_oleh_id])

class PenjualanDetail(Base):
    __tablename__ = "penjualan_detail"
    __table_args__ = (
        UniqueConstraint("penjualan_id", "produk_id"),
        CheckConstraint("jumlah > 0", name="jumlah"),
        CheckConstraint("harga_satuan > 0", name="harga_satuan"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    penjualan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("penjualan.id", ondelete="CASCADE")
    )
    produk_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("produk.id", ondelete="RESTRICT"), index=True
    )
    jumlah: Mapped[int]
    # harga jual saat penjualan, tidak ikut berubah bila harga produk diubah
    harga_satuan: Mapped[int]

    penjualan: Mapped["Penjualan"] = relationship(back_populates="detail")
    produk: Mapped["Produk"] = relationship()
