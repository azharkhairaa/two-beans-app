import { ref } from 'vue'

import { kategoriApi, lokasiApi } from '@/services'
import { useToastStore } from '@/stores/toast'

// satu daftar pilihan dropdown, dimuat sendiri agar satu daftar gagal tidak mengosongkan lainnya
export function useOptions(loader, label) {
  const toast = useToastStore()
  const items = ref([])

  async function load() {
    try {
      items.value = (await loader()) || []
    } catch (err) {
      items.value = []
      toast.show(err?.message || `Gagal memuat daftar ${label}.`, 'error')
    }
  }

  return { items, load }
}

export function useLokasiOptions() {
  return useOptions(() => lokasiApi.list({ aktif: 'true' }), 'lokasi')
}

export function useKategoriOptions() {
  return useOptions(() => kategoriApi.list(), 'kategori')
}
