import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import { ApiError } from '@/services/ApiClient'

// state daftar: empat keadaan request (loading, error, empty, data), filter dan paginasi
export function useList(fetcher, optionsOrFilters = {}, maybeOptions = {}) {
  const route = useRoute()
  const hasNestedInitial =
    optionsOrFilters &&
    typeof optionsOrFilters === 'object' &&
    ('initialFilters' in optionsOrFilters || 'paginated' in optionsOrFilters || 'immediate' in optionsOrFilters)

  const rawInitial = hasNestedInitial ? optionsOrFilters.initialFilters || {} : optionsOrFilters || {}
  const opts = hasNestedInitial ? optionsOrFilters : maybeOptions || {}
  const paginated = opts.paginated !== false
  const immediate = opts.immediate !== false

  const defaults = {
    ...(paginated ? { page: 1, per_page: opts.perPage || 15 } : {}),
    ...rawInitial,
  }
  const initialFromQuery = {}
  if (route?.query) {
    for (const key of Object.keys(defaults)) {
      const qVal = route.query[key]
      if (typeof qVal === 'string' && qVal !== '') {
        initialFromQuery[key] = qVal
      }
    }
  }
  const filters = reactive({ ...defaults, ...initialFromQuery })
  const items = ref([])
  const meta = ref({ page: 1, per_page: defaults.per_page || 15, total: 0, total_pages: 1 })
  const extra = ref({})
  const loading = ref(immediate)
  const error = ref('')
  let latestRequest = 0

  function buildParams() {
    const out = {}
    for (const [key, val] of Object.entries(filters)) {
      if (val !== '' && val !== null && val !== undefined) {
        out[key] = val
      }
    }
    return out
  }

  async function load() {
    // hanya respons request terakhir yang dipakai supaya hasil lama tidak menimpa filter baru
    const requestId = ++latestRequest
    loading.value = true
    error.value = ''
    try {
      const response = await fetcher(buildParams())
      if (requestId !== latestRequest) return
      if (Array.isArray(response)) {
        items.value = response
        meta.value = {
          page: 1,
          per_page: response.length || 15,
          total: response.length,
          total_pages: 1,
        }
        extra.value = {}
      } else {
        items.value = response?.data || []
        meta.value = response?.meta || {
          page: filters.page || 1,
          per_page: filters.per_page || 15,
          total: items.value.length,
          total_pages: 1,
        }
        extra.value = response || {}
        // halaman terakhir kosong sesudah hapus, pindah ke halaman terakhir yang masih ada isinya
        const lastPage = meta.value.total_pages || 1
        if (paginated && !items.value.length && filters.page > lastPage) {
          filters.page = lastPage
          return load()
        }
      }
    } catch (err) {
      if (requestId !== latestRequest) return
      error.value = err instanceof ApiError ? err.message : err?.message || 'Gagal memuat data.'
    } finally {
      if (requestId === latestRequest) loading.value = false
    }
  }

  function applyFilters() {
    if (paginated) filters.page = 1
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
