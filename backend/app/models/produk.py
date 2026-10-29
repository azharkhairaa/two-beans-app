from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Identity, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, check_values

if TYPE_CHECKING:
    from app.models.kategori import Kategori
    from app.models.stok import Stok

class ProdukUnit(StrEnum):
    PACK = "pack"
    PCS = "pcs"
    BOX = "box"
    SET = "set"
    KG = "kg"

class RoastLevel(StrEnum):
    LIGHT = "light"
    MEDIUM = "medium"
    MEDIUM_DARK = "medium_dark"
    DARK = "dark"

class CoffeeType(StrEnum):
    ARABIKA = "arabika"
    ROBUSTA = "robusta"
    EXCELSA = "excelsa"
    LIBERIKA = "liberika"
    # campuran beberapa jenis kopi
    BLENDED = "blended"

class Produk(TimestampMixin, Base):
    __tablename__ = "produk"
    __table_args__ = (
        CheckConstraint(r"sku ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'", name="sku_format"),
        check_values("satuan", ProdukUnit),
        CheckConstraint("berat_gram IS NULL OR berat_gram > 0", name="berat_gram"),
        check_values("tingkat_sangrai", RoastLevel, nullable=True),
        check_values("jenis_kopi", CoffeeType, nullable=True),
        CheckConstraint("harga_beli >= 0", name="harga_beli"),
        CheckConstraint("harga_jual >= 0", name="harga_jual"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sku: Mapped[str] = mapped_column(String(30), unique=True)
    nama: Mapped[str] = mapped_column(String(120))
    kategori_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("kategori.id", ondelete="RESTRICT"), index=True
    )
    merek: Mapped[str | None] = mapped_column(String(60))
    satuan: Mapped[str] = mapped_column(String(10))
    berat_gram: Mapped[int | None]
    tingkat_sangrai: Mapped[str | None] = mapped_column(String(12))
    # wajib untuk green bean dan roasted bean, kosong untuk jenis lain (dijaga ProdukService)
    jenis_kopi: Mapped[str | None] = mapped_column(String(10))
    # HPP rupiah per satuan (nama kolom lama dipertahankan), ikut harga PO terakhir
    harga_beli: Mapped[int] = mapped_column(server_default=text("0"))
    harga_jual: Mapped[int] = mapped_column(server_default=text("0"))
    deskripsi: Mapped[str | None] = mapped_column(String(1000))
    aktif: Mapped[bool] = mapped_column(server_default=text("true"))

    kategori: Mapped["Kategori"] = relationship(back_populates="produk")
    # FK RESTRICT dijaga database, ORM tidak mengosongkan FK anak saat induk dihapus
    stok: Mapped[list["Stok"]] = relationship(back_populates="produk", passive_deletes="all")
