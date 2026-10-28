import random
from dataclasses import dataclass, field
from typing import TypeVar

from sqlalchemy.orm import Session

from app.models import Customer, Kategori, Lokasi, Produk, Supplier, User

T = TypeVar("T")

# password sama untuk semua akun demo, dicantumkan di README
DEMO_PASSWORD = "twobeans2026"

@dataclass
class SeedContext:
    # objek hasil seeder sebelumnya, dicari lewat kode, email, nama atau SKU oleh seeder berikutnya
    rng: random.Random = field(default_factory=lambda: random.Random(2026))
    lokasi: dict[str, Lokasi] = field(default_factory=dict)
    users: dict[str, User] = field(default_factory=dict)
    kategori: dict[str, Kategori] = field(default_factory=dict)
    supplier: dict[str, Supplier] = field(default_factory=dict)
    customer: dict[str, Customer] = field(default_factory=dict)
    produk: dict[str, Produk] = field(default_factory=dict)

class Seeder:
    def __init__(self, db: Session, context: SeedContext):
        self.db = db
        self.context = context

    def run(self) -> None:
        raise NotImplementedError

    def add(self, obj: T) -> T:
        self.db.add(obj)
        return obj
