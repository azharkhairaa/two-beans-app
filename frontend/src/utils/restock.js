import { LOKASI_TYPES, ROLES } from '@/utils/constants'

// cara isi ulang stock yang menipis atau habis: cabang dan outlet meminta ke gudang utama, gudang
// utama membeli ke supplier kecuali roasted bean yang bertambah lewat hasil roasting (BR-11)
// jumlah awal mengisi sampai dua kali batas minimum dan masih bisa diubah di formulir
export function restockLink({ lokasiId, lokasiJenis, produkId, produkJenis, jumlah, stokMinimum }) {
  const query = {
    buat: '1',
    isi_lokasi: String(lokasiId),
    isi_produk: String(produkId),
    isi_jumlah: String(Math.max(1, stokMinimum * 2 - jumlah)),
  }
  if (lokasiJenis !== LOKASI_TYPES.GUDANG_UTAMA) {
    return { label: 'Ajukan permintaan', icon: 'clipboard', to: { name: 'permintaan', query } }
  }
  if (produkJenis === 'roasted_bean') {
    return { label: 'Catat roasting', icon: 'coffee', to: { name: 'transaksi', query } }
  }
  return { label: 'Buat PO', icon: 'cart', to: { name: 'pembelian', query } }
}

// tombol isi ulang hanya untuk admin atau manager lokasi itu sendiri
export function canRestock(user, lokasiId) {
  return user?.role === ROLES.ADMIN || (lokasiId != null && user?.lokasi?.id === lokasiId)
}
