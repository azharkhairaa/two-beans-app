import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException

from app.core.errors import AppError, ServerError, TooManyRequests, ValidationFailed
from app.core.headers import SecurityHeadersMiddleware
from app.core.integrity_errors import IntegrityErrorMapper
from app.core.validation_messages import ValidationMessages

log = logging.getLogger("uvicorn.error")

class ErrorHandler:
    # semua error dijawab dengan bentuk {"detail": ..., "errors": {...}}
    HTTP_MESSAGES = {
        404: "Endpoint tidak ditemukan",
        405: "Method tidak diizinkan untuk endpoint ini",
    }

    def __init__(self, integrity: IntegrityErrorMapper, messages: ValidationMessages | None = None):
        self.integrity = integrity
        self.messages = messages or ValidationMessages()

    def register(self, app: FastAPI) -> None:
        app.add_exception_handler(AppError, self.app_error)
        app.add_exception_handler(RequestValidationError, self.validation_error)
        app.add_exception_handler(IntegrityError, self.integrity_error)
        app.add_exception_handler(HTTPException, self.http_error)
        app.add_exception_handler(RateLimitExceeded, self.rate_limited)
        app.add_exception_handler(Exception, self.server_error)

    def app_error(self, request: Request, exc: AppError) -> JSONResponse:
        return exc.response()

    def validation_error(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        return ValidationFailed(errors=self.messages.translate(exc.errors())).response()

    def integrity_error(self, request: Request, exc: IntegrityError) -> JSONResponse:
        error = self.integrity.to_app_error(exc)
        if error is None:
            return self.server_error(request, exc)
        return error.response()

    def http_error(self, request: Request, exc: HTTPException) -> JSONResponse:
        # 404 dan 405 bawaan Starlette diganti pesan Indonesia, header seperti Allow tetap dikirim
        message = self.HTTP_MESSAGES.get(exc.status_code, str(exc.detail))
        return JSONResponse({"detail": message}, status_code=exc.status_code, headers=exc.headers)

    def rate_limited(self, request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return TooManyRequests.retry_after(exc.limit.limit.get_expiry()).response()

    def server_error(self, request: Request, exc: Exception) -> JSONResponse:
        # detail error hanya di log server, traceback-nya dicetak Starlette sesudah handler ini
        log.error("error 500 di %s %s: %s", request.method, request.url.path, type(exc).__name__)
        response = ServerError().response()
        # response 500 dibuat di luar middleware, jadi header keamanan dipasang di sini
        response.headers.update(SecurityHeadersMiddleware.headers_for(request.url.path))
        return response
