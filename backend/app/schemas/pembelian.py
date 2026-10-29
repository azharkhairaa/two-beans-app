from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LokasiKontakRef, ProdukRef, UserRef
from app.schemas.fields import (
    BlankToNone,
    DocumentDate,
    ForeignId,
    FutureOrTodayDate,
    OptionalAddress,
    Rupiah,
    UtcDateTime,
)

class PembelianItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produk_id: ForeignId
    jumlah: Annotated[int, Field(ge=1, le=100_000, strict=True)]
    harga_satuan: Rupiah

class PembelianInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_id: ForeignId
    tanggal_perkiraan: Annotated[FutureOrTodayDate | None, BlankToNone] = None
    catatan: OptionalAddress = None
    items: Annotated[list[PembelianItemInput], Field(min_length=1, max_length=50)]

class PembelianPesanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tanggal_pesan: Annotated[DocumentDate | None, BlankToNone] = None
    tanggal_perkiraan: Annotated[FutureOrTodayDate | None, BlankToNone] = None

class PembelianTerimaItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produk_id: ForeignId
    jumlah_diterima: Annotated[int, Field(ge=0, le=100_000, strict=True)]

class PembelianTerimaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catatan: OptionalAddress = None
    items: Annotated[list[PembelianTerimaItemInput], Field(min_length=1, max_length=50)]

class SupplierRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    kontak: str | None
    telepon: str | None
    email: str | None

class PembelianProduk(ProdukRef):
    harga_beli: int

class PembelianItemResponse(BaseModel):
    id: int
    produk: PembelianProduk
    jumlah: int
    harga_satuan: int
    subtotal: int
    jumlah_diterima: int | None
    subtotal_diterima: int | None

class PembelianSummary(BaseModel):
    id: int
    kode: str
    status: str
    supplier: SupplierRef
    lokasi: LokasiKontakRef
    tanggal_pesan: date | None
    tanggal_perkiraan: date | None
    catatan: str | None
    jumlah_item: int
    total_pesanan: int
    total_diterima: int | None
    dibuat_oleh: UserRef
    dipesan_oleh: UserRef | None
    diterima_oleh: UserRef | None
    diterima_pada: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime

class PembelianDetailResponse(PembelianSummary):
    items: list[PembelianItemResponse]
