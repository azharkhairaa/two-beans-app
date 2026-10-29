# semua model diimpor di sini supaya Base.metadata lengkap untuk Alembic dan test
from app.models.base import DOCUMENT_NUMBER_SEQUENCE, Base, TimestampMixin
from app.models.customer import Customer, CustomerType
from app.models.kategori import Kategori, KategoriType
from app.models.lokasi import Lokasi, LokasiType
from app.models.pembelian import Pembelian, PembelianDetail, PembelianStatus
from app.models.pengiriman import KendaraanType, Pengiriman, PengirimanDetail, PengirimanStatus
from app.models.penjualan import Penjualan, PenjualanDetail, PenjualanStatus
from app.models.permintaan import Permintaan, PermintaanDetail, PermintaanStatus
from app.models.produk import CoffeeType, Produk, ProdukUnit, RoastLevel
from app.models.stok import Stok, StokStatus
from app.models.stok_mutasi import StokMutasi, StokMutasiType
from app.models.supplier import Supplier
from app.models.transaksi import (
    REDUCING_REASONS,
    TRANSAKSI_REASONS,
    Transaksi,
    TransaksiDetail,
    TransaksiStatus,
    TransaksiType,
)
from app.models.user import User, UserRole, UserStatus
from app.models.user_session import UserSession

__all__ = [
    "DOCUMENT_NUMBER_SEQUENCE", "REDUCING_REASONS", "TRANSAKSI_REASONS", "Base", "CoffeeType",
    "Customer", "CustomerType", "Kategori", "KategoriType", "KendaraanType", "Lokasi", "LokasiType",
    "Pembelian", "PembelianDetail", "PembelianStatus", "Pengiriman", "PengirimanDetail",
    "PengirimanStatus", "Penjualan", "PenjualanDetail", "PenjualanStatus", "Permintaan",
    "PermintaanDetail", "PermintaanStatus", "Produk", "ProdukUnit", "RoastLevel", "Stok",
    "StokMutasi", "StokMutasiType", "StokStatus", "Supplier", "TimestampMixin", "Transaksi",
    "TransaksiDetail", "TransaksiStatus", "TransaksiType", "User", "UserRole", "UserSession",
    "UserStatus",
]
