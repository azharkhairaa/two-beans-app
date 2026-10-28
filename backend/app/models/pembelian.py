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
    from app.models.lokasi import Lokasi
    from app.models.produk import Produk
    from app.models.supplier import Supplier
    from app.models.user import User

class PembelianStatus(StrEnum):
    DRAF = "draf"
    DIPESAN = "dipesan"
    DITERIMA = "diterima"
    DIBATALKAN = "dibatalkan"

class Pembelian(TimestampMixin, Base):
    __tablename__ = "pembelian"
    __table_args__ = (
        check_values("status", PembelianStatus),
        CheckConstraint(r"kode ~ '^PO-[0-9]{6}-[0-9]{4,}$'", name="kode_format"),
        CheckConstraint(
            "status <> 'draf' OR (dipesan_oleh_id IS NULL AND tanggal_pesan IS NULL)",
            name="data_draf",
        ),
        CheckConstraint(
            "status NOT IN ('dipesan', 'diterima') "
            "OR (dipesan_oleh_id IS NOT NULL AND tanggal_pesan IS NOT NULL)",
            name="data_pesan",
        ),
        CheckConstraint(
            "(status = 'diterima') = (diterima_oleh_id IS NOT NULL AND diterima_pada IS NOT NULL)",
            name="data_terima",
        ),
        CheckConstraint(
            "tanggal_perkiraan IS NULL OR tanggal_pesan IS NULL "
            "OR tanggal_perkiraan >= tanggal_pesan",
            name="tanggal",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    kode: Mapped[str] = mapped_column(String(20), unique=True)
    status: Mapped[str] = mapped_column(
        String(10), server_default=PembelianStatus.DRAF.value, index=True
    )
    supplier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("supplier.id", ondelete="RESTRICT"), index=True
    )
    lokasi_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"))
    tanggal_pesan: Mapped[date | None] = mapped_column(Date)
    tanggal_perkiraan: Mapped[date | None] = mapped_column(Date)
    catatan: Mapped[str | None] = mapped_column(String(500))
    dibuat_oleh_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    dipesan_oleh_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diterima_oleh_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diterima_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    supplier: Mapped["Supplier"] = relationship(back_populates="pembelian")
    lokasi: Mapped["Lokasi"] = relationship()
    detail: Mapped[list["PembelianDetail"]] = relationship(
        back_populates="pembelian", cascade="all, delete-orphan", passive_deletes=True,
        order_by="PembelianDetail.id",
    )
    dibuat_oleh: Mapped["User"] = relationship(foreign_keys=[dibuat_oleh_id])
    dipesan_oleh: Mapped["User | None"] = relationship(foreign_keys=[dipesan_oleh_id])
    diterima_oleh: Mapped["User | None"] = relationship(foreign_keys=[diterima_oleh_id])

class PembelianDetail(Base):
    __tablename__ = "pembelian_detail"
    __table_args__ = (
        UniqueConstraint("pembelian_id", "produk_id"),
        CheckConstraint("jumlah > 0", name="jumlah"),
        CheckConstraint("harga_satuan >= 0", name="harga_satuan"),
        CheckConstraint(
            "jumlah_diterima IS NULL OR jumlah_diterima BETWEEN 0 AND jumlah",
            name="jumlah_diterima",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    pembelian_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pembelian.id", ondelete="CASCADE")
    )
    produk_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("produk.id", ondelete="RESTRICT"))
    jumlah: Mapped[int]
    harga_satuan: Mapped[int]
    jumlah_diterima: Mapped[int | None]

    pembelian: Mapped["Pembelian"] = relationship(back_populates="detail")
    produk: Mapped["Produk"] = relationship()
