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
    from app.models.pengiriman import Pengiriman
    from app.models.produk import Produk
    from app.models.user import User

class PermintaanStatus(StrEnum):
    DIAJUKAN = "diajukan"
    DISETUJUI = "disetujui"
    DITOLAK = "ditolak"
    DIBATALKAN = "dibatalkan"
    SELESAI = "selesai"

class Permintaan(TimestampMixin, Base):
    __tablename__ = "permintaan"
    __table_args__ = (
        check_values("status", PermintaanStatus),
        CheckConstraint(r"kode ~ '^PM-[0-9]{6}-[0-9]{4,}$'", name="kode_format"),
        CheckConstraint("lokasi_peminta_id <> lokasi_sumber_id", name="lokasi_berbeda"),
        CheckConstraint(
            "(status IN ('disetujui', 'ditolak', 'selesai')) "
            "= (diproses_oleh_id IS NOT NULL AND diproses_pada IS NOT NULL)",
            name="data_proses",
        ),
        CheckConstraint(
            "(status = 'ditolak') = (alasan_penolakan IS NOT NULL)", name="alasan_tolak"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    kode: Mapped[str] = mapped_column(String(20), unique=True)
    status: Mapped[str] = mapped_column(
        String(10), server_default=PermintaanStatus.DIAJUKAN.value, index=True
    )
    lokasi_peminta_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"), index=True
    )
    lokasi_sumber_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT")
    )
    tanggal_butuh: Mapped[date | None] = mapped_column(Date)
    catatan: Mapped[str | None] = mapped_column(String(500))
    diajukan_oleh_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diproses_oleh_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diproses_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    alasan_penolakan: Mapped[str | None] = mapped_column(String(300))

    lokasi_peminta: Mapped["Lokasi"] = relationship(foreign_keys=[lokasi_peminta_id])
    lokasi_sumber: Mapped["Lokasi"] = relationship(foreign_keys=[lokasi_sumber_id])
    detail: Mapped[list["PermintaanDetail"]] = relationship(
        back_populates="permintaan", cascade="all, delete-orphan", passive_deletes=True,
        order_by="PermintaanDetail.id",
    )
    pengiriman: Mapped["Pengiriman | None"] = relationship(back_populates="permintaan")
    diajukan_oleh: Mapped["User"] = relationship(foreign_keys=[diajukan_oleh_id])
    diproses_oleh: Mapped["User | None"] = relationship(foreign_keys=[diproses_oleh_id])

class PermintaanDetail(Base):
    __tablename__ = "permintaan_detail"
    __table_args__ = (
        UniqueConstraint("permintaan_id", "produk_id"),
        CheckConstraint("jumlah_diminta > 0", name="jumlah_diminta"),
        CheckConstraint(
            "jumlah_disetujui IS NULL OR jumlah_disetujui BETWEEN 0 AND jumlah_diminta",
            name="jumlah_disetujui",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    permintaan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("permintaan.id", ondelete="CASCADE")
    )
    produk_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("produk.id", ondelete="RESTRICT"))
    jumlah_diminta: Mapped[int]
    jumlah_disetujui: Mapped[int | None]

    permintaan: Mapped["Permintaan"] = relationship(back_populates="detail")
    produk: Mapped["Produk"] = relationship()
