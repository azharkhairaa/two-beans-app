import logging

from sqlalchemy import ForeignKeyConstraint, MetaData, UniqueConstraint
from sqlalchemy.exc import IntegrityError

from app.core.errors import AppError, Conflict, DataInUse, InsufficientStock, ValidationFailed

log = logging.getLogger("uvicorn.error")

class IntegrityErrorMapper:
    # IntegrityError di-mapping lewat nama constraint (naming convention models/base.py)
    UNIQUE_VIOLATION = "23505"
    FOREIGN_KEY_VIOLATION = "23503"
    CHECK_VIOLATION = "23514"
    NOT_NULL_VIOLATION = "23502"

    UNIQUE_MESSAGES = {
        "uq_lokasi_kode": ("kode", "Kode lokasi sudah dipakai"),
        "uq_lokasi_nama_lower": ("nama", "Nama lokasi sudah dipakai"),
        "uq_lokasi_satu_gudang_utama": ("jenis", "Gudang utama sudah ada"),
        "uq_users_email": ("email", "Email sudah terdaftar"),
        "uq_kategori_nama_lower": ("nama", "Nama kategori sudah dipakai"),
        "uq_supplier_nama_lower": ("nama", "Nama supplier sudah dipakai"),
        "uq_customer_nama_lower": ("nama", "Nama customer sudah dipakai"),
        "uq_produk_sku": ("sku", "SKU sudah dipakai produk lain"),
        "uq_pengiriman_permintaan_id": ("permintaan_id", "Permintaan ini sudah punya pengiriman"),
    }
    STOCK_CHECKS = frozenset({"ck_stok_jumlah", "ck_stok_mutasi_saldo"})
    TABLE_LABELS = {"users": "user", "stok_mutasi": "riwayat mutasi stok"}

    def __init__(self, metadata: MetaData):
        # tabel dan kolom per constraint dibaca dari model, bukan ditulis ulang
        self.unique: dict[str, str] = {}
        self.foreign_keys: dict[str, tuple[str, list[str]]] = {}
        for table in metadata.tables.values():
            for constraint in table.constraints:
                if isinstance(constraint, UniqueConstraint):
                    self.unique[constraint.name] = table.name
                elif isinstance(constraint, ForeignKeyConstraint):
                    columns = [column.name for column in constraint.columns]
                    self.foreign_keys[constraint.name] = (table.name, columns)

    def to_app_error(self, exc: IntegrityError) -> AppError | None:
        sqlstate = getattr(exc.orig, "sqlstate", None)
        diag = getattr(exc.orig, "diag", None)
        name = getattr(diag, "constraint_name", None) or ""
        if sqlstate == self.UNIQUE_VIOLATION:
            return self._unique(name)
        if sqlstate == self.FOREIGN_KEY_VIOLATION:
            return self._foreign_key(name, exc.statement or "")
        if sqlstate == self.CHECK_VIOLATION:
            return self._check(name)
        if sqlstate == self.NOT_NULL_VIOLATION:
            column = getattr(diag, "column_name", None) or "body"
            return ValidationFailed(errors={column: "Wajib diisi"})
        return None

    def _unique(self, name: str) -> AppError:
        if name in self.UNIQUE_MESSAGES:
            field, message = self.UNIQUE_MESSAGES[name]
            return Conflict(message, {field: message})
        if self.unique.get(name, "").endswith("_detail"):
            return Conflict("Produk yang sama muncul lebih dari sekali",
                            {"items": "Produk tidak boleh ganda dalam satu dokumen"})
        return Conflict("Data yang sama sudah ada")

    def _foreign_key(self, name: str, statement: str) -> AppError:
        table, columns = self.foreign_keys.get(name, ("", []))
        # DELETE ditolak FK RESTRICT berarti induk masih dirujuk, selain itu id rujukan tidak ada
        if statement.lstrip().upper().startswith("DELETE"):
            return DataInUse(
                f"Data tidak bisa dihapus karena masih dipakai di {self._label(table)}"
            )
        field = columns[0] if columns else "body"
        return ValidationFailed("Data rujukan tidak ditemukan", {field: "Data tidak ditemukan"})

    def _check(self, name: str) -> AppError:
        if name in self.STOCK_CHECKS:
            return InsufficientStock()
        # CHECK lain sudah ditangkap schema atau service, nama constraint cukup di log
        log.warning("CHECK %s dilanggar", name)
        return ValidationFailed("Data tidak memenuhi aturan penyimpanan")

    def _label(self, table: str) -> str:
        if not table:
            return "data lain"
        if table in self.TABLE_LABELS:
            return self.TABLE_LABELS[table]
        if table.endswith("_detail"):
            return "detail " + table.removesuffix("_detail")
        return table.replace("_", " ")
