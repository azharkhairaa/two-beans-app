from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, MetaData, Sequence, column, func, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# nama constraint konsisten supaya IntegrityError bisa di-mapping ke pesan yang jelas
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "ix": "ix_%(column_0_label)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

# satu sequence untuk nomor urut semua kode dokumen (BM, BK, PS, PM, KR, PO, PJ)
DOCUMENT_NUMBER_SEQUENCE = Sequence("dokumen_nomor_seq", start=1, metadata=Base.metadata)

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

def check_values(
    column_name: str, values: type[StrEnum], nullable: bool = False
) -> CheckConstraint:
    # CHECK kolom IN (...) di-build dari enum
    target = column(column_name)
    rule = target.in_([item.value for item in values])
    if nullable:
        rule = or_(target.is_(None), rule)
    return CheckConstraint(rule, name=column_name)
