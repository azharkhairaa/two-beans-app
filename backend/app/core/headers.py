from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

class SecurityHeadersMiddleware:
    # header keamanan response backend, header halaman statis diatur vercel.json
    COMMON = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }
    # CSP sama dengan halaman di vercel.json, no-store supaya data API tidak tersimpan di cache
    API = {
        "Content-Security-Policy": (
            "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'; form-action 'self'"
        ),
        "Cache-Control": "no-store",
    }

    def __init__(self, app: ASGIApp):
        self.app = app

    @classmethod
    def headers_for(cls, path: str) -> dict[str, str]:
        # /docs load Swagger UI dari CDN, CSP hanya dipasang di /api
        if path.startswith("/api/"):
            return cls.COMMON | cls.API
        return dict(cls.COMMON)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        extra = self.headers_for(scope["path"])

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in extra.items():
                    headers.setdefault(name, value)
            await send(message)

        await self.app(scope, receive, send_with_headers)
