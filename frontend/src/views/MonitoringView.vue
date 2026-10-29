<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AppIcon from '@/components/AppIcon'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import KartuStokModal from '@/components/KartuStokModal.vue'
import LoadingState from '@/components/LoadingState.vue'
import MatriksStok from '@/components/MatriksStok.vue'
import { dashboardApi, kategoriApi } from '@/services'
import { KATEGORI_TYPE_LABELS, LOKASI_TYPE_LABELS } from '@/utils/constants'
import { formatNumber, formatRupiah, formatRupiahCompact } from '@/utils/format'

const route = useRoute()

const filters = reactive({
  q: typeof route.query.q === 'string' ? route.query.q : '',
  kategori_id: typeof route.query.kategori_id === 'string' ? route.query.kategori_id : '',
  jenis: typeof route.query.jenis === 'string' ? route.query.jenis : '',
  status_stok:
    typeof route.query.status_stok === 'string' &&
    ['semua', 'aman', 'menipis', 'habis'].includes(route.query.status_stok)
      ? route.query.status_stok
      : 'semua',
})

const kategoriOptions = ref([])
const loading = ref(true)
const error = ref('')
const matrix = ref({
  lokasi: [],
  baris: [],
  total_per_lokasi: {},
  total_jumlah: 0,
  total_nilai: 0,
})

const kartuModal = reactive({
  open: false,
  produk: null,
  lokasi: null,
})

const hasActiveFilter = computed(
  () =>
    Boolean(filters.q.trim()) ||
    Boolean(filters.kategori_id) ||
    Boolean(filters.jenis) ||
    filters.status_stok !== 'semua',
)

async function loadKategoriOptions() {
  try {
    const res = await kategoriApi.options()
    kategoriOptions.value = Array.isArray(res) ? res : res?.data || []
  } catch {
    kategoriOptions.value = []
  }
}

async function fetchMatrix() {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (filters.status_stok && filters.status_stok !== 'semua') {
      params.status_stok = filters.status_stok
    }
    if (filters.q.trim()) params.q = filters.q.trim()
    if (filters.kategori_id) params.kategori_id = Number(filters.kategori_id)
    if (filters.jenis) params.jenis = filters.jenis

    const res = await dashboardApi.monitoring(params)
    matrix.value = {
      lokasi: res?.lokasi || [],
      baris: res?.baris || [],
      total_per_lokasi: res?.total_per_lokasi || {},
      total_jumlah: Number(res?.total_jumlah || 0),
      total_nilai: Number(res?.total_nilai || 0),
    }
  } catch (err) {
    error.value = err?.message || 'Gagal memuat matriks monitoring stock.'
  } finally {
    loading.value = false
  }
}

let searchTimer = null
watch(
  () => filters.q,
  () => {
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      fetchMatrix()
    }, 250)
  },
)

watch(
  () => [filters.kategori_id, filters.jenis, filters.status_stok],
  () => {
    clearTimeout(searchTimer)
    fetchMatrix()
  },
)

function resetFilters() {
  filters.q = ''
  filters.kategori_id = ''
  filters.jenis = ''
  filters.status_stok = 'semua'
}

function openKartuStok({ produk, lokasi }) {
  kartuModal.produk = produk
  kartuModal.lokasi = lokasi
  kartuModal.open = true
}

function closeKartuStok() {
  kartuModal.open = false
}

function totalLokasi(kode) {
  return (
    matrix.value.total_per_lokasi?.[kode] || {
      total_jumlah: 0,
      total_nilai: 0,
    }
  )
}

