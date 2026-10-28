import logging
from collections.abc import Iterable
from urllib.parse import urlsplit

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.errors import Forbidden

log = logging.getLogger("uvicorn.error")

class OriginGuard:
    # CSRF lapis 2: request pengubah data ke /api wajib berasal dari origin yang diizinkan
    UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    def __init__(self, app: ASGIApp, allowed_origins: Iterable[str]):
        self.app = app
        self.allowed_origins = frozenset(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self.must_check(scope):
            origin = self.request_origin(Headers(scope=scope))
            if origin not in self.allowed_origins:
                log.warning("origin ditolak: %s %s dari %s",
                            scope["method"], scope["path"], origin or "-")
                await Forbidden("Origin tidak diizinkan").response()(scope, receive, send)
                return
        await self.app(scope, receive, send)

    def must_check(self, scope: Scope) -> bool:
        return scope["method"] in self.UNSAFE_METHODS and scope["path"].startswith("/api/")

    @staticmethod
    def request_origin(headers: Headers) -> str:
        # Referer dipakai kalau browser lama tidak mengirim Origin, "null" tetap ditolak
        if origin := headers.get("origin"):
            return origin
        parts = urlsplit(headers.get("referer", ""))
        return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""
