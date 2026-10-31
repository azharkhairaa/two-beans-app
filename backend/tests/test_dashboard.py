from datetime import timedelta

import pytest
from sqlalchemy import text

from app.core.clock import Clock
from app.models import (
    CoffeeType,
    Customer,
    CustomerType,
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
    PermintaanDetail,
    PermintaanStatus,
    Produk,
    ProdukUnit,
    Stok,
    StokMutasi,
    StokMutasiType,
    Supplier,
    UserRole,
)
from tests.conftest import PASSWORD

def login_as(client, email: str) -> str:
    res = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200
    return res.json()["csrf_token"]

@pytest.fixture
def seeded_dashboard(db, factory):
    kat_biji = factory.add(Kategori(nama="Single Origin", jenis=KategoriType.ROASTED_BEAN))
    kat_alat = factory.add(Kategori(nama="Alat Seduh", jenis=KategoriType.PERALATAN))

    prod_gayo = factory.add(
        Produk(
            sku="BK-ARB-GAYO-200",
            nama="Arabika Gayo 200 g",
            kategori=kat_biji,
            satuan=ProdukUnit.PACK,
            berat_gram=200,
            jenis_kopi=CoffeeType.ARABIKA,
            harga_beli=65000,
            harga_jual=95000,
        )
    )
    prod_v60 = factory.add(
        Produk(
            sku="AL-V60-02",
            nama="Dripper V60 02",
            kategori=kat_alat,
            satuan=ProdukUnit.PCS,
            harga_beli=120000,
            harga_jual=165000,
        )
    )

    gu = factory.add(
        Lokasi(kode="GU-01", nama="Gudang Utama Roastery", jenis=LokasiType.GUDANG_UTAMA)
    )
    ot = factory.add(Lokasi(kode="OT-01", nama="Outlet Pusat Kota", jenis=LokasiType.OUTLET))

    admin = factory.user("admin@twobeans.id", role=UserRole.ADMIN)
    mgr_gu = factory.user("mgr.gu@twobeans.id", role=UserRole.MANAGER_GUDANG, lokasi=gu)
    mgr_ot = factory.user("mgr.ot@twobeans.id", role=UserRole.MANAGER_OUTLET, lokasi=ot)
    kurir = factory.user("kurir1@twobeans.id", role=UserRole.DELIVERYMAN)

    # stok GU-01 aman dan menipis, stok OT-01 menipis dan habis
    factory.add(Stok(lokasi=gu, produk=prod_gayo, jumlah=40, stok_minimum=20, rak="A-01"))
    factory.add(Stok(lokasi=gu, produk=prod_v60, jumlah=5, stok_minimum=5, rak="B-01"))
    factory.add(Stok(lokasi=ot, produk=prod_gayo, jumlah=8, stok_minimum=10, rak="R-01"))
    factory.add(Stok(lokasi=ot, produk=prod_v60, jumlah=0, stok_minimum=2, rak="R-02"))

    # mutasi hari ini ikut tercatat bersama dokumennya di bawah
    now = Clock.now()
    today = Clock.today()

    # pengiriman berstatus dikirim (dalam perjalanan)
    kirim = factory.add(
        Pengiriman(
            kode="KR-261028-0001",
            status=PengirimanStatus.DIKIRIM,
            lokasi_asal=gu,
            lokasi_tujuan=ot,
            deliveryman=kurir,
            kendaraan_jenis="mobil_box",
            kendaraan_nomor="B 1234 TBC",
            tanggal_kirim=today,
            dibuat_oleh=mgr_gu,
            dikirim_oleh=mgr_gu,
            dikirim_pada=now,
        )
    )
    factory.add(
        PengirimanDetail(pengiriman=kirim, produk=prod_gayo, jumlah_dikirim=10)
    )

    # pembelian berstatus dipesan (PO terbuka)
    sup = factory.add(Supplier(nama="Koperasi Gayo"))
    po = factory.add(
        Pembelian(
            kode="PO-261028-0001",
            status=PembelianStatus.DIPESAN,
            supplier=sup,
            lokasi=gu,
            tanggal_pesan=today,
            tanggal_perkiraan=today + timedelta(days=3),
            dibuat_oleh=mgr_gu,
            dipesan_oleh=mgr_gu,
        )
    )
    factory.add(
        PembelianDetail(
            pembelian=po, produk=prod_v60, jumlah=15, harga_satuan=115000
        )
    )

    # permintaan berstatus diajukan
    pm = factory.add(
        Permintaan(
            kode="PM-261028-0001",
            status=PermintaanStatus.DIAJUKAN,
            lokasi_peminta=ot,
            lokasi_sumber=gu,
            tanggal_butuh=today + timedelta(days=2),
            diajukan_oleh=mgr_ot,
        )
    )
    factory.add(PermintaanDetail(permintaan=pm, produk=prod_gayo, jumlah_diminta=12))

    # penjualan diposting: GU-01 ke Kafe Senja, OT-01 ke pembeli umum
    cust = factory.add(Customer(nama="Kafe Senja", jenis=CustomerType.KAFE))
    pj_gu = factory.add(
        Penjualan(
            kode="PJ-261028-0001",
            status=PenjualanStatus.DIPOSTING,
            lokasi=gu,
            customer=cust,
            tanggal=today,
            dibuat_oleh=mgr_gu,
            diposting_oleh=mgr_gu,
            diposting_pada=now,
        )
    )
    factory.add(
        PenjualanDetail(
            penjualan=pj_gu, produk=prod_gayo, jumlah=10, harga_satuan=90000
        )
    )
    pj_ot = factory.add(
        Penjualan(
            kode="PJ-261028-0002",
            status=PenjualanStatus.DIPOSTING,
            lokasi=ot,
            customer=None,
            tanggal=today,
            dibuat_oleh=mgr_ot,
            diposting_oleh=mgr_ot,
            diposting_pada=now,
        )
    )
    factory.add(
        PenjualanDetail(
            penjualan=pj_ot, produk=prod_gayo, jumlah=4, harga_satuan=95000
        )
    )
    factory.add(
        StokMutasi(
            lokasi=gu,
            produk=prod_gayo,
            jenis=StokMutasiType.KIRIM,
            perubahan=-10,
            stok_sebelum=50,
            stok_sesudah=40,
            pengiriman_id=kirim.id,
            user=mgr_gu,
            created_at=now,
        )
    )
    factory.add(
        StokMutasi(
            lokasi=ot,
            produk=prod_gayo,
            jenis=StokMutasiType.PENJUALAN,
            perubahan=-4,
            stok_sebelum=12,
            stok_sesudah=8,
            penjualan_id=pj_ot.id,
            user=mgr_ot,
            created_at=now,
        )
    )
    db.commit()

    return {
        "gu": gu,
        "ot": ot,
        "prod_gayo": prod_gayo,
        "prod_v60": prod_v60,
        "admin": admin,
        "mgr_gu": mgr_gu,
        "mgr_ot": mgr_ot,
        "kurir": kurir,
    }

