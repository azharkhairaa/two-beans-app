from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.clock import Clock
from app.core.errors import NotFound
from app.models import (
    Customer,
    Kategori,
    KategoriType,
    Lokasi,
    LokasiType,
    Pembelian,
    PembelianDetail,
    PembelianStatus,
    Pengiriman,
    PengirimanDetail,
    PengirimanStatus,
    Penjualan,
    PenjualanDetail,
    PenjualanStatus,
    Permintaan,
    PermintaanStatus,
    Produk,
    Stok,
    StokMutasi,
    StokStatus,
    Transaksi,
    User,
    UserRole,
    UserStatus,
)
from app.policies.lokasi_policy import LokasiPolicy
from app.schemas.dashboard import (
    DashboardAktivitasItem,
    DashboardCustomerItem,
    DashboardLokasiItem,
    DashboardResponse,
    DashboardRingkasan,
    DashboardStokKritisItem,
    DashboardTugasItem,
    DeliverymanPengirimanItem,
    MonitoringBaris,
    MonitoringLokasiHeader,
    MonitoringProdukInfo,
    MonitoringResponse,
    MonitoringSel,
    MonitoringTotalLokasi,
    TrenHariItem,
    TrenResponse,
)
from app.schemas.pengiriman import PengirimanLokasi
from app.services.base import CrudService

@dataclass(frozen=True)
class MonitoringFilter:
    kategori_id: int | None = None
    jenis: KategoriType | None = None
    status_stok: StokStatus | None = None
    q: str | None = None


