<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import KartuStokModal from '@/components/KartuStokModal.vue'
import LoadingState from '@/components/LoadingState.vue'
import { dashboardApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import {
  CUSTOMER_TYPE_LABELS,
  LOKASI_TYPE_LABELS,
  LOKASI_TYPES,
  MUTASI_TYPE_LABELS,
  ROLE_LABELS,
  ROLES,
} from '@/utils/constants'
import {
  formatDate,
  formatDateTime,
  formatNumber,
  formatRupiah,
  formatRupiahCompact,
} from '@/utils/format'

const auth = useAuthStore()

const loading = ref(true)
const error = ref('')
const dashboard = ref(null)

const trenLoading = ref(false)
const trenError = ref('')
const trenData = ref([])
const trenFilter = reactive({
  hari: 14,
  lokasi_id: '',
})

const kartuModal = reactive({
  open: false,
  produk: null,
  lokasi: null,
})

const isDeliveryman = computed(() => auth.user?.role === ROLES.DELIVERYMAN)
const isAdmin = computed(() => auth.user?.role === ROLES.ADMIN)
const isGudangUtama = computed(
  () => auth.user?.lokasi?.jenis === LOKASI_TYPES.GUDANG_UTAMA,
)

const subtitleText = computed(() => {
  const roleLabel = ROLE_LABELS[auth.user?.role] || 'User'
  const lok = auth.user?.lokasi
  if (lok) return `Halo, ${auth.user?.name} · ${roleLabel} (${lok.kode} · ${lok.nama})`
  return `Halo, ${auth.user?.name} · ${roleLabel} (Semua lokasi aktif)`
})

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const res = await dashboardApi.summary()
    dashboard.value = res
    if (!isDeliveryman.value) {
      await loadTren()
    }
  } catch (err) {
    error.value = err?.message || 'Gagal memuat ringkasan dashboard.'
  } finally {
    loading.value = false
  }
}

async function loadTren() {
  if (isDeliveryman.value) return
  trenLoading.value = true
  trenError.value = ''
  try {
    const params = { hari: Number(trenFilter.hari || 14) }
    if (isAdmin.value && trenFilter.lokasi_id) {
      params.lokasi_id = Number(trenFilter.lokasi_id)
    }
    const res = await dashboardApi.tren(params)
    trenData.value = res?.data || []
  } catch (err) {
    trenError.value = err?.message || 'Gagal memuat grafik tren mutasi.'
  } finally {
    trenLoading.value = false
  }
}

watch(
  () => [trenFilter.hari, trenFilter.lokasi_id],
  () => {
    if (!loading.value && !isDeliveryman.value) {
      loadTren()
    }
  },
)

// perhitungan grafik batang nilai persediaan & omzet 30 hari per lokasi
const barChartModel = computed(() => {
  const rows = dashboard.value?.per_lokasi || []
  if (!rows.length) return { bars: [], ticks: [], maxVal: 1 }

  const rawMax = Math.max(
    1,
    ...rows.flatMap((r) => [Number(r.nilai_persediaan || 0), Number(r.omzet_30_hari || 0)]),
  )
  const magnitude = 10 ** Math.floor(Math.log10(rawMax))
  const niceMax = Math.ceil(rawMax / magnitude) * magnitude || 1

  const chartLeft = 84
  const chartRight = 656
  const chartTop = 24
  const chartBottom = 216
  const plotWidth = chartRight - chartLeft
  const plotHeight = chartBottom - chartTop

  const groupWidth = plotWidth / rows.length
  const barWidth = Math.min(28, Math.max(12, Math.floor(groupWidth * 0.28)))
  const barGap = 6

  const bars = rows.map((row, idx) => {
    const centerX = chartLeft + groupWidth * idx + groupWidth / 2
    const nilai = Number(row.nilai_persediaan || 0)
    const omzet = Number(row.omzet_30_hari || 0)
    const nilaiHeight = Math.max(nilai > 0 ? 3 : 0, Math.round((nilai / niceMax) * plotHeight))
    const omzetHeight = Math.max(omzet > 0 ? 3 : 0, Math.round((omzet / niceMax) * plotHeight))

    return {
      ...row,
      centerX,
      nilaiX: centerX - barWidth - barGap / 2,
      nilaiY: chartBottom - nilaiHeight,
      nilaiHeight,
      omzetX: centerX + barGap / 2,
      omzetY: chartBottom - omzetHeight,
      omzetHeight,
      barWidth,
    }
  })

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const val = Math.round(niceMax * ratio)
    const y = Math.round(chartBottom - ratio * plotHeight)
    return { val, y, label: formatRupiahCompact(val) }
  })

  return {
    bars,
    ticks,
    chartLeft,
    chartRight,
    chartTop,
    chartBottom,
  }
})

