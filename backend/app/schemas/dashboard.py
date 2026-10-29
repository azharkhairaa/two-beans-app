from datetime import date

from pydantic import BaseModel

from app.schemas.common import LokasiKontakRef
from app.schemas.fields import UtcDateTime

class DashboardRingkasan(BaseModel):
    nilai_persediaan: int
    nilai_dalam_perjalanan: int
    nilai_po_terbuka: int
    omzet_30_hari: int
    nota_30_hari: int
    sku_aktif: int
    stok_menipis: int
    stok_habis: int
    permintaan_menunggu: int
    pengiriman_dalam_perjalanan: int
    akun_menunggu: int
    masuk_hari_ini: int = 0
    keluar_hari_ini: int = 0

class DashboardLokasiItem(BaseModel):
    id: int
    kode: str
    nama: str
    jenis: str
    sku_ada: int
    menipis: int
    habis: int
    nilai: int
    nota_30_hari: int
    omzet_30_hari: int

class DashboardCustomerItem(BaseModel):
    id: int | None = None
    nama: str
    jenis: str | None = None
    nota: int
    total: int

class DashboardStokKritisItem(BaseModel):
    lokasi_id: int
    lokasi: str
    lokasi_nama: str
    # jenis lokasi dan produk menentukan cara isi ulang: permintaan, PO atau hasil roasting
    lokasi_jenis: str
    produk_id: int
    produk_jenis: str
    sku: str
    nama: str
    satuan: str
    jumlah: int
    stok_minimum: int
    status_stok: str

class DashboardTugasItem(BaseModel):
    jenis: str
    id: int
    kode: str
    keterangan: str
    tanggal: str | None = None

class DashboardAktivitasItem(BaseModel):
    id: int
    waktu: UtcDateTime
    lokasi_kode: str
    lokasi_nama: str
    produk_sku: str
    produk_nama: str
    satuan: str
    jenis: str
    perubahan: int
    stok_sesudah: int
    dokumen_kode: str | None = None
    oleh: str

class DeliverymanPengirimanItem(BaseModel):
    id: int
    kode: str
    status: str
    tanggal_kirim: date
    lokasi_asal: LokasiKontakRef
    lokasi_tujuan: LokasiKontakRef
    kendaraan_jenis: str | None
    kendaraan_nomor: str | None
    jumlah_item: int
    total_unit: int
    catatan: str | None = None
    dikirim_pada: UtcDateTime | None = None
    diterima_pada: UtcDateTime | None = None

class DashboardResponse(BaseModel):
    peran: str
    lokasi: LokasiKontakRef | None = None
    ringkasan: DashboardRingkasan | None = None
    per_lokasi: list[DashboardLokasiItem] = []
    customer_teratas: list[DashboardCustomerItem] = []
    stok_kritis: list[DashboardStokKritisItem] = []
    tugas: list[DashboardTugasItem] = []
    aktivitas_terbaru: list[DashboardAktivitasItem] = []
    pengiriman_aktif: list[DeliverymanPengirimanItem] = []
    riwayat: list[DeliverymanPengirimanItem] = []

class MonitoringLokasiHeader(BaseModel):
    id: int
    kode: str
    nama: str
    jenis: str

class MonitoringProdukInfo(BaseModel):
    id: int
    sku: str
    nama: str
    satuan: str
    jenis: str
    kategori_nama: str
    # nilai rupiah null untuk manager yang hanya boleh melihat jumlah lokasi lain
    harga_beli: int | None

class MonitoringSel(BaseModel):
    lokasi_id: int
    jumlah: int
    stok_minimum: int
    rak: str | None = None
    status_stok: str
    nilai: int | None

class MonitoringBaris(BaseModel):
    produk: MonitoringProdukInfo
    sel: list[MonitoringSel]
    total: int
    nilai: int | None

class MonitoringTotalLokasi(BaseModel):
    lokasi_id: int
    kode: str
    nama: str
    nilai: int | None

class MonitoringResponse(BaseModel):
    lokasi: list[MonitoringLokasiHeader]
    baris: list[MonitoringBaris]
    total_per_lokasi: list[MonitoringTotalLokasi]
    total_nilai: int | None
    # false untuk manager gudang cabang dan outlet, semua nilai rupiah di matriks berisi null
    nilai_terlihat: bool

class TrenHariItem(BaseModel):
    tanggal: date
    masuk: int
    keluar: int

class TrenResponse(BaseModel):
    hari: int
    lokasi_id: int | None = None
    data: list[TrenHariItem]
