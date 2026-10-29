from datetime import date, timedelta

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.clock import Clock
from app.models import (
    Customer,
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
    Transaksi,
    User,
    UserRole,
    UserStatus,
)
from app.schemas.common import LokasiKontakRef
from app.schemas.dashboard import (
    DashboardAktivitasItem,
    DashboardCustomerItem,
    DashboardLokasiItem,
    DashboardResponse,
    DashboardRingkasan,
    DashboardStokKritisItem,
    DashboardTugasItem,
    DeliverymanPengirimanItem,
)
from app.services.base import CrudService, SqlMoney

class DashboardService:
    # ringkasan beranda per peran: admin semua lokasi, manager lokasinya, deliveryman tugasnya
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user

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

        sku_aktif = self.scalar_int(select(func.count(Produk.id)).where(Produk.aktif.is_(True)))
        permintaan_menunggu = self.scalar_int(
            select(func.count(Permintaan.id)).where(Permintaan.status == PermintaanStatus.DIAJUKAN)
        )
        pengiriman_dalam_perjalanan = self.scalar_int(
            select(func.count(Pengiriman.id)).where(Pengiriman.status == PengirimanStatus.DIKIRIM)
        )
        akun_menunggu = self.scalar_int(
            select(func.count(User.id)).where(User.status == UserStatus.MENUNGGU)
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
        lokasi_item = per_lokasi[0] if per_lokasi else None

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
        permintaan_menunggu = self.scalar_int(permintaan_query)

        pengiriman_dalam_perjalanan = self.scalar_int(
            select(func.count(Pengiriman.id)).where(
                Pengiriman.status == PengirimanStatus.DIKIRIM,
                or_(
                    Pengiriman.lokasi_asal_id == lokasi_id,
                    Pengiriman.lokasi_tujuan_id == lokasi_id,
                ),
            )
        )

        masuk_hari_ini, keluar_hari_ini = self.query_mutasi_hari_ini(today, lokasi_id=lokasi_id)

        ringkasan = DashboardRingkasan(
            nilai_persediaan=lokasi_item.nilai if lokasi_item else 0,
            nilai_dalam_perjalanan=nilai_dalam_perjalanan,
            nilai_po_terbuka=nilai_po_terbuka,
            omzet_30_hari=lokasi_item.omzet_30_hari if lokasi_item else 0,
            nota_30_hari=lokasi_item.nota_30_hari if lokasi_item else 0,
            sku_aktif=lokasi_item.sku_ada if lokasi_item else 0,
            stok_menipis=lokasi_item.menipis if lokasi_item else 0,
            stok_habis=lokasi_item.habis if lokasi_item else 0,
            permintaan_menunggu=permintaan_menunggu,
            pengiriman_dalam_perjalanan=pengiriman_dalam_perjalanan,
            akun_menunggu=0,
            masuk_hari_ini=masuk_hari_ini,
            keluar_hari_ini=keluar_hari_ini,
        )

        return DashboardResponse(
            peran=self.user.role,
            lokasi=LokasiKontakRef.model_validate(lokasi) if lokasi else None,
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
        return DeliverymanPengirimanItem(
            id=pengiriman.id,
            kode=pengiriman.kode,
            status=pengiriman.status,
            tanggal_kirim=pengiriman.tanggal_kirim,
            lokasi_asal=LokasiKontakRef.model_validate(pengiriman.lokasi_asal),
            lokasi_tujuan=LokasiKontakRef.model_validate(pengiriman.lokasi_tujuan),
            kendaraan_jenis=pengiriman.kendaraan_jenis,
            kendaraan_nomor=pengiriman.kendaraan_nomor,
            jumlah_item=len(pengiriman.detail),
            total_unit=total_unit,
            catatan=pengiriman.catatan,
            dikirim_pada=pengiriman.dikirim_pada,
            diterima_pada=pengiriman.diterima_pada,
        )

    def scalar_int(self, query: Select) -> int:
        return int(self.db.scalar(query) or 0)

    def query_per_lokasi(
        self, since: date, today: date, lokasi_id: int | None
    ) -> list[DashboardLokasiItem]:
        # nilai persediaan dan status stok per lokasi (Desain Database 8.2)
        stok_query = (
            select(
                Lokasi,
                func.count().filter(Stok.jumlah > 0).label("sku_ada"),
                func.count()
                .filter(Stok.jumlah > 0, Stok.jumlah <= Stok.stok_minimum)
                .label("menipis"),
                func.count().filter(Stok.jumlah == 0).label("habis"),
                SqlMoney.total(Stok.jumlah, Produk.harga_beli).label("nilai"),
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

        # omzet dan jumlah nota 30 hari per lokasi (Desain Database 8.6)
        omzet_query = (
            select(
                Lokasi.id.label("lokasi_id"),
                func.count(func.distinct(Penjualan.id)).label("nota"),
                SqlMoney.total(PenjualanDetail.jumlah, PenjualanDetail.harga_satuan).label(
                    "omzet"
                ),
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
        for lokasi, sku_ada, menipis, habis, nilai in stok_rows:
            nota, omzet = omzet_map.get(lokasi.id, (0, 0))
            result.append(
                DashboardLokasiItem(
                    id=lokasi.id,
                    kode=lokasi.kode,
                    nama=lokasi.nama,
                    jenis=lokasi.jenis,
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
        # nilai barang dalam pengiriman berstatus dikirim (Desain Database 8.4)
        query = (
            select(
                SqlMoney.total(PengirimanDetail.jumlah_dikirim, Produk.harga_beli)
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
        return self.scalar_int(query)

    def query_nilai_po_terbuka(self, lokasi_id: int | None) -> int:
        # nilai pesanan pembelian berstatus dipesan (Desain Database 8.4)
        query = (
            select(
                SqlMoney.total(PembelianDetail.jumlah, PembelianDetail.harga_satuan)
            )
            .select_from(Pembelian)
            .join(PembelianDetail, PembelianDetail.pembelian_id == Pembelian.id)
            .where(Pembelian.status == PembelianStatus.DIPESAN)
        )
        if lokasi_id is not None:
            query = query.where(Pembelian.lokasi_id == lokasi_id)
        return self.scalar_int(query)

    def query_mutasi_hari_ini(self, today: date, lokasi_id: int | None) -> tuple[int, int]:
        wib_date = CrudService.local_date(StokMutasi.created_at)
        query = select(
            func.coalesce(func.sum(StokMutasi.perubahan).filter(StokMutasi.perubahan > 0), 0),
            func.coalesce(-func.sum(StokMutasi.perubahan).filter(StokMutasi.perubahan < 0), 0),
        ).where(wib_date == today)
        if lokasi_id is not None:
            query = query.where(StokMutasi.lokasi_id == lokasi_id)
        masuk, keluar = self.db.execute(query).one()
        return int(masuk or 0), int(keluar or 0)

    def query_customer_teratas(
        self, since: date, today: date, lokasi_id: int | None
    ) -> list[DashboardCustomerItem]:
        # 5 customer teratas dari penjualan diposting 30 hari terakhir (Desain Database 8.6)
        total_column = SqlMoney.total(PenjualanDetail.jumlah, PenjualanDetail.harga_satuan)
        total_column = total_column.label("total")
        nota_column = func.count(func.distinct(Penjualan.id)).label("nota")
        query = (
            select(
                Customer.id.label("id"),
                func.coalesce(Customer.nama, "Umum").label("nama"),
                Customer.jenis.label("jenis"),
                nota_column,
                total_column,
            )
            .select_from(Penjualan)
            .join(PenjualanDetail, PenjualanDetail.penjualan_id == Penjualan.id)
            .outerjoin(Customer, Customer.id == Penjualan.customer_id)
            .where(
                Penjualan.status == PenjualanStatus.DIPOSTING,
                Penjualan.tanggal.between(since, today),
            )
            .group_by(Customer.id, Customer.nama, Customer.jenis)
            .order_by(total_column.desc(), nota_column.desc())
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
                lokasi_id=lokasi.id,
                lokasi=lokasi.kode,
                lokasi_nama=lokasi.nama,
                produk_id=produk.id,
                sku=produk.sku,
                nama=produk.nama,
                satuan=produk.satuan,
                jumlah=stok.jumlah,
                stok_minimum=stok.stok_minimum,
                status_stok=stok.status_stok.value,
            )
            for stok, lokasi, produk in rows
        ]

    def query_tugas(self, lokasi: Lokasi | None) -> list[DashboardTugasItem]:
        tugas: list[DashboardTugasItem] = []
        is_admin = self.user.role == UserRole.ADMIN
        lokasi_id = lokasi.id if lokasi else None
        is_gudang_utama = is_admin or (
            lokasi is not None and lokasi.jenis == LokasiType.GUDANG_UTAMA
        )

        # pengiriman masuk berstatus dikirim yang menunggu konfirmasi terima
        incoming_query = (
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
            incoming_query = incoming_query.where(Pengiriman.lokasi_tujuan_id == lokasi_id)
        for pengiriman in self.db.scalars(incoming_query).all():
            asal_nama = pengiriman.lokasi_asal.nama
            tujuan_nama = pengiriman.lokasi_tujuan.nama
            jumlah_produk = len(pengiriman.detail)
            tugas.append(
                DashboardTugasItem(
                    jenis="terima_pengiriman",
                    id=pengiriman.id,
                    kode=pengiriman.kode,
                    keterangan=(
                        f"Kiriman dari {asal_nama} menuju {tujuan_nama} ({jumlah_produk} produk)"
                    ),
                    tanggal=str(pengiriman.tanggal_kirim),
                )
            )

        # permintaan yang menunggu persetujuan gudang utama
        if is_gudang_utama:
            permintaan_query = (
                select(Permintaan)
                .options(
                    joinedload(Permintaan.lokasi_peminta),
                    selectinload(Permintaan.detail),
                )
                .where(Permintaan.status == PermintaanStatus.DIAJUKAN)
                .order_by(Permintaan.created_at.asc())
            )
            for permintaan in self.db.scalars(permintaan_query).all():
                peminta_nama = permintaan.lokasi_peminta.nama
                jumlah_produk = len(permintaan.detail)
                tanggal_butuh = permintaan.tanggal_butuh
                tugas.append(
                    DashboardTugasItem(
                        jenis="proses_permintaan",
                        id=permintaan.id,
                        kode=permintaan.kode,
                        keterangan=f"Permintaan dari {peminta_nama} ({jumlah_produk} produk)",
                        tanggal=str(tanggal_butuh) if tanggal_butuh else None,
                    )
                )

        # PO berstatus dipesan yang menunggu diterima di gudang utama
        if is_gudang_utama:
            po_query = (
                select(Pembelian)
                .options(joinedload(Pembelian.supplier), selectinload(Pembelian.detail))
                .where(Pembelian.status == PembelianStatus.DIPESAN)
                .order_by(Pembelian.tanggal_perkiraan.asc().nulls_last(), Pembelian.id.asc())
            )
            for pembelian in self.db.scalars(po_query).all():
                supplier_nama = pembelian.supplier.nama
                tugas.append(
                    DashboardTugasItem(
                        jenis="terima_pembelian",
                        id=pembelian.id,
                        kode=pembelian.kode,
                        keterangan=f"PO ke {supplier_nama} ({len(pembelian.detail)} produk)",
                        tanggal=str(pembelian.tanggal_perkiraan or pembelian.tanggal_pesan or ""),
                    )
                )

        # draf pengiriman yang menunggu dikirim dari gudang asal
        draft_query = (
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
            draft_query = draft_query.where(Pengiriman.lokasi_asal_id == lokasi_id)
        for pengiriman in self.db.scalars(draft_query).all():
            asal_nama = pengiriman.lokasi_asal.nama
            tujuan_nama = pengiriman.lokasi_tujuan.nama
            tugas.append(
                DashboardTugasItem(
                    jenis="kirim_pengiriman",
                    id=pengiriman.id,
                    kode=pengiriman.kode,
                    keterangan=f"Draf pengiriman dari {asal_nama} ke {tujuan_nama}",
                    tanggal=str(pengiriman.tanggal_kirim),
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
            mutasi,
            lokasi_kode,
            lokasi_nama,
            produk_sku,
            produk_nama,
            satuan,
            oleh,
            dokumen_kode,
        ) in rows:
            items.append(
                DashboardAktivitasItem(
                    id=mutasi.id,
                    waktu=mutasi.created_at,
                    lokasi_kode=lokasi_kode,
                    lokasi_nama=lokasi_nama,
                    produk_sku=produk_sku,
                    produk_nama=produk_nama,
                    satuan=satuan,
                    jenis=mutasi.jenis,
                    perubahan=mutasi.perubahan,
                    stok_sesudah=mutasi.stok_sesudah,
                    dokumen_kode=dokumen_kode,
                    oleh=oleh or "-",
                )
            )
        return items
