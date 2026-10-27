from typing import Literal

from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: Literal["ok", "gangguan"]
    database: Literal["koneksi database ok", "koneksi database putus"]
