from typing import Annotated, ClassVar

from pydantic import BaseModel, ConfigDict, Field, StrictBool, ValidationInfo, field_validator

from app.core.sanitize import SingleLineText
from app.models import LokasiType
from app.schemas.fields import LokasiKode, OptionalAddress, OptionalPhone, UtcDateTime

class LokasiSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    nama: str
    jenis: str

class LokasiInput(BaseModel):
    # jenis ditulis sebelum kode supaya prefiks kode bisa dicek terhadap jenis
    model_config = ConfigDict(extra="forbid")
    PREFIX: ClassVar[dict[str, str]] = {
        LokasiType.GUDANG_UTAMA: "GU", LokasiType.GUDANG_CABANG: "GC", LokasiType.OUTLET: "OT",
    }

    jenis: LokasiType
    kode: LokasiKode
    nama: Annotated[SingleLineText, Field(min_length=3, max_length=100)]
    alamat: OptionalAddress = None
    telepon: OptionalPhone = None
    aktif: StrictBool = True

    @field_validator("kode")
    @classmethod
    def prefix_matches_jenis(cls, value: str, info: ValidationInfo) -> str:
        jenis = info.data.get("jenis")
        if jenis is not None and not value.startswith(cls.PREFIX[jenis] + "-"):
            raise ValueError(f"Kode {jenis.replace('_', ' ')} diawali {cls.PREFIX[jenis]}-")
        return value

class LokasiRingkasan(BaseModel):
    sku_ada: int
    menipis: int
    habis: int
    nilai: int

class LokasiResponse(LokasiSummary):
    alamat: str | None
    telepon: str | None
    aktif: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime
    ringkasan: LokasiRingkasan

    @classmethod
    def of(cls, lokasi, sku_ada: int, menipis: int, habis: int, nilai: int) -> "LokasiResponse":
        fields = {name: getattr(lokasi, name) for name in cls.model_fields if name != "ringkasan"}
        ringkasan = LokasiRingkasan(sku_ada=sku_ada, menipis=menipis, habis=habis, nilai=nilai)
        return cls(**fields, ringkasan=ringkasan)
