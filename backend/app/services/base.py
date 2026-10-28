from typing import Any

from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import DataInUse, NotFound
from app.models import Base
from app.schemas.common import ActiveFilter, Page, PageParams

class CrudService[M: Base]:
    # induk service master data: ambil atau 404, simpan, ubah, hapus yang belum dipakai dan paginasi
    model: type[M]
    label: str
    # nama tabel anak untuk pesan "masih dipakai", sisanya memakai nama tabel
    TABLE_LABELS = {"users": "user", "stok_mutasi": "riwayat stok"}

    def __init__(self, db: Session):
        self.db = db

    def get_or_404(self, item_id: int) -> M:
        obj = self.db.get(self.model, item_id)
        if obj is None:
            raise NotFound(f"{self.label} tidak ditemukan")
        return obj

    def create(self, data: BaseModel) -> M:
        return self.save(self.model(**data.model_dump()))

    def update(self, obj: M, data: BaseModel) -> M:
        for field, value in data.model_dump().items():
            setattr(obj, field, value)
        return self.save(obj)

    def save(self, obj: M) -> M:
        # nilai unik ganda ditangkap IntegrityError lalu dipetakan handler lewat nama constraint
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: M) -> None:
        self.ensure_unused(obj)
        self.db.delete(obj)
        self.db.commit()

    def usage(self, obj: M) -> list[tuple[str, int]]:
        # jumlah baris tabel lain yang merujuk obj, dibaca dari FK di metadata model
        result = []
        for table in Base.metadata.sorted_tables:
            for fk in table.foreign_keys:
                if fk.column.table is self.model.__table__:
                    count = self.db.scalar(select(func.count()).where(fk.parent == obj.id))
                    if count:
                        result.append((table.name, count))
        return result

    def ensure_unused(self, obj: M) -> None:
        usage = self.usage(obj)
        if not usage:
            return
        table, count = max(usage, key=lambda item: item[1])
        message = f"{self.label} masih dipakai {count} {self.table_label(table)}"
        if hasattr(self.model, "aktif"):
            message += ". Nonaktifkan saja bila tidak dipakai lagi"
        raise DataInUse(message)

    def table_label(self, table: str) -> str:
        if table in self.TABLE_LABELS:
            return self.TABLE_LABELS[table]
        if table.endswith("_detail"):
            return "baris " + table.removesuffix("_detail")
        return table.replace("_", " ")

    def paginate(self, query: Select, params: PageParams, schema: type[BaseModel]) -> Page:
        total = self.db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        rows = self.db.scalars(query.limit(params.per_page).offset(params.offset)).all()
        return Page[schema].of([schema.model_validate(row) for row in rows], total, params)

    @staticmethod
    def contains(column: ColumnElement[str], text: str) -> ColumnElement[bool]:
        # %, _ dan \ dari input di-escape supaya dicari sebagai teks biasa
        escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return column.ilike(f"%{escaped}%", escape="\\")

    @staticmethod
    def active_filter(query: Select, column: Any, aktif: ActiveFilter) -> Select:
        if aktif == ActiveFilter.ALL:
            return query
        return query.where(column.is_(aktif == ActiveFilter.TRUE))