class DashboardService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.lokasi_policy = LokasiPolicy(user)

    def summary(self) -> DashboardResponse:
        if self.user.role == UserRole.DELIVERYMAN:
            return self.deliveryman_dashboard()
        if self.user.role == UserRole.ADMIN:
            return self.admin_dashboard()
        return self.manager_dashboard()

    def admin_dashboard(self) -> DashboardResponse:
        today = Clock.today()
        since = today - timedelta(days=29)

        per_lokasi = self.query_per_lokasi(since, today, lokasi_id=None)
        nilai_persediaan = sum(item.nilai for item in per_lokasi)
        stok_menipis = sum(item.menipis for item in per_lokasi)
        stok_habis = sum(item.habis for item in per_lokasi)
        omzet_30_hari = sum(item.omzet_30_hari for item in per_lokasi)
        nota_30_hari = sum(item.nota_30_hari for item in per_lokasi)

        nilai_dalam_perjalanan = self.query_nilai_dalam_perjalanan(lokasi_id=None)
        nilai_po_terbuka = self.query_nilai_po_terbuka(lokasi_id=None)

        sku_aktif = int(
            self.db.scalar(select(func.count(Produk.id)).where(Produk.aktif.is_(True))) or 0
        )
        permintaan_menunggu = int(
            self.db.scalar(
                select(func.count(Permintaan.id)).where(
                    Permintaan.status == PermintaanStatus.DIAJUKAN
                )
            )
            or 0
        )
        pengiriman_dalam_perjalanan = int(
            self.db.scalar(
                select(func.count(Pengiriman.id)).where(
                    Pengiriman.status == PengirimanStatus.DIKIRIM
                )
            )
            or 0
        )
        akun_menunggu = int(
            self.db.scalar(
                select(func.count(User.id)).where(User.status == UserStatus.MENUNGGU)
            )
            or 0
        )
        masuk_hari_ini, keluar_hari_ini = self.query_mutasi_hari_ini(today, lokasi_id=None)

        ringkasan = DashboardRingkasan(
            nilai_persediaan=nilai_persediaan,
            nilai_dalam_perjalanan=nilai_dalam_perjalanan,
            nilai_po_terbuka=nilai_po_terbuka,
            omzet_30_hari=omzet_30_hari,
            nota_30_hari=nota_30_hari,
            sku_aktif=sku_aktif,
            stok_menipis=stok_menipis,
            stok_habis=stok_habis,
            permintaan_menunggu=permintaan_menunggu,
            pengiriman_dalam_perjalanan=pengiriman_dalam_perjalanan,
            akun_menunggu=akun_menunggu,
            masuk_hari_ini=masuk_hari_ini,
            keluar_hari_ini=keluar_hari_ini,
        )

        return DashboardResponse(
            peran=UserRole.ADMIN.value,
            ringkasan=ringkasan,
            per_lokasi=per_lokasi,
            customer_teratas=self.query_customer_teratas(since, today, lokasi_id=None),
            stok_kritis=self.query_stok_kritis(lokasi_id=None),
            tugas=self.query_tugas(lokasi=None),
            aktivitas_terbaru=self.query_aktivitas_terbaru(lokasi_id=None),
        )

    def manager_dashboard(self) -> DashboardResponse:
        today = Clock.today()
        since = today - timedelta(days=29)
        lokasi = self.user.lokasi
        lokasi_id = lokasi.id if lokasi else self.user.lokasi_id

        per_lokasi = self.query_per_lokasi(since, today, lokasi_id=lokasi_id)
        lok_summary = per_lokasi[0] if per_lokasi else None

        is_gudang_utama = lokasi is not None and lokasi.jenis == LokasiType.GUDANG_UTAMA
        nilai_dalam_perjalanan = self.query_nilai_dalam_perjalanan(lokasi_id=lokasi_id)
        nilai_po_terbuka = (
            self.query_nilai_po_terbuka(lokasi_id=lokasi_id) if is_gudang_utama else 0
        )

        permintaan_query = select(func.count(Permintaan.id)).where(
            Permintaan.status == PermintaanStatus.DIAJUKAN
        )
        if not is_gudang_utama:
            permintaan_query = permintaan_query.where(Permintaan.lokasi_peminta_id == lokasi_id)
        permintaan_menunggu = int(self.db.scalar(permintaan_query) or 0)

        pengiriman_dalam_perjalanan = int(
            self.db.scalar(
                select(func.count(Pengiriman.id)).where(
                    Pengiriman.status == PengirimanStatus.DIKIRIM,
                    or_(
                        Pengiriman.lokasi_asal_id == lokasi_id,
                        Pengiriman.lokasi_tujuan_id == lokasi_id,
                    ),
                )
            )
            or 0
        )

        masuk_hari_ini, keluar_hari_ini = self.query_mutasi_hari_ini(today, lokasi_id=lokasi_id)

        ringkasan = DashboardRingkasan(
            nilai_persediaan=lok_summary.nilai if lok_summary else 0,
            nilai_dalam_perjalanan=nilai_dalam_perjalanan,
            nilai_po_terbuka=nilai_po_terbuka,
            omzet_30_hari=lok_summary.omzet_30_hari if lok_summary else 0,
            nota_30_hari=lok_summary.nota_30_hari if lok_summary else 0,
            sku_aktif=lok_summary.sku_ada if lok_summary else 0,
            stok_menipis=lok_summary.menipis if lok_summary else 0,
            stok_habis=lok_summary.habis if lok_summary else 0,
            permintaan_menunggu=permintaan_menunggu,
            pengiriman_dalam_perjalanan=pengiriman_dalam_perjalanan,
            akun_menunggu=0,
            masuk_hari_ini=masuk_hari_ini,
            keluar_hari_ini=keluar_hari_ini,
        )

        return DashboardResponse(
            peran=self.user.role,
            lokasi=PengirimanLokasi.model_validate(lokasi) if lokasi else None,
            ringkasan=ringkasan,
            per_lokasi=per_lokasi,
            customer_teratas=self.query_customer_teratas(since, today, lokasi_id=lokasi_id),
            stok_kritis=self.query_stok_kritis(lokasi_id=lokasi_id),
            tugas=self.query_tugas(lokasi=lokasi),
            aktivitas_terbaru=self.query_aktivitas_terbaru(lokasi_id=lokasi_id),
        )

    def deliveryman_dashboard(self) -> DashboardResponse:
        base_query = (
            select(Pengiriman)
            .options(
                joinedload(Pengiriman.lokasi_asal),
                joinedload(Pengiriman.lokasi_tujuan),
                selectinload(Pengiriman.detail).joinedload(PengirimanDetail.produk),
            )
            .where(Pengiriman.deliveryman_id == self.user.id)
        )
        aktif_rows = self.db.scalars(
            base_query.where(Pengiriman.status == PengirimanStatus.DIKIRIM).order_by(
                Pengiriman.tanggal_kirim.asc(), Pengiriman.id.desc()
            )
        ).all()
        riwayat_rows = self.db.scalars(
            base_query.where(Pengiriman.status == PengirimanStatus.DITERIMA)
            .order_by(Pengiriman.diterima_pada.desc(), Pengiriman.id.desc())
            .limit(20)
        ).all()

        return DashboardResponse(
            peran=UserRole.DELIVERYMAN.value,
            pengiriman_aktif=[self.to_deliveryman_item(row) for row in aktif_rows],
            riwayat=[self.to_deliveryman_item(row) for row in riwayat_rows],
        )

    @staticmethod
    def to_deliveryman_item(pengiriman: Pengiriman) -> DeliverymanPengirimanItem:
        total_unit = sum(row.jumlah_dikirim for row in pengiriman.detail)
        nilai_dikirim = sum(
            row.jumlah_dikirim * row.produk.harga_beli for row in pengiriman.detail
        )
        return DeliverymanPengirimanItem(
            id=pengiriman.id,
            kode=pengiriman.kode,
            status=pengiriman.status,
            tanggal_kirim=pengiriman.tanggal_kirim,
            lokasi_asal=PengirimanLokasi.model_validate(pengiriman.lokasi_asal),
            lokasi_tujuan=PengirimanLokasi.model_validate(pengiriman.lokasi_tujuan),
            kendaraan_jenis=pengiriman.kendaraan_jenis,
            kendaraan_nomor=pengiriman.kendaraan_nomor,
            jumlah_item=len(pengiriman.detail),
            total_unit=total_unit,
            nilai_dikirim=nilai_dikirim,
            catatan=pengiriman.catatan,
            dikirim_pada=pengiriman.dikirim_pada,
            diterima_pada=pengiriman.diterima_pada,
        )

    def query_per_lokasi(
        self, since, today, lokasi_id: int | None
    ) -> list[DashboardLokasiItem]:
        # Desain Database 8.2: nilai persediaan dan status stok per lokasi
        stok_query = (
            select(
                Lokasi,
                func.count().filter(Stok.jumlah > 0).label("sku_ada"),
                func.count()
                .filter(Stok.jumlah > 0, Stok.jumlah <= Stok.stok_minimum)
                .label("menipis"),
                func.count().filter(Stok.jumlah == 0).label("habis"),
                func.coalesce(func.sum(Stok.jumlah * Produk.harga_beli), 0).label("nilai"),
            )
            .outerjoin(Stok, Stok.lokasi_id == Lokasi.id)
            .outerjoin(Produk, Produk.id == Stok.produk_id)
            .where(Lokasi.aktif.is_(True))
            .group_by(Lokasi.id)
            .order_by(Lokasi.kode)
        )
        if lokasi_id is not None:
            stok_query = stok_query.where(Lokasi.id == lokasi_id)
        stok_rows = self.db.execute(stok_query).all()

        # Desain Database 8.6: omzet dan jumlah nota 30 hari per lokasi
        omzet_query = (
            select(
                Lokasi.id.label("lokasi_id"),
                func.count(func.distinct(Penjualan.id)).label("nota"),
                func.coalesce(
                    func.sum(PenjualanDetail.jumlah * PenjualanDetail.harga_satuan), 0
                ).label("omzet"),
            )
            .outerjoin(
                Penjualan,
                (Penjualan.lokasi_id == Lokasi.id)
                & (Penjualan.status == PenjualanStatus.DIPOSTING)
                & Penjualan.tanggal.between(since, today),
            )
            .outerjoin(PenjualanDetail, PenjualanDetail.penjualan_id == Penjualan.id)
            .where(Lokasi.aktif.is_(True))
            .group_by(Lokasi.id)
        )
        if lokasi_id is not None:
            omzet_query = omzet_query.where(Lokasi.id == lokasi_id)
        omzet_map = {
            row.lokasi_id: (int(row.nota or 0), int(row.omzet or 0))
            for row in self.db.execute(omzet_query).all()
        }

        result: list[DashboardLokasiItem] = []
        for lok, sku_ada, menipis, habis, nilai in stok_rows:
            nota, omzet = omzet_map.get(lok.id, (0, 0))
            result.append(
                DashboardLokasiItem(
                    id=lok.id,
                    kode=lok.kode,
                    nama=lok.nama,
                    jenis=lok.jenis,
                    sku_ada=int(sku_ada or 0),
                    menipis=int(menipis or 0),
                    habis=int(habis or 0),
                    nilai=int(nilai or 0),
                    nota_30_hari=nota,
                    omzet_30_hari=omzet,
                )
            )
        return result

    def query_nilai_dalam_perjalanan(self, lokasi_id: int | None) -> int:
        # Desain Database 8.4: nilai barang dalam pengiriman berstatus dikirim
        query = (
            select(
                func.coalesce(func.sum(PengirimanDetail.jumlah_dikirim * Produk.harga_beli), 0)
            )
            .select_from(Pengiriman)
            .join(PengirimanDetail, PengirimanDetail.pengiriman_id == Pengiriman.id)
            .join(Produk, Produk.id == PengirimanDetail.produk_id)
            .where(Pengiriman.status == PengirimanStatus.DIKIRIM)
        )
        if lokasi_id is not None:
            query = query.where(
                or_(
                    Pengiriman.lokasi_asal_id == lokasi_id,
                    Pengiriman.lokasi_tujuan_id == lokasi_id,
                )
            )
        return int(self.db.scalar(query) or 0)

    def query_nilai_po_terbuka(self, lokasi_id: int | None) -> int:
        # Desain Database 8.4: nilai pesanan pembelian berstatus dipesan
        query = (
            select(
                func.coalesce(func.sum(PembelianDetail.jumlah * PembelianDetail.harga_satuan), 0)
            )
            .select_from(Pembelian)
            .join(PembelianDetail, PembelianDetail.pembelian_id == Pembelian.id)
            .where(Pembelian.status == PembelianStatus.DIPESAN)
        )
        if lokasi_id is not None:
            query = query.where(Pembelian.lokasi_id == lokasi_id)
        return int(self.db.scalar(query) or 0)

    def query_mutasi_hari_ini(self, today, lokasi_id: int | None) -> tuple[int, int]:
        wib_date = func.date(func.timezone("Asia/Jakarta", StokMutasi.created_at))
        query = select(
            func.coalesce(func.sum(StokMutasi.perubahan).filter(StokMutasi.perubahan > 0), 0),
            func.coalesce(-func.sum(StokMutasi.perubahan).filter(StokMutasi.perubahan < 0), 0),
        ).where(wib_date == today)
        if lokasi_id is not None:
            query = query.where(StokMutasi.lokasi_id == lokasi_id)
        masuk, keluar = self.db.execute(query).one()
        return int(masuk or 0), int(keluar or 0)

    def query_customer_teratas(
        self, since, today, lokasi_id: int | None
    ) -> list[DashboardCustomerItem]:
        # Desain Database 8.6: 5 customer teratas dari penjualan diposting 30 hari terakhir
        total_col = func.coalesce(
            func.sum(PenjualanDetail.jumlah * PenjualanDetail.harga_satuan), 0
        ).label("total")
        nota_col = func.count(func.distinct(Penjualan.id)).label("nota")
        query = (
            select(
                Customer.id.label("id"),
                func.coalesce(Customer.nama, "Umum").label("nama"),
                Customer.jenis.label("jenis"),
                nota_col,
                total_col,
            )
            .select_from(Penjualan)
            .join(PenjualanDetail, PenjualanDetail.penjualan_id == Penjualan.id)
            .outerjoin(Customer, Customer.id == Penjualan.customer_id)
            .where(
                Penjualan.status == PenjualanStatus.DIPOSTING,
                Penjualan.tanggal.between(since, today),
            )
            .group_by(Customer.id, Customer.nama, Customer.jenis)
            .order_by(total_col.desc(), nota_col.desc())
            .limit(5)
        )
        if lokasi_id is not None:
            query = query.where(Penjualan.lokasi_id == lokasi_id)
        return [
            DashboardCustomerItem(
                id=row.id,
                nama=row.nama,
                jenis=row.jenis,
                nota=int(row.nota or 0),
                total=int(row.total or 0),
            )
            for row in self.db.execute(query).all()
        ]

    def query_stok_kritis(self, lokasi_id: int | None) -> list[DashboardStokKritisItem]:
        severity = case((Stok.jumlah == 0, 0), else_=1)
        query = (
            select(Stok, Lokasi, Produk)
            .join(Lokasi, Lokasi.id == Stok.lokasi_id)
            .join(Produk, Produk.id == Stok.produk_id)
            .where(
                Lokasi.aktif.is_(True),
                Produk.aktif.is_(True),
                or_(Stok.jumlah == 0, Stok.jumlah <= Stok.stok_minimum),
            )
            .order_by(severity.asc(), Lokasi.kode.asc(), Produk.sku.asc())
            .limit(20)
        )
        if lokasi_id is not None:
            query = query.where(Stok.lokasi_id == lokasi_id)
        rows = self.db.execute(query).all()
        return [
            DashboardStokKritisItem(
                lokasi_id=lok.id,
                lokasi=lok.kode,
                lokasi_nama=lok.nama,
                produk_id=prod.id,
                sku=prod.sku,
                nama=prod.nama,
                satuan=prod.satuan,
                jumlah=stok.jumlah,
                stok_minimum=stok.stok_minimum,
                status_stok=stok.status_stok.value,
            )
            for stok, lok, prod in rows
        ]

    def query_tugas(self, lokasi: Lokasi | None) -> list[DashboardTugasItem]:
        tugas: list[DashboardTugasItem] = []
        is_admin = self.user.role == UserRole.ADMIN
        lokasi_id = lokasi.id if lokasi else None
        is_gudang_utama = is_admin or (
            lokasi is not None and lokasi.jenis == LokasiType.GUDANG_UTAMA
        )

        # 1. Pengiriman masuk berstatus dikirim yang perlu dikonfirmasi terima
        incoming_q = (
            select(Pengiriman)
            .options(
                joinedload(Pengiriman.lokasi_asal),
                joinedload(Pengiriman.lokasi_tujuan),
                selectinload(Pengiriman.detail),
            )
            .where(Pengiriman.status == PengirimanStatus.DIKIRIM)
            .order_by(Pengiriman.tanggal_kirim.asc(), Pengiriman.id.asc())
        )
        if lokasi_id is not None:
            incoming_q = incoming_q.where(Pengiriman.lokasi_tujuan_id == lokasi_id)
        for k in self.db.scalars(incoming_q).all():
            asal_nama = k.lokasi_asal.nama
            tujuan_nama = k.lokasi_tujuan.nama
            ket = f"Kiriman dari {asal_nama} menuju {tujuan_nama} ({len(k.detail)} produk)"
            tugas.append(
                DashboardTugasItem(
                    jenis="terima_pengiriman",
                    id=k.id,
                    kode=k.kode,
                    keterangan=ket,
                    tanggal=str(k.tanggal_kirim),
                )
            )

        # 2. Permintaan menunggu persetujuan di Gudang Utama
        if is_gudang_utama:
            pm_q = (
                select(Permintaan)
                .options(
                    joinedload(Permintaan.lokasi_peminta),
                    selectinload(Permintaan.detail),
                )
                .where(Permintaan.status == PermintaanStatus.DIAJUKAN)
                .order_by(Permintaan.created_at.asc())
            )
            for p in self.db.scalars(pm_q).all():
                peminta_nama = p.lokasi_peminta.nama
                tugas.append(
                    DashboardTugasItem(
                        jenis="proses_permintaan",
                        id=p.id,
                        kode=p.kode,
                        keterangan=f"Permintaan dari {peminta_nama} ({len(p.detail)} produk)",
                        tanggal=str(p.tanggal_butuh) if p.tanggal_butuh else None,
                    )
                )

        # 3. Pesanan pembelian (PO) berstatus dipesan yang menunggu diterima di Gudang Utama
        if is_gudang_utama:
            po_q = (
                select(Pembelian)
                .options(joinedload(Pembelian.supplier), selectinload(Pembelian.detail))
                .where(Pembelian.status == PembelianStatus.DIPESAN)
                .order_by(Pembelian.tanggal_perkiraan.asc().nulls_last(), Pembelian.id.asc())
            )
            for b in self.db.scalars(po_q).all():
                tugas.append(
                    DashboardTugasItem(
                        jenis="terima_pembelian",
                        id=b.id,
                        kode=b.kode,
                        keterangan=f"PO ke {b.supplier.nama} ({len(b.detail)} produk)",
                        tanggal=str(b.tanggal_perkiraan or b.tanggal_pesan or ""),
                    )
                )

        # 4. Draf pengiriman yang perlu dikirim dari gudang asal
        draft_kirim_q = (
            select(Pengiriman)
            .options(
                joinedload(Pengiriman.lokasi_asal),
                joinedload(Pengiriman.lokasi_tujuan),
                selectinload(Pengiriman.detail),
            )
            .where(Pengiriman.status == PengirimanStatus.DRAF)
            .order_by(Pengiriman.tanggal_kirim.asc(), Pengiriman.id.asc())
        )
        if lokasi_id is not None:
            draft_kirim_q = draft_kirim_q.where(Pengiriman.lokasi_asal_id == lokasi_id)
        for k in self.db.scalars(draft_kirim_q).all():
            asal_nama = k.lokasi_asal.nama
            tujuan_nama = k.lokasi_tujuan.nama
            tugas.append(
                DashboardTugasItem(
                    jenis="kirim_pengiriman",
                    id=k.id,
                    kode=k.kode,
                    keterangan=f"Draf pengiriman dari {asal_nama} ke {tujuan_nama}",
                    tanggal=str(k.tanggal_kirim),
                )
            )

        return tugas

    def query_aktivitas_terbaru(
        self, lokasi_id: int | None
    ) -> list[DashboardAktivitasItem]:
        dokumen = func.coalesce(
            Transaksi.kode, Pengiriman.kode, Pembelian.kode, Penjualan.kode
        )
        query = (
            select(
                StokMutasi,
                Lokasi.kode,
                Lokasi.nama,
                Produk.sku,
                Produk.nama,
                Produk.satuan,
                User.name,
                dokumen,
            )
            .join(Lokasi, Lokasi.id == StokMutasi.lokasi_id)
            .join(Produk, Produk.id == StokMutasi.produk_id)
            .join(User, User.id == StokMutasi.user_id)
            .outerjoin(Transaksi, Transaksi.id == StokMutasi.transaksi_id)
            .outerjoin(Pengiriman, Pengiriman.id == StokMutasi.pengiriman_id)
            .outerjoin(Pembelian, Pembelian.id == StokMutasi.pembelian_id)
            .outerjoin(Penjualan, Penjualan.id == StokMutasi.penjualan_id)
            .order_by(StokMutasi.created_at.desc(), StokMutasi.id.desc())
            .limit(10)
        )
        if lokasi_id is not None:
            query = query.where(StokMutasi.lokasi_id == lokasi_id)
        rows = self.db.execute(query).all()
        items: list[DashboardAktivitasItem] = []
        for (
            m,
            lokasi_kode,
            lokasi_nama,
            produk_sku,
            produk_nama,
            satuan,
            oleh,
            dok_kode,
        ) in rows:
            items.append(
                DashboardAktivitasItem(
                    id=m.id,
                    waktu=m.created_at,
                    lokasi_kode=lokasi_kode,
                    lokasi_nama=lokasi_nama,
                    produk_sku=produk_sku,
                    produk_nama=produk_nama,
                    satuan=satuan,
                    jenis=m.jenis,
                    perubahan=m.perubahan,
                    stok_sesudah=m.stok_sesudah,
                    dokumen_kode=dok_kode,
                    oleh=oleh or "-",
                )
            )
        return items


