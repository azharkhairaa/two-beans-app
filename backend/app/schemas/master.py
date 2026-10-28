from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.core.sanitize import SingleLineText
from app.models import CustomerType, KategoriType
from app.schemas.fields import (
    OptionalAddress,
    OptionalEmail,
    OptionalLine,
    OptionalPhone,
    UtcDateTime,
)

Nama = Annotated[SingleLineText, Field(min_length=3, max_length=100)]

class KategoriInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nama: Annotated[SingleLineText, Field(min_length=3, max_length=60)]
    jenis: KategoriType
    deskripsi: OptionalAddress = None

class KategoriResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    jenis: str
    deskripsi: str | None
    jumlah_produk: int
    created_at: UtcDateTime
    updated_at: UtcDateTime

    @classmethod
    def of(cls, kategori, jumlah_produk: int) -> "KategoriResponse":
        names = (name for name in cls.model_fields if name != "jumlah_produk")
        fields = {name: getattr(kategori, name) for name in names}
        return cls(**fields, jumlah_produk=jumlah_produk)

class SupplierInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nama: Nama
    kontak: OptionalLine = None
    telepon: OptionalPhone = None
    email: OptionalEmail = None
    alamat: OptionalAddress = None
    aktif: StrictBool = True

class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    kontak: str | None
    telepon: str | None
    email: str | None
    alamat: str | None
    aktif: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime

class CustomerInput(SupplierInput):
    jenis: CustomerType

class CustomerResponse(SupplierResponse):
    jenis: str

class CustomerDetail(CustomerResponse):
    # omzet penjualan diposting ke customer ini dalam 30 hari terakhir (WIB)
    total_pembelian_30_hari: int

class CustomerOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    jenis: str
