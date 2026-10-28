from app.models import CoffeeType, Produk, ProdukUnit, RoastLevel
from app.seeders.base import Seeder

ARABIKA, ROBUSTA, EXCELSA = CoffeeType.ARABIKA, CoffeeType.ROBUSTA, CoffeeType.EXCELSA
LIBERIKA, BLENDED = CoffeeType.LIBERIKA, CoffeeType.BLENDED
LIGHT, MEDIUM, MEDIUM_DARK, DARK = RoastLevel.LIGHT, RoastLevel.MEDIUM, RoastLevel.MEDIUM_DARK, RoastLevel.DARK

class ProdukSeeder(Seeder):
    # green bean per kg: sku, nama, jenis kopi, asal, harga beli, harga jual
    GREEN_BEAN = [
        ("GB-ARB-GAYO", "Green Bean Arabika Gayo", ARABIKA, "Aceh Tengah", 120000, 150000),
        ("GB-ARB-KINTAMANI", "Green Bean Arabika Kintamani", ARABIKA, "Bangli, Bali", 125000, 155000),
        ("GB-ARB-PREANGER", "Green Bean Arabika Java Preanger", ARABIKA, "Pangalengan", 115000, 145000),
        ("GB-ROB-TEMANGGUNG", "Green Bean Robusta Temanggung", ROBUSTA, "Temanggung", 65000, 85000),
        ("GB-ROB-LAMPUNG", "Green Bean Robusta Lampung", ROBUSTA, "Lampung Barat", 60000, 80000),
        ("GB-EXC-MERANTI", "Green Bean Excelsa Meranti", EXCELSA, "Kepulauan Meranti", 90000, 115000),
        ("GB-LIB-JAMBI", "Green Bean Liberika Jambi", LIBERIKA, "Tanjung Jabung Barat", 95000, 120000),
        ("GB-LIB-RANGSANG", "Green Bean Liberika Rangsang", LIBERIKA, "Kepulauan Meranti", 100000, 125000),
    ]
    # biji kopi sangrai per kemasan: kategori, sku, nama, jenis kopi, asal, berat, tingkat sangrai, harga
    ROASTED_BEAN = [
        ("Single Origin", "BK-ARB-GAYO-200", "Arabika Gayo 200 g", ARABIKA, "Aceh Tengah", 200, MEDIUM,
         65000, 95000),
        ("Single Origin", "BK-ARB-GAYO-1000", "Arabika Gayo 1 kg", ARABIKA, "Aceh Tengah", 1000, MEDIUM,
         290000, 400000),
        ("Single Origin", "BK-ARB-KINTAMANI-200", "Arabika Kintamani 200 g", ARABIKA, "Bangli, Bali", 200,
         LIGHT, 68000, 98000),
        ("Single Origin", "BK-ARB-PREANGER-250", "Arabika Java Preanger 250 g", ARABIKA, "Pangalengan", 250,
         MEDIUM, 75000, 110000),
        ("Single Origin", "BK-ROB-TEMANGGUNG-200", "Robusta Temanggung 200 g", ROBUSTA, "Temanggung", 200,
         DARK, 35000, 55000),
        ("Single Origin", "BK-ROB-LAMPUNG-500", "Robusta Lampung 500 g", ROBUSTA, "Lampung Barat", 500,
         MEDIUM_DARK, 80000, 120000),
        ("Single Origin", "BK-EXC-MERANTI-200", "Excelsa Meranti 200 g", EXCELSA, "Kepulauan Meranti", 200,
         MEDIUM, 55000, 85000),
        ("Single Origin", "BK-LIB-JAMBI-100", "Liberika Jambi 100 g", LIBERIKA, "Tanjung Jabung Barat", 100,
         MEDIUM, 32000, 48000),
        ("Single Origin", "BK-LIB-JAMBI-200", "Liberika Jambi 200 g", LIBERIKA, "Tanjung Jabung Barat", 200,
         MEDIUM, 58000, 88000),
        ("Blend", "BK-BLD-HOUSE-250", "House Blend 250 g", BLENDED, "Two Beans", 250, MEDIUM_DARK,
         60000, 90000),
        ("Blend", "BK-BLD-HOUSE-1000", "House Blend 1 kg", BLENDED, "Two Beans", 1000, MEDIUM_DARK,
         220000, 320000),
        ("Blend", "BK-BLD-ESPRESSO-500", "Espresso Blend 500 g", BLENDED, "Two Beans", 500, DARK,
         110000, 165000),
        ("Blend", "BK-BLD-SUSU-1000", "Blend Kopi Susu 1 kg", BLENDED, "Two Beans", 1000, DARK,
         190000, 280000),
    ]
    # peralatan dan bahan habis pakai: kategori, sku, nama, satuan, harga beli, harga jual
    LAINNYA = [
        ("Alat Seduh Manual", "AL-V60-02", "Dripper V60 02", ProdukUnit.PCS, 120000, 165000),
        ("Alat Seduh Manual", "AL-WAVE-185", "Dripper Wave 185", ProdukUnit.PCS, 350000, 450000),
        ("Alat Seduh Manual", "AL-POUROVER-6", "Pour Over Kaca 6 Cup", ProdukUnit.PCS, 650000, 850000),
        ("Alat Seduh Manual", "AL-FRENCH-600", "French Press 600 ml", ProdukUnit.PCS, 150000, 210000),
        ("Alat Seduh Manual", "AL-PRESS-AIR", "Press Seduh Tekanan Udara", ProdukUnit.PCS, 450000, 590000),
        ("Alat Seduh Manual", "AL-KETTLE-1000", "Kettle Leher Angsa 1 L", ProdukUnit.PCS, 280000, 375000),
        ("Alat Seduh Manual", "AL-SET-SEDUH", "Paket Seduh Manual", ProdukUnit.SET, 550000, 720000),
        ("Grinder", "GR-MANUAL-38", "Grinder Manual Burr 38 mm", ProdukUnit.PCS, 450000, 620000),
        ("Grinder", "GR-LISTRIK-40", "Grinder Listrik Conical 40 mm", ProdukUnit.PCS, 1200000, 1600000),
        ("Grinder", "GR-LISTRIK-64", "Grinder Listrik Flat Burr 64 mm", ProdukUnit.PCS, 3500000, 4500000),
        ("Mesin Espresso dan Aksesori", "ME-ESPRESSO-1G", "Mesin Espresso 1 Group", ProdukUnit.PCS,
         18000000, 23000000),
        ("Mesin Espresso dan Aksesori", "ME-TAMPER-58", "Tamper 58 mm", ProdukUnit.PCS, 180000, 260000),
        ("Mesin Espresso dan Aksesori", "ME-PITCHER-600", "Milk Jug 600 ml", ProdukUnit.PCS, 95000, 140000),
        ("Mesin Espresso dan Aksesori", "ME-TIMBANGAN", "Timbangan Digital Kopi", ProdukUnit.PCS,
         250000, 340000),
        ("Mesin Espresso dan Aksesori", "ME-KNOCKBOX", "Knock Box", ProdukUnit.PCS, 120000, 175000),
        ("Filter dan Bahan Habis Pakai", "HP-FILTER-V60-100", "Kertas Filter V60 isi 100", ProdukUnit.PACK,
         45000, 65000),
        ("Filter dan Bahan Habis Pakai", "HP-FILTER-WAVE-100", "Kertas Filter Wave isi 100", ProdukUnit.PACK,
         55000, 78000),
        ("Filter dan Bahan Habis Pakai", "HP-CUP-8OZ-50", "Paper Cup 8 oz isi 50", ProdukUnit.PACK,
         35000, 50000),
        ("Filter dan Bahan Habis Pakai", "HP-CUP-12OZ-50", "Paper Cup 12 oz isi 50", ProdukUnit.PACK,
         42000, 60000),
        ("Filter dan Bahan Habis Pakai", "HP-PEMBERSIH-MESIN", "Pembersih Mesin Espresso", ProdukUnit.BOX,
         110000, 155000),
        ("Filter dan Bahan Habis Pakai", "HP-KANTONG-VALVE-50", "Kantong Kemasan Valve isi 50",
         ProdukUnit.PACK, 75000, 105000),
    ]

    def run(self) -> None:
        kategori = self.context.kategori
        for sku, nama, jenis_kopi, asal, harga_beli, harga_jual in self.GREEN_BEAN:
            self.save(Produk(sku=sku, nama=nama, kategori=kategori["Green Bean"], merek=asal,
                             satuan=ProdukUnit.KG, jenis_kopi=jenis_kopi, harga_beli=harga_beli,
                             harga_jual=harga_jual))
        for nama_kategori, sku, nama, jenis_kopi, asal, berat, sangrai, harga_beli, harga_jual in self.ROASTED_BEAN:
            self.save(Produk(sku=sku, nama=nama, kategori=kategori[nama_kategori], merek=asal,
                             satuan=ProdukUnit.PACK, berat_gram=berat, tingkat_sangrai=sangrai,
                             jenis_kopi=jenis_kopi, harga_beli=harga_beli, harga_jual=harga_jual))
        for nama_kategori, sku, nama, satuan, harga_beli, harga_jual in self.LAINNYA:
            self.save(Produk(sku=sku, nama=nama, kategori=kategori[nama_kategori], satuan=satuan,
                             harga_beli=harga_beli, harga_jual=harga_jual))

    def save(self, produk: Produk) -> None:
        self.context.produk[produk.sku] = self.add(produk)
