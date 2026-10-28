from enum import StrEnum
from math import ceil

from fastapi import Query
from pydantic import BaseModel

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
