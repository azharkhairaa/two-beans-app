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
    from app.models.permintaan import Permintaan
    from app.models.produk import Produk
    from app.models.user import User

class PengirimanStatus(StrEnum):
    DRAF = "draf"
    DIKIRIM = "dikirim"
    DITERIMA = "diterima"
    DIBATALKAN = "dibatalkan"

class KendaraanType(StrEnum):
    MOTOR = "motor"
    MOBIL_BOX = "mobil_box"
    PICKUP = "pickup"
    VAN = "van"
    LAINNYA = "lainnya"

class Pengiriman(TimestampMixin, Base):
    __tablename__ = "pengiriman"
    __table_args__ = (
        check_values("status", PengirimanStatus),
        CheckConstraint(r"kode ~ '^KR-[0-9]{6}-[0-9]{4,}$'", name="kode_format"),
        CheckConstraint("lokasi_asal_id <> lokasi_tujuan_id", name="lokasi_berbeda"),
        check_values("kendaraan_jenis", KendaraanType, nullable=True),
        CheckConstraint(
            "kendaraan_nomor IS NULL OR kendaraan_nomor ~ '^[A-Z]{1,2} [0-9]{1,4}( [A-Z]{1,3})?$'",
            name="kendaraan_nomor",
        ),
        CheckConstraint(
            "(status IN ('dikirim', 'diterima')) "
            "= (dikirim_oleh_id IS NOT NULL AND dikirim_pada IS NOT NULL)",
            name="data_kirim",
        ),
        # sejak dikirim, deliveryman dan kendaraan wajib tercatat
        CheckConstraint(
            "status NOT IN ('dikirim', 'diterima') OR (deliveryman_id IS NOT NULL "
            "AND kendaraan_jenis IS NOT NULL AND kendaraan_nomor IS NOT NULL)",
            name="kurir_kendaraan",
        ),
        CheckConstraint(
            "(status = 'diterima') = (diterima_oleh_id IS NOT NULL AND diterima_pada IS NOT NULL)",
            name="data_terima",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    kode: Mapped[str] = mapped_column(String(20), unique=True)
    status: Mapped[str] = mapped_column(
        String(10), server_default=PengirimanStatus.DRAF.value, index=True
    )
    lokasi_asal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"), index=True
    )
    lokasi_tujuan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"), index=True
    )
    # satu permintaan dipenuhi tepat satu pengiriman (D9)
    permintaan_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("permintaan.id", ondelete="RESTRICT"), unique=True
    )
    deliveryman_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    kendaraan_jenis: Mapped[str | None] = mapped_column(String(10))
    kendaraan_nomor: Mapped[str | None] = mapped_column(String(12))
    tanggal_kirim: Mapped[date] = mapped_column(Date)
    catatan: Mapped[str | None] = mapped_column(String(500))
    dibuat_oleh_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    dikirim_oleh_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    dikirim_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    diterima_oleh_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    diterima_pada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    catatan_penerimaan: Mapped[str | None] = mapped_column(String(500))

    lokasi_asal: Mapped["Lokasi"] = relationship(foreign_keys=[lokasi_asal_id])
    lokasi_tujuan: Mapped["Lokasi"] = relationship(foreign_keys=[lokasi_tujuan_id])
    permintaan: Mapped["Permintaan | None"] = relationship(back_populates="pengiriman")
    deliveryman: Mapped["User | None"] = relationship(foreign_keys=[deliveryman_id])
    detail: Mapped[list["PengirimanDetail"]] = relationship(
        back_populates="pengiriman", cascade="all, delete-orphan", passive_deletes=True,
        order_by="PengirimanDetail.id",
    )
    dibuat_oleh: Mapped["User"] = relationship(foreign_keys=[dibuat_oleh_id])
    dikirim_oleh: Mapped["User | None"] = relationship(foreign_keys=[dikirim_oleh_id])
    diterima_oleh: Mapped["User | None"] = relationship(foreign_keys=[diterima_oleh_id])

class PengirimanDetail(Base):
    __tablename__ = "pengiriman_detail"
    __table_args__ = (
        UniqueConstraint("pengiriman_id", "produk_id"),
        CheckConstraint("jumlah_dikirim > 0", name="jumlah_dikirim"),
        CheckConstraint(
            "jumlah_diterima IS NULL OR jumlah_diterima BETWEEN 0 AND jumlah_dikirim",
            name="jumlah_diterima",
        ),
        # selisih penerimaan wajib dijelaskan di catatan
        CheckConstraint(
            "jumlah_diterima IS NULL OR jumlah_diterima = jumlah_dikirim OR catatan IS NOT NULL",
            name="catatan_selisih",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    pengiriman_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("pengiriman.id", ondelete="CASCADE")
    )
    produk_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("produk.id", ondelete="RESTRICT"))
    jumlah_dikirim: Mapped[int]
    jumlah_diterima: Mapped[int | None]
    catatan: Mapped[str | None] = mapped_column(String(300))

    pengiriman: Mapped["Pengiriman"] = relationship(back_populates="detail")
    produk: Mapped["Produk"] = relationship()
