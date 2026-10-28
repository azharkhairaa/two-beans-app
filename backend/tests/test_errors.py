from datetime import date
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import (
    Conflict,
    DataInUse,
    InsufficientStock,
    InvalidStatus,
    TooManyRequests,
    ValidationFailed,
)
from app.core.integrity_errors import IntegrityErrorMapper
from app.core.sanitize import MultiLineText, SingleLineText
from app.core.validation_messages import ValidationMessages
from app.main import create_app
from app.models import (
    Base,
    Lokasi,
    LokasiType,
    Penjualan,
    PenjualanDetail,
    Produk,
    ProdukUnit,
    Stok,
)
from app.routes.api import Access, Route

class SampleItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    produk_id: Annotated[int, Field(gt=0, strict=True)]
    jumlah: Annotated[int, Field(ge=1, le=1000, strict=True)]

class SampleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nama: Annotated[SingleLineText, Field(min_length=3, max_length=60)]
    catatan: Annotated[MultiLineText, Field(max_length=500)] | None = None
    aktif: bool = True
    tanggal: date | None = None
    items: Annotated[list[SampleItem], Field(min_length=1, max_length=2)]

class SampleController:
    # endpoint contoh untuk menguji handler error sebelum ada controller domain

    def create(self, body: SampleBody) -> SampleBody:
        return body

    def conflict(self) -> None:
        raise InvalidStatus("Pengiriman sudah dikirim")

    def crash(self) -> None:
        raise RuntimeError("rahasia internal password=abc")

    def add_outlet(self, nama: str, db: Session = Depends(get_db)) -> dict:
        db.add(Lokasi(kode="OT-01", nama=nama, jenis=LokasiType.OUTLET))
        db.commit()
        return {"status": "ok"}

sample = SampleController()
SAMPLE_ROUTES = [
    Route("POST", "/sample", sample.create, Access.PUBLIC, "Contoh body"),
    Route("POST", "/sample/conflict", sample.conflict, Access.PUBLIC, "Contoh 409"),
    Route("GET", "/sample/crash", sample.crash, Access.PUBLIC, "Contoh 500"),
    Route("POST", "/sample/outlet", sample.add_outlet, Access.PUBLIC, "Contoh unique"),
]
VALID_ITEM = {"produk_id": 1, "jumlah": 2}

@pytest.fixture
def sample_client():
    app = create_app(SAMPLE_ROUTES)
    with TestClient(app, headers={"Origin": "http://testserver"}, raise_server_exceptions=False) as client:
        yield client

@pytest.fixture
def mapper():
    return IntegrityErrorMapper(Base.metadata)

def raise_integrity(db) -> IntegrityError:
    with pytest.raises(IntegrityError) as error:
        db.flush()
    db.rollback()
    return error.value

def test_missing_fields_translated(sample_client):
    response = sample_client.post("/api/sample", json={})
    assert response.status_code == 422
    assert response.json() == {"detail": "Data belum valid", "errors": {"nama": "Wajib diisi", "items": "Wajib diisi"}}

def test_tag_type_and_unknown_field_messages(sample_client):
    body = {"nama": "<script>alert(1)</script>", "items": [{"produk_id": "5", "jumlah": 0}], "status": "diposting"}
    assert sample_client.post("/api/sample", json=body).json()["errors"] == {
        "nama": "Tidak boleh memuat tag HTML",
        "items.0.produk_id": "Harus bilangan bulat",
        "items.0.jumlah": "Minimal 1",
        "status": "Field tidak dikenal",
    }

def test_length_date_and_boolean_messages(sample_client):
    body = {"nama": "  ab  ", "items": [], "tanggal": "28-10-2026", "aktif": "ya"}
    assert sample_client.post("/api/sample", json=body).json()["errors"] == {
        "nama": "Minimal 3 karakter",
        "items": "Minimal 1 baris",
        "tanggal": "Format tanggal harus YYYY-MM-DD",
        "aktif": "Harus true atau false",
    }

def test_maximum_length_messages(sample_client):
    body = {"nama": "x" * 61, "items": [VALID_ITEM] * 3}
    assert sample_client.post("/api/sample", json=body).json()["errors"] == {
        "nama": "Maksimal 60 karakter",
        "items": "Maksimal 2 baris",
    }

