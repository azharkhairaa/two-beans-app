from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings

class RateLimiter(Limiter):
    # slowapi dengan IP klien yang benar di belakang proxy Vercel

    def __init__(self, serverless: bool):
        self.serverless = serverless
        super().__init__(key_func=self.client_address)

    def client_address(self, request: Request) -> str:
        # di Vercel request.client milik proxy, IP asli ada di x-real-ip ditulis Vercel
        if self.serverless:
            return request.headers.get("x-real-ip") or get_remote_address(request)
        return get_remote_address(request)

# hitungan disimpan di memori tiap instance function, kunci akun di database jadi lapis utama login
rate_limiter = RateLimiter(settings.serverless)
