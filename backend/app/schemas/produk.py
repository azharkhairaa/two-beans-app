from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.core.sanitize import MultiLineText, SingleLineText
from app.models import CoffeeType, ProdukUnit, RoastLevel
from app.schemas.fields import BlankToNone, ForeignId, Rupiah, Sku, UtcDateTime

class ProdukInput(BaseModel):
    # tidak ada field stok, stok hanya berubah lewat dokumen (BR-01), field asing ditolak 422
    model_config = ConfigDict(extra="forbid")

    sku: Sku
    nama: Annotated[SingleLineText, Field(min_length=3, max_length=120)]
    kategori_id: ForeignId
    merek: Annotated[Annotated[SingleLineText, Field(max_length=60)] | None, BlankToNone] = None
    satuan: ProdukUnit
    berat_gram: Annotated[int, Field(gt=0, strict=True)] | None = None
    tingkat_sangrai: Annotated[RoastLevel | None, BlankToNone] = None
    jenis_kopi: Annotated[CoffeeType | None, BlankToNone] = None
    harga_beli: Rupiah = 0
    harga_jual: Rupiah = 0
    deskripsi: Annotated[
        Annotated[MultiLineText, Field(max_length=1000)] | None, BlankToNone
    ] = None
    aktif: StrictBool = True

class KategoriRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    jenis: str

class LokasiRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    nama: str
    # jenis lokasi menentukan cara isi ulang stock dari kartu stock
    jenis: str

class ProdukResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    nama: str
    kategori: KategoriRef
    merek: str | None
    satuan: str
    berat_gram: int | None
    tingkat_sangrai: str | None
    jenis_kopi: str | None
    harga_beli: int
    harga_jual: int
    deskripsi: str | None
    aktif: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime

class StokLokasi(BaseModel):
    lokasi: LokasiRef
    jumlah: int
    stok_minimum: int
    rak: str | None
    status_stok: str
    # null untuk lokasi lain bila manager hanya boleh melihat jumlahnya
    nilai: int | None

class ProdukDetail(ProdukResponse):
    stok: list[StokLokasi]
    total_stok: int
    total_nilai: int | None
    # jumlah yang sedang dibawa pengiriman berstatus dikirim
    dalam_perjalanan: int

class ProdukOption(BaseModel):
    # stok terisi bila opsi diminta untuk satu lokasi, misalnya di formulir pengiriman
    id: int
    sku: str
    nama: str
    satuan: str
    jenis: str
    harga_beli: int
    harga_jual: int
    stok: int | None = None
