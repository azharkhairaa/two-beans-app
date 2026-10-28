from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Identity, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, check_values

if TYPE_CHECKING:
    from app.models.produk import Produk

class KategoriType(StrEnum):
    GREEN_BEAN = "green_bean"
    ROASTED_BEAN = "roasted_bean"
    PERALATAN = "peralatan"
    HABIS_PAKAI = "habis_pakai"

class Kategori(TimestampMixin, Base):
    __tablename__ = "kategori"
    __table_args__ = (check_values("jenis", KategoriType),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    nama: Mapped[str] = mapped_column(String(60))
    jenis: Mapped[str] = mapped_column(String(12))
    deskripsi: Mapped[str | None] = mapped_column(String(500))

    # FK RESTRICT dijaga database, ORM tidak mengosongkan FK anak saat induk dihapus
    produk: Mapped[list["Produk"]] = relationship(back_populates="kategori", passive_deletes="all")

Index("uq_kategori_nama_lower", func.lower(Kategori.nama), unique=True)
