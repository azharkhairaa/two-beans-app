import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Self
from urllib.parse import urlsplit

from dotenv import load_dotenv

ENV = ("local", "test", "production")
RATE_LIMIT_PATTERN = re.compile(r"\d+/(second|minute|hour|day)")

class ConfigError(RuntimeError):
    def __init__(self, error: list[str]):
        lines = "\n".join(f"- {k}" for k in error)
        super().__init__(
            f"Konfigurasi environment belum benar:\n{lines}\n"
            "Lokal: copy backend/.env.example menjadi backend/.env lalu isi nilainya. "
            "Vercel: isi Environment Variables project lalu redeploy."
        )
        self.error = error

class EnvReader:
    # read env sesuai tipenya, semua error dikumpulkan, dilaporkan sekaligus

    def __init__(self, env: Mapping[str, str]):
        self.env = env
        self.error: list[str] = []

    def text(self, name: str, default: str = "") -> str:
        return self.env.get(name, "").strip() or default

    def required(self, name: str, min_length: int = 1) -> str:
        value = self.text(name)
        # value tidak ditulis di pesan
        if not value:
            self.error.append(f"{name} wajib diisi")
        elif len(value) < min_length:
            self.error.append(f"{name} minimal {min_length} karakter")
        return value

    def choice(self, name: str, choices: tuple[str, ...], default: str) -> str:
        value = self.text(name, default)
        if value not in choices:
            self.error.append(f"{name} harus salah satu dari {', '.join(choices)}")
        return value

    def number(self, name: str, default: int, minimum: int, maximum: int) -> int:
        value = self.text(name, str(default))
        if not value.isdigit() or not minimum <= int(value) <= maximum:
            self.error.append(f"{name} harus bilangan bulat {minimum} sampai {maximum}")
            return default
        return int(value)

    def boolean(self, name: str, default: bool) -> bool:
        value = self.text(name).lower()
        if value in ("true", "1"):
            return True
        if value in ("false", "0"):
            return False
        if value:
            self.error.append(f"{name} harus true atau false")
        return default

    def pattern(self, name: str, pattern: re.Pattern, default: str, example: str) -> str:
        value = self.text(name, default)
        if not pattern.fullmatch(value):
            self.error.append(f"{name} harus berbentuk seperti {example}")
        return value

    def postgresql_url(self, name: str) -> str:
        url = self.required(name)
        # Neon url postgresql://, SQLAlchemy butuh driver psycopg 3
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                url = "postgresql+psycopg://" + url.removeprefix(prefix)
        if url and not url.startswith("postgresql+psycopg://"):
            self.error.append(f"{name} harus URL PostgreSQL yang diawali postgresql://")
        return url

    def origins(self, name: str, default: str) -> list[str]:
        origins = []
        for origin in self.text(name, default).split(","):
            origin = origin.strip().rstrip("/")
            if not origin:
                continue
            parts = urlsplit(origin)
            # origin hanya skema dan host, tanpa path atau query
            if parts.scheme not in ("http", "https") or origin != f"{parts.scheme}://{parts.netloc}":
                self.error.append(f"{name} load origin tidak valid: {origin}")
            origins.append(origin)
        return origins

@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str = field(repr=False)
    secret_key: str = field(repr=False)
    allowed_origins: tuple[str, ...]
    cookie_secure: bool
    session_idle_minutes: int
    session_max_hours: int
    login_rate_limit: str
    bcrypt_rounds: int
    serverless: bool

    @property
    def production(self) -> bool:
        return self.app_env == "production"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Self:
        if env is None:
            load_dotenv()
            env = os.environ
        read = EnvReader(env)
        app_env = read.choice("APP_ENV", ENV, "local")
        settings = cls(
            app_env=app_env,
            database_url=read.postgresql_url("DATABASE_URL"),
            secret_key=read.required("SECRET_KEY", min_length=32),
            allowed_origins=cls._origins(read),
            cookie_secure=read.boolean("COOKIE_SECURE", app_env == "production"),
            session_idle_minutes=read.number("SESSION_IDLE_MINUTES", 60, 1, 24 * 60),
            session_max_hours=read.number("SESSION_MAX_HOURS", 12, 1, 24 * 7),
            login_rate_limit=read.pattern(
                "LOGIN_RATE_LIMIT", RATE_LIMIT_PATTERN, "5/minute", "5/minute"
            ),
            bcrypt_rounds=read.number("BCRYPT_ROUNDS", 12, 4, 31),
            serverless=bool(read.text("VERCEL")),
        )
        error = read.error + settings._check_combination()
        if error:
            raise ConfigError(error)
        return settings

    @staticmethod
    def _origins(read: EnvReader) -> tuple[str, ...]:
        origins = read.origins("ALLOWED_ORIGINS", "http://localhost:5173")
        # URL deployment Vercel (preview dan production) otomatis diizinkan
        for name in ("VERCEL_URL", "VERCEL_PROJECT_PRODUCTION_URL"):
            if host := read.text(name):
                origins.append(f"https://{host}")
        return tuple(dict.fromkeys(origins))

    def _check_combination(self) -> list[str]:
        error = []
        if self.session_idle_minutes > self.session_max_hours * 60:
            error.append("SESSION_IDLE_MINUTES tidak boleh melebihi SESSION_MAX_HOURS")
        if self.production and not self.cookie_secure:
            error.append("COOKIE_SECURE wajib true saat APP_ENV=production")
        return error

settings = Settings.from_env()
