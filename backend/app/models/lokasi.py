from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Identity, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, check_values

if TYPE_CHECKING:
    from app.models.stok import Stok
    from app.models.user import User

class LokasiType(StrEnum):
    GUDANG_UTAMA = "gudang_utama"
    GUDANG_CABANG = "gudang_cabang"
    OUTLET = "outlet"

class Lokasi(TimestampMixin, Base):
    __tablename__ = "lokasi"
    __table_args__ = (
        check_values("jenis", LokasiType),
        CheckConstraint(r"kode ~ '^(GU|GC|OT)-[0-9]{2}$'", name="kode_format"),
        CheckConstraint(
            "left(kode, 2) = CASE jenis WHEN 'gudang_utama' THEN 'GU' "
            "WHEN 'gudang_cabang' THEN 'GC' ELSE 'OT' END",
            name="kode_jenis",
        ),
        CheckConstraint(r"telepon IS NULL OR telepon ~ '^\+?[0-9]{9,15}$'", name="telepon"),
        # indeks unik parsial: hanya boleh ada satu gudang utama
        Index(
            "uq_lokasi_satu_gudang_utama", "jenis", unique=True,
            postgresql_where=text("jenis = 'gudang_utama'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    kode: Mapped[str] = mapped_column(String(10), unique=True)
    nama: Mapped[str] = mapped_column(String(100))
    jenis: Mapped[str] = mapped_column(String(15))
    alamat: Mapped[str | None] = mapped_column(String(500))
    telepon: Mapped[str | None] = mapped_column(String(20))
    aktif: Mapped[bool] = mapped_column(server_default=text("true"))

    # FK RESTRICT dijaga database, ORM tidak mengosongkan FK anak saat induk dihapus
    users: Mapped[list["User"]] = relationship(back_populates="lokasi", passive_deletes="all")
    stok: Mapped[list["Stok"]] = relationship(back_populates="lokasi", passive_deletes="all")

# nama lokasi unik tanpa membedakan huruf besar dan kecil
Index("uq_lokasi_nama_lower", func.lower(Lokasi.nama), unique=True)
