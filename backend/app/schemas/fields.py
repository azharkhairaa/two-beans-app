import re
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field

class FieldRules:
    # aturan field yang dipakai ulang di banyak schema
    LETTER = re.compile(r"[^\W\d_]")
    DIGIT = re.compile(r"\d")

    @staticmethod
    def lowercase(value: str) -> str:
        return value.lower()

    @staticmethod
    def utc(value: datetime) -> datetime:
        # zona sesi database bisa berbeda (lokal WIB, Neon UTC), response selalu UTC berakhiran Z
        return value.astimezone(UTC)

    @classmethod
    def password(cls, value: str) -> str:
        # password tidak dibersihkan, panjang dihitung dalam byte karena batas bcrypt 72 byte
        size = len(value.encode())
        if size < 8:
            raise ValueError("Minimal 8 karakter")
        if size > 72:
            raise ValueError("Maksimal 72 byte")
        if not (cls.LETTER.search(value) and cls.DIGIT.search(value)):
            raise ValueError("Harus berisi huruf dan angka")
        return value

EmailAddress = Annotated[EmailStr, Field(max_length=254), AfterValidator(FieldRules.lowercase)]
Password = Annotated[str, AfterValidator(FieldRules.password)]
UtcDateTime = Annotated[datetime, AfterValidator(FieldRules.utc)]
