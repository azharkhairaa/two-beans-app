from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import CustomerType, User
from app.policies.access import current_user
from app.policies.lokasi_policy import LokasiPolicy
from app.schemas.common import ActiveFilter, OptionResponse, Page, PageParams, SortDirection
from app.schemas.master import (
    CustomerDetail,
    CustomerInput,
    CustomerOption,
    CustomerResponse,
    KategoriInput,
    KategoriResponse,
    SupplierInput,
    SupplierResponse,
)
from app.services.master_service import (
    CustomerService,
    KategoriService,
    MasterSort,
    PartnerFilter,
    SupplierService,
)

Search = Query(None, max_length=100, description="Cari di nama, kontak atau email")

class KategoriController:
    def index(self, db: Session = Depends(get_db)) -> list[KategoriResponse]:
        return KategoriService(db).summaries()

    def show(self, id: int, db: Session = Depends(get_db)) -> KategoriResponse:
        return KategoriService(db).detail(id)

    def store(self, body: KategoriInput, db: Session = Depends(get_db)) -> KategoriResponse:
        service = KategoriService(db)
        return service.detail(service.create(body).id)

    def update(
        self, id: int, body: KategoriInput, db: Session = Depends(get_db)
    ) -> KategoriResponse:
        service = KategoriService(db)
        service.update(service.get_or_404(id), body)
        return service.detail(id)

    def destroy(self, id: int, db: Session = Depends(get_db)) -> None:
        service = KategoriService(db)
        service.delete(service.get_or_404(id))

class SupplierController:
    def index(
        self,
        q: str | None = Search,
        aktif: ActiveFilter = ActiveFilter.ALL,
        sort: MasterSort = MasterSort.NAMA,
        arah: SortDirection = SortDirection.ASC,
        params: PageParams = Depends(),
        db: Session = Depends(get_db),
    ) -> Page[SupplierResponse]:
        return SupplierService(db).search(PartnerFilter(q, aktif, sort, arah), params)

    def options(self, db: Session = Depends(get_db)) -> list[OptionResponse]:
        return [OptionResponse(id=s.id, nama=s.nama) for s in SupplierService(db).options()]

    def show(self, id: int, db: Session = Depends(get_db)) -> SupplierResponse:
        return SupplierResponse.model_validate(SupplierService(db).get_or_404(id))

    def store(self, body: SupplierInput, db: Session = Depends(get_db)) -> SupplierResponse:
        return SupplierResponse.model_validate(SupplierService(db).create(body))

    def update(
        self, id: int, body: SupplierInput, db: Session = Depends(get_db)
    ) -> SupplierResponse:
        service = SupplierService(db)
        return SupplierResponse.model_validate(service.update(service.get_or_404(id), body))

    def destroy(self, id: int, db: Session = Depends(get_db)) -> None:
        service = SupplierService(db)
        service.delete(service.get_or_404(id))

class CustomerController:
    def index(
        self,
        q: str | None = Search,
        jenis: CustomerType | None = None,
        aktif: ActiveFilter = ActiveFilter.ALL,
        sort: MasterSort = MasterSort.NAMA,
        arah: SortDirection = SortDirection.ASC,
        params: PageParams = Depends(),
        db: Session = Depends(get_db),
    ) -> Page[CustomerResponse]:
        return CustomerService(db).search(PartnerFilter(q, aktif, sort, arah, jenis), params)

    def options(self, db: Session = Depends(get_db)) -> list[CustomerOption]:
        return [CustomerOption.model_validate(c) for c in CustomerService(db).options()]

    def show(
        self, id: int, user: User = Depends(current_user), db: Session = Depends(get_db)
    ) -> CustomerDetail:
        return CustomerService(db).detail(id, LokasiPolicy(user))

    def store(self, body: CustomerInput, db: Session = Depends(get_db)) -> CustomerResponse:
        return CustomerResponse.model_validate(CustomerService(db).create(body))

    def update(
        self, id: int, body: CustomerInput, db: Session = Depends(get_db)
    ) -> CustomerResponse:
        service = CustomerService(db)
        return CustomerResponse.model_validate(service.update(service.get_or_404(id), body))

    def destroy(self, id: int, db: Session = Depends(get_db)) -> None:
        service = CustomerService(db)
        service.delete(service.get_or_404(id))
