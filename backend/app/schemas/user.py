from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import UserRole
from app.schemas.fields import ForeignId, UtcDateTime
from app.schemas.lokasi import LokasiSummary

class UserUpdate(BaseModel):
    # PATCH sebagian: hanya field yang dikirim yang diubah, status menunggu tidak bisa dipilih lagi
    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = None
    lokasi_id: ForeignId | None = None
    status: Literal["aktif", "nonaktif"] | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Isi minimal satu dari role, lokasi_id atau status")
        return self

class UserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str | None
    status: str
    lokasi: LokasiSummary | None
    last_login_at: UtcDateTime | None
    created_at: UtcDateTime
