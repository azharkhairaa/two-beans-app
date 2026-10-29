import { useRoute, useRouter } from 'vue-router'

// tombol pintas (misalnya isi ulang stock dari dashboard) membuka formulir lewat query ?buat=1,
// query dibuang sesudah dipakai supaya reload tidak membuka formulir yang sama lagi
export function usePrefillQuery() {
  const route = useRoute()
  const router = useRouter()

  async function consume(open) {
    if (route.query.buat !== '1') return
    const query = route.query
    const prefill = {
      lokasiId: Number(query.isi_lokasi) || '',
      produkId: Number(query.isi_produk) || '',
      jumlah: Number(query.isi_jumlah) || 1,
    }
    await router.replace({ query: {} })
    await open(prefill)
  }

  return { consume }
}
