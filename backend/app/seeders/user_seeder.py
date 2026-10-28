from app.core.security import password_hasher
from app.models import User, UserRole, UserStatus
from app.seeders.base import DEMO_PASSWORD, Seeder

class UserSeeder(Seeder):
    # email, nama, peran, kode lokasi, status
    ROWS = [
        ("admin@example.com", "Admin Two Beans", UserRole.ADMIN, None, UserStatus.AKTIF),
        ("manager.roastery@example.com", "Manager Gudang Utama", UserRole.MANAGER_GUDANG, "GU-01",
         UserStatus.AKTIF),
        ("manager.barat@example.com", "Manager Gudang Barat", UserRole.MANAGER_GUDANG, "GC-01",
         UserStatus.AKTIF),
        ("manager.timur@example.com", "Manager Gudang Timur", UserRole.MANAGER_GUDANG, "GC-02",
         UserStatus.AKTIF),
        ("manager.pusat@example.com", "Manager Outlet Pusat", UserRole.MANAGER_OUTLET, "OT-01",
         UserStatus.AKTIF),
        ("manager.kampus@example.com", "Manager Outlet Kampus", UserRole.MANAGER_OUTLET, "OT-02",
         UserStatus.AKTIF),
        ("kurir@example.com", "Deliveryman Two Beans", UserRole.DELIVERYMAN, None, UserStatus.AKTIF),
        # contoh akun hasil registrasi yang menunggu persetujuan admin
        ("calon.manager@example.com", "Calon Manager", None, None, UserStatus.MENUNGGU),
    ]

    def run(self) -> None:
        for email, name, role, kode_lokasi, status in self.ROWS:
            self.context.users[email] = self.add(User(
                email=email,
                name=name,
                password_hash=password_hasher.hash(DEMO_PASSWORD),
                role=role,
                status=status,
                lokasi=self.context.lokasi[kode_lokasi] if kode_lokasi else None,
            ))
