from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.sanitize import MultiLineText
from app.schemas.common import LokasiKontakRef, ProdukRef, UserRef
from app.schemas.fields import (
    BlankToNone,
    ForeignId,
    FutureOrTodayDate,
    OptionalAddress,
    UtcDateTime,
)

class PermintaanItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produk_id: ForeignId
    jumlah_diminta: Annotated[int, Field(ge=1, le=100_000, strict=True)]

class PermintaanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lokasi_peminta_id: ForeignId | None = None
    tanggal_butuh: Annotated[FutureOrTodayDate | None, BlankToNone] = None
    catatan: OptionalAddress = None
    items: Annotated[list[PermintaanItemInput], Field(min_length=1, max_length=50)]

class PermintaanSetujuiItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produk_id: ForeignId
    jumlah_disetujui: Annotated[int, Field(ge=0, le=100_000, strict=True)]

class PermintaanSetujuiInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tanggal_kirim: FutureOrTodayDate
    catatan: OptionalAddress = None
    items: Annotated[list[PermintaanSetujuiItemInput], Field(min_length=1, max_length=50)]

class PermintaanTolakInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alasan_penolakan: Annotated[MultiLineText, Field(min_length=3, max_length=300)]

class PengirimanRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    status: str
    tanggal_kirim: date

class PermintaanProduk(ProdukRef):
    harga_beli: int
    stok_sumber: int = 0

class PermintaanItemResponse(BaseModel):
    id: int
    produk: PermintaanProduk
    jumlah_diminta: int
    jumlah_disetujui: int | None

class PermintaanSummary(BaseModel):
    id: int
    kode: str
    status: str
    lokasi_peminta: LokasiKontakRef
    lokasi_sumber: LokasiKontakRef
    tanggal_butuh: date | None
    catatan: str | None
    alasan_penolakan: str | None
    jumlah_item: int
    pengiriman: PengirimanRef | None
    diajukan_oleh: UserRef
    diproses_oleh: UserRef | None
    diproses_pada: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime

class PermintaanDetailResponse(PermintaanSummary):
    items: list[PermintaanItemResponse]
