export const ROLES = Object.freeze({
  ADMIN: 'admin',
  MANAGER_GUDANG: 'manager_gudang',
  MANAGER_OUTLET: 'manager_outlet',
  DELIVERYMAN: 'deliveryman',
})

// admin ikut dihitung manager untuk menu dan aksi
export const MANAGER_ROLES = Object.freeze([ROLES.ADMIN, ROLES.MANAGER_GUDANG, ROLES.MANAGER_OUTLET])

export const LOKASI_TYPES = Object.freeze({
  GUDANG_UTAMA: 'gudang_utama',
  GUDANG_CABANG: 'gudang_cabang',
  OUTLET: 'outlet',
})

export const ROLE_LABELS = Object.freeze({
  [ROLES.ADMIN]: 'Admin',
  [ROLES.MANAGER_GUDANG]: 'Manager Gudang',
  [ROLES.MANAGER_OUTLET]: 'Manager Outlet',
  [ROLES.DELIVERYMAN]: 'Deliveryman',
})

export const LOKASI_TYPE_LABELS = Object.freeze({
  gudang_utama: 'Gudang Utama',
  gudang_cabang: 'Gudang Cabang',
  outlet: 'Outlet',
})

export const KATEGORI_TYPE_LABELS = Object.freeze({
  green_bean: 'Green Bean',
  roasted_bean: 'Roasted Bean',
  peralatan: 'Peralatan',
  habis_pakai: 'Bahan Habis Pakai',
})

export const CUSTOMER_TYPE_LABELS = Object.freeze({
  kafe: 'Kafe',
  reseller: 'Reseller',
  perorangan: 'Perorangan',
  lainnya: 'Lainnya',
})

export const USER_STATUS_LABELS = Object.freeze({
  menunggu: 'Menunggu',
  aktif: 'Aktif',
  nonaktif: 'Nonaktif',
})

export const STOK_STATUS_LABELS = Object.freeze({
  aman: 'Aman',
  menipis: 'Menipis',
  habis: 'Habis',
})

export const COFFEE_TYPE_LABELS = Object.freeze({
  arabika: 'Arabika',
  robusta: 'Robusta',
  excelsa: 'Excelsa',
  liberika: 'Liberika',
  blended: 'Blended',
})

export const ROAST_LEVEL_LABELS = Object.freeze({
  light: 'Light',
  medium: 'Medium',
  medium_dark: 'Medium Dark',
  dark: 'Dark',
})

export const PRODUK_UNIT_LABELS = Object.freeze({
  pack: 'Pack',
  pcs: 'Pcs',
  box: 'Box',
  set: 'Set',
  kg: 'Kg',
})

export const PRODUK_WEIGHTS = Object.freeze([100, 200, 250, 500, 1000])

export const MUTASI_TYPE_LABELS = Object.freeze({
  masuk: 'Masuk (IN)',
  keluar: 'Keluar (OUT)',
  penyesuaian: 'Penyesuaian (ADJ)',
  kirim: 'Pengiriman (OUT)',
  terima: 'Penerimaan (IN)',
  pembelian: 'Pembelian (IN)',
  penjualan: 'Penjualan (OUT)',
})

export const TRANSAKSI_TYPE_LABELS = Object.freeze({
  masuk: 'Masuk (IN)',
  keluar: 'Keluar (OUT)',
  penyesuaian: 'Penyesuaian (ADJ)',
})

export const TRANSAKSI_REASON_LABELS = Object.freeze({
  hasil_roasting: 'Hasil Roasting',
  retur: 'Retur',
  pemakaian: 'Pemakaian',
  roasting: 'Roasting',
  sampel: 'Sampel',
  opname: 'Stock Opname',
  rusak: 'Barang Rusak',
  hilang: 'Barang Hilang',
  kedaluwarsa: 'Kedaluwarsa',
  lainnya: 'Lainnya',
})

export const TRANSAKSI_REASONS = Object.freeze({
  masuk: ['hasil_roasting', 'retur', 'lainnya'],
  keluar: ['pemakaian', 'roasting', 'sampel', 'lainnya'],
  penyesuaian: ['opname', 'rusak', 'hilang', 'kedaluwarsa', 'lainnya'],
})

export const DOKUMEN_STATUS_LABELS = Object.freeze({
  draf: 'Draf',
  diposting: 'Diposting',
  dikirim: 'Dikirim',
  diterima: 'Diterima',
  dibatalkan: 'Dibatalkan',
  diajukan: 'Diajukan',
  disetujui: 'Disetujui',
  ditolak: 'Ditolak',
  selesai: 'Selesai',
  dipesan: 'Dipesan',
})

export const KENDARAAN_TYPE_LABELS = Object.freeze({
  motor: 'Motor',
  mobil_box: 'Mobil Box',
  pickup: 'Pickup',
  van: 'Van',
  lainnya: 'Lainnya',
})
