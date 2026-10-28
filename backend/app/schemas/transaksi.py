from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.sanitize import SingleLineText
from app.models import TransaksiType
from app.schemas.fields import (
    BlankToNone,
    DocumentDate,
    ForeignId,
    OptionalAddress,
    UtcDateTime,
)
from app.schemas.lokasi import LokasiSummary

class TransaksiItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produk_id: ForeignId
    jumlah: Annotated[int, Field(ge=-100_000, le=100_000, strict=True)]

class TransaksiUpdate(BaseModel):
    # jenis opsional saat ubah draf dan tidak boleh berbeda dari jenis awal
    model_config = ConfigDict(extra="forbid")

    jenis: TransaksiType | None = None
    lokasi_id: ForeignId | None = None
    tanggal: DocumentDate
    alasan: Annotated[SingleLineText, Field(min_length=2, max_length=30)]
    keterangan: Annotated[
        Annotated[SingleLineText, Field(max_length=120)] | None, BlankToNone
    ] = None
    catatan: OptionalAddress = None
    items: Annotated[list[TransaksiItemInput], Field(min_length=1, max_length=50)]

class TransaksiInput(TransaksiUpdate):
    jenis: TransaksiType

class TransaksiProduk(BaseModel):
    id: int
    sku: str
    nama: str
    satuan: str
    jenis: str
    harga_beli: int

class TransaksiItemResponse(BaseModel):
    id: int
    produk: TransaksiProduk
    jumlah: int

class TransaksiSummary(BaseModel):
    id: int
    kode: str
    jenis: str
    status: str
    tanggal: date
    lokasi: LokasiSummary
    alasan: str
    keterangan: str | None
    catatan: str | None
    jumlah_item: int
    dibuat_oleh: str
    diposting_oleh: str | None
    diposting_pada: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime

class TransaksiDetailResponse(TransaksiSummary):
    items: list[TransaksiItemResponse]
