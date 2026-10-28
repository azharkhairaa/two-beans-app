from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter, Depends

from app.controllers.auth_controller import AuthController
from app.controllers.lokasi_controller import LokasiController
from app.controllers.master_controller import (
    CustomerController,
    KategoriController,
    SupplierController,
)
from app.controllers.system_controller import SystemController
from app.core.config import settings
from app.core.limiter import rate_limiter
from app.policies.access import current_user, require_admin, require_manager

class Access(Enum):
    # value berisi dependency yang dijalankan sebelum action controller
    PUBLIC = ()
    LOGIN = (Depends(current_user),)
    # admin, manager_gudang dan manager_outlet
    MANAGER = (Depends(require_manager),)
    ADMIN = (Depends(require_admin),)

@dataclass(frozen=True)
class Route:
    method: str
    path: str
    action: Callable
    access: Access
    summary: str
    status: int = 200
    tag: str = ""
    # contoh "5/minute", action-nya wajib punya parameter request: Request
    rate_limit: str | None = None

def resource(
    prefix: str, controller, noun: str, read: Access, write: Access, remove: Access,
    options: bool = False,
) -> list[Route]:
    # padanan Route::apiResource di Laravel, route statis /opsi didaftarkan sebelum /{id}
    routes = [Route("GET", prefix, controller.index, read, f"Daftar {noun}", tag=noun)]
    if options:
        routes.append(Route("GET", f"{prefix}/opsi", controller.options, read,
                            f"Pilihan {noun} aktif untuk formulir", tag=noun))
    return routes + [
        Route("POST", prefix, controller.store, write, f"Tambah {noun}", status=201, tag=noun),
        Route("GET", f"{prefix}/{{id}}", controller.show, read, f"Detail {noun}", tag=noun),
        Route("PUT", f"{prefix}/{{id}}", controller.update, write, f"Ubah {noun}", tag=noun),
        Route("DELETE", f"{prefix}/{{id}}", controller.destroy, remove,
              f"Hapus {noun} yang belum dipakai", status=204, tag=noun),
    ]

system = SystemController()
auth = AuthController()

# list endpoint API
ROUTES = [
    Route("GET", "/health", system.health, Access.PUBLIC, "Status aplikasi dan koneksi database",
          tag="system"),
    Route("POST", "/auth/register", auth.register, Access.PUBLIC,
          "Registrasi akun baru yang menunggu persetujuan admin", status=201, tag="auth",
          rate_limit="3/minute"),
    Route("POST", "/auth/login", auth.login, Access.PUBLIC,
          "Login, memasang cookie sesi dan token CSRF", tag="auth",
          rate_limit=settings.login_rate_limit),
    Route("POST", "/auth/logout", auth.logout, Access.LOGIN, "Logout dan menghapus sesi",
          status=204, tag="auth"),
    Route("GET", "/auth/me", auth.me, Access.LOGIN,
          "Profil, peran, lokasi dan token CSRF dari sesi", tag="auth"),
    *resource("/lokasi", LokasiController(), "lokasi",
              read=Access.MANAGER, write=Access.ADMIN, remove=Access.ADMIN),
    *resource("/kategori", KategoriController(), "kategori",
              read=Access.MANAGER, write=Access.ADMIN, remove=Access.ADMIN),
    *resource("/supplier", SupplierController(), "supplier",
              read=Access.MANAGER, write=Access.ADMIN, remove=Access.ADMIN, options=True),
    # manager boleh menambah dan mengubah customer, menghapus hanya admin
    *resource("/customer", CustomerController(), "customer",
              read=Access.MANAGER, write=Access.MANAGER, remove=Access.ADMIN, options=True),
]

def build_router(routes: Sequence[Route] = ROUTES) -> APIRouter:
    router = APIRouter(prefix="/api")
    for route in routes:
        action = route.action
        if route.rate_limit:
            action = rate_limiter.apply(route.rate_limit, action)
        router.add_api_route(
            route.path,
            action,
            methods=[route.method],
            status_code=route.status,
            summary=route.summary,
            dependencies=list(route.access.value),
            tags=[route.tag],
        )
    return router
