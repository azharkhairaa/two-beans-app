from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter

from app.controllers.system_controller import SystemController
from app.core.limiter import rate_limiter

class Access(Enum):
    # value berisi dependency yang dijalankan sebelum action controller
    PUBLIC = ()

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

system = SystemController()

# list endpoint API
ROUTES = [
    Route("GET", "/health", system.health, Access.PUBLIC, "Status aplikasi dan koneksi database",
          tag="system"),
]

def build_router(routes: Sequence[Route] = ROUTES) -> APIRouter:
    router = APIRouter(prefix="/api")
    for route in routes:
        action = route.action
        if route.rate_limit:
            action = rate_limiter.limit(route.rate_limit)(action)
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
