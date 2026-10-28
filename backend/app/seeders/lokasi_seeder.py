from app.models import Lokasi, LokasiType
from app.seeders.base import Seeder

class LokasiSeeder(Seeder):
    # kode, nama, jenis, alamat, telepon (data fiktif)
    ROWS = [
        ("GU-01", "Gudang Utama Roastery", LokasiType.GUDANG_UTAMA,
         "Jl. Soekarno-Hatta No. 120, Bandung", "0227301201"),
        ("GC-01", "Gudang Cabang Barat", LokasiType.GUDANG_CABANG,
         "Jl. Raya Cimahi No. 45, Cimahi", "0226601145"),
        ("GC-02", "Gudang Cabang Timur", LokasiType.GUDANG_CABANG,
         "Jl. Raya Cileunyi No. 88, Kabupaten Bandung", "0227801288"),
        ("OT-01", "Outlet Pusat Kota", LokasiType.OUTLET, "Jl. Braga No. 21, Bandung", "0224201021"),
        ("OT-02", "Outlet Kampus", LokasiType.OUTLET, "Jl. Setiabudhi No. 210, Bandung", "0222001210"),
        ("OT-03", "Outlet Stasiun", LokasiType.OUTLET, "Jl. Kebon Kawung No. 43, Bandung", "0224203043"),
    ]

    def run(self) -> None:
        for kode, nama, jenis, alamat, telepon in self.ROWS:
            self.context.lokasi[kode] = self.add(
                Lokasi(kode=kode, nama=nama, jenis=jenis, alamat=alamat, telepon=telepon)
            )
