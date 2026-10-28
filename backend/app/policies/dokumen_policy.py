from sqlalchemy import Select, false, or_

from app.core.errors import Forbidden
from app.models import Lokasi, LokasiType, Pengiriman, Permintaan, User, UserRole

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


class PermintaanPolicy:
    # hak akses per objek permintaan: gudang cabang dan outlet mengajukan,
    # gudang utama menyetujui atau menolak (BR-08, BR-09, BR-14)
    REQUESTER_TYPES = (LokasiType.GUDANG_CABANG, LokasiType.OUTLET)

    def __init__(self, user: User):
        self.user = user

    @property
    def is_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN

    def can_read(self, permintaan: Permintaan) -> bool:
        if self.is_admin:
            return True
        return self.user.lokasi_id in (
            permintaan.lokasi_peminta_id,
            permintaan.lokasi_sumber_id,
        )

    def restrict(self, query: Select) -> Select:
        if self.is_admin:
            return query
        if self.user.lokasi_id is None:
            return query.where(false())
        return query.where(
            or_(
                Permintaan.lokasi_peminta_id == self.user.lokasi_id,
                Permintaan.lokasi_sumber_id == self.user.lokasi_id,
            )
        )

    def ensure_can_create(self, lokasi_peminta: Lokasi) -> None:
        if not self.is_admin and lokasi_peminta.jenis not in self.REQUESTER_TYPES:
            raise Forbidden("Permintaan hanya bisa diajukan dari gudang cabang atau outlet")

    def ensure_can_edit_or_cancel(self, permintaan: Permintaan) -> None:
        if self.is_admin or self.user.lokasi_id == permintaan.lokasi_peminta_id:
            return
        raise Forbidden(
            "Hanya manager lokasi peminta yang bisa mengubah atau membatalkan permintaan ini"
        )

    def ensure_can_process(self, permintaan: Permintaan) -> None:
        if self.is_admin:
            return
        if (
            self.user.role == UserRole.MANAGER_GUDANG
            and self.user.lokasi_id == permintaan.lokasi_sumber_id
        ):
            return
        raise Forbidden("Hanya manager gudang utama yang bisa memproses permintaan ini")


class PembelianPolicy:
    # hak akses pembelian ke supplier: hanya manager gudang utama dan admin (BR-11)

    def __init__(self, user: User):
        self.user = user

    @property
    def is_admin(self) -> bool:
        return self.user.role == UserRole.ADMIN

    @property
    def is_gudang_utama_manager(self) -> bool:
        return (
            self.user.role == UserRole.MANAGER_GUDANG
            and self.user.lokasi is not None
            and self.user.lokasi.jenis == LokasiType.GUDANG_UTAMA
        )

    def can_manage(self) -> bool:
        return self.is_admin or self.is_gudang_utama_manager

    def ensure_can_manage(self) -> None:
        if not self.can_manage():
            raise Forbidden(
                "Pembelian ke supplier hanya bisa dikelola oleh manager gudang utama atau admin"
            )
