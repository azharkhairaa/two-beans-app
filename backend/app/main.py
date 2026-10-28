from collections.abc import Sequence

from fastapi import FastAPI

from app.core.config import settings
from app.core.csrf import OriginGuard
from app.core.error_handler import ErrorHandler
from app.core.headers import SecurityHeadersMiddleware
from app.core.integrity_errors import IntegrityErrorMapper
from app.core.limiter import rate_limiter
from app.models import Base
from app.routes.api import ROUTES, Route, build_router

OPENAPI_TAGS = [
    {"name": "system", "description": "Status aplikasi dan koneksi database"},
    {"name": "auth", "description": "Registrasi, login, logout dan sesi"},
    {"name": "lokasi", "description": "Gudang utama, gudang cabang dan outlet beserta ringkasan"},
    {"name": "kategori", "description": "Kategori produk beserta jumlah produknya"},
    {"name": "supplier", "description": "Pemasok green bean, peralatan dan bahan habis pakai"},
    {"name": "customer", "description": "Pembeli di semua jenis lokasi"},
    {"name": "produk", "description": "Produk beserta aturan jenis kategori dan stok per lokasi"},
    {"name": "stok", "description": "Stok per lokasi, stok minimum dan rak"},
    {"name": "users", "description": "Persetujuan akun, peran, lokasi dan status user"},
]

def create_app(routes: Sequence[Route] = ROUTES) -> FastAPI:
    app = FastAPI(
        title="Two Beans App API",
        description=(
            "Backend inventaris Two Beans Coffee untuk gudang utama (roastery), "
            "gudang cabang dan outlet."
        ),
        version="0.1.0",
        openapi_tags=OPENAPI_TAGS,
        redoc_url=None,
    )
    app.state.limiter = rate_limiter
    ErrorHandler(IntegrityErrorMapper(Base.metadata)).register(app)
    # middleware terakhir menjadi lapis terluar, response 403 OriginGuard ikut diberi header
    app.add_middleware(OriginGuard, allowed_origins=settings.allowed_origins)
    app.add_middleware(SecurityHeadersMiddleware)
    app.include_router(build_router(routes))
    return app

app = create_app()