// perhitungan grafik garis tren mutasi masuk dan keluar harian
const lineChartModel = computed(() => {
  const rows = trenData.value || []
  const chartLeft = 64
  const chartRight = 656
  const chartTop = 24
  const chartBottom = 204
  const plotWidth = chartRight - chartLeft
  const plotHeight = chartBottom - chartTop

  if (!rows.length) {
    return {
      points: [],
      masukPath: '',
      keluarPath: '',
      ticks: [],
      totalMasuk: 0,
      totalKeluar: 0,
      chartLeft,
      chartRight,
      chartBottom,
    }
  }

  const rawMax = Math.max(
    4,
    ...rows.flatMap((r) => [Number(r.masuk || 0), Number(r.keluar || 0)]),
  )
  const niceMax = Math.ceil(rawMax / 4) * 4

  const stepX = rows.length > 1 ? plotWidth / (rows.length - 1) : 0
  const labelStride = rows.length > 20 ? 5 : rows.length > 10 ? 2 : 1

  const points = rows.map((r, idx) => {
    const x = rows.length > 1 ? Math.round(chartLeft + idx * stepX) : Math.round(chartLeft + plotWidth / 2)
    const masuk = Number(r.masuk || 0)
    const keluar = Number(r.keluar || 0)
    const masukY = Math.round(chartBottom - (masuk / niceMax) * plotHeight)
    const keluarY = Math.round(chartBottom - (keluar / niceMax) * plotHeight)
    const shortDate = String(r.tanggal || '').slice(5)
    return {
      tanggal: r.tanggal,
      shortDate,
      showLabel: idx === 0 || idx === rows.length - 1 || idx % labelStride === 0,
      x,
      masuk,
      keluar,
      masukY,
      keluarY,
    }
  })

  const masukPath = points
    .map((pt, idx) => `${idx === 0 ? 'M' : 'L'}${pt.x},${pt.masukY}`)
    .join(' ')
  const keluarPath = points
    .map((pt, idx) => `${idx === 0 ? 'M' : 'L'}${pt.x},${pt.keluarY}`)
    .join(' ')

  const ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const val = Math.round(niceMax * ratio)
    const y = Math.round(chartBottom - ratio * plotHeight)
    return { val, y, label: formatNumber(val) }
  })

  const totalMasuk = points.reduce((acc, pt) => acc + pt.masuk, 0)
  const totalKeluar = points.reduce((acc, pt) => acc + pt.keluar, 0)

  return {
    points,
    masukPath,
    keluarPath,
    ticks,
    totalMasuk,
    totalKeluar,
    chartLeft,
    chartRight,
    chartBottom,
  }
})

function tugasRoute(tugas) {
  if (tugas.jenis === 'terima_pengiriman' || tugas.jenis === 'kirim_pengiriman') {
    return { name: 'pengiriman' }
  }
  if (tugas.jenis === 'setujui_permintaan') {
    return { name: 'permintaan' }
  }
  if (tugas.jenis === 'terima_pembelian') {
    return { name: 'pembelian' }
  }
  return { name: 'dashboard' }
}

function tugasActionLabel(jenis) {
  if (jenis === 'terima_pengiriman') return 'Konfirmasi terima'
  if (jenis === 'kirim_pengiriman') return 'Kirim sekarang'
  if (jenis === 'setujui_permintaan') return 'Proses permintaan'
  if (jenis === 'terima_pembelian') return 'Terima barang PO'
  return 'Buka dokumen'
}

function openKartuFromKritis(item) {
  kartuModal.produk = {
    id: item.produk_id,
    sku: item.sku,
    nama: item.nama_produk,
    satuan: item.satuan,
  }
  kartuModal.lokasi = {
    id: item.lokasi_id,
    kode: item.lokasi_kode,
    nama: item.lokasi_nama,
  }
  kartuModal.open = true
}

function closeKartuModal() {
  kartuModal.open = false
}

