from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, check_values

if TYPE_CHECKING:
    from app.models.lokasi import Lokasi
    from app.models.produk import Produk
    from app.models.user import User

class StokMutasiType(StrEnum):
    MASUK = "masuk"
    KELUAR = "keluar"
    PENYESUAIAN = "penyesuaian"
    KIRIM = "kirim"
    TERIMA = "terima"
    PEMBELIAN = "pembelian"
    PENJUALAN = "penjualan"

class StokMutasi(Base):
    # buku besar stok, satu baris per perubahan dengan saldo sebelum dan sesudah
    __tablename__ = "stok_mutasi"
    __table_args__ = (
        check_values("jenis", StokMutasiType),
        CheckConstraint("perubahan <> 0", name="perubahan"),
        CheckConstraint(
            "(jenis IN ('masuk', 'terima', 'pembelian') AND perubahan > 0) "
            "OR (jenis IN ('keluar', 'kirim', 'penjualan') AND perubahan < 0) "
            "OR jenis = 'penyesuaian'",
            name="arah",
        ),
        CheckConstraint(
            "stok_sebelum >= 0 AND stok_sesudah >= 0 AND stok_sesudah = stok_sebelum + perubahan",
            name="saldo",
        ),
        # satu dokumen sumber, kolom sumbernya harus cocok dengan jenis mutasi
        CheckConstraint(
            "num_nonnulls(transaksi_id, pengiriman_id, pembelian_id, penjualan_id) = 1",
            name="satu_sumber",
        ),
        CheckConstraint(
            "((jenis IN ('masuk', 'keluar', 'penyesuaian')) = (transaksi_id IS NOT NULL)) "
            "AND ((jenis IN ('kirim', 'terima')) = (pengiriman_id IS NOT NULL)) "
            "AND ((jenis = 'pembelian') = (pembelian_id IS NOT NULL)) "
            "AND ((jenis = 'penjualan') = (penjualan_id IS NOT NULL))",
            name="sumber_jenis",
        ),
        Index("ix_stok_mutasi_lokasi_produk", "lokasi_id", "produk_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    lokasi_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("lokasi.id", ondelete="RESTRICT"))
    produk_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("produk.id", ondelete="RESTRICT"), index=True
    )
    jenis: Mapped[str] = mapped_column(String(12))
    perubahan: Mapped[int]
    stok_sebelum: Mapped[int]
    stok_sesudah: Mapped[int]
    transaksi_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("transaksi.id", ondelete="RESTRICT"), index=True
    )
    pengiriman_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pengiriman.id", ondelete="RESTRICT"), index=True
    )
    pembelian_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pembelian.id", ondelete="RESTRICT"), index=True
    )
    penjualan_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("penjualan.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    lokasi: Mapped["Lokasi"] = relationship()
    produk: Mapped["Produk"] = relationship()
    user: Mapped["User"] = relationship()
