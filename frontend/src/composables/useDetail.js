import { ref } from 'vue'

import { useToastStore } from '@/stores/toast'

// state modal detail dokumen: buka, muat dari API, tutup lagi bila gagal dimuat
export function useDetail(fetcher, label, { previewRow = false } = {}) {
  const toast = useToastStore()
  const open = ref(false)
  const loading = ref(false)
  const data = ref(null)

  // previewRow menampilkan data baris selama memuat dan modal tetap terbuka bila gagal
  async function show(row) {
    open.value = true
    loading.value = true
    data.value = previewRow ? row : null
    try {
      data.value = await fetcher(row.id)
    } catch (err) {
      toast.show(err?.message || `Gagal memuat detail ${label}.`, 'error')
      if (!previewRow) open.value = false
    } finally {
      loading.value = false
    }
  }

  function close() {
    open.value = false
  }

  return { open, loading, data, show, close }
}
