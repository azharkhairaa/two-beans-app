import re
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, EmailStr, Field

from app.core.clock import Clock
from app.core.sanitize import MultiLineText, SingleLineText

class FieldRules:
    # aturan field yang dipakai ulang di banyak schema
    LETTER = re.compile(r"[^\W\d_]")
    DIGIT = re.compile(r"\d")
    # 9 sampai 15 digit, diawali 0 atau +62
    PHONE = re.compile(r"(?:\+62\d{7,13}|0\d{8,14})")
    LOKASI_KODE = re.compile(r"(?:GU|GC|OT)-\d{2}")
    SKU = re.compile(r"[A-Z0-9]+(?:-[A-Z0-9]+)*")
    RAK = re.compile(r"[A-Z]{1,2}-\d{2}")
    VEHICLE_NUMBER = re.compile(r"[A-Z]{1,2} [0-9]{1,4}(?: [A-Z]{1,3})?")

    @staticmethod
    def lowercase(value: str) -> str:
        return value.lower()

    @staticmethod
    def blank_to_none(value: object) -> object:
        # field opsional yang dikirim kosong disimpan NULL, bukan string kosong
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @classmethod
    def phone(cls, value: str) -> str:
        value = re.sub(r"[\s-]", "", value)
        if not cls.PHONE.fullmatch(value):
            raise ValueError("Format telepon seperti 081234567890 atau +6281234567890")
        return value

    @classmethod
    def lokasi_kode(cls, value: str) -> str:
        value = value.strip().upper()
        if not cls.LOKASI_KODE.fullmatch(value):
            raise ValueError("Format kode seperti GU-01, GC-01 atau OT-01")
        return value

    @classmethod
    def sku(cls, value: str) -> str:
        value = value.strip().upper()
        if not 3 <= len(value) <= 30:
            raise ValueError("SKU 3 sampai 30 karakter")
        if not cls.SKU.fullmatch(value):
            raise ValueError("SKU hanya huruf, angka dan tanda hubung, misalnya BK-ARB-GAYO-200")
        return value

    @classmethod
    def rak(cls, value: str) -> str:
        value = value.strip().upper()
        if not cls.RAK.fullmatch(value):
            raise ValueError("Format rak seperti A-01 atau BC-12")
        return value

    @classmethod
    def vehicle_number(cls, value: str) -> str:
        value = " ".join(value.strip().upper().split())
        if not cls.VEHICLE_NUMBER.fullmatch(value):
            raise ValueError("Format nomor kendaraan seperti D 1234 ABC atau B 9012")
        return value

    @staticmethod
    def utc(value: datetime) -> datetime:
        # zona sesi database bisa berbeda (lokal WIB, Neon UTC), response selalu UTC berakhiran Z
        return value.astimezone(UTC)

    @staticmethod
    def document_date(value: date) -> date:
        # BR-19: tanggal transaksi dan penjualan tidak lewat hari ini WIB dan maksimal 365 hari lalu
        today = Clock.today()
        if value > today:
            raise ValueError("Tanggal tidak boleh melewati hari ini")
        if value < today - timedelta(days=365):
            raise ValueError("Tanggal tidak boleh lebih tua dari 365 hari")
        return value

    @staticmethod
    def future_or_today(value: date) -> date:
        today = Clock.today()
        if value < today:
            raise ValueError("Tanggal tidak boleh sebelum hari ini")
        if value > today + timedelta(days=365):
            raise ValueError("Tanggal tidak boleh lebih dari 365 hari ke depan")
        return value

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
DocumentDate = Annotated[date, AfterValidator(FieldRules.document_date)]
FutureOrTodayDate = Annotated[date, AfterValidator(FieldRules.future_or_today)]
LokasiKode = Annotated[str, AfterValidator(FieldRules.lokasi_kode)]
Sku = Annotated[str, AfterValidator(FieldRules.sku)]
VehicleNumber = Annotated[str, AfterValidator(FieldRules.vehicle_number)]
# integer ketat: "5" dari JSON ditolak, sesuai Spesifikasi API
Rupiah = Annotated[int, Field(ge=0, le=1_000_000_000, strict=True)]
ForeignId = Annotated[int, Field(gt=0, strict=True)]

# field opsional: string kosong menjadi None lalu panjang dicek sesudah teks dibersihkan
BlankToNone = BeforeValidator(FieldRules.blank_to_none)
OptionalLine = Annotated[Annotated[SingleLineText, Field(max_length=100)] | None, BlankToNone]
OptionalAddress = Annotated[Annotated[MultiLineText, Field(max_length=500)] | None, BlankToNone]
OptionalEmail = Annotated[EmailAddress | None, BlankToNone]
OptionalPhone = Annotated[Annotated[str, AfterValidator(FieldRules.phone)] | None, BlankToNone]
OptionalRak = Annotated[Annotated[str, AfterValidator(FieldRules.rak)] | None, BlankToNone]
OptionalVehicleNumber = Annotated[VehicleNumber | None, BlankToNone]
