from datetime import date, datetime, time, timedelta

from app.core.clock import Clock
from app.models import KendaraanType, TransaksiType
from app.schemas.pembelian import (
    PembelianInput,
    PembelianItemInput,
    PembelianPesanInput,
    PembelianTerimaInput,
    PembelianTerimaItemInput,
)
from app.schemas.pengiriman import (
    PengirimanInput,
    PengirimanItemInput,
    PengirimanKirimInput,
    PengirimanTerimaInput,
    PengirimanTerimaItemInput,
)
from app.schemas.penjualan import PenjualanInput, PenjualanItemInput
from app.schemas.permintaan import (
    PermintaanInput,
    PermintaanItemInput,
    PermintaanSetujuiInput,
    PermintaanSetujuiItemInput,
    PermintaanTolakInput,
)
from app.schemas.stok import StokSettingInput
from app.schemas.transaksi import TransaksiInput, TransaksiItemInput
from app.seeders.base import Seeder
from app.services.pembelian_service import PembelianService
from app.services.pengiriman_service import PengirimanService
from app.services.penjualan_service import PenjualanService
from app.services.permintaan_service import PermintaanService
from app.services.stok_service import StokService
from app.services.transaksi_service import TransaksiService

class RiwayatSeeder(Seeder):
    # riwayat 60 hari: 12 pembelian, 15 permintaan, 25 pengiriman, 40 transaksi dan 60 penjualan
    # seluruhnya dijalankan lewat service agar buku besar stok_mutasi identik dengan saldo stok

    def run(self) -> None:
        self.base_today = Clock.today()
        self.admin = self.context.users["admin@example.com"]
        self.mgr_gu = self.context.users["manager.roastery@example.com"]
        self.mgr_gc1 = self.context.users["manager.barat@example.com"]
        self.mgr_gc2 = self.context.users["manager.timur@example.com"]
        self.mgr_ot1 = self.context.users["manager.pusat@example.com"]
        self.mgr_ot2 = self.context.users["manager.kampus@example.com"]
        self.kurir = self.context.users["kurir@example.com"]

        self.seed_pembelian_and_roasting()
        self.seed_permintaan_and_pengiriman()
        self.seed_branch_and_outlet_transactions()
        self.seed_penjualan()
        self.seed_stok_minimum_and_rak()

    def day(self, days_ago: int, hour: int = 9, minute: int = 0) -> tuple[date, datetime]:
        target_date = self.base_today - timedelta(days=days_ago)
        moment = datetime.combine(target_date, time(hour, minute), tzinfo=Clock.ZONE)
        return target_date, moment

    def sku(self, code: str) -> int:
        return self.context.produk[code].id

    def loc(self, code: str) -> int:
        return self.context.lokasi[code].id

    def sup(self, name: str) -> int:
        return self.context.supplier[name].id

    def cust(self, name: str) -> int:
        return self.context.customer[name].id

    def seed_pembelian_and_roasting(self) -> None:
        # 12 pembelian: 10 PO diterima, 1 PO dipesan dan 1 PO draf
        po_plans = [
            (
                58,
                "CV Biji Hijau Nusantara",
                [
                    ("GB-ARB-GAYO", 180, 118000),
                    ("GB-ARB-KINTAMANI", 140, 123000),
                    ("GB-EXC-MERANTI", 90, 88000),
                ],
                "Kontrak panen awal musim Gayo dan Kintamani",
            ),
            (
                54,
                "PT Kebun Kopi Priangan",
                [
                    ("GB-ARB-PREANGER", 160, 113000),
                    ("GB-LIB-JAMBI", 100, 93000),
                    ("GB-LIB-RANGSANG", 80, 98000),
                ],
                "Pasokan green bean Prianger dan Liberika",
            ),
            (
                50,
                "UD Tani Kopi Temanggung",
                [
                    ("GB-ROB-TEMANGGUNG", 220, 64000),
                    ("GB-ROB-LAMPUNG", 200, 59000),
                ],
                "Pasokan robusta untuk single origin dan house blend",
            ),
            (
                46,
                "PT Alat Seduh Indonesia",
                [
                    ("AL-V60-02", 60, 118000),
                    ("AL-WAVE-185", 40, 345000),
                    ("AL-FRENCH-600", 45, 148000),
                    ("AL-KETTLE-1000", 35, 275000),
                    ("GR-MANUAL-38", 30, 445000),
                ],
                "Stok awal peralatan seduh manual dan grinder",
            ),
            (
                42,
                "PT Alat Seduh Indonesia",
                [
                    ("AL-POUROVER-6", 25, 640000),
                    ("AL-PRESS-AIR", 30, 445000),
                    ("AL-SET-SEDUH", 25, 540000),
                    ("GR-LISTRIK-40", 18, 1180000),
                    ("GR-LISTRIK-64", 10, 3450000),
                ],
                "Stok grinder listrik dan paket seduh",
            ),
            (
                38,
                "PT Alat Seduh Indonesia",
                [
                    ("ME-ESPRESSO-1G", 6, 17800000),
                    ("ME-TAMPER-58", 40, 178000),
                    ("ME-PITCHER-600", 50, 94000),
                    ("ME-TIMBANGAN", 40, 248000),
                    ("ME-KNOCKBOX", 35, 118000),
                ],
                "Peralatan bar espresso dan aksesori kalibrasi",
            ),
            (
                32,
                "CV Kemasan Kopi Mandiri",
                [
                    ("HP-FILTER-V60-100", 120, 44000),
                    ("HP-FILTER-WAVE-100", 90, 54000),
                    ("HP-CUP-8OZ-50", 150, 34000),
                    ("HP-CUP-12OZ-50", 140, 41000),
                    ("HP-PEMBERSIH-MESIN", 60, 108000),
                    ("HP-KANTONG-VALVE-50", 110, 74000),
                ],
                "Pasokan kertas filter, paper cup dan kantong kemasan valve",
            ),
            (
                24,
                "CV Biji Hijau Nusantara",
                [
                    ("GB-ARB-GAYO", 120, 120000),
                    ("GB-ARB-KINTAMANI", 90, 125000),
                    ("GB-EXC-MERANTI", 60, 90000),
                ],
                "Restock green bean Sumatera dan Bali",
            ),
            (
                15,
                "PT Kebun Kopi Priangan",
                [
                    ("GB-ARB-PREANGER", 110, 115000),
                    ("GB-LIB-JAMBI", 70, 95000),
                    ("GB-LIB-RANGSANG", 60, 100000),
                ],
                "Restock green bean Jawa Barat dan Jambi",
            ),
            (
                7,
                "UD Tani Kopi Temanggung",
                [
                    ("GB-ROB-TEMANGGUNG", 130, 65000),
                    ("GB-ROB-LAMPUNG", 120, 60000),
                ],
                "Restock robusta untuk produksi blend bulanan",
            ),
        ]

        service = PembelianService(self.db, self.mgr_gu)
        for days_ago, sup_name, items, note in po_plans:
            tgl_pesan, dt_pesan = self.day(days_ago, 9, 15)
            tgl_tiba, dt_tiba = self.day(days_ago - 1, 14, 30)
            with Clock.at(dt_pesan):
                po = service.create(
                    PembelianInput(
                        supplier_id=self.sup(sup_name),
                        tanggal_perkiraan=tgl_tiba,
                        catatan=note,
                        items=[
                            PembelianItemInput(
                                produk_id=self.sku(sku), jumlah=qty, harga_satuan=price
                            )
                            for sku, qty, price in items
                        ],
                    )
                )
                service.pesan(
                    po.id,
                    PembelianPesanInput(
                        tanggal_pesan=tgl_pesan, tanggal_perkiraan=tgl_tiba
                    ),
                )
            with Clock.at(dt_tiba):
                service.terima(
                    po.id,
                    PembelianTerimaInput(
                        items=[
                            PembelianTerimaItemInput(
                                produk_id=self.sku(sku), jumlah_diterima=qty
                            )
                            for sku, qty, _ in items
                        ]
                    ),
                )

        # PO ke-11 berstatus dipesan sebagai PO terbuka untuk indikator dashboard
        tgl_open, dt_open = self.day(2, 10, 0)
        with Clock.at(dt_open):
            po_open = service.create(
                PembelianInput(
                    supplier_id=self.sup("CV Biji Hijau Nusantara"),
                    tanggal_perkiraan=self.base_today + timedelta(days=4),
                    catatan="Pesanan green bean Gayo dan kemasan untuk bulan depan",
                    items=[
                        PembelianItemInput(
                            produk_id=self.sku("GB-ARB-GAYO"),
                            jumlah=50,
                            harga_satuan=120000,
                        ),
                        PembelianItemInput(
                            produk_id=self.sku("GB-ARB-KINTAMANI"),
                            jumlah=30,
                            harga_satuan=125000,
                        ),
                    ],
                )
            )
            service.pesan(
                po_open.id,
                PembelianPesanInput(
                    tanggal_pesan=tgl_open,
                    tanggal_perkiraan=self.base_today + timedelta(days=4),
                ),
            )

        # PO ke-12 dibiarkan draf
        _, dt_today = self.day(0, 8, 30)
        with Clock.at(dt_today):
            service.create(
                PembelianInput(
                    supplier_id=self.sup("CV Kemasan Kopi Mandiri"),
                    tanggal_perkiraan=self.base_today + timedelta(days=7),
                    catatan="Rencana pembelian filter dan paper cup kuartal depan",
                    items=[
                        PembelianItemInput(
                            produk_id=self.sku("HP-FILTER-V60-100"),
                            jumlah=40,
                            harga_satuan=45000,
                        ),
                        PembelianItemInput(
                            produk_id=self.sku("HP-CUP-8OZ-50"),
                            jumlah=60,
                            harga_satuan=35000,
                        ),
                    ],
                )
            )

        # 12 pasang roasting di GU-01: keluar green bean lalu masuk roasted bean (24 transaksi)
        roast_batches = [
            (
                52,
                [("GB-ARB-GAYO", 32), ("GB-ARB-KINTAMANI", 20), ("GB-ROB-TEMANGGUNG", 28)],
                [
                    ("BK-ARB-GAYO-200", 110),
                    ("BK-ARB-GAYO-1000", 18),
                    ("BK-ARB-KINTAMANI-200", 85),
                    ("BK-ROB-TEMANGGUNG-200", 110),
                ],
                "Batch roasting #01 single origin Sumatera, Bali dan Jawa",
            ),
            (
                48,
                [("GB-ARB-PREANGER", 28), ("GB-EXC-MERANTI", 16), ("GB-LIB-JAMBI", 18)],
                [
                    ("BK-ARB-PREANGER-250", 90),
                    ("BK-EXC-MERANTI-200", 65),
                    ("BK-LIB-JAMBI-100", 70),
                    ("BK-LIB-JAMBI-200", 55),
                ],
                "Batch roasting #02 Preanger, Excelsa dan Liberika",
            ),
            (
                44,
                [("GB-ROB-LAMPUNG", 35), ("GB-ARB-GAYO", 24), ("GB-ROB-TEMANGGUNG", 24)],
                [
                    ("BK-ROB-LAMPUNG-500", 60),
                    ("BK-BLD-HOUSE-250", 110),
                    ("BK-BLD-HOUSE-1000", 30),
                    ("BK-BLD-ESPRESSO-500", 55),
                    ("BK-BLD-SUSU-1000", 35),
                ],
                "Batch roasting #03 produksi House Blend dan Espresso Blend",
            ),
            (
                39,
                [("GB-ARB-GAYO", 25), ("GB-ARB-KINTAMANI", 18)],
                [
                    ("BK-ARB-GAYO-200", 95),
                    ("BK-ARB-GAYO-1000", 14),
                    ("BK-ARB-KINTAMANI-200", 75),
                ],
                "Batch roasting #04 Gayo dan Kintamani",
            ),
            (
                34,
                [("GB-ARB-PREANGER", 22), ("GB-ROB-TEMANGGUNG", 22), ("GB-ROB-LAMPUNG", 24)],
                [
                    ("BK-ARB-PREANGER-250", 75),
                    ("BK-ROB-TEMANGGUNG-200", 85),
                    ("BK-ROB-LAMPUNG-500", 42),
                ],
                "Batch roasting #05 Preanger dan Robusta",
            ),
            (
                29,
                [("GB-ARB-GAYO", 20), ("GB-ROB-LAMPUNG", 22)],
                [
                    ("BK-BLD-HOUSE-250", 85),
                    ("BK-BLD-HOUSE-1000", 22),
                    ("BK-BLD-ESPRESSO-500", 40),
                    ("BK-BLD-SUSU-1000", 25),
                ],
                "Batch roasting #06 blend reguler kafe dan outlet",
            ),
            (
                23,
                [("GB-EXC-MERANTI", 14), ("GB-LIB-JAMBI", 14), ("GB-LIB-RANGSANG", 12)],
                [
                    ("BK-EXC-MERANTI-200", 55),
                    ("BK-LIB-JAMBI-100", 60),
                    ("BK-LIB-JAMBI-200", 50),
                ],
                "Batch roasting #07 varian nusantara",
            ),
            (
                18,
                [("GB-ARB-GAYO", 24), ("GB-ARB-KINTAMANI", 16), ("GB-ARB-PREANGER", 18)],
                [
                    ("BK-ARB-GAYO-200", 90),
                    ("BK-ARB-GAYO-1000", 12),
                    ("BK-ARB-KINTAMANI-200", 65),
                    ("BK-ARB-PREANGER-250", 60),
                ],
                "Batch roasting #08 arabika pilihan",
            ),
            (
                13,
                [("GB-ROB-TEMANGGUNG", 20), ("GB-ROB-LAMPUNG", 20)],
                [
                    ("BK-ROB-TEMANGGUNG-200", 75),
                    ("BK-ROB-LAMPUNG-500", 35),
                    ("BK-BLD-HOUSE-250", 70),
                    ("BK-BLD-ESPRESSO-500", 35),
                ],
                "Batch roasting #09 robusta dan blend",
            ),
            (
                9,
                [("GB-ARB-GAYO", 18), ("GB-ROB-LAMPUNG", 18)],
                [
                    ("BK-BLD-HOUSE-1000", 20),
                    ("BK-BLD-SUSU-1000", 22),
                    ("BK-ARB-GAYO-200", 60),
                ],
                "Batch roasting #10 kebutuhan grosir kafe",
            ),
            (
                5,
                [("GB-ARB-KINTAMANI", 14), ("GB-ARB-PREANGER", 14)],
                [
                    ("BK-ARB-KINTAMANI-200", 55),
                    ("BK-ARB-PREANGER-250", 50),
                ],
                "Batch roasting #11 pekan berjalan",
            ),
            (
                2,
                [("GB-ARB-GAYO", 16), ("GB-ROB-TEMANGGUNG", 16)],
                [
                    ("BK-ARB-GAYO-200", 65),
                    ("BK-BLD-HOUSE-250", 60),
                ],
                "Batch roasting #12 stok segar roastery",
            ),
        ]

        tx_gu = TransaksiService(self.db, self.mgr_gu)
        for days_ago, green_items, roast_items, ket in roast_batches:
            tgl, dt_out = self.day(days_ago, 10, 0)
            _, dt_in = self.day(days_ago, 15, 0)
            with Clock.at(dt_out):
                keluar = tx_gu.create(
                    TransaksiInput(
                        jenis=TransaksiType.KELUAR,
                        tanggal=tgl,
                        alasan="roasting",
                        keterangan=f"{ket} (bahan green bean)",
                        items=[
                            TransaksiItemInput(produk_id=self.sku(sku), jumlah=qty)
                            for sku, qty in green_items
                        ],
                    )
                )
                tx_gu.posting(keluar.id)
            with Clock.at(dt_in):
                masuk = tx_gu.create(
                    TransaksiInput(
                        jenis=TransaksiType.MASUK,
                        tanggal=tgl,
                        alasan="hasil_roasting",
                        keterangan=f"{ket} (hasil sangrai)",
                        items=[
                            TransaksiItemInput(produk_id=self.sku(sku), jumlah=qty)
                            for sku, qty in roast_items
                        ],
                    )
                )
                tx_gu.posting(masuk.id)

    def seed_permintaan_and_pengiriman(self) -> None:
        # 15 permintaan (10 selesai, 1 dikirim, 1 draf pengiriman, 2 diajukan, 1 ditolak)
        # ditambah 13 pengiriman langsung sehingga total pengiriman 25
        pm_gu = PermintaanService(self.db, self.mgr_gu)
        kr_gu = PengirimanService(self.db, self.mgr_gu)

        completed_requests = [
            (
                45,
                self.mgr_gc1,
                "GC-01",
                [
                    ("BK-ARB-GAYO-200", 40, 40, 40),
                    ("BK-ARB-GAYO-1000", 8, 8, 8),
                    ("BK-BLD-HOUSE-250", 45, 45, 45),
                    ("BK-BLD-HOUSE-1000", 12, 12, 12),
                    ("AL-V60-02", 12, 12, 12),
                    ("HP-FILTER-V60-100", 25, 25, 25),
                ],
                KendaraanType.MOBIL_BOX,
                "D 8101 TB",
                "Stok awal Gudang Cabang Barat",
            ),
            (
                44,
                self.mgr_gc2,
                "GC-02",
                [
                    ("BK-ARB-KINTAMANI-200", 35, 35, 35),
                    ("BK-ARB-PREANGER-250", 35, 35, 35),
                    ("BK-BLD-ESPRESSO-500", 25, 25, 25),
                    ("BK-BLD-SUSU-1000", 14, 14, 14),
                    ("AL-FRENCH-600", 10, 10, 10),
                    ("HP-KANTONG-VALVE-50", 20, 20, 20),
                ],
                KendaraanType.MOBIL_BOX,
                "D 8102 TB",
                "Stok awal Gudang Cabang Timur",
            ),
            (
                41,
                self.mgr_ot1,
                "OT-01",
                [
                    ("BK-ARB-GAYO-200", 35, 35, 35),
                    ("BK-ARB-KINTAMANI-200", 30, 30, 30),
                    ("BK-BLD-HOUSE-250", 35, 35, 35),
                    ("HP-CUP-8OZ-50", 25, 25, 25),
                    ("HP-CUP-12OZ-50", 25, 25, 25),
                    ("AL-V60-02", 16, 16, 16),
                ],
                KendaraanType.VAN,
                "D 8201 TB",
                "Supply awal Outlet Pusat Kota",
            ),
            (
                40,
                self.mgr_ot2,
                "OT-02",
                [
                    ("BK-ARB-PREANGER-250", 35, 35, 35),
                    ("BK-ROB-TEMANGGUNG-200", 35, 35, 35),
                    ("BK-BLD-HOUSE-250", 35, 35, 35),
                    ("HP-CUP-8OZ-50", 25, 25, 25),
                    ("HP-FILTER-V60-100", 20, 20, 20),
                ],
                KendaraanType.VAN,
                "D 8202 TB",
                "Supply awal Outlet Kampus",
            ),
            (
                33,
                self.admin,
                "OT-03",
                [
                    ("BK-ARB-GAYO-200", 35, 35, 35),
                    ("BK-BLD-ESPRESSO-500", 25, 25, 25),
                    ("BK-ROB-LAMPUNG-500", 25, 25, 25),
                    ("HP-CUP-8OZ-50", 20, 20, 20),
                    ("HP-CUP-12OZ-50", 20, 20, 20),
                ],
                KendaraanType.PICKUP,
                "D 8301 TB",
                "Supply awal Outlet Stasiun",
            ),
            (
                26,
                self.mgr_gc1,
                "GC-01",
                [
                    ("BK-EXC-MERANTI-200", 24, 24, 24),
                    ("BK-LIB-JAMBI-200", 20, 20, 20),
                    ("GR-MANUAL-38", 6, 6, 6),
                    ("ME-TIMBANGAN", 8, 8, 8),
                ],
                KendaraanType.MOBIL_BOX,
                "D 8101 TB",
                "Restock varian nusantara dan alat seduh GC Barat",
            ),
            (
                21,
                self.mgr_ot1,
                "OT-01",
                [
                    # contoh penerimaan dengan selisih 1 pack
                    ("BK-ARB-GAYO-200", 25, 25, 24),
                    ("BK-ARB-PREANGER-250", 20, 20, 20),
                    ("ME-PITCHER-600", 6, 6, 6),
                ],
                KendaraanType.VAN,
                "D 8201 TB",
                "Penambahan stok biji kopi akhir pekan",
            ),
            (
                16,
                self.mgr_gc2,
                "GC-02",
                [
                    ("BK-ARB-GAYO-200", 30, 28, 28),
                    ("BK-ROB-TEMANGGUNG-200", 30, 30, 30),
                    ("AL-KETTLE-1000", 6, 6, 6),
                ],
                KendaraanType.MOBIL_BOX,
                "D 8102 TB",
                "Restock mingguan Gudang Cabang Timur",
            ),
            (
                11,
                self.mgr_ot2,
                "OT-02",
                [
                    ("BK-ARB-KINTAMANI-200", 20, 20, 19),
                    ("BK-BLD-ESPRESSO-500", 14, 14, 14),
                ],
                KendaraanType.MOTOR,
                "D 4512 KC",
                "Restock biji kopi Outlet Kampus",
            ),
            (
                6,
                self.admin,
                "OT-03",
                [
                    ("BK-BLD-HOUSE-250", 22, 22, 22),
                    ("HP-FILTER-V60-100", 12, 12, 12),
                ],
                KendaraanType.MOTOR,
                "D 4512 KC",
                "Restock mingguan Outlet Stasiun",
            ),
        ]

        for days_ago, req_user, loc_code, items, v_type, v_plate, note in completed_requests:
            tgl_req, dt_req = self.day(days_ago, 9, 0)
            tgl_kirim, dt_kirim = self.day(days_ago, 13, 0)
            _, dt_terima = self.day(days_ago - 1, 10, 30)
            req_service = PermintaanService(self.db, req_user)
            with Clock.at(dt_req):
                pm = req_service.create(
                    PermintaanInput(
                        lokasi_peminta_id=(
                            self.loc(loc_code) if req_user == self.admin else None
                        ),
                        tanggal_butuh=tgl_req + timedelta(days=2),
                        catatan=note,
                        items=[
                            PermintaanItemInput(
                                produk_id=self.sku(sku), jumlah_diminta=diminta
                            )
                            for sku, diminta, _, _ in items
                        ],
                    )
                )
            with Clock.at(dt_kirim):
                approved = pm_gu.setujui(
                    pm.id,
                    PermintaanSetujuiInput(
                        tanggal_kirim=tgl_kirim,
                        items=[
                            PermintaanSetujuiItemInput(
                                produk_id=self.sku(sku), jumlah_disetujui=disetujui
                            )
                            for sku, _, disetujui, _ in items
                        ],
                    ),
                )
                kr_id = approved.pengiriman.id
                kr_gu.kirim(
                    kr_id,
                    PengirimanKirimInput(
                        deliveryman_id=self.kurir.id,
                        kendaraan_jenis=v_type,
                        kendaraan_nomor=v_plate,
                    ),
                )
            rec_service = PengirimanService(self.db, req_user)
            with Clock.at(dt_terima):
                rec_service.terima(
                    kr_id,
                    PengirimanTerimaInput(
                        catatan_penerimaan="Barang telah diperiksa di lokasi tujuan",
                        items=[
                            PengirimanTerimaItemInput(
                                produk_id=self.sku(sku),
                                jumlah_diterima=diterima,
                                catatan=(
                                    "1 kemasan penyok saat bongkar muat"
                                    if diterima < disetujui
                                    else None
                                ),
                            )
                            for sku, _, disetujui, diterima in items
                        ],
                    ),
                )

        # permintaan ke-11 disetujui dan pengirimannya masih dalam perjalanan
        tgl_11, dt_11 = self.day(1, 10, 0)
        with Clock.at(dt_11):
            pm_transit = PermintaanService(self.db, self.mgr_ot1).create(
                PermintaanInput(
                    tanggal_butuh=self.base_today + timedelta(days=1),
                    catatan="Tambahan stok Arabika Gayo dan V60 untuk akhir pekan",
                    items=[
                        PermintaanItemInput(
                            produk_id=self.sku("BK-ARB-GAYO-200"), jumlah_diminta=15
                        ),
                        PermintaanItemInput(
                            produk_id=self.sku("AL-V60-02"), jumlah_diminta=4
                        ),
                    ],
                )
            )
            approved_transit = pm_gu.setujui(
                pm_transit.id,
                PermintaanSetujuiInput(
                    tanggal_kirim=tgl_11,
                    items=[
                        PermintaanSetujuiItemInput(
                            produk_id=self.sku("BK-ARB-GAYO-200"),
                            jumlah_disetujui=15,
                        ),
                        PermintaanSetujuiItemInput(
                            produk_id=self.sku("AL-V60-02"), jumlah_disetujui=4
                        ),
                    ],
                ),
            )
            kr_gu.kirim(
                approved_transit.pengiriman.id,
                PengirimanKirimInput(
                    deliveryman_id=self.kurir.id,
                    kendaraan_jenis=KendaraanType.VAN,
                    kendaraan_nomor="D 8201 TB",
                ),
            )

        # permintaan ke-12 disetujui tetapi pengirimannya masih draf
        tgl_12, dt_12 = self.day(0, 9, 0)
        with Clock.at(dt_12):
            pm_draf_kr = PermintaanService(self.db, self.mgr_ot2).create(
                PermintaanInput(
                    tanggal_butuh=self.base_today + timedelta(days=2),
                    catatan="Persiapan acara seduh bersama mahasiswa",
                    items=[
                        PermintaanItemInput(
                            produk_id=self.sku("BK-ARB-KINTAMANI-200"),
                            jumlah_diminta=12,
                        ),
                        PermintaanItemInput(
                            produk_id=self.sku("HP-FILTER-V60-100"), jumlah_diminta=8
                        ),
                    ],
                )
            )
            pm_gu.setujui(
                pm_draf_kr.id,
                PermintaanSetujuiInput(
                    tanggal_kirim=tgl_12,
                    items=[
                        PermintaanSetujuiItemInput(
                            produk_id=self.sku("BK-ARB-KINTAMANI-200"),
                            jumlah_disetujui=12,
                        ),
                        PermintaanSetujuiItemInput(
                            produk_id=self.sku("HP-FILTER-V60-100"),
                            jumlah_disetujui=8,
                        ),
                    ],
                ),
            )

        # permintaan ke-13 dan ke-14 masih diajukan, menunggu persetujuan GU-01
        _, dt_13 = self.day(1, 14, 0)
        with Clock.at(dt_13):
            PermintaanService(self.db, self.mgr_gc1).create(
                PermintaanInput(
                    tanggal_butuh=self.base_today + timedelta(days=3),
                    catatan="Permintaan stok kafe langganan wilayah Cimahi",
                    items=[
                        PermintaanItemInput(
                            produk_id=self.sku("BK-BLD-HOUSE-1000"), jumlah_diminta=10
                        ),
                        PermintaanItemInput(
                            produk_id=self.sku("BK-BLD-SUSU-1000"), jumlah_diminta=8
                        ),
                    ],
                )
            )
        _, dt_14 = self.day(0, 10, 15)
        with Clock.at(dt_14):
            PermintaanService(self.db, self.mgr_ot1).create(
                PermintaanInput(
                    tanggal_butuh=self.base_today + timedelta(days=2),
                    catatan="Stok paper cup dan liberika untuk promo",
                    items=[
                        PermintaanItemInput(
                            produk_id=self.sku("BK-LIB-JAMBI-100"), jumlah_diminta=15
                        ),
                        PermintaanItemInput(
                            produk_id=self.sku("HP-CUP-8OZ-50"), jumlah_diminta=10
                        ),
                    ],
                )
            )

        # permintaan ke-15 ditolak
        _, dt_15 = self.day(14, 11, 0)
        with Clock.at(dt_15):
            pm_tolak = PermintaanService(self.db, self.mgr_ot2).create(
                PermintaanInput(
                    tanggal_butuh=(self.base_today - timedelta(days=12)),
                    catatan="Permintaan mesin espresso cadangan",
                    items=[
                        PermintaanItemInput(
                            produk_id=self.sku("ME-ESPRESSO-1G"), jumlah_diminta=2
                        )
                    ],
                )
            )
            pm_gu.tolak(
                pm_tolak.id,
                PermintaanTolakInput(
                    alasan_penolakan="Stok mesin espresso di gudang utama dialokasikan untuk pembukaan cabang"
                ),
            )

        # 13 pengiriman langsung: 11 diterima, 1 dikirim dan 1 draf
        direct_shipments = [
            (
                37,
                self.mgr_gu,
                self.mgr_gc1,
                "GC-01",
                [("AL-WAVE-185", 8), ("AL-KETTLE-1000", 6), ("ME-TAMPER-58", 8)],
                KendaraanType.MOBIL_BOX,
                "D 8101 TB",
                "Distribusi peralatan bar ke Gudang Cabang Barat",
            ),
            (
                36,
                self.mgr_gu,
                self.mgr_gc2,
                "GC-02",
                [("AL-WAVE-185", 8), ("GR-MANUAL-38", 6), ("ME-PITCHER-600", 10)],
                KendaraanType.MOBIL_BOX,
                "D 8102 TB",
                "Distribusi peralatan bar ke Gudang Cabang Timur",
            ),
            (
                31,
                self.mgr_gu,
                self.mgr_ot1,
                "OT-01",
                [("AL-FRENCH-600", 6), ("AL-PRESS-AIR", 5), ("GR-MANUAL-38", 4)],
                KendaraanType.VAN,
                "D 8201 TB",
                "Penempatan peralatan display Outlet Pusat Kota",
            ),
            (
                30,
                self.mgr_gu,
                self.mgr_ot2,
                "OT-02",
                [("AL-V60-02", 8), ("AL-FRENCH-600", 5), ("ME-TIMBANGAN", 4)],
                KendaraanType.VAN,
                "D 8202 TB",
                "Penempatan peralatan display Outlet Kampus",
            ),
            (
                28,
                self.mgr_gu,
                self.admin,
                "OT-03",
                [("AL-V60-02", 6), ("ME-PITCHER-600", 6), ("ME-KNOCKBOX", 4)],
                KendaraanType.PICKUP,
                "D 8301 TB",
                "Perlengkapan bar Outlet Stasiun",
            ),
            (
                24,
                self.mgr_gc1,
                self.mgr_ot2,
                "OT-02",
                [("BK-ARB-GAYO-200", 10), ("BK-BLD-HOUSE-250", 10)],
                KendaraanType.MOTOR,
                "D 4512 KC",
                "Transfer stok cepat dari GC Barat ke Outlet Kampus",
            ),
            (
                20,
                self.mgr_gc2,
                self.admin,
                "OT-03",
                [("BK-ARB-KINTAMANI-200", 10), ("BK-ARB-PREANGER-250", 10)],
                KendaraanType.MOTOR,
                "D 4512 KC",
                "Transfer stok dari GC Timur ke Outlet Stasiun",
            ),
            (
                17,
                self.mgr_gu,
                self.mgr_gc1,
                "GC-01",
                [("BK-ARB-GAYO-200", 25), ("BK-ROB-LAMPUNG-500", 15)],
                KendaraanType.MOBIL_BOX,
                "D 8101 TB",
                "Pengiriman rutin ke Gudang Cabang Barat",
            ),
            (
                12,
                self.mgr_gu,
                self.mgr_gc2,
                "GC-02",
                [("BK-BLD-HOUSE-250", 25), ("BK-EXC-MERANTI-200", 15)],
                KendaraanType.MOBIL_BOX,
                "D 8102 TB",
                "Pengiriman rutin ke Gudang Cabang Timur",
            ),
            (
                8,
                self.mgr_gu,
                self.mgr_ot1,
                "OT-01",
                [("BK-LIB-JAMBI-100", 18), ("BK-LIB-JAMBI-200", 15)],
                KendaraanType.VAN,
                "D 8201 TB",
                "Distribusi edisi Liberika ke Outlet Pusat Kota",
            ),
            (
                4,
                self.mgr_gu,
                self.mgr_ot2,
                "OT-02",
                [("BK-ARB-GAYO-200", 16), ("HP-CUP-12OZ-50", 12)],
                KendaraanType.VAN,
                "D 8202 TB",
                "Pengiriman rutin ke Outlet Kampus",
            ),
        ]

        for days_ago, sender, receiver, dest_code, items, v_type, v_plate, note in direct_shipments:
            tgl, dt_send = self.day(days_ago, 11, 0)
            _, dt_rec = self.day(days_ago - 1, 15, 0)
            send_service = PengirimanService(self.db, sender)
            rec_service = PengirimanService(self.db, receiver)
            with Clock.at(dt_send):
                kr = send_service.create(
                    PengirimanInput(
                        lokasi_tujuan_id=self.loc(dest_code),
                        tanggal_kirim=tgl,
                        deliveryman_id=self.kurir.id,
                        kendaraan_jenis=v_type,
                        kendaraan_nomor=v_plate,
                        catatan=note,
                        items=[
                            PengirimanItemInput(
                                produk_id=self.sku(sku), jumlah_dikirim=qty
                            )
                            for sku, qty in items
                        ],
                    )
                )
                send_service.kirim(kr.id)
            with Clock.at(dt_rec):
                rec_service.terima(
                    kr.id,
                    PengirimanTerimaInput(
                        catatan_penerimaan="Diterima lengkap",
                        items=[
                            PengirimanTerimaItemInput(
                                produk_id=self.sku(sku), jumlah_diterima=qty
                            )
                            for sku, qty in items
                        ],
                    ),
                )

        # pengiriman langsung ke-12 masih dalam perjalanan ke GC-01
        tgl_kr12, dt_kr12 = self.day(1, 15, 30)
        with Clock.at(dt_kr12):
            kr_transit2 = kr_gu.create(
                PengirimanInput(
                    lokasi_tujuan_id=self.loc("GC-01"),
                    tanggal_kirim=tgl_kr12,
                    deliveryman_id=self.kurir.id,
                    kendaraan_jenis=KendaraanType.MOBIL_BOX,
                    kendaraan_nomor="D 8101 TB",
                    catatan="Restock produk blend dan grinder ke Gudang Cabang Barat",
                    items=[
                        PengirimanItemInput(
                            produk_id=self.sku("BK-BLD-HOUSE-250"), jumlah_dikirim=20
                        ),
                        PengirimanItemInput(
                            produk_id=self.sku("GR-LISTRIK-40"), jumlah_dikirim=2
                        ),
                    ],
                )
            )
            kr_gu.kirim(kr_transit2.id)

        # pengiriman langsung ke-13 dibiarkan draf
        tgl_kr13, dt_kr13 = self.day(0, 11, 0)
        with Clock.at(dt_kr13):
            kr_gu.create(
                PengirimanInput(
                    lokasi_tujuan_id=self.loc("GC-02"),
                    tanggal_kirim=tgl_kr13,
                    catatan="Rencana distribusi alat seduh minggu depan",
                    items=[
                        PengirimanItemInput(
                            produk_id=self.sku("AL-POUROVER-6"), jumlah_dikirim=4
                        ),
                        PengirimanItemInput(
                            produk_id=self.sku("HP-FILTER-WAVE-100"), jumlah_dikirim=15
                        ),
                    ],
                )
            )

    def seed_branch_and_outlet_transactions(self) -> None:
        # 16 transaksi operasional (14 diposting, 2 draf) melengkapi 24 roasting menjadi 40
        tx_plans = [
            (
                38,
                self.mgr_gu,
                None,
                TransaksiType.KELUAR,
                "sampel",
                "Sampel cupping untuk calon pembeli kafe",
                [("BK-ARB-GAYO-200", 3), ("BK-ARB-KINTAMANI-200", 3)],
            ),
            (
                35,
                self.mgr_ot1,
                None,
                TransaksiType.KELUAR,
                "pemakaian",
                "Pemakaian paper cup dan filter untuk bar harian",
                [("HP-CUP-8OZ-50", 3), ("HP-CUP-12OZ-50", 2)],
            ),
            (
                32,
                self.mgr_ot2,
                None,
                TransaksiType.KELUAR,
                "pemakaian",
                "Pemakaian bar espresso dan seduh manual",
                [("HP-CUP-8OZ-50", 3), ("HP-FILTER-V60-100", 2)],
            ),
            (
                28,
                self.mgr_gc1,
                None,
                TransaksiType.KELUAR,
                "sampel",
                "Sampel biji kopi untuk prospek reseller Cimahi",
                [("BK-BLD-HOUSE-250", 2)],
            ),
            (
                25,
                self.admin,
                "OT-03",
                TransaksiType.KELUAR,
                "pemakaian",
                "Pemakaian paper cup bar Outlet Stasiun",
                [("HP-CUP-8OZ-50", 3), ("HP-CUP-12OZ-50", 2)],
            ),
            (
                22,
                self.mgr_gu,
                None,
                TransaksiType.PENYESUAIAN,
                "opname",
                "Koreksi stok opname bulanan Gudang Utama",
                [("HP-KANTONG-VALVE-50", -2), ("HP-PEMBERSIH-MESIN", 1)],
            ),
            (
                19,
                self.mgr_ot1,
                None,
                TransaksiType.MASUK,
                "retur",
                "Retur kemasan utuh dari pelanggan yang tukar varian",
                [("BK-ARB-KINTAMANI-200", 1)],
            ),
            (
                16,
                self.mgr_gc2,
                None,
                TransaksiType.PENYESUAIAN,
                "rusak",
                "Kemasan robek saat penataan rak",
                [("BK-ROB-TEMANGGUNG-200", -1)],
            ),
            (
                14,
                self.mgr_ot2,
                None,
                TransaksiType.KELUAR,
                "sampel",
                "Tester seduh gratis acara kampus",
                [("BK-ARB-PREANGER-250", 2)],
            ),
            (
                11,
                self.mgr_gu,
                None,
                TransaksiType.KELUAR,
                "pemakaian",
                "Pemakaian bubuk pembersih mesin roastery dan bar",
                [("HP-PEMBERSIH-MESIN", 2)],
            ),
            (
                8,
                self.mgr_gc1,
                None,
                TransaksiType.MASUK,
                "retur",
                "Retur 1 pack House Blend dari reseller",
                [("BK-BLD-HOUSE-250", 1)],
            ),
            (
                6,
                self.mgr_ot1,
                None,
                TransaksiType.PENYESUAIAN,
                "opname",
                "Penyesuaian hasil stok opname pekan ini",
                [("HP-CUP-8OZ-50", -1)],
            ),
            (
                4,
                self.admin,
                "OT-03",
                TransaksiType.KELUAR,
                "pemakaian",
                "Kalibrasi mesin espresso pagi",
                [("BK-BLD-ESPRESSO-500", 1)],
            ),
            (
                2,
                self.mgr_ot2,
                None,
                TransaksiType.KELUAR,
                "pemakaian",
                "Kebutuhan paper cup bar akhir pekan",
                [("HP-CUP-12OZ-50", 2)],
            ),
        ]

        for days_ago, user, loc_code, jenis, alasan, ket, items in tx_plans:
            tgl, dt_tx = self.day(days_ago, 16, 0)
            service = TransaksiService(self.db, user)
            with Clock.at(dt_tx):
                tx = service.create(
                    TransaksiInput(
                        lokasi_id=self.loc(loc_code) if loc_code else None,
                        jenis=jenis,
                        tanggal=tgl,
                        alasan=alasan,
                        keterangan=ket,
                        items=[
                            TransaksiItemInput(produk_id=self.sku(sku), jumlah=qty)
                            for sku, qty in items
                        ],
                    )
                )
                service.posting(tx.id)

        # 2 transaksi draf, satu di GU-01 dan satu di OT-01
        tgl_today, dt_today = self.day(0, 11, 30)
        with Clock.at(dt_today):
            TransaksiService(self.db, self.mgr_gu).create(
                TransaksiInput(
                    jenis=TransaksiType.KELUAR,
                    tanggal=tgl_today,
                    alasan="sampel",
                    keterangan="Rencana sampel cupping pekan depan",
                    items=[
                        TransaksiItemInput(
                            produk_id=self.sku("BK-EXC-MERANTI-200"), jumlah=2
                        )
                    ],
                )
            )
            TransaksiService(self.db, self.mgr_ot1).create(
                TransaksiInput(
                    jenis=TransaksiType.KELUAR,
                    tanggal=tgl_today,
                    alasan="pemakaian",
                    keterangan="Pemakaian filter V60 shift sore",
                    items=[
                        TransaksiItemInput(
                            produk_id=self.sku("HP-FILTER-V60-100"), jumlah=1
                        )
                    ],
                )
            )

    def seed_penjualan(self) -> None:
        # 60 penjualan (58 diposting, 2 draf) tersebar di semua gudang dan outlet
        # gudang selalu memakai customer aktif, outlet campuran customer terdaftar dan pembeli umum
        gu_catalog = [
            ("BK-ARB-GAYO-1000", 2, 390000),
            ("BK-BLD-HOUSE-1000", 3, 310000),
            ("BK-BLD-SUSU-1000", 3, 270000),
            ("BK-BLD-ESPRESSO-500", 4, 160000),
            ("BK-ARB-PREANGER-250", 5, 105000),
            ("AL-V60-02", 2, 165000),
            ("GR-LISTRIK-40", 1, 1600000),
            ("HP-FILTER-V60-100", 4, 65000),
        ]
        gc1_catalog = [
            ("BK-ARB-GAYO-200", 4, 92000),
            ("BK-BLD-HOUSE-250", 5, 88000),
            ("BK-BLD-HOUSE-1000", 2, 315000),
            ("BK-EXC-MERANTI-200", 3, 85000),
            ("AL-V60-02", 1, 165000),
            ("HP-FILTER-V60-100", 2, 65000),
        ]
        gc2_catalog = [
            ("BK-ARB-KINTAMANI-200", 4, 95000),
            ("BK-ARB-PREANGER-250", 4, 108000),
            ("BK-BLD-ESPRESSO-500", 3, 162000),
            ("BK-BLD-SUSU-1000", 2, 275000),
            ("BK-ROB-TEMANGGUNG-200", 4, 54000),
        ]
        ot1_catalog = [
            ("BK-ARB-GAYO-200", 2, None),
            ("BK-ARB-KINTAMANI-200", 2, None),
            ("BK-BLD-HOUSE-250", 2, None),
            ("BK-ARB-PREANGER-250", 1, None),
            ("BK-LIB-JAMBI-100", 1, None),
            ("AL-V60-02", 1, None),
        ]
        ot2_catalog = [
            ("BK-ARB-PREANGER-250", 2, None),
            ("BK-ROB-TEMANGGUNG-200", 2, None),
            ("BK-BLD-HOUSE-250", 2, None),
            ("BK-ARB-KINTAMANI-200", 1, None),
            ("BK-BLD-ESPRESSO-500", 1, None),
        ]
        ot3_catalog = [
            ("BK-ARB-GAYO-200", 2, None),
            ("BK-BLD-ESPRESSO-500", 1, None),
            ("BK-ROB-LAMPUNG-500", 1, None),
            ("BK-BLD-HOUSE-250", 2, None),
        ]

        warehouse_customers = [
            "Kafe Senja",
            "Kafe Teras Dago",
            "Kedai Kopi Lembang",
            "Toko Oleh-oleh Priangan",
            "Reseller Kopi Cimahi",
            "Komunitas Seduh Bandung",
        ]
        outlet_customers = [
            None,
            None,
            "Pelanggan Perorangan Antapani",
            None,
            "Kafe Senja",
            "Komunitas Seduh Bandung",
        ]

        # 58 jadwal penjualan diposting dari hari -38 sampai hari 0 (mayoritas di 30 hari terakhir)
        locations = [
            (self.mgr_gu, None, gu_catalog, warehouse_customers, "Penjualan grosir roastery"),
            (self.mgr_gc1, None, gc1_catalog, warehouse_customers, "Penjualan cabang barat"),
            (self.mgr_gc2, None, gc2_catalog, warehouse_customers, "Penjualan cabang timur"),
            (self.mgr_ot1, None, ot1_catalog, outlet_customers, "Penjualan eceran Outlet Pusat"),
            (self.mgr_ot2, None, ot2_catalog, outlet_customers, "Penjualan eceran Outlet Kampus"),
            (self.admin, "OT-03", ot3_catalog, outlet_customers, "Penjualan eceran Outlet Stasiun"),
        ]

        for idx in range(58):
            days_ago = max(0, 38 - (idx * 38 // 57))
            visit = idx // len(locations)
            user, loc_code, catalog, cust_pool, note_prefix = locations[idx % len(locations)]
            cust_name = cust_pool[visit % len(cust_pool)]
            item_a = catalog[visit % len(catalog)]
            item_b = catalog[(visit + 1) % len(catalog)]
            chosen = [item_a] if item_a[0] == item_b[0] else [item_a, item_b]

            tgl, dt_sale = self.day(days_ago, 12 + (idx % 6), (idx * 7) % 60)
            service = PenjualanService(self.db, user)
            with Clock.at(dt_sale):
                pj = service.create(
                    PenjualanInput(
                        lokasi_id=self.loc(loc_code) if loc_code else None,
                        tanggal=tgl,
                        customer_id=self.cust(cust_name) if cust_name else None,
                        catatan=f"{note_prefix} #{idx + 1:02d}",
                        items=[
                            PenjualanItemInput(
                                produk_id=self.sku(sku),
                                jumlah=qty,
                                harga_satuan=price,
                            )
                            for sku, qty, price in chosen
                        ],
                    )
                )
                service.posting(pj.id)

        # 2 penjualan draf, satu di GU-01 dan satu di OT-01
        tgl_today, dt_today = self.day(0, 13, 0)
        with Clock.at(dt_today):
            PenjualanService(self.db, self.mgr_gu).create(
                PenjualanInput(
                    tanggal=tgl_today,
                    customer_id=self.cust("Kafe Senja"),
                    catatan="Draf pesanan bulanan Kafe Senja",
                    items=[
                        PenjualanItemInput(
                            produk_id=self.sku("BK-ARB-GAYO-1000"),
                            jumlah=3,
                            harga_satuan=385000,
                        )
                    ],
                )
            )
            PenjualanService(self.db, self.mgr_ot1).create(
                PenjualanInput(
                    tanggal=tgl_today,
                    customer_id=None,
                    catatan="Draf pembelian pelanggan walk-in",
                    items=[
                        PenjualanItemInput(
                            produk_id=self.sku("BK-ARB-GAYO-200"), jumlah=2
                        )
                    ],
                )
            )

    def seed_stok_minimum_and_rak(self) -> None:
        # stok_minimum dan rak per lokasi, sebagian sengaja menipis atau habis untuk demo
        stok_service = StokService(self.db, self.admin)
        settings = [
            # GU-01
            ("GU-01", "GB-ARB-GAYO", 40, "A-01"),
            ("GU-01", "GB-ARB-KINTAMANI", 30, "A-02"),
            ("GU-01", "GB-ARB-PREANGER", 30, "A-03"),
            ("GU-01", "GB-ROB-TEMANGGUNG", 40, "A-04"),
            ("GU-01", "GB-ROB-LAMPUNG", 40, "A-05"),
            ("GU-01", "BK-ARB-GAYO-200", 50, "B-01"),
            ("GU-01", "BK-ARB-GAYO-1000", 25, "B-02"),
            ("GU-01", "BK-BLD-HOUSE-250", 50, "B-03"),
            ("GU-01", "BK-BLD-HOUSE-1000", 20, "B-04"),
            ("GU-01", "AL-V60-02", 15, "C-01"),
            ("GU-01", "ME-ESPRESSO-1G", 8, "C-02"),
            # GC-01, beberapa menipis dan satu habis
            ("GC-01", "BK-ARB-GAYO-200", 25, "A-01"),
            ("GC-01", "BK-BLD-HOUSE-250", 20, "A-02"),
            ("GC-01", "BK-EXC-MERANTI-200", 15, "A-03"),
            ("GC-01", "AL-V60-02", 10, "B-01"),
            ("GC-01", "ME-ESPRESSO-1G", 2, "B-02"),
            # GC-02
            ("GC-02", "BK-ARB-KINTAMANI-200", 20, "A-01"),
            ("GC-02", "BK-ARB-PREANGER-250", 20, "A-02"),
            ("GC-02", "BK-BLD-ESPRESSO-500", 15, "A-03"),
            ("GC-02", "AL-FRENCH-600", 12, "B-01"),
            # OT-01, beberapa menipis dan satu habis
            ("OT-01", "BK-ARB-GAYO-200", 35, "R-01"),
            ("OT-01", "BK-ARB-KINTAMANI-200", 15, "R-02"),
            ("OT-01", "BK-BLD-HOUSE-250", 20, "R-03"),
            ("OT-01", "HP-CUP-8OZ-50", 15, "R-04"),
            ("OT-01", "GR-LISTRIK-64", 1, "R-05"),
            # OT-02
            ("OT-02", "BK-ARB-PREANGER-250", 20, "R-01"),
            ("OT-02", "BK-ROB-TEMANGGUNG-200", 20, "R-02"),
            ("OT-02", "BK-BLD-HOUSE-250", 25, "R-03"),
            ("OT-02", "HP-CUP-8OZ-50", 15, "R-04"),
            # OT-03
            ("OT-03", "BK-ARB-GAYO-200", 15, "R-01"),
            ("OT-03", "BK-BLD-ESPRESSO-500", 12, "R-02"),
            ("OT-03", "HP-CUP-8OZ-50", 15, "R-03"),
        ]
        for loc_code, sku, min_stok, rak in settings:
            stok_service.update_setting(
                self.loc(loc_code),
                self.sku(sku),
                StokSettingInput(stok_minimum=min_stok, rak=rak),
            )