onMounted(() => {
  loadKategoriOptions()
  fetchMatrix()
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">Monitoring Matriks Stock</h1>
        <p class="page-subtitle">
          Sebaran stock dan nilai persediaan produk di seluruh lokasi yang dapat diakses.
        </p>
      </div>
      <div class="action-group">
        <button type="button" class="btn btn-secondary" :disabled="loading" @click="fetchMatrix">
          <span v-if="loading" class="btn-spinner" aria-hidden="true"></span>
          <AppIcon v-else name="refresh" :size="18" />
          <span>{{ loading ? 'Memuat...' : 'Muat ulang' }}</span>
        </button>
      </div>
    </header>

    <div class="toolbar">
      <div class="toolbar-search">
        <label for="mon-q" class="toolbar-label">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="mon-q"
            v-model="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari SKU atau nama produk..."
          />
        </div>
      </div>

      <div class="toolbar-group">
        <div class="toolbar-field">
          <label for="mon-kategori" class="toolbar-label">Kategori</label>
          <select id="mon-kategori" v-model="filters.kategori_id" class="input input-sm">
            <option value="">Semua kategori</option>
            <option v-for="kat in kategoriOptions" :key="kat.id" :value="String(kat.id)">
              {{ kat.nama }}
            </option>
          </select>
        </div>

        <div class="toolbar-field">
          <label for="mon-jenis" class="toolbar-label">Jenis Produk</label>
          <select id="mon-jenis" v-model="filters.jenis" class="input input-sm">
            <option value="">Semua jenis</option>
            <option v-for="(label, key) in KATEGORI_TYPE_LABELS" :key="key" :value="key">
              {{ label }}
            </option>
          </select>
        </div>

        <div class="toolbar-field">
          <label for="mon-status" class="toolbar-label">Status Stock</label>
          <select id="mon-status" v-model="filters.status_stok" class="input input-sm">
            <option value="semua">Semua status</option>
            <option value="aman">Aman</option>
            <option value="menipis">Menipis</option>
            <option value="habis">Habis</option>
          </select>
        </div>

        <div v-if="hasActiveFilter" class="toolbar-field">
          <label class="toolbar-label">&nbsp;</label>
          <button type="button" class="btn btn-secondary btn-sm" @click="resetFilters">
            Reset filter
          </button>
        </div>
      </div>
    </div>

    <LoadingState v-if="loading" message="Memuat matriks monitoring stock..." :rows="6" />

    <ErrorState v-else-if="error" :message="error" @retry="fetchMatrix" />

    <template v-else>
      <div class="summary-strip">
        <div class="summary-item">
          <span class="detail-label">Total Nilai Persediaan</span>
          <strong class="detail-value num" :title="formatRupiah(matrix.total_nilai)">
            {{ formatRupiahCompact(matrix.total_nilai) }}
          </strong>
          <small class="field-hint num">
            {{ formatRupiah(matrix.total_nilai) }} · {{ formatNumber(matrix.total_jumlah) }} unit ({{ matrix.baris.length }} SKU)
          </small>
        </div>

        <div
          v-for="lok in matrix.lokasi"
          :key="lok.id"
          class="summary-item"
        >
          <span class="detail-label">{{ lok.kode }} · {{ lok.nama }}</span>
          <strong class="detail-value num" :title="formatRupiah(totalLokasi(lok.kode).total_nilai)">
            {{ formatRupiahCompact(totalLokasi(lok.kode).total_nilai) }}
          </strong>
          <small class="field-hint num">
            {{ LOKASI_TYPE_LABELS[lok.jenis] || lok.jenis }} · {{ formatNumber(totalLokasi(lok.kode).total_jumlah) }} unit
          </small>
        </div>
      </div>

      <EmptyState
        v-if="!matrix.baris.length"
        icon="grid"
        title="Tidak ada produk yang cocok dengan filter"
        description="Ubah kata kunci pencarian atau pilih filter status stok yang lain."
        :action-label="hasActiveFilter ? 'Reset filter' : ''"
        @action="resetFilters"
      />

      <MatriksStok
        v-else
        :lokasi="matrix.lokasi"
        :baris="matrix.baris"
        :total-per-lokasi="matrix.total_per_lokasi"
        :total-jumlah="matrix.total_jumlah"
        :total-nilai="matrix.total_nilai"
        @select-cell="openKartuStok"
      />
    </template>

    <KartuStokModal
      :open="kartuModal.open"
      :produk="kartuModal.produk"
      :lokasi="kartuModal.lokasi"
      @close="closeKartuStok"
    />
  </section>
</template>
