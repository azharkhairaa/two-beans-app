from sqlalchemy import ColumnElement, Select, false, or_

from app.models import LokasiType, User, UserRole

class LokasiPolicy:
    # admin bisa semua lokasi, manager dan deliveryman dibatasi lokasinya sendiri
    def __init__(self, user: User):
        self.user = user

    @property
    def is_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN

    @property
    def sees_all_values(self) -> bool:
        # admin dan manager gudang utama memantau nilai semua lokasi, manager lain hanya jumlahnya
        if self.is_admin:
            return True
        lokasi = self.user.lokasi
        return lokasi is not None and lokasi.jenis == LokasiType.GUDANG_UTAMA

    def can_see_detail(self, lokasi_id: int) -> bool:
        # rincian stock (nilai, rak, kartu stock) lokasi lain hanya untuk yang memantau semua lokasi
        return self.sees_all_values or self.can_manage(lokasi_id)

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
