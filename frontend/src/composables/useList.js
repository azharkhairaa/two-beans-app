import { onMounted, reactive, ref } from 'vue'

import { ApiError } from '@/services/ApiClient'

// state daftar: empat keadaan request (loading, error, empty, data), filter dan paginasi
export function useList(fetcher, initialFilters = {}, { immediate = true } = {}) {
  const defaults = { ...initialFilters }
  const filters = reactive({ ...defaults })
  const items = ref([])
  const meta = ref({ page: 1, per_page: 10, total: 0, total_pages: 0 })
  const extra = ref({})
  const loading = ref(immediate)
  const error = ref('')

  async function load() {
    loading.value = true
    error.value = ''
    try {
      const response = await fetcher({ ...filters })
      if (Array.isArray(response)) {
        items.value = response
        meta.value = { page: 1, per_page: response.length || 10, total: response.length, total_pages: 1 }
        extra.value = {}
      } else {
        items.value = response?.data || []
        meta.value = response?.meta || { page: 1, per_page: 10, total: items.value.length, total_pages: 1 }
        extra.value = response || {}
      }
    } catch (err) {
      error.value = err instanceof ApiError ? err.message : 'Gagal memuat data.'
    } finally {
      loading.value = false
    }
  }

  function applyFilters() {
    if ('page' in filters) filters.page = 1
    return load()
  }

  function resetFilters() {
    Object.assign(filters, defaults)
    return load()
  }

  function setPage(page) {
    filters.page = page
    return load()
  }

  function setPerPage(perPage) {
    filters.per_page = Number(perPage)
    filters.page = 1
    return load()
  }

  if (immediate) onMounted(load)

  return {
    filters,
    items,
    meta,
    extra,
    loading,
    error,
    load,
    applyFilters,
    resetFilters,
    setPage,
    setPerPage,
  }
}
