from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page
from app.schemas.fields import OptionalRak, UtcDateTime
from app.schemas.lokasi import LokasiSummary

class StokSettingInput(BaseModel):
    # tidak ada field jumlah, stok hanya berubah lewat dokumen (BR-01)
    model_config = ConfigDict(extra="forbid")

    stok_minimum: Annotated[int, Field(ge=0, le=100_000, strict=True)]
    rak: OptionalRak = None

class StokProduk(BaseModel):
    id: int
    sku: str
    nama: str
    satuan: str
    kategori: str
    jenis: str
    harga_beli: int

class StokItem(BaseModel):
    produk: StokProduk
    jumlah: int
    stok_minimum: int
    rak: str | None
    status_stok: str
    nilai: int
    updated_at: UtcDateTime

class StokPage(Page[StokItem]):
    # lokasi yang ditampilkan, berguna saat lokasi_id tidak dikirim
    lokasi: LokasiSummary

class KartuStokItem(BaseModel):
    id: int
    jenis: str
    dokumen: str
    perubahan: int
    stok_sebelum: int
    stok_sesudah: int
    oleh: str
    created_at: UtcDateTime