def test_dashboard_admin_matches_sql_queries_and_monitoring_matrix(
    client, db, seeded_dashboard
):
    login_as(client, "admin@twobeans.id")
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert body["peran"] == "admin"

    today = Clock.today()
    since = today - timedelta(days=29)

    # dibandingkan dengan query SQL Desain Database 8.2
    sql_8_2 = db.execute(
        text(
            """
            SELECT l.kode,
                   count(*) FILTER (WHERE s.jumlah > 0) AS sku_ada,
                   count(*) FILTER (WHERE s.jumlah > 0 AND s.jumlah <= s.stok_minimum) AS menipis,
                   count(*) FILTER (WHERE s.jumlah = 0) AS habis,
                   coalesce(sum(s.jumlah::bigint * p.harga_beli), 0) AS nilai
            FROM lokasi l
            LEFT JOIN stok s ON s.lokasi_id = l.id
            LEFT JOIN produk p ON p.id = s.produk_id
            WHERE l.aktif
            GROUP BY l.id
            ORDER BY l.kode
            """
        )
    ).all()
    expected_nilai_persediaan = sum(int(r.nilai) for r in sql_8_2)
    assert body["ringkasan"]["nilai_persediaan"] == expected_nilai_persediaan

    # dibandingkan dengan query SQL Desain Database 8.4
    sql_8_4 = db.execute(
        text(
            """
            SELECT (SELECT coalesce(sum(d.jumlah_dikirim::bigint * p.harga_beli), 0)
                      FROM pengiriman k
                      JOIN pengiriman_detail d ON d.pengiriman_id = k.id
                      JOIN produk p ON p.id = d.produk_id
                     WHERE k.status = 'dikirim') AS nilai_dalam_perjalanan,
                   (SELECT coalesce(sum(d.jumlah::bigint * d.harga_satuan), 0)
                      FROM pembelian b
                      JOIN pembelian_detail d ON d.pembelian_id = b.id
                     WHERE b.status = 'dipesan') AS nilai_po_terbuka
            """
        )
    ).one()
    assert body["ringkasan"]["nilai_dalam_perjalanan"] == int(sql_8_4.nilai_dalam_perjalanan)
    assert body["ringkasan"]["nilai_po_terbuka"] == int(sql_8_4.nilai_po_terbuka)

    # dibandingkan dengan query SQL Desain Database 8.6
    sql_8_6 = db.execute(
        text(
            """
            SELECT coalesce(c.nama, 'Umum') AS customer, count(DISTINCT j.id) AS nota,
                   sum(d.jumlah::bigint * d.harga_satuan) AS total
            FROM penjualan j
            JOIN penjualan_detail d ON d.penjualan_id = j.id
            LEFT JOIN customer c ON c.id = j.customer_id
            WHERE j.status = 'diposting' AND j.tanggal BETWEEN :dari AND :sampai
            GROUP BY c.id, c.nama
            ORDER BY total DESC
            LIMIT 5
            """
        ),
        {"dari": since, "sampai": today},
    ).all()
    assert [c["nama"] for c in body["customer_teratas"]] == [r.customer for r in sql_8_6]
    assert body["ringkasan"]["omzet_30_hari"] == sum(int(r.total) for r in sql_8_6)

    # total_nilai matriks monitoring sama dengan nilai_persediaan dashboard
    mon_res = client.get("/api/dashboard/monitoring")
    assert mon_res.status_code == 200
    mon = mon_res.json()
    assert mon["total_nilai"] == body["ringkasan"]["nilai_persediaan"]
    assert len(mon["lokasi"]) == 2
    assert len(mon["baris"]) == 2

