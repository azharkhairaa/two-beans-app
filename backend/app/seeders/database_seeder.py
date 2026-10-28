from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Base
from app.seeders.base import SeedContext, Seeder
from app.seeders.lokasi_seeder import LokasiSeeder
from app.seeders.master_seeder import CustomerSeeder, KategoriSeeder, SupplierSeeder
from app.seeders.produk_seeder import ProdukSeeder
from app.seeders.riwayat_seeder import RiwayatSeeder
from app.seeders.user_seeder import UserSeeder

class DatabaseSeeder:
    # urutan mengikuti FK, termasuk riwayat dokumen 60 hari yang dijalankan lewat service
    SEEDERS: tuple[type[Seeder], ...] = (
        LokasiSeeder,
        UserSeeder,
        KategoriSeeder,
        SupplierSeeder,
        CustomerSeeder,
        ProdukSeeder,
        RiwayatSeeder,
    )

    def __init__(self, db: Session):
        self.db = db
        self.context = SeedContext()

    def run(self) -> dict[str, int]:
        self.truncate()
        for seeder in self.SEEDERS:
            seeder(self.db, self.context).run()
            self.db.flush()
        self.db.commit()
        return self.summary()

    def truncate(self) -> None:
        # nama tabel diambil dari metadata model, bukan dari input user
        preparer = self.db.get_bind().dialect.identifier_preparer
        tables = ", ".join(preparer.format_table(table) for table in Base.metadata.sorted_tables)
        self.db.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        self.db.execute(text("ALTER SEQUENCE dokumen_nomor_seq RESTART WITH 1"))

    def summary(self) -> dict[str, int]:
        counts = {
            table.name: self.db.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }
        return {name: count for name, count in counts.items() if count}
