from dataclasses import dataclass

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.core.errors import InsufficientStock
from app.models import Stok, StokMutasi, StokMutasiType, User

@dataclass(frozen=True)
class StockChange:
    # field menunjuk baris formulir supaya pesan stok kurang tampil di baris yang tepat
    lokasi_id: int
    produk_id: int
    delta: int
    field: str

@dataclass(frozen=True)
class MutationSource:
    jenis: StokMutasiType
    document_id: int

    # kolom dokumen sumber per jenis mutasi, sama dengan CHECK ck_stok_mutasi_sumber_jenis
    COLUMNS = {
        StokMutasiType.MASUK: "transaksi_id",
        StokMutasiType.KELUAR: "transaksi_id",
        StokMutasiType.PENYESUAIAN: "transaksi_id",
        StokMutasiType.KIRIM: "pengiriman_id",
        StokMutasiType.TERIMA: "pengiriman_id",
        StokMutasiType.PEMBELIAN: "pembelian_id",
        StokMutasiType.PENJUALAN: "penjualan_id",
    }

    def foreign_key(self) -> dict[str, int]:
        return {self.COLUMNS[self.jenis]: self.document_id}

class MutasiStok:
    # satu-satunya pengubah stok (BR-01): kunci baris, hitung saldo, tolak saldo negatif,
    # lalu tulis buku besar
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

    def apply(self, changes: list[StockChange], source: MutationSource) -> list[StokMutasi]:
        changes = [change for change in changes if change.delta != 0]
        keys = sorted({(c.lokasi_id, c.produk_id) for c in changes})
        if not keys:
            return []
        self.ensure_rows(keys)
        rows = self.lock(keys)
        balances = {key: rows[key].jumlah for key in keys}
        shortages: dict[str, str] = {}
        plan: list[tuple[StockChange, int, int]] = []
        for change in changes:
            key = (change.lokasi_id, change.produk_id)
            before = balances[key]
            after = before + change.delta
            if after < 0:
                row = rows[key]
                shortages[change.field] = (
                    f"Stok {row.produk.sku} di {row.lokasi.nama} tersisa {before} "
                    f"{row.produk.satuan}"
                )
                continue
            balances[key] = after
            plan.append((change, before, after))
        # BR-02: satu baris kurang menggagalkan seluruh aksi, tidak ada stok yang berubah sebagian
        if shortages:
            self.db.rollback()
            raise InsufficientStock(f"Stok tidak cukup untuk {len(shortages)} produk", shortages)
        mutations = []
        for change, before, after in plan:
            mutation = StokMutasi(
                lokasi_id=change.lokasi_id, produk_id=change.produk_id, jenis=source.jenis,
                perubahan=change.delta, stok_sebelum=before, stok_sesudah=after,
                user_id=self.user.id,
                **source.foreign_key(),
            )
            self.db.add(mutation)
            mutations.append(mutation)
        for key, balance in balances.items():
            rows[key].jumlah = balance
        # commit dilakukan pemanggil bersama perubahan status dokumen
        self.db.flush()
        return mutations

    def ensure_rows(self, keys: list[tuple[int, int]]) -> None:
        values = [{"lokasi_id": lokasi_id, "produk_id": produk_id} for lokasi_id, produk_id in keys]
        self.db.execute(insert(Stok).values(values).on_conflict_do_nothing())

    def lock(self, keys: list[tuple[int, int]]) -> dict[tuple[int, int], Stok]:
        # urutan kunci selalu lokasi_id lalu produk_id di setiap aksi, jadi tidak terjadi deadlock
        query = (
            select(Stok)
            .options(joinedload(Stok.produk), joinedload(Stok.lokasi))
            .where(tuple_(Stok.lokasi_id, Stok.produk_id).in_(keys))
            .order_by(Stok.lokasi_id, Stok.produk_id)
            .with_for_update(of=Stok)
            .execution_options(populate_existing=True)
        )
        return {(row.lokasi_id, row.produk_id): row for row in self.db.scalars(query).unique()}
