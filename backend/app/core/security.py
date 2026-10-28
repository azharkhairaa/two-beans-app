import secrets
from functools import cached_property

import bcrypt

from app.core.config import settings

class PasswordHasher:
    # bcrypt 5 menolak password di atas 72 byte, batas yang sama juga dicek di schema
    MAX_BYTES = 72

    def __init__(self, rounds: int):
        self.rounds = rounds

    @cached_property
    def dummy_hash(self) -> str:
        # dipakai saat email tidak terdaftar supaya waktu respons login tetap sama
        return self.hash(secrets.token_urlsafe(16))

    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(self.rounds)).decode()

    def verify(self, password: str, password_hash: str | None) -> bool:
        data = password.encode()
        # bcrypt tetap dijalankan walau user tidak ada atau password kepanjangan, waktunya jadi sama
        stored = (password_hash or self.dummy_hash).encode()
        matched = bcrypt.checkpw(data[: self.MAX_BYTES], stored)
        return matched and password_hash is not None and len(data) <= self.MAX_BYTES

password_hasher = PasswordHasher(settings.bcrypt_rounds)
