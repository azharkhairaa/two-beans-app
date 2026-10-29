from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LokasiKontakRef, ProdukRef
from app.schemas.fields import (
    DocumentDate,
    ForeignId,
    OptionalAddress,
    UtcDateTime,
)

class PenjualanItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produk_id: ForeignId
    jumlah: Annotated[int, Field(ge=1, le=100_000, strict=True)]
    harga_satuan: Annotated[int, Field(ge=1, le=1_000_000_000, strict=True)] | None = None

class PenjualanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lokasi_id: ForeignId | None = None
    tanggal: DocumentDate
    customer_id: ForeignId | None = None
    catatan: OptionalAddress = None
    items: Annotated[list[PenjualanItemInput], Field(min_length=1, max_length=50)]

class CustomerRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    jenis: str
    telepon: str | None
    alamat: str | None

class PenjualanProduk(ProdukRef):
    harga_jual: int

class PenjualanItemResponse(BaseModel):
    id: int
    produk: PenjualanProduk
    jumlah: int
    harga_satuan: int
    subtotal: int
    # HPP per unit yang tersimpan di baris, margin = (harga satuan - HPP) x jumlah
    harga_beli: int
    margin: int

class PenjualanSummary(BaseModel):
    id: int
    kode: str
    status: str
    tanggal: date
    lokasi: LokasiKontakRef
    customer: CustomerRef | None
    nama_customer: str
    catatan: str | None
    jumlah_item: int
    total: int
    total_hpp: int
    margin: int
    dibuat_oleh: str
    diposting_oleh: str | None
    diposting_pada: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime

class PenjualanDetailResponse(PenjualanSummary):
    items: list[PenjualanItemResponse]
