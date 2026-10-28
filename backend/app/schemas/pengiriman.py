from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.core.sanitize import SingleLineText
from app.models import KendaraanType
from app.schemas.fields import (
    BlankToNone,
    ForeignId,
    FutureOrTodayDate,
    OptionalAddress,
    OptionalVehicleNumber,
    UtcDateTime,
)

class PengirimanItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produk_id: ForeignId
    jumlah_dikirim: Annotated[int, Field(ge=1, le=100_000, strict=True)]

class PengirimanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lokasi_asal_id: ForeignId | None = None
    lokasi_tujuan_id: ForeignId
    tanggal_kirim: FutureOrTodayDate
    deliveryman_id: ForeignId | None = None
    kendaraan_jenis: Annotated[KendaraanType | None, BlankToNone] = None
    kendaraan_nomor: OptionalVehicleNumber = None
    catatan: OptionalAddress = None
    items: Annotated[list[PengirimanItemInput], Field(min_length=1, max_length=50)]

class PengirimanKirimInput(BaseModel):
    # melengkapi kurir dan kendaraan saat mengirim draf (boleh diisi saat draf maupun saat kirim)
    model_config = ConfigDict(extra="forbid")

    deliveryman_id: ForeignId | None = None
    kendaraan_jenis: Annotated[KendaraanType | None, BlankToNone] = None
    kendaraan_nomor: OptionalVehicleNumber = None

class PengirimanTerimaItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    produk_id: ForeignId
    jumlah_diterima: Annotated[int, Field(ge=0, le=100_000, strict=True)]
    catatan: Annotated[
        Annotated[SingleLineText, Field(max_length=300)] | None, BlankToNone
    ] = None

class PengirimanTerimaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catatan_penerimaan: OptionalAddress = None
    items: Annotated[list[PengirimanTerimaItemInput], Field(min_length=1, max_length=50)]

class PengirimanLokasi(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    nama: str
    jenis: str
    alamat: str | None
    telepon: str | None

class PermintaanRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str

class UserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class PengirimanProduk(BaseModel):
    id: int
    sku: str
    nama: str
    satuan: str
    jenis: str
    harga_beli: int

class PengirimanItemResponse(BaseModel):
    id: int
    produk: PengirimanProduk
    jumlah_dikirim: int
    jumlah_diterima: int | None
    selisih: int | None
    catatan: str | None

class PengirimanSummary(BaseModel):
    id: int
    kode: str
    status: str
    lokasi_asal: PengirimanLokasi
    lokasi_tujuan: PengirimanLokasi
    permintaan: PermintaanRef | None
    deliveryman: UserRef | None
    kendaraan_jenis: str | None
    kendaraan_nomor: str | None
    tanggal_kirim: date
    catatan: str | None
    catatan_penerimaan: str | None
    jumlah_item: int
    nilai_dikirim: int
    dibuat_oleh: UserRef
    dikirim_oleh: UserRef | None
    dikirim_pada: UtcDateTime | None
    diterima_oleh: UserRef | None
    diterima_pada: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime

class PengirimanDetailResponse(PengirimanSummary):
    items: list[PengirimanItemResponse]