def test_dashboard_roles_and_tren_isolation(client, seeded_dashboard):
    # manager outlet hanya melihat lokasi OT-01 dan tugas penerimaan pengiriman
    login_as(client, "mgr.ot@twobeans.id")
    res_ot = client.get("/api/dashboard")
    assert res_ot.status_code == 200
    data_ot = res_ot.json()
    assert data_ot["peran"] == "manager_outlet"
    assert data_ot["lokasi"]["kode"] == "OT-01"
    assert len(data_ot["per_lokasi"]) == 1
    assert data_ot["ringkasan"]["omzet_30_hari"] == 4 * 95000
    assert any(t["jenis"] == "terima_pengiriman" for t in data_ot["tugas"])
    # jenis lokasi dan produk dipakai frontend untuk memilih tombol isi ulang stock
    assert {(s["sku"], s["lokasi_jenis"], s["produk_jenis"]) for s in data_ot["stok_kritis"]} == {
        ("BK-ARB-GAYO-200", "outlet", "roasted_bean"),
        ("AL-V60-02", "outlet", "peralatan"),
    }

    # manager outlet meminta tren lokasinya sendiri -> 200, lokasi GU-01 -> 404
    tren_ok = client.get("/api/dashboard/tren?hari=14")
    assert tren_ok.status_code == 200
    assert len(tren_ok.json()["data"]) == 14
    assert tren_ok.json()["data"][-1]["keluar"] == 4

    gu_id = seeded_dashboard["gu"].id
    tren_forbidden = client.get(f"/api/dashboard/tren?hari=14&lokasi_id={gu_id}")
    assert tren_forbidden.status_code == 404

    # deliveryman melihat pengiriman aktifnya dan ditolak di monitoring
    login_as(client, "kurir1@twobeans.id")
    res_dm = client.get("/api/dashboard")
    assert res_dm.status_code == 200
    data_dm = res_dm.json()
    assert data_dm["peran"] == "deliveryman"
    assert len(data_dm["pengiriman_aktif"]) == 1
    assert data_dm["pengiriman_aktif"][0]["kode"] == "KR-261028-0001"

    assert client.get("/api/dashboard/monitoring").status_code == 403
    assert client.get("/api/dashboard/tren").status_code == 403

