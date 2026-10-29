from fastapi.responses import JSONResponse

class AppError(Exception):
    # error yang pesannya aman ditampilkan ke user
    status_code = 400
    default_message = "Permintaan tidak bisa diproses"

    def __init__(
        self,
        message: str | None = None,
        errors: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.message = message or self.default_message
        self.errors = errors or {}
        self.headers = headers or {}
        super().__init__(self.message)

    def body(self) -> dict:
        # errors hanya dikirim kalau error bisa ditunjuk ke field tertentu
        body: dict = {"detail": self.message}
        if self.errors:
            body["errors"] = self.errors
        return body

    def response(self) -> JSONResponse:
        return JSONResponse(self.body(), status_code=self.status_code, headers=self.headers)

class NotAuthenticated(AppError):
    status_code = 401
    default_message = "Belum login atau sesi sudah berakhir"

class Forbidden(AppError):
    status_code = 403
    default_message = "Akses ditolak"

class NotFound(AppError):
    status_code = 404
    default_message = "Data tidak ditemukan"

class Conflict(AppError):
    status_code = 409
    default_message = "Data bentrok dengan data yang sudah ada"

class DataInUse(Conflict):
    default_message = "Data masih dipakai sehingga tidak bisa dihapus"

class InvalidStatus(Conflict):
    default_message = "Status dokumen tidak sesuai untuk aksi ini"

class InsufficientStock(Conflict):
    default_message = "Stock tidak cukup"

class ValidationFailed(AppError):
    status_code = 422
    default_message = "Data belum valid"

class TooManyRequests(AppError):
    status_code = 429
    default_message = "Terlalu banyak percobaan. Coba lagi nanti"

    @classmethod
    def retry_after(cls, seconds: int) -> "TooManyRequests":
        # Retry-After memberi tahu frontend kapan boleh coba lagi
        return cls(
            f"Terlalu banyak percobaan. Coba lagi dalam {cls._duration(seconds)}",
            headers={"Retry-After": str(seconds)},
        )

    @staticmethod
    def _duration(seconds: int) -> str:
        if seconds % 3600 == 0:
            return f"{seconds // 3600} jam"
        if seconds % 60 == 0:
            return f"{seconds // 60} menit"
        return f"{seconds} detik"

class ServerError(AppError):
    status_code = 500
    default_message = "Terjadi error di server"
