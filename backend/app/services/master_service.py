from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

from sqlalchemy import Select, func, or_, select

from app.core.clock import Clock
from app.core.errors import Conflict
from app.models import (
    Customer,
    Kategori,
    Penjualan,
    PenjualanDetail,
    PenjualanStatus,
    Produk,
    Supplier,
)
from app.policies.lokasi_policy import LokasiPolicy
from app.schemas.common import ActiveFilter, Page, PageParams, SortDirection
from app.schemas.master import (
    CustomerDetail,
    CustomerResponse,
    KategoriInput,
    KategoriResponse,
    SupplierResponse,
)
from app.services.base import CrudService, SqlMoney

class MasterSort(StrEnum):
    NAMA = "nama"
    UPDATED_AT = "updated_at"

@dataclass(frozen=True)
class PartnerFilter:
    # pencarian di nama, kontak dan email serta filter aktif, jenis dan urutan
    q: str | None = None
    aktif: ActiveFilter = ActiveFilter.ALL
    sort: MasterSort = MasterSort.NAMA
    arah: SortDirection = SortDirection.ASC
    jenis: str | None = None

class KategoriService(CrudService[Kategori]):
    model = Kategori
    label = "Kategori"

    def summary_query(self) -> Select:
        return (
            select(Kategori, func.count(Produk.id).label("jumlah_produk"))
            .outerjoin(Produk, Produk.kategori_id == Kategori.id)
            .group_by(Kategori.id)
        )

    def summaries(self) -> list[KategoriResponse]:
        rows = self.db.execute(self.summary_query().order_by(Kategori.nama))
        return [KategoriResponse.of(*row) for row in rows]

    def detail(self, item_id: int) -> KategoriResponse:
        self.get_or_404(item_id)
        row = self.db.execute(self.summary_query().where(Kategori.id == item_id)).one()
        return KategoriResponse.of(*row)

    def update(self, kategori: Kategori, data: KategoriInput) -> Kategori:
        # BR-23: aturan produk mengikuti jenis kategori, jadi jenis dikunci setelah ada produk
        if data.jenis != kategori.jenis and self.usage(kategori):
            message = "Jenis kategori tidak bisa diubah karena sudah berisi produk"
            raise Conflict(message, {"jenis": message})
        return super().update(kategori, data)

class PartnerService[M: (Supplier, Customer)](CrudService[M]):
    # bagian bersama supplier dan customer
    response: type[SupplierResponse]

    def search(self, filters: PartnerFilter, params: PageParams) -> Page:
        query = self.active_filter(select(self.model), self.model.aktif, filters.aktif)
        if filters.q:
            columns = (self.model.nama, self.model.kontak, self.model.email)
            query = query.where(or_(*(self.contains(column, filters.q) for column in columns)))
        if filters.jenis:
            query = query.where(self.model.jenis == filters.jenis)
        column = getattr(self.model, filters.sort.value)
        order = column.desc() if filters.arah == SortDirection.DESC else column.asc()
        return self.paginate(query.order_by(order, self.model.id), params, self.response)

    def options(self) -> list[M]:
        query = select(self.model).where(self.model.aktif).order_by(self.model.nama)
        return list(self.db.scalars(query))

class SupplierService(PartnerService[Supplier]):
    model = Supplier
    label = "Supplier"
    response = SupplierResponse

class CustomerService(PartnerService[Customer]):
    model = Customer
    label = "Customer"
    response = CustomerResponse

    def detail(self, item_id: int, policy: LokasiPolicy) -> CustomerDetail:
        customer = self.get_or_404(item_id)
        # 30 hari termasuk hari ini, hanya penjualan yang sudah diposting (BR-28)
        since = Clock.today() - timedelta(days=29)
        omzet = SqlMoney.total(PenjualanDetail.jumlah, PenjualanDetail.harga_satuan)
        query = (
            select(omzet)
            .join(Penjualan, Penjualan.id == PenjualanDetail.penjualan_id)
            .where(
                Penjualan.customer_id == customer.id,
                Penjualan.status == PenjualanStatus.DIPOSTING,
                Penjualan.tanggal >= since,
            )
        )
        # manager hanya melihat omzet lokasinya sendiri, sama dengan dashboard
        total = self.db.scalar(policy.restrict(query, Penjualan.lokasi_id))
        data = CustomerResponse.model_validate(customer).model_dump()
        return CustomerDetail.model_validate({**data, "total_pembelian_30_hari": total})
