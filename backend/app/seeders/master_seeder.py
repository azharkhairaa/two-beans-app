from app.models import Customer, CustomerType, Kategori, KategoriType, Supplier
from app.seeders.base import Seeder

class KategoriSeeder(Seeder):
    # jenis kopi dicatat di produk, jadi nama kategori tidak menyebut jenisnya
    ROWS = [
        ("Green Bean", KategoriType.GREEN_BEAN, "Biji kopi mentah untuk disangrai di roastery"),
        ("Single Origin", KategoriType.ROASTED_BEAN, "Roasted bean dari satu daerah asal"),
        ("Blend", KategoriType.ROASTED_BEAN, "Campuran beberapa roasted bean"),
        ("Alat Seduh Manual", KategoriType.PERALATAN, "Dripper, french press dan alat seduh lain"),
        ("Grinder", KategoriType.PERALATAN, "Penggiling kopi manual dan listrik"),
        ("Mesin Espresso dan Aksesori", KategoriType.PERALATAN, "Mesin espresso beserta perlengkapannya"),
        ("Filter dan Bahan Habis Pakai", KategoriType.HABIS_PAKAI, "Kertas filter, gelas dan kemasan"),
    ]

    def run(self) -> None:
        for nama, jenis, deskripsi in self.ROWS:
            self.context.kategori[nama] = self.add(Kategori(nama=nama, jenis=jenis, deskripsi=deskripsi))

class SupplierSeeder(Seeder):
    # nama, kontak, telepon, email, alamat, aktif (data fiktif)
    ROWS = [
        ("CV Biji Hijau Nusantara", "Bagian Penjualan", "081234567890", "sales@bijihijau.example",
         "Takengon, Aceh Tengah", True),
        ("PT Kebun Kopi Priangan", "Bagian Pemasaran", "082112345678", "order@kopipriangan.example",
         "Pangalengan, Kabupaten Bandung", True),
        ("UD Tani Kopi Temanggung", "Admin Gudang", "085643210987", "tani@kopitemanggung.example",
         "Kledung, Temanggung", True),
        ("PT Alat Seduh Indonesia", "Customer Service", "02150012345", "cs@alatseduh.example",
         "Kelapa Gading, Jakarta Utara", True),
        ("CV Kemasan Kopi Mandiri", "Bagian Penjualan", "0317654321", "halo@kemasankopi.example",
         "Rungkut, Surabaya", True),
        ("PT Mesin Kopi Jaya", "Bagian Penjualan", "02145678901", "info@mesinkopi.example",
         "Cempaka Putih, Jakarta Pusat", False),
    ]

    def run(self) -> None:
        for nama, kontak, telepon, email, alamat, aktif in self.ROWS:
            self.context.supplier[nama] = self.add(Supplier(
                nama=nama, kontak=kontak, telepon=telepon, email=email, alamat=alamat, aktif=aktif,
            ))

class CustomerSeeder(Seeder):
    # nama, jenis, kontak, telepon, alamat, aktif (data fiktif)
    ROWS = [
        ("Kafe Senja", CustomerType.KAFE, "Pemilik kafe", "081322110011", "Jl. Dago No. 101, Bandung", True),
        ("Kafe Teras Dago", CustomerType.KAFE, "Barista kepala", "081322110022",
         "Jl. Ir. H. Juanda No. 300, Bandung", True),
        ("Kedai Kopi Lembang", CustomerType.KAFE, "Pemilik kedai", "081322110033",
         "Jl. Raya Lembang No. 77, Bandung Barat", True),
        ("Toko Oleh-oleh Priangan", CustomerType.RESELLER, "Bagian pembelian", "081322110044",
         "Jl. Cihampelas No. 160, Bandung", True),
        ("Reseller Kopi Cimahi", CustomerType.RESELLER, "Pemilik toko", "081322110055",
         "Jl. Amir Machmud No. 12, Cimahi", True),
        ("Pelanggan Perorangan Antapani", CustomerType.PERORANGAN, None, "081322110066", None, True),
        ("Komunitas Seduh Bandung", CustomerType.LAINNYA, "Pengurus komunitas", "081322110077", None, True),
        ("Kafe Sudut Kota", CustomerType.KAFE, "Pemilik kafe", "081322110088",
         "Jl. Asia Afrika No. 8, Bandung", False),
    ]

    def run(self) -> None:
        for nama, jenis, kontak, telepon, alamat, aktif in self.ROWS:
            self.context.customer[nama] = self.add(Customer(
                nama=nama, jenis=jenis, kontak=kontak, telepon=telepon, alamat=alamat, aktif=aktif,
            ))