def test_large_values_inactive_products_and_unknown_status(client, db, seeded_dashboard):
    # 48 x Rp45 juta melewati batas int4, produk nonaktif yang masih berstok tetap dihitung
    mahal = Produk(
        sku="AL-ESPRESSO-01",
        nama="Mesin Espresso",
        kategori=seeded_dashboard["prod_v60"].kategori,
        satuan=ProdukUnit.PCS,
        harga_beli=45_000_000,
        harga_jual=52_000_000,
        aktif=False,
    )
    db.add(mahal)
    db.flush()
    db.add(Stok(lokasi=seeded_dashboard["gu"], produk=mahal, jumlah=48))
    db.commit()

    login_as(client, "admin@twobeans.id")
    dashboard = client.get("/api/dashboard")
    monitoring = client.get("/api/dashboard/monitoring")
    assert dashboard.status_code == monitoring.status_code == 200
    nilai = dashboard.json()["ringkasan"]["nilai_persediaan"]
    assert nilai > 2**31 and nilai == monitoring.json()["total_nilai"]
    assert client.get("/api/stok", params={"sort": "nilai"}).status_code == 200

    for path in ("/api/dashboard/monitoring", "/api/stok"):
        res = client.get(path, params={"status_stok": "xyz"})
        assert res.status_code == 422 and "status_stok" in res.json()["errors"]

def test_monitoring_values_only_for_admin_and_gudang_utama(client, seeded_dashboard):
    # manager gudang utama memantau nilai semua lokasi
    login_as(client, "mgr.gu@twobeans.id")
    mon_gu = client.get("/api/dashboard/monitoring").json()
    assert mon_gu["nilai_terlihat"] is True and mon_gu["total_nilai"] > 0
    assert "total_jumlah" not in mon_gu and "jumlah" not in mon_gu["total_per_lokasi"][0]

    # manager outlet tetap melihat jumlah semua lokasi tetapi semua nilai rupiah null
    client.cookies.clear()
    login_as(client, "mgr.ot@twobeans.id")
    mon_ot = client.get("/api/dashboard/monitoring").json()
    assert mon_ot["nilai_terlihat"] is False and mon_ot["total_nilai"] is None
    assert {row["produk"]["harga_beli"] for row in mon_ot["baris"]} == {None}
    assert {row["nilai"] for row in mon_ot["baris"]} == {None}
    assert {sel["nilai"] for row in mon_ot["baris"] for sel in row["sel"]} == {None}
    assert {item["nilai"] for item in mon_ot["total_per_lokasi"]} == {None}
    # rak hanya terlihat di lokasi sendiri, rak gudang utama disembunyikan
    rak_ot = {sel["lokasi_id"]: sel["rak"] for row in mon_ot["baris"] for sel in row["sel"] if sel["rak"]}
    assert set(rak_ot) == {seeded_dashboard["ot"].id}
    rak_gu = {sel["rak"] for row in mon_gu["baris"] for sel in row["sel"] if sel["rak"]}
    assert {"A-01", "B-01", "R-01"} <= rak_gu
    jumlah_gu = [
        sel["jumlah"] for row in mon_ot["baris"] for sel in row["sel"]
        if sel["lokasi_id"] == seeded_dashboard["gu"].id
    ]
    assert sum(jumlah_gu) == 40 + 5