onMounted(() => {
  loadDashboard()
})
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">{{ subtitleText }}</p>
      </div>

      <div class="action-group">
        <template v-if="!isDeliveryman && !isAdmin">
          <RouterLink :to="{ name: 'penjualan' }" class="btn btn-primary">
            <AppIcon name="receipt" :size="18" />
            <span>Penjualan baru</span>
          </RouterLink>
          <RouterLink
            v-if="isGudangUtama"
            :to="{ name: 'pengiriman' }"
            class="btn btn-secondary"
          >
            <AppIcon name="truck" :size="18" />
            <span>Pengiriman</span>
          </RouterLink>
          <RouterLink
            v-else
            :to="{ name: 'permintaan' }"
            class="btn btn-secondary"
          >
            <AppIcon name="clipboard" :size="18" />
            <span>Ajukan permintaan</span>
          </RouterLink>
        </template>

        <button type="button" class="btn btn-secondary" :disabled="loading" @click="loadDashboard">
          <AppIcon name="refresh" :size="18" />
          <span>Muat ulang</span>
        </button>
      </div>
    </header>

    <LoadingState v-if="loading" message="Memuat ringkasan dashboard..." :rows="6" />

    <ErrorState v-else-if="error" :message="error" @retry="loadDashboard" />

    <template v-else-if="dashboard">
      <!-- ==================== TAMPILAN ADMIN ==================== -->
      <template v-if="dashboard.peran === 'admin'">
        <div class="dash-tile-grid">
          <RouterLink :to="{ name: 'monitoring' }" class="dash-tile">
            <span class="dash-tile-label">Nilai Persediaan</span>
            <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_persediaan)">
              {{ formatRupiahCompact(dashboard.ringkasan.nilai_persediaan) }}
            </strong>
            <span class="dash-tile-meta num">
              {{ formatRupiah(dashboard.ringkasan.nilai_persediaan) }} · {{ dashboard.per_lokasi.length }} lokasi
            </span>
          </RouterLink>

          <RouterLink :to="{ name: 'penjualan', query: { status: 'diposting' } }" class="dash-tile">
            <span class="dash-tile-label">Omzet 30 Hari</span>
            <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.omzet_30_hari)">
              {{ formatRupiahCompact(dashboard.ringkasan.omzet_30_hari) }}
            </strong>
            <span class="dash-tile-meta num">
              {{ formatRupiah(dashboard.ringkasan.omzet_30_hari) }}
            </span>
          </RouterLink>

          <RouterLink :to="{ name: 'pengiriman', query: { status: 'dikirim' } }" class="dash-tile">
            <span class="dash-tile-label">Nilai dalam Perjalanan</span>
            <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_dalam_perjalanan)">
              {{ formatRupiahCompact(dashboard.ringkasan.nilai_dalam_perjalanan) }}
            </strong>
            <span class="dash-tile-meta num">
              {{ formatNumber(dashboard.ringkasan.pengiriman_dalam_perjalanan) }} pengiriman aktif
            </span>
          </RouterLink>

          <RouterLink :to="{ name: 'pembelian', query: { status: 'dipesan' } }" class="dash-tile">
            <span class="dash-tile-label">Nilai PO Terbuka</span>
            <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_po_terbuka)">
              {{ formatRupiahCompact(dashboard.ringkasan.nilai_po_terbuka) }}
            </strong>
            <span class="dash-tile-meta num">
              {{ formatRupiah(dashboard.ringkasan.nilai_po_terbuka) }}
            </span>
          </RouterLink>

          <RouterLink
            :to="{ name: 'monitoring', query: { status_stok: 'menipis' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.stok_menipis > 0 }"
          >
            <span class="dash-tile-label">Stock Menipis</span>
            <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.stok_menipis) }} SKU</strong>
            <span class="dash-tile-meta">Di atas 0 sampai batas minimum</span>
          </RouterLink>

          <RouterLink
            :to="{ name: 'monitoring', query: { status_stok: 'habis' } }"
            class="dash-tile"
            :class="{ 'dash-tile-bahaya': dashboard.ringkasan.stok_habis > 0 }"
          >
            <span class="dash-tile-label">Stock Habis</span>
            <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.stok_habis) }} SKU</strong>
            <span class="dash-tile-meta">Saldo 0 pada SKU wajib tersedia</span>
          </RouterLink>

          <RouterLink
            :to="{ name: 'permintaan', query: { status: 'diajukan' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.permintaan_menunggu > 0 }"
          >
            <span class="dash-tile-label">Permintaan Menunggu</span>
            <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.permintaan_menunggu) }}</strong>
            <span class="dash-tile-meta">Menunggu keputusan Gudang Utama</span>
          </RouterLink>

          <RouterLink
            :to="{ name: 'users', query: { status: 'menunggu' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.akun_menunggu > 0 }"
          >
            <span class="dash-tile-label">Akun Menunggu</span>
            <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.akun_menunggu) }}</strong>
            <span class="dash-tile-meta">Registrasi baru perlu disetujui</span>
          </RouterLink>
        </div>

        <div class="dash-grid-2">
          <!-- Grafik 1: Batang Nilai Persediaan & Omzet 30 Hari per Lokasi -->
          <article class="card chart-card">
            <div class="chart-header">
              <div>
                <h2 class="section-title">Nilai Persediaan &amp; Omzet per Lokasi</h2>
                <p class="field-hint">Perbandingan nilai stock (HPP) dan omzet penjualan 30 hari terakhir</p>
              </div>
              <div class="chart-legend" aria-label="Legenda grafik nilai per lokasi">
                <span class="chart-legend-item">
                  <span class="chart-swatch chart-swatch-kopi"></span>
                  <span>Nilai Persediaan</span>
                </span>
                <span class="chart-legend-item">
                  <span class="chart-swatch chart-swatch-biru"></span>
                  <span>Omzet 30 Hari</span>
                </span>
              </div>
            </div>

            <div class="chart-svg-wrap">
              <svg
                class="chart-svg"
                viewBox="0 0 680 256"
                role="img"
                aria-label="Grafik batang nilai persediaan dan omzet 30 hari per lokasi"
              >
                <g v-for="t in barChartModel.ticks" :key="t.val">
                  <line
                    :x1="barChartModel.chartLeft"
                    :y1="t.y"
                    :x2="barChartModel.chartRight"
                    :y2="t.y"
                    class="chart-grid-line"
                  />
                  <text :x="barChartModel.chartLeft - 8" :y="t.y + 4" text-anchor="end" class="chart-axis-text">
                    {{ t.label }}
                  </text>
                </g>

                <g v-for="bar in barChartModel.bars" :key="bar.lokasi_id">
                  <rect
                    :x="bar.nilaiX"
                    :y="bar.nilaiY"
                    :width="bar.barWidth"
                    :height="bar.nilaiHeight"
                    rx="3"
                    class="chart-bar-kopi"
                  >
                    <title>{{ bar.kode }} ({{ bar.nama }}) - Nilai Persediaan: {{ formatRupiah(bar.nilai_persediaan) }}</title>
                  </rect>
                  <rect
                    :x="bar.omzetX"
                    :y="bar.omzetY"
                    :width="bar.barWidth"
                    :height="bar.omzetHeight"
                    rx="3"
                    class="chart-bar-biru"
                  >
                    <title>{{ bar.kode }} ({{ bar.nama }}) - Omzet 30 Hari: {{ formatRupiah(bar.omzet_30_hari) }}</title>
                  </rect>
                  <text :x="bar.centerX" :y="barChartModel.chartBottom + 18" text-anchor="middle" class="chart-axis-code">
                    {{ bar.kode }}
                  </text>
                  <text :x="bar.centerX" :y="barChartModel.chartBottom + 32" text-anchor="middle" class="chart-axis-sub">
                    {{ bar.sku_ada }} SKU
                  </text>
                </g>
              </svg>
            </div>

            <details class="chart-alt-details">
              <summary>Tabel data nilai persediaan dan omzet per lokasi</summary>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Lokasi</th>
                      <th scope="col">Jenis</th>
                      <th scope="col" class="num">SKU Ada</th>
                      <th scope="col" class="num">Menipis</th>
                      <th scope="col" class="num">Habis</th>
                      <th scope="col" class="num">Nilai Persediaan</th>
                      <th scope="col" class="num">Omzet 30 Hari</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="lok in dashboard.per_lokasi" :key="lok.lokasi_id">
                      <td data-label="Lokasi">
                        <strong>{{ lok.kode }}</strong> · {{ lok.nama }}
                      </td>
                      <td data-label="Jenis">{{ LOKASI_TYPE_LABELS[lok.jenis] || lok.jenis }}</td>
                      <td data-label="SKU Ada" class="num">{{ formatNumber(lok.sku_ada) }}</td>
                      <td data-label="Menipis" class="num">{{ formatNumber(lok.menipis) }}</td>
                      <td data-label="Habis" class="num">{{ formatNumber(lok.habis) }}</td>
                      <td data-label="Nilai Persediaan" class="num">{{ formatRupiah(lok.nilai_persediaan) }}</td>
                      <td data-label="Omzet 30 Hari" class="num">{{ formatRupiah(lok.omzet_30_hari) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </details>
          </article>

          <!-- Grafik 2: Garis Tren Mutasi Harian -->
          <article class="card chart-card">
            <div class="chart-header">
              <div>
                <h2 class="section-title">Tren Mutasi Stock Harian</h2>
                <p class="field-hint">
                  Masuk <strong class="num">{{ formatNumber(lineChartModel.totalMasuk) }}</strong> unit ·
                  Keluar <strong class="num">{{ formatNumber(lineChartModel.totalKeluar) }}</strong> unit
                </p>
              </div>
              <div class="chart-controls">
                <label for="adm-tren-lokasi" class="sr-only">Filter Lokasi Tren</label>
                <select id="adm-tren-lokasi" v-model="trenFilter.lokasi_id" class="input input-sm">
                  <option value="">Semua lokasi</option>
                  <option
                    v-for="lok in dashboard.per_lokasi"
                    :key="lok.lokasi_id"
                    :value="String(lok.lokasi_id)"
                  >
                    {{ lok.kode }} · {{ lok.nama }}
                  </option>
                </select>
                <label for="adm-tren-hari" class="sr-only">Rentang Hari Tren</label>
                <select id="adm-tren-hari" v-model="trenFilter.hari" class="input input-sm">
                  <option :value="7">7 hari</option>
                  <option :value="14">14 hari</option>
                  <option :value="30">30 hari</option>
                </select>
              </div>
            </div>

            <div class="chart-legend" aria-label="Legenda grafik tren mutasi">
              <span class="chart-legend-item">
                <span class="chart-swatch chart-swatch-hijau"></span>
                <span>Barang Masuk (garis utuh)</span>
              </span>
              <span class="chart-legend-item">
                <span class="chart-swatch chart-swatch-merah"></span>
                <span>Barang Keluar (garis putus-putus)</span>
              </span>
            </div>

            <ErrorState v-if="trenError" :message="trenError" @retry="loadTren" />
            <div v-else class="chart-svg-wrap">
              <svg
                class="chart-svg"
                viewBox="0 0 680 240"
                role="img"
                aria-label="Grafik garis tren mutasi barang masuk dan keluar harian"
              >
                <g v-for="t in lineChartModel.ticks" :key="t.val">
                  <line
                    :x1="lineChartModel.chartLeft"
                    :y1="t.y"
                    :x2="lineChartModel.chartRight"
                    :y2="t.y"
                    class="chart-grid-line"
                  />
                  <text :x="lineChartModel.chartLeft - 8" :y="t.y + 4" text-anchor="end" class="chart-axis-text">
                    {{ t.label }}
                  </text>
                </g>

                <path :d="lineChartModel.masukPath" class="chart-line-masuk" />
                <path :d="lineChartModel.keluarPath" class="chart-line-keluar" />

                <g v-for="pt in lineChartModel.points" :key="pt.tanggal">
                  <circle :cx="pt.x" :cy="pt.masukY" r="3.5" class="chart-dot-masuk">
                    <title>{{ formatDate(pt.tanggal) }} - Masuk: {{ formatNumber(pt.masuk) }} unit</title>
                  </circle>
                  <rect
                    :x="pt.x - 3"
                    :y="pt.keluarY - 3"
                    width="6"
                    height="6"
                    class="chart-dot-keluar"
                  >
                    <title>{{ formatDate(pt.tanggal) }} - Keluar: {{ formatNumber(pt.keluar) }} unit</title>
                  </rect>
                  <text
                    v-if="pt.showLabel"
                    :x="pt.x"
                    :y="lineChartModel.chartBottom + 20"
                    text-anchor="middle"
                    class="chart-axis-sub"
                  >
                    {{ pt.shortDate }}
                  </text>
                </g>
              </svg>
            </div>

            <details class="chart-alt-details">
              <summary>Tabel data tren mutasi harian ({{ trenFilter.hari }} hari)</summary>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Tanggal</th>
                      <th scope="col" class="num">Barang Masuk</th>
                      <th scope="col" class="num">Barang Keluar</th>
                      <th scope="col" class="num">Selisih</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="pt in trenData" :key="pt.tanggal">
                      <td data-label="Tanggal">{{ formatDate(pt.tanggal) }}</td>
                      <td data-label="Barang Masuk" class="num">+{{ formatNumber(pt.masuk) }}</td>
                      <td data-label="Barang Keluar" class="num">-{{ formatNumber(pt.keluar) }}</td>
                      <td data-label="Selisih" class="num">
                        {{ pt.masuk - pt.keluar >= 0 ? `+${formatNumber(pt.masuk - pt.keluar)}` : formatNumber(pt.masuk - pt.keluar) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </details>
          </article>
        </div>
      </template>

      <!-- ==================== TAMPILAN MANAGER (GUDANG & OUTLET) ==================== -->
      <template v-else-if="dashboard.peran === 'manager_gudang' || dashboard.peran === 'manager_outlet'">
        <div class="dash-tile-grid">
          <RouterLink :to="{ name: 'stok' }" class="dash-tile">
            <span class="dash-tile-label">Nilai Persediaan Lokasi</span>
            <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_persediaan)">
              {{ formatRupiahCompact(dashboard.ringkasan.nilai_persediaan) }}
            </strong>
            <span class="dash-tile-meta num">
              {{ formatNumber(dashboard.ringkasan.sku_ada) }} SKU tersedia di {{ dashboard.lokasi.kode }}
            </span>
          </RouterLink>

          <RouterLink :to="{ name: 'penjualan', query: { status: 'diposting' } }" class="dash-tile">
            <span class="dash-tile-label">Omzet 30 Hari</span>
            <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.omzet_30_hari)">
              {{ formatRupiahCompact(dashboard.ringkasan.omzet_30_hari) }}
            </strong>
            <span class="dash-tile-meta num">{{ formatRupiah(dashboard.ringkasan.omzet_30_hari) }}</span>
          </RouterLink>

          <RouterLink
            :to="{ name: 'stok', query: { status_stok: 'menipis' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.stok_menipis > 0 }"
          >
            <span class="dash-tile-label">Stock Menipis</span>
            <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.stok_menipis) }} SKU</strong>
            <span class="dash-tile-meta">Perlu pengajuan atau pengisian stock</span>
          </RouterLink>

          <RouterLink
            :to="{ name: 'stok', query: { status_stok: 'habis' } }"
            class="dash-tile"
            :class="{ 'dash-tile-bahaya': dashboard.ringkasan.stok_habis > 0 }"
          >
            <span class="dash-tile-label">Stock Habis</span>
            <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.stok_habis) }} SKU</strong>
            <span class="dash-tile-meta">Saldo 0 pada SKU wajib tersedia</span>
          </RouterLink>

          <RouterLink :to="{ name: 'transaksi' }" class="dash-tile">
            <span class="dash-tile-label">Mutasi Hari Ini (WIB)</span>
            <strong class="dash-tile-value num">
              +{{ formatNumber(dashboard.ringkasan.masuk_hari_ini) }} / -{{ formatNumber(dashboard.ringkasan.keluar_hari_ini) }}
            </strong>
            <span class="dash-tile-meta">Unit masuk dan keluar hari ini</span>
          </RouterLink>

          <RouterLink
            :to="{ name: 'pengiriman', query: { status: 'dikirim' } }"
            class="dash-tile"
            :class="{ 'dash-tile-proses': dashboard.ringkasan.pengiriman_masuk_menunggu > 0 }"
          >
            <span class="dash-tile-label">Pengiriman Masuk</span>
            <strong class="dash-tile-value num">
              {{ formatNumber(dashboard.ringkasan.pengiriman_masuk_menunggu) }}
            </strong>
            <span class="dash-tile-meta">Dalam perjalanan ke {{ dashboard.lokasi.kode }}</span>
          </RouterLink>

          <RouterLink
            v-if="isGudangUtama"
            :to="{ name: 'permintaan', query: { status: 'diajukan' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.permintaan_menunggu > 0 }"
          >
            <span class="dash-tile-label">Permintaan Cabang/Outlet</span>
            <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.permintaan_menunggu) }}</strong>
            <span class="dash-tile-meta">Menunggu disetujui Gudang Utama</span>
          </RouterLink>

          <RouterLink
            v-else
            :to="{ name: 'permintaan' }"
            class="dash-tile"
          >
            <span class="dash-tile-label">Permintaan Supply Saya</span>
            <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.permintaan_saya_aktif) }}</strong>
            <span class="dash-tile-meta">Berstatus diajukan atau disetujui</span>
          </RouterLink>

          <RouterLink
            v-if="isGudangUtama"
            :to="{ name: 'pembelian', query: { status: 'dipesan' } }"
            class="dash-tile"
          >
            <span class="dash-tile-label">Nilai PO Terbuka</span>
            <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_po_terbuka)">
              {{ formatRupiahCompact(dashboard.ringkasan.nilai_po_terbuka) }}
            </strong>
            <span class="dash-tile-meta">Pesanan ke supplier belum diterima</span>
          </RouterLink>
        </div>

        <div class="dash-grid-2">
          <!-- Kartu Perlu Tindakan -->
          <article class="card">
            <div class="section-header-row">
              <div>
                <h2 class="section-title">Perlu Tindakan</h2>
                <p class="field-hint">Dokumen aktif yang membutuhkan konfirmasi atau keputusan</p>
              </div>
              <BadgeStatus :value="dashboard.tugas.length ? 'menunggu' : 'aman'" :label="`${dashboard.tugas.length} tugas`" />
            </div>

            <EmptyState
              v-if="!dashboard.tugas.length"
              icon="check"
              title="Semua dokumen sudah tertangani"
              description="Tidak ada pengiriman masuk, permintaan atau PO terbuka yang menunggu tindakan."
            />

            <ul v-else class="task-list">
              <li v-for="t in dashboard.tugas" :key="`${t.jenis}-${t.id}`" class="task-item">
                <div class="task-item-info">
                  <div class="task-item-top">
                    <strong class="mono">{{ t.kode }}</strong>
                    <span class="field-hint">{{ formatDate(t.tanggal) }}</span>
                  </div>
                  <p class="task-item-desc">{{ t.keterangan }}</p>
                </div>
                <RouterLink :to="tugasRoute(t)" class="btn btn-secondary btn-small">
                  {{ tugasActionLabel(t.jenis) }}
                </RouterLink>
              </li>
            </ul>
          </article>

          <!-- Grafik Tren Mutasi Lokasi Manager -->
          <article class="card chart-card">
            <div class="chart-header">
              <div>
                <h2 class="section-title">Tren Mutasi {{ dashboard.lokasi.kode }}</h2>
                <p class="field-hint">
                  Masuk <strong class="num">{{ formatNumber(lineChartModel.totalMasuk) }}</strong> unit ·
                  Keluar <strong class="num">{{ formatNumber(lineChartModel.totalKeluar) }}</strong> unit
                </p>
              </div>
              <div class="chart-controls">
                <label for="mgr-tren-hari" class="sr-only">Rentang Hari Tren</label>
                <select id="mgr-tren-hari" v-model="trenFilter.hari" class="input input-sm">
                  <option :value="7">7 hari</option>
                  <option :value="14">14 hari</option>
                  <option :value="30">30 hari</option>
                </select>
              </div>
            </div>

            <div class="chart-legend" aria-label="Legenda grafik tren mutasi">
              <span class="chart-legend-item">
                <span class="chart-swatch chart-swatch-hijau"></span>
                <span>Barang Masuk (garis utuh)</span>
              </span>
              <span class="chart-legend-item">
                <span class="chart-swatch chart-swatch-merah"></span>
                <span>Barang Keluar (garis putus-putus)</span>
              </span>
            </div>

            <ErrorState v-if="trenError" :message="trenError" @retry="loadTren" />
            <div v-else class="chart-svg-wrap">
              <svg
                class="chart-svg"
                viewBox="0 0 680 240"
                role="img"
                aria-label="Grafik garis tren mutasi barang masuk dan keluar harian lokasi"
              >
                <g v-for="t in lineChartModel.ticks" :key="t.val">
                  <line
                    :x1="lineChartModel.chartLeft"
                    :y1="t.y"
                    :x2="lineChartModel.chartRight"
                    :y2="t.y"
                    class="chart-grid-line"
                  />
                  <text :x="lineChartModel.chartLeft - 8" :y="t.y + 4" text-anchor="end" class="chart-axis-text">
                    {{ t.label }}
                  </text>
                </g>

                <path :d="lineChartModel.masukPath" class="chart-line-masuk" />
                <path :d="lineChartModel.keluarPath" class="chart-line-keluar" />

                <g v-for="pt in lineChartModel.points" :key="pt.tanggal">
                  <circle :cx="pt.x" :cy="pt.masukY" r="3.5" class="chart-dot-masuk">
                    <title>{{ formatDate(pt.tanggal) }} - Masuk: {{ formatNumber(pt.masuk) }} unit</title>
                  </circle>
                  <rect
                    :x="pt.x - 3"
                    :y="pt.keluarY - 3"
                    width="6"
                    height="6"
                    class="chart-dot-keluar"
                  >
                    <title>{{ formatDate(pt.tanggal) }} - Keluar: {{ formatNumber(pt.keluar) }} unit</title>
                  </rect>
                  <text
                    v-if="pt.showLabel"
                    :x="pt.x"
                    :y="lineChartModel.chartBottom + 20"
                    text-anchor="middle"
                    class="chart-axis-sub"
                  >
                    {{ pt.shortDate }}
                  </text>
                </g>
              </svg>
            </div>

            <details class="chart-alt-details">
              <summary>Tabel data tren mutasi harian ({{ trenFilter.hari }} hari)</summary>
              <div class="table-wrap">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th scope="col">Tanggal</th>
                      <th scope="col" class="num">Barang Masuk</th>
                      <th scope="col" class="num">Barang Keluar</th>
                      <th scope="col" class="num">Selisih</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="pt in trenData" :key="pt.tanggal">
                      <td data-label="Tanggal">{{ formatDate(pt.tanggal) }}</td>
                      <td data-label="Barang Masuk" class="num">+{{ formatNumber(pt.masuk) }}</td>
                      <td data-label="Barang Keluar" class="num">-{{ formatNumber(pt.keluar) }}</td>
                      <td data-label="Selisih" class="num">
                        {{ pt.masuk - pt.keluar >= 0 ? `+${formatNumber(pt.masuk - pt.keluar)}` : formatNumber(pt.masuk - pt.keluar) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </details>
          </article>
        </div>
      </template>

      <!-- ==================== BAGIAN BERSAMA ADMIN & MANAGER ==================== -->
      <template v-if="dashboard.peran !== 'deliveryman'">
        <div class="dash-grid-2">
          <!-- Lima Customer Teratas (30 Hari) -->
          <article class="card">
            <div class="section-header-row">
              <div>
                <h2 class="section-title">Lima Customer Teratas (30 Hari)</h2>
                <p class="field-hint">Berdasarkan nilai penjualan yang sudah diposting</p>
              </div>
              <RouterLink :to="{ name: 'penjualan' }" class="btn btn-secondary btn-small">
                Semua penjualan
              </RouterLink>
            </div>

            <EmptyState
              v-if="!dashboard.customer_teratas?.length"
              icon="users"
              title="Belum ada penjualan 30 hari terakhir"
              description="Data customer teratas muncul setelah nota penjualan diposting."
            />

            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th scope="col">Customer</th>
                    <th scope="col">Jenis</th>
                    <th scope="col" class="num">Nota</th>
                    <th scope="col" class="num">Omzet 30 Hari</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(cust, idx) in dashboard.customer_teratas"
                    :key="cust.customer_id ?? `umum-${idx}`"
                  >
                    <td data-label="Customer">
                      <strong>{{ cust.nama }}</strong>
                    </td>
                    <td data-label="Jenis">
                      {{ cust.jenis ? CUSTOMER_TYPE_LABELS[cust.jenis] || cust.jenis : 'Eceran Outlet' }}
                    </td>
                    <td data-label="Nota" class="num">{{ formatNumber(cust.jumlah_nota) }}</td>
                    <td data-label="Omzet 30 Hari" class="num">
                      <strong>{{ formatRupiah(cust.omzet) }}</strong>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <!-- Stock Kritis -->
          <article class="card">
            <div class="section-header-row">
              <div>
                <h2 class="section-title">Stock Kritis (Menipis &amp; Habis)</h2>
                <p class="field-hint">Produk yang berada pada atau di bawah stock minimum</p>
              </div>
              <RouterLink :to="{ name: 'monitoring' }" class="btn btn-secondary btn-small">
                Buka matriks
              </RouterLink>
            </div>

            <EmptyState
              v-if="!dashboard.stok_kritis?.length"
              icon="check"
              title="Seluruh stock berada di batas aman"
              description="Tidak ada produk yang berstatus menipis atau habis."
            />

            <div v-else class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th scope="col">Lokasi</th>
                    <th scope="col">Produk</th>
                    <th scope="col" class="num">Stock / Min</th>
                    <th scope="col">Status</th>
                    <th scope="col" class="col-actions">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="item in dashboard.stok_kritis"
                    :key="`${item.lokasi_id}-${item.produk_id}`"
                  >
                    <td data-label="Lokasi">
                      <strong>{{ item.lokasi_kode }}</strong>
                      <div class="field-hint">{{ item.lokasi_nama }}</div>
                    </td>
                    <td data-label="Produk">
                      <span class="mono">{{ item.sku }}</span>
                      <div><strong>{{ item.nama_produk }}</strong></div>
                    </td>
                    <td data-label="Stock / Min" class="num">
                      <strong>{{ formatNumber(item.jumlah) }}</strong> / {{ formatNumber(item.stok_minimum) }} {{ item.satuan }}
                    </td>
                    <td data-label="Status">
                      <BadgeStatus :value="item.status_stok" />
                    </td>
                    <td class="col-actions">
                      <button
                        type="button"
                        class="btn btn-secondary btn-small"
                        @click="openKartuFromKritis(item)"
                      >
                        Stock Card
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <!-- Aktivitas Buku Besar Terbaru -->
        <article class="card">
          <div class="section-header-row">
            <div>
              <h2 class="section-title">Aktivitas Mutasi Stock Terbaru</h2>
              <p class="field-hint">10 pencatatan terakhir pada buku besar stock</p>
            </div>
            <RouterLink :to="{ name: 'stok' }" class="btn btn-secondary btn-small">
              Kelola stock
            </RouterLink>
          </div>

          <EmptyState
            v-if="!dashboard.aktivitas_terbaru?.length"
            icon="swap"
            title="Belum ada mutasi stock"
            description="Riwayat perubahan stock dari transaksi, pengiriman, pembelian dan penjualan akan tampil di sini."
          />

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th scope="col">Waktu</th>
                  <th scope="col">Lokasi</th>
                  <th scope="col">Produk</th>
                  <th scope="col">Jenis</th>
                  <th scope="col" class="num">Perubahan</th>
                  <th scope="col" class="num">Saldo Akhir</th>
                  <th scope="col">Dokumen</th>
                  <th scope="col">Oleh</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="akt in dashboard.aktivitas_terbaru" :key="akt.id">
                  <td data-label="Waktu">{{ formatDateTime(akt.waktu) }}</td>
                  <td data-label="Lokasi">
                    <strong>{{ akt.lokasi_kode }}</strong> · {{ akt.lokasi_nama }}
                  </td>
                  <td data-label="Produk">
                    <span class="mono">{{ akt.produk_sku }}</span> · {{ akt.produk_nama }}
                  </td>
                  <td data-label="Jenis">
                    <BadgeStatus
                      :value="akt.perubahan >= 0 ? 'masuk' : 'keluar'"
                      :label="MUTASI_TYPE_LABELS[akt.jenis] || akt.jenis"
                    />
                  </td>
                  <td data-label="Perubahan" class="num">
                    <strong :class="akt.perubahan >= 0 ? 'text-aman' : 'text-bahaya'">
                      {{ akt.perubahan >= 0 ? `+${formatNumber(akt.perubahan)}` : formatNumber(akt.perubahan) }}
                      {{ akt.satuan }}
                    </strong>
                  </td>
                  <td data-label="Saldo Akhir" class="num">
                    {{ formatNumber(akt.stok_sesudah) }} {{ akt.satuan }}
                  </td>
                  <td data-label="Dokumen">
                    <span class="mono">{{ akt.dokumen_kode || '-' }}</span>
                  </td>
                  <td data-label="Oleh">{{ akt.oleh }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </template>

      <!-- ==================== TAMPILAN DELIVERYMAN ==================== -->
      <template v-else>
        <div class="summary-strip">
          <div class="summary-item">
            <span class="detail-label">Pengiriman Sedang Diantar</span>
            <strong class="detail-value num">{{ formatNumber(dashboard.ringkasan.sedang_dikirim) }}</strong>
            <small class="field-hint">Tugas pengantaran aktif dalam perjalanan</small>
          </div>
          <div class="summary-item">
            <span class="detail-label">Riwayat Selesai Diantar</span>
            <strong class="detail-value num">{{ formatNumber(dashboard.ringkasan.selesai_diterima) }}</strong>
            <small class="field-hint">Pengiriman yang sudah dikonfirmasi lokasi tujuan</small>
          </div>
        </div>

        <article class="card">
          <div class="section-header-row">
            <div>
              <h2 class="section-title">Pengiriman yang Sedang Dibawa</h2>
              <p class="field-hint">Cetak atau tunjukkan surat jalan kepada manager lokasi penerima</p>
            </div>
            <RouterLink :to="{ name: 'pengiriman' }" class="btn btn-secondary btn-small">
              Daftar pengiriman
            </RouterLink>
          </div>

          <EmptyState
            v-if="!dashboard.pengiriman_aktif?.length"
            icon="truck"
            title="Tidak ada pengiriman yang sedang dibawa"
            description="Saat ini tidak ada pengiriman berstatus dikirim yang ditugaskan kepada Anda."
          />

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th scope="col">Kode</th>
                  <th scope="col">Tanggal Kirim</th>
                  <th scope="col">Asal</th>
                  <th scope="col">Tujuan</th>
                  <th scope="col">Kendaraan</th>
                  <th scope="col" class="num">Muatan</th>
                  <th scope="col" class="col-actions">Aksi</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in dashboard.pengiriman_aktif" :key="item.id">
                  <td data-label="Kode">
                    <strong class="mono">{{ item.kode }}</strong>
                  </td>
                  <td data-label="Tanggal Kirim">{{ formatDate(item.tanggal_kirim) }}</td>
                  <td data-label="Asal">
                    <strong>{{ item.lokasi_asal_kode }} · {{ item.lokasi_asal_nama }}</strong>
                    <div class="field-hint">{{ item.lokasi_asal_alamat }}</div>
                  </td>
                  <td data-label="Tujuan">
                    <strong>{{ item.lokasi_tujuan_kode }} · {{ item.lokasi_tujuan_nama }}</strong>
                    <div class="field-hint">{{ item.lokasi_tujuan_alamat }}</div>
                  </td>
                  <td data-label="Kendaraan">
                    {{ item.jenis_kendaraan || '-' }}
                    <div class="mono field-hint">{{ item.nomor_kendaraan || '' }}</div>
                  </td>
                  <td data-label="Muatan" class="num">
                    <strong>{{ formatNumber(item.total_jumlah) }} unit</strong>
                    <div class="field-hint">{{ formatNumber(item.jumlah_item) }} SKU</div>
                  </td>
                  <td class="col-actions">
                    <div class="action-group">
                      <RouterLink
                        :to="{ name: 'pengiriman-surat-jalan', params: { id: item.id } }"
                        class="btn btn-primary btn-small"
                      >
                        <AppIcon name="printer" :size="16" />
                        <span>Surat jalan</span>
                      </RouterLink>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

        <article class="card">
          <div class="section-header-row">
            <div>
              <h2 class="section-title">Riwayat Pengiriman Selesai</h2>
              <p class="field-hint">10 pengiriman terakhir yang sudah diterima lokasi tujuan</p>
            </div>
          </div>

          <EmptyState
            v-if="!dashboard.pengiriman_selesai?.length"
            icon="clipboard"
            title="Belum ada riwayat pengiriman selesai"
            description="Pengiriman yang sudah dikonfirmasi penerima akan tercatat di daftar ini."
          />

          <div v-else class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th scope="col">Kode</th>
                  <th scope="col">Tanggal Kirim</th>
                  <th scope="col">Diterima Pada</th>
                  <th scope="col">Rute</th>
                  <th scope="col" class="num">Muatan</th>
                  <th scope="col">Status</th>
                  <th scope="col" class="col-actions">Aksi</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in dashboard.pengiriman_selesai" :key="item.id">
                  <td data-label="Kode"><strong class="mono">{{ item.kode }}</strong></td>
                  <td data-label="Tanggal Kirim">{{ formatDate(item.tanggal_kirim) }}</td>
                  <td data-label="Diterima Pada">{{ formatDateTime(item.diterima_pada) }}</td>
                  <td data-label="Rute">
                    {{ item.lokasi_asal_kode }} ({{ item.lokasi_asal_nama }}) &rarr;
                    {{ item.lokasi_tujuan_kode }} ({{ item.lokasi_tujuan_nama }})
                  </td>
                  <td data-label="Muatan" class="num">
                    {{ formatNumber(item.total_jumlah) }} unit ({{ formatNumber(item.jumlah_item) }} SKU)
                  </td>
                  <td data-label="Status">
                    <BadgeStatus :value="item.status" />
                  </td>
                  <td class="col-actions">
                    <RouterLink
                      :to="{ name: 'pengiriman-surat-jalan', params: { id: item.id } }"
                      class="btn btn-secondary btn-small"
                    >
                      Surat jalan
                    </RouterLink>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </template>
    </template>

    <KartuStokModal
      :open="kartuModal.open"
      :produk="kartuModal.produk"
      :lokasi="kartuModal.lokasi"
      @close="closeKartuModal"
    />
  </section>
</template>
