from sqlalchemy import Select, false, or_

from app.core.errors import Forbidden
from app.models import LokasiType, Pengiriman, User, UserRole

class PengirimanPolicy:
    # hak akses per objek pengiriman: gudang asal mengirim, lokasi tujuan menerima,
    # deliveryman hanya membaca pengiriman yang ditugaskan kepadanya (BR-14, BR-15)
    WAREHOUSE_TYPES = (LokasiType.GUDANG_UTAMA, LokasiType.GUDANG_CABANG)

    def __init__(self, user: User):
        self.user = user

    @property
    def is_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN

    @property
    def is_deliveryman(self) -> bool:
        return self.user.role == UserRole.DELIVERYMAN

    def can_read(self, pengiriman: Pengiriman) -> bool:
        if self.is_admin:
            return True
        if self.is_deliveryman:
            return pengiriman.deliveryman_id == self.user.id
        return self.user.lokasi_id in (pengiriman.lokasi_asal_id, pengiriman.lokasi_tujuan_id)

    def restrict(self, query: Select) -> Select:
        if self.is_admin:
            return query
        if self.is_deliveryman:
            return query.where(Pengiriman.deliveryman_id == self.user.id)
        if self.user.lokasi_id is None:
            return query.where(false())
        return query.where(
            or_(
                Pengiriman.lokasi_asal_id == self.user.lokasi_id,
                Pengiriman.lokasi_tujuan_id == self.user.lokasi_id,
            )
        )

    def ensure_can_create(self) -> None:
        if self.user.role not in (UserRole.ADMIN, UserRole.MANAGER_GUDANG):
            raise Forbidden("Pengiriman hanya bisa dibuat oleh manager gudang atau admin")

    def ensure_can_send(self, pengiriman: Pengiriman) -> None:
        if self.is_admin:
            return
        if (
            self.user.role == UserRole.MANAGER_GUDANG
            and self.user.lokasi_id == pengiriman.lokasi_asal_id
        ):
            return
        raise Forbidden("Hanya manager gudang asal yang bisa memproses pengiriman ini")

    def ensure_can_receive(self, pengiriman: Pengiriman) -> None:
        if self.is_admin:
            return
        if (
            self.user.role in (UserRole.MANAGER_GUDANG, UserRole.MANAGER_OUTLET)
            and self.user.lokasi_id == pengiriman.lokasi_tujuan_id
        ):
            return
        raise Forbidden("Hanya manager lokasi tujuan yang bisa menerima pengiriman ini")
