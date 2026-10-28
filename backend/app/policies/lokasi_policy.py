from sqlalchemy import ColumnElement, Select, false, or_

from app.models import User, UserRole

class LokasiPolicy:
    # admin bisa semua lokasi, manager dan deliveryman dibatasi lokasinya sendiri
    def __init__(self, user: User):
        self.user = user

    @property
    def is_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN

    def can_manage(self, lokasi_id: int) -> bool:
        if self.is_admin:
            return True
        return self.user.lokasi_id is not None and self.user.lokasi_id == lokasi_id

    def restrict(self, query: Select, *columns: ColumnElement[int]) -> Select:
        # daftar dokumen disaring ke yang melibatkan lokasi user, misalnya lokasi asal atau tujuan
        if self.is_admin:
            return query
        if self.user.lokasi_id is None:
            return query.where(false())
        return query.where(or_(*(column == self.user.lokasi_id for column in columns)))
