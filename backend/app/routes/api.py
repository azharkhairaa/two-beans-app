from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from fastapi import APIRouter

from app.controllers.system_controller import SystemController

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

system = SystemController()

# list endpoint API
ROUTES = [
    Route("GET", "/health", system.health, Access.PUBLIC, "Status aplikasi dan koneksi database",
          tag="system"),
]

def build_router() -> APIRouter:
    router = APIRouter(prefix="/api")
    for route in ROUTES:
        router.add_api_route(
            route.path,
            route.action,
            methods=[route.method],
            status_code=route.status,
            summary=route.summary,
            dependencies=list(route.access.value),
            tags=[route.tag],
        )
    return router
