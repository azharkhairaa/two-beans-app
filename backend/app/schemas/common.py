from enum import StrEnum
from math import ceil
from typing import Self

from fastapi import Query
from pydantic import BaseModel, ConfigDict

from app.models import Produk

class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"

class ActiveFilter(StrEnum):
    TRUE = "true"
    FALSE = "false"
    ALL = "semua"

class PageParams:
    # dependency paginasi: page mulai 1, per_page 1 sampai 50
    def __init__(
        self,
        page: int = Query(1, ge=1, le=100000),
        per_page: int = Query(10, ge=1, le=50),
    ):
        self.page = page
        self.per_page = per_page

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

class PageMeta(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int

class Page[T](BaseModel):
    data: list[T]
    meta: PageMeta

    @classmethod
    def of(cls, data: list, total: int, params: PageParams) -> "Page[T]":
        return cls(data=data, meta=PageMeta(
            page=params.page, per_page=params.per_page, total=total,
            total_pages=ceil(total / params.per_page) if total else 0,
        ))

class OptionResponse(BaseModel):
    # pilihan ringkas untuk dropdown formulir
    id: int
    nama: str

class LokasiKontakRef(BaseModel):
    # lokasi yang dirujuk dokumen, alamat dan telepon ikut untuk surat jalan dan nota
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    nama: str
    jenis: str
    alamat: str | None
    telepon: str | None

class UserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class ProdukRef(BaseModel):
    # identitas produk di baris dokumen, harga dan stok ditambahkan schema dokumennya
    id: int
    sku: str
    nama: str
    satuan: str
    jenis: str

    @classmethod
    def of(cls, produk: Produk, **extra: int | None) -> Self:
        return cls(
            id=produk.id,
            sku=produk.sku,
            nama=produk.nama,
            satuan=produk.satuan,
            jenis=produk.kategori.jenis,
            **extra,
        )
