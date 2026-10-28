from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.core.sanitize import SingleLineText
from app.models import UserSession
from app.schemas.fields import EmailAddress, Password, UtcDateTime
from app.schemas.lokasi import LokasiSummary

class RegisterRequest(BaseModel):
    # role dan lokasi tidak ada di schema, keduanya diisi admin saat menyetujui akun
    model_config = ConfigDict(extra="forbid")

    name: Annotated[SingleLineText, Field(min_length=2, max_length=100)]
    email: EmailAddress
    password: Password
    password_confirmation: str

    @field_validator("password_confirmation")
    @classmethod
    def same_as_password(cls, value: str, info: ValidationInfo) -> str:
        # dicek hanya kalau password sendiri sudah valid
        if "password" in info.data and value != info.data["password"]:
            raise ValueError("Konfirmasi password tidak sama")
        return value

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailAddress
    password: Annotated[str, Field(min_length=1, max_length=128)]


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: Annotated[str, Field(min_length=1, max_length=128)]
    new_password: Password
    new_password_confirmation: str

    @field_validator("new_password_confirmation")
    @classmethod
    def same_as_new_password(cls, value: str, info: ValidationInfo) -> str:
        if "new_password" in info.data and value != info.data["new_password"]:
            raise ValueError("Konfirmasi password tidak sama")
        return value

class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str | None
    status: str
    lokasi: LokasiSummary | None
    last_login_at: UtcDateTime | None

class AuthResponse(BaseModel):
    user: UserProfile
    csrf_token: str

    @classmethod
    def of(cls, session: UserSession) -> "AuthResponse":
        return cls(user=UserProfile.model_validate(session.user), csrf_token=session.csrf_token)

class MessageResponse(BaseModel):
    pesan: str