def test_invalid_json_body(sample_client):
    response = sample_client.post("/api/sample", content="{nama:", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["errors"] == {"body": "Body bukan JSON yang valid"}

def test_valid_body_is_cleaned(sample_client):
    body = {"nama": "  Kopi   Gayo\t200 g​ ", "catatan": "baris 1  \r\n\r\n\r\n\r\nbaris 2", "items": [VALID_ITEM]}
    response = sample_client.post("/api/sample", json=body)
    assert response.status_code == 200
    assert (response.json()["nama"], response.json()["catatan"]) == ("Kopi Gayo 200 g", "baris 1\n\nbaris 2")

def test_app_error_returns_its_status_and_message(sample_client):
    response = sample_client.post("/api/sample/conflict")
    assert response.status_code == 409
    assert response.json() == {"detail": "Pengiriman sudah dikirim"}

def test_unexpected_error_hides_detail(sample_client):
    response = sample_client.get("/api/sample/crash")
    assert response.status_code == 500
    assert response.json() == {"detail": "Terjadi error di server"}
    assert "rahasia" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"

def test_unknown_endpoint_and_method_in_indonesian(client):
    assert client.get("/api/tidak-ada").json() == {"detail": "Endpoint tidak ditemukan"}
    response = client.post("/api/health")
    assert response.status_code == 405
    assert response.json() == {"detail": "Method tidak diizinkan untuk endpoint ini"}
    assert response.headers["allow"] == "GET"

def test_duplicate_code_becomes_409_with_field(sample_client, db):
    assert sample_client.post("/api/sample/outlet", params={"nama": "Outlet Kampus"}).status_code == 200
    response = sample_client.post("/api/sample/outlet", params={"nama": "Outlet Dago"})
    assert response.status_code == 409
    assert response.json() == {"detail": "Kode lokasi sudah dipakai", "errors": {"kode": "Kode lokasi sudah dipakai"}}

def test_delete_parent_still_used_becomes_data_in_use(db, factory, mapper):
    produk = factory.produk()
    db.commit()
    db.delete(produk.kategori)
    error = mapper.to_app_error(raise_integrity(db))
    assert isinstance(error, DataInUse)
    assert error.message == "Data tidak bisa dihapus karena masih dipakai di produk"

def test_missing_reference_becomes_422(db, mapper):
    db.add(Produk(sku="BK-ARB-GAYO-200", nama="Arabika Gayo 200 g", kategori_id=999, satuan=ProdukUnit.PACK,
                  berat_gram=200))
    error = mapper.to_app_error(raise_integrity(db))
    assert isinstance(error, ValidationFailed)
    assert error.errors == {"kategori_id": "Data tidak ditemukan"}

def test_negative_stock_becomes_insufficient_stock(db, factory, mapper):
    outlet = factory.outlet()
    produk = factory.produk()
    db.add(Stok(lokasi_id=outlet.id, produk_id=produk.id, jumlah=-1))
    error = mapper.to_app_error(raise_integrity(db))
    assert isinstance(error, InsufficientStock) and error.status_code == 409

def test_same_product_twice_in_document_becomes_409(db, factory, mapper):
    outlet = factory.outlet()
    manager = factory.manager(outlet)
    produk = factory.produk()
    db.add(Penjualan(kode="PJ-261028-0001", tanggal=date(2026, 10, 28), lokasi=outlet, dibuat_oleh=manager,
                     detail=[PenjualanDetail(produk=produk, jumlah=1, harga_satuan=95000),
                             PenjualanDetail(produk=produk, jumlah=2, harga_satuan=95000)]))
    error = mapper.to_app_error(raise_integrity(db))
    assert isinstance(error, Conflict)
    assert error.errors == {"items": "Produk tidak boleh ganda dalam satu dokumen"}

def test_retry_after_duration_text():
    assert TooManyRequests.retry_after(60).message == "Terlalu banyak percobaan. Coba lagi dalam 1 menit"
    assert TooManyRequests.retry_after(3600).message.endswith("1 jam")
    error = TooManyRequests.retry_after(90)
    assert error.message.endswith("90 detik") and error.headers == {"Retry-After": "90"}

def test_validation_message_fallbacks():
    messages = ValidationMessages()
    assert messages.message({"type": "value_error", "ctx": {"reason": "no @"}}) == "Format email tidak valid"
    assert messages.message({"type": "url_parsing"}) == "Nilai tidak valid"
