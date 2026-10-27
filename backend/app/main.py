from fastapi import FastAPI

from app.routes.api import build_router

OPENAPI_TAGS = [
    {"name": "system", "description": "Status aplikasi dan koneksi database"},
]

def create_app() -> FastAPI:
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
    app.include_router(build_router())
    return app

app = create_app()
