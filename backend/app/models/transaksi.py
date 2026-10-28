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
    and_,
    column,
    or_,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, check_values

if TYPE_CHECKING:
    from app.models.lokasi import Lokasi
    from app.models.produk import Produk
    from app.models.user import User

class TransaksiType(StrEnum):
    MASUK = "masuk"
    KELUAR = "keluar"
    PENYESUAIAN = "penyesuaian"

class TransaksiStatus(StrEnum):
    DRAF = "draf"
    DIPOSTING = "diposting"

# alasan yang boleh dipakai untuk setiap jenis transaksi (PRD BR-13)
TRANSAKSI_REASONS = {
    TransaksiType.MASUK: ("hasil_roasting", "retur", "lainnya"),
    TransaksiType.KELUAR: ("pemakaian", "roasting", "sampel", "lainnya"),
    TransaksiType.PENYESUAIAN: ("opname", "rusak", "hilang", "kedaluwarsa", "lainnya"),
}

class Transaksi(TimestampMixin, Base):
    __tablename__ = "transaksi"
    __table_args__ = (
        check_values("jenis", TransaksiType),
        check_values("status", TransaksiStatus),
        CheckConstraint(r"kode ~ '^(BM|BK|PS)-[0-9]{6}-[0-9]{4,}$'", name="kode_format"),
        CheckConstraint(
            "left(kode, 2) = CASE jenis WHEN 'masuk' THEN 'BM' "
            "WHEN 'keluar' THEN 'BK' ELSE 'PS' END",
            name="kode_jenis",
        ),
        CheckConstraint(
            or_(*(and_(column("jenis") == jenis.value, column("alasan").in_(alasan))
                  for jenis, alasan in TRANSAKSI_REASONS.items())),
            name="alasan",
        ),
        CheckConstraint(
            "(status = 'draf' AND diposting_oleh_id IS NULL AND diposting_pada IS NULL) "
            "OR (status = 'diposting' AND diposting_oleh_id IS NOT NULL "
            "AND diposting_pada IS NOT NULL)",
            name="data_posting",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    kode: Mapped[str] = mapped_column(String(20), unique=True)
    jenis: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(10), server_default=TransaksiStatus.DRAF.value)
    tanggal: Mapped[date] = mapped_column(Date, index=True)
    lokasi_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"), index=True
    )
    alasan: Mapped[str] = mapped_column(String(15))
    keterangan: Mapped[str | None] = mapped_column(String(120))
    catatan: Mapped[str | None] = mapped_column(String(500))
    dibuat_oleh_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diposting_oleh_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diposting_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lokasi: Mapped["Lokasi"] = relationship()
    detail: Mapped[list["TransaksiDetail"]] = relationship(
        back_populates="transaksi", cascade="all, delete-orphan", passive_deletes=True,
        order_by="TransaksiDetail.id",
    )
    dibuat_oleh: Mapped["User"] = relationship(foreign_keys=[dibuat_oleh_id])
    diposting_oleh: Mapped["User | None"] = relationship(foreign_keys=[diposting_oleh_id])

class TransaksiDetail(Base):
    __tablename__ = "transaksi_detail"
    __table_args__ = (
        UniqueConstraint("transaksi_id", "produk_id"),
        # positif untuk masuk dan keluar, bertanda untuk penyesuaian
        CheckConstraint("jumlah <> 0", name="jumlah"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    transaksi_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("transaksi.id", ondelete="CASCADE")
    )
    produk_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("produk.id", ondelete="RESTRICT"), index=True
    )
    jumlah: Mapped[int]

    transaksi: Mapped["Transaksi"] = relationship(back_populates="detail")
    produk: Mapped["Produk"] = relationship()