class MonitoringService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.lokasi_policy = LokasiPolicy(user)

    def matriks(self, filters: MonitoringFilter) -> MonitoringResponse:
        lokasi_rows = self.db.scalars(
            select(Lokasi).where(Lokasi.aktif.is_(True)).order_by(Lokasi.kode)
        ).all()
        lokasi_headers = [
            MonitoringLokasiHeader(id=lok.id, kode=lok.kode, nama=lok.nama, jenis=lok.jenis)
            for lok in lokasi_rows
        ]
        lokasi_ids = [lok.id for lok in lokasi_rows]

        produk_query = (
            select(Produk)
            .join(Kategori, Kategori.id == Produk.kategori_id)
            .options(joinedload(Produk.kategori))
            .where(Produk.aktif.is_(True))
            .order_by(Produk.sku)
        )
        if filters.kategori_id:
            produk_query = produk_query.where(Produk.kategori_id == filters.kategori_id)
        if filters.jenis:
            produk_query = produk_query.where(Kategori.jenis == filters.jenis)
        if filters.q:
            columns = (Produk.sku, Produk.nama, Produk.merek)
            produk_query = produk_query.where(
                or_(*(CrudService.contains(col, filters.q) for col in columns))
            )
        produk_rows = self.db.scalars(produk_query).all()
        produk_ids = [p.id for p in produk_rows]

        stok_map: dict[tuple[int, int], Stok] = {}
        if lokasi_ids and produk_ids:
            stok_rows = self.db.scalars(
                select(Stok).where(
                    Stok.lokasi_id.in_(lokasi_ids),
                    Stok.produk_id.in_(produk_ids),
                )
            ).all()
            stok_map = {(s.lokasi_id, s.produk_id): s for s in stok_rows}

        baris_list: list[MonitoringBaris] = []
        tot_jumlah_per_lokasi = {lok.id: 0 for lok in lokasi_rows}
        tot_nilai_per_lokasi = {lok.id: 0 for lok in lokasi_rows}

        for prod in produk_rows:
            sel_list: list[MonitoringSel] = []
            recorded_statuses: set[str] = set()
            total_prod = 0
            for lok in lokasi_rows:
                stok = stok_map.get((lok.id, prod.id))
                if stok is not None:
                    jumlah = stok.jumlah
                    minimum = stok.stok_minimum
                    rak = stok.rak
                    status = stok.status_stok.value
                    recorded_statuses.add(status)
                else:
                    jumlah = 0
                    minimum = 0
                    rak = None
                    status = StokStatus.HABIS.value
                nilai_sel = jumlah * prod.harga_beli
                total_prod += jumlah
                sel_list.append(
                    MonitoringSel(
                        lokasi_id=lok.id,
                        jumlah=jumlah,
                        stok_minimum=minimum,
                        rak=rak,
                        status_stok=status,
                        nilai=nilai_sel,
                    )
                )

            if filters.status_stok is not None:
                target_status = filters.status_stok.value
                if target_status not in recorded_statuses:
                    continue

            nilai_prod = total_prod * prod.harga_beli
            for sel in sel_list:
                tot_jumlah_per_lokasi[sel.lokasi_id] += sel.jumlah
                tot_nilai_per_lokasi[sel.lokasi_id] += sel.nilai

            baris_list.append(
                MonitoringBaris(
                    produk=MonitoringProdukInfo(
                        id=prod.id,
                        sku=prod.sku,
                        nama=prod.nama,
                        satuan=prod.satuan,
                        jenis=prod.kategori.jenis,
                        kategori_nama=prod.kategori.nama,
                        harga_beli=prod.harga_beli,
                    ),
                    sel=sel_list,
                    total=total_prod,
                    nilai=nilai_prod,
                )
            )

        total_per_lokasi = [
            MonitoringTotalLokasi(
                lokasi_id=lok.id,
                kode=lok.kode,
                nama=lok.nama,
                jumlah=tot_jumlah_per_lokasi[lok.id],
                nilai=tot_nilai_per_lokasi[lok.id],
            )
            for lok in lokasi_rows
        ]
        total_jumlah = sum(item.jumlah for item in total_per_lokasi)
        total_nilai = sum(item.nilai for item in total_per_lokasi)

        return MonitoringResponse(
            lokasi=lokasi_headers,
            baris=baris_list,
            total_per_lokasi=total_per_lokasi,
            total_jumlah=total_jumlah,
            total_nilai=total_nilai,
        )

    def tren(self, hari: int = 30, lokasi_id: int | None = None) -> TrenResponse:
        if self.user.role == UserRole.ADMIN:
            resolved_lokasi_id = lokasi_id
            if resolved_lokasi_id is not None and self.db.get(Lokasi, resolved_lokasi_id) is None:
                raise NotFound("Lokasi tidak ditemukan")
        else:
            if self.user.lokasi_id is None:
                raise NotFound("Lokasi tidak ditemukan")
            if lokasi_id is not None and not self.lokasi_policy.can_manage(lokasi_id):
                raise NotFound("Lokasi tidak ditemukan")
            resolved_lokasi_id = self.user.lokasi_id

        today = Clock.today()
        start_date = today - timedelta(days=hari - 1)
        wib_date = func.date(func.timezone("Asia/Jakarta", StokMutasi.created_at))

        query = (
            select(
                wib_date.label("tanggal"),
                func.coalesce(
                    func.sum(StokMutasi.perubahan).filter(StokMutasi.perubahan > 0), 0
                ).label("masuk"),
                func.coalesce(
                    -func.sum(StokMutasi.perubahan).filter(StokMutasi.perubahan < 0), 0
                ).label("keluar"),
            )
            .where(wib_date.between(start_date, today))
            .group_by(wib_date)
            .order_by(wib_date)
        )
        if resolved_lokasi_id is not None:
            query = query.where(StokMutasi.lokasi_id == resolved_lokasi_id)

        by_date = {
            row.tanggal: (int(row.masuk or 0), int(row.keluar or 0))
            for row in self.db.execute(query).all()
        }

        data: list[TrenHariItem] = []
        for offset in range(hari):
            day = start_date + timedelta(days=offset)
            masuk, keluar = by_date.get(day, (0, 0))
            data.append(TrenHariItem(tanggal=day, masuk=masuk, keluar=keluar))

        return TrenResponse(hari=hari, lokasi_id=resolved_lokasi_id, data=data)
