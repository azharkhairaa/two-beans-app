from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from pydantic import BaseModel
from sqlalchemy import BigInteger, ColumnElement, Select, cast, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.clock import Clock
from app.core.errors import DataInUse, InvalidStatus, NotFound, ValidationFailed
from app.models import DOCUMENT_NUMBER_SEQUENCE, Base, Lokasi, Produk, User
from app.policies.lokasi_policy import LokasiPolicy
from app.schemas.common import ActiveFilter, Page, PageParams

class SqlMoney:
    # jumlah x harga dihitung bigint supaya tidak overflow int4 (Desain Database 8.2)
    @staticmethod
    def line(quantity: Any, price: Any) -> ColumnElement:
        return cast(quantity, BigInteger) * price

    @staticmethod
    def total(quantity: Any, price: Any) -> ColumnElement:
        return cast(func.coalesce(func.sum(SqlMoney.line(quantity, price)), 0), BigInteger)

class CrudService[M: Base]:
    # induk service master data: ambil atau 404, simpan, ubah, hapus yang belum dipakai dan paginasi
    model: type[M]
    label: str
    # nama tabel anak untuk pesan "masih dipakai", sisanya memakai nama tabel
    TABLE_LABELS = {"users": "user", "stok": "catatan stok lokasi", "stok_mutasi": "riwayat stok"}

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
        # jumlah baris tabel lain yang merujuk obj, dibaca dari FK di metadata model.
        # FK ON DELETE CASCADE (sesi, baris detail) ikut terhapus sehingga tidak menghalangi
        result = []
        for table in Base.metadata.sorted_tables:
            for fk in table.foreign_keys:
                if fk.column.table is self.model.__table__ and fk.ondelete != "CASCADE":
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
        if self.can_deactivate:
            message += ". Nonaktifkan saja bila tidak dipakai lagi"
        raise DataInUse(message)

    @property
    def can_deactivate(self) -> bool:
        return hasattr(self.model, "aktif")

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
    def local_date(column: Any) -> ColumnElement:
        # tanggal WIB dari timestamptz, tidak bergantung zona waktu sesi database (Neon UTC)
        return func.date(func.timezone(Clock.ZONE.key, column))

    @staticmethod
    def active_filter(query: Select, column: Any, aktif: ActiveFilter) -> Select:
        if aktif == ActiveFilter.ALL:
            return query
        return query.where(column.is_(aktif == ActiveFilter.TRUE))

class DokumenService[M: Base]:
    # induk service dokumen: kode otomatis, penggantian detail, cek status dan cakupan lokasi
    model: type[M]
    label: str

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.policy = LokasiPolicy(user)

    def next_code(self, prefix: str, on_date: date | None = None) -> str:
        day = on_date or Clock.today()
        number = self.db.scalar(DOCUMENT_NUMBER_SEQUENCE.next_value())
        return f"{prefix}-{day:%y%m%d}-{number:04d}"

    def get_or_404(self, item_id: int, for_update: bool = False) -> M:
        query = select(self.model).where(self.model.id == item_id)
        if for_update:
            query = query.with_for_update(of=self.model).execution_options(populate_existing=True)
        obj = self.db.scalar(query)
        # BR-14: dokumen lokasi lain dijawab 404 supaya keberadaannya tidak bocor
        if obj is None or not self.can_access(obj):
            raise NotFound(f"{self.label} tidak ditemukan")
        return obj

    def can_access(self, obj: M) -> bool:
        return self.policy.can_manage(obj.lokasi_id)

    def restrict(self, query: Select, *columns: ColumnElement[int]) -> Select:
        target = columns or (self.model.lokasi_id,)
        return self.policy.restrict(query, *target)

    def ensure_status(self, obj: M, *allowed: str) -> None:
        # BR-03: dokumen final tidak bisa diubah, dihapus atau diproses ulang
        if obj.status in allowed:
            return
        if obj.status == "draf":
            raise InvalidStatus(f"{self.label} masih berstatus draf")
        raise InvalidStatus(f"{self.label} sudah {obj.status}")

    def resolve_lokasi(self, lokasi_id: int | None, field: str = "lokasi_id") -> Lokasi:
        if self.policy.is_admin:
            if lokasi_id is None:
                raise ValidationFailed(errors={field: "Wajib diisi untuk admin"})
            target_id = lokasi_id
        else:
            if lokasi_id is not None and not self.policy.can_manage(lokasi_id):
                raise NotFound(f"{self.label} tidak ditemukan")
            target_id = self.user.lokasi_id
        lokasi = self.db.get(Lokasi, target_id) if target_id else None
        if lokasi is None:
            raise ValidationFailed(errors={field: "Lokasi tidak ditemukan"})
        if not lokasi.aktif:
            raise ValidationFailed(errors={field: "Lokasi sudah tidak aktif"})
        return lokasi

    def check_products(self, items: Sequence[Any]) -> tuple[dict[int, Produk], dict[str, str]]:
        ids = {item.produk_id for item in items}
        rows = self.db.scalars(
            select(Produk).options(joinedload(Produk.kategori)).where(Produk.id.in_(ids))
        ).all()
        products = {produk.id: produk for produk in rows}
        errors: dict[str, str] = {}
        for index, item in enumerate(items):
            produk = products.get(item.produk_id)
            if produk is None:
                errors[f"items.{index}.produk_id"] = "Produk tidak ditemukan"
            elif not produk.aktif:
                errors[f"items.{index}.produk_id"] = "Produk sudah tidak aktif"
        return products, errors

    def load_products(self, items: Sequence[Any]) -> dict[int, Produk]:
        products, errors = self.check_products(items)
        if errors:
            raise ValidationFailed(errors=errors)
        return products

    def replace_details(self, obj: Any, details: list[Any]) -> None:
        # hapus baris lama lebih dulu supaya UNIQUE (dokumen_id, produk_id) tidak bentrok saat flush
        obj.detail.clear()
        self.db.flush()
        obj.detail.extend(details)

    def paginate(self, query: Select, params: PageParams, convert: Callable) -> Page:
        total = self.db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        rows = self.db.scalars(query.limit(params.per_page).offset(params.offset)).all()
        return Page.of([convert(row) for row in rows], total, params)
