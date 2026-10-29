<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import ChartTooltip from '@/components/ChartTooltip.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import KartuStokModal from '@/components/KartuStokModal.vue'
import LoadingState from '@/components/LoadingState.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import TrenChart from '@/components/TrenChart.vue'
import { dashboardApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import {
  CUSTOMER_TYPE_LABELS,
  KENDARAAN_TYPE_LABELS,
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
import { restockLink } from '@/utils/restock'

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
  stok: null,
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
  if (auth.user?.role === ROLES.DELIVERYMAN) return `Halo, ${auth.user?.name} · ${roleLabel}`
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

const hoverBar = ref(null)
const hoveredBar = computed(() => barChartModel.value.bars[hoverBar.value] ?? null)

// perhitungan grafik batang nilai persediaan dan omzet 30 hari per lokasi
const barChartModel = computed(() => {
  const rows = dashboard.value?.per_lokasi || []
  if (!rows.length) return { bars: [], ticks: [], maxVal: 1 }

  const rawMax = Math.max(
    1,
    ...rows.flatMap((r) => [Number(r.nilai || 0), Number(r.omzet_30_hari || 0)]),
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
    const groupX = chartLeft + groupWidth * idx
    const centerX = groupX + groupWidth / 2
    const nilai = Number(row.nilai || 0)
    const omzet = Number(row.omzet_30_hari || 0)
    const nilaiHeight = Math.max(nilai > 0 ? 3 : 0, Math.round((nilai / niceMax) * plotHeight))
    const omzetHeight = Math.max(omzet > 0 ? 3 : 0, Math.round((omzet / niceMax) * plotHeight))

    return {
      ...row,
      groupX,
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
    groupWidth,
    chartLeft,
    chartRight,
    chartTop,
    chartBottom,
  }
})

// total tren untuk judul kartu, grafiknya digambar TrenChart
const trenTotal = computed(() => ({
  masuk: trenData.value.reduce((sum, row) => sum + Number(row.masuk || 0), 0),
  keluar: trenData.value.reduce((sum, row) => sum + Number(row.keluar || 0), 0),
}))

function tugasRoute(tugas) {
  if (tugas.jenis === 'terima_pengiriman' || tugas.jenis === 'kirim_pengiriman') {
    return { name: 'pengiriman' }
  }
  if (tugas.jenis === 'proses_permintaan') {
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
  if (jenis === 'proses_permintaan') return 'Proses permintaan'
  if (jenis === 'terima_pembelian') return 'Terima barang PO'
  return 'Buka dokumen'
}

function restockAction(item) {
  return restockLink({
    lokasiId: item.lokasi_id,
    lokasiJenis: item.lokasi_jenis,
    produkId: item.produk_id,
    produkJenis: item.produk_jenis,
    jumlah: item.jumlah,
    stokMinimum: item.stok_minimum,
  })
}

function openKartuFromKritis(item) {
  kartuModal.produk = {
    id: item.produk_id,
    sku: item.sku,
    nama: item.nama,
    satuan: item.satuan,
  }
  kartuModal.lokasi = {
    id: item.lokasi_id,
    kode: item.lokasi,
    nama: item.lokasi_nama,
  }
  kartuModal.stok = {
    jumlah: item.jumlah,
    stokMinimum: item.stok_minimum,
    status: item.status_stok,
    lokasiJenis: item.lokasi_jenis,
    produkJenis: item.produk_jenis,
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
          <RouterLink :to="{ name: 'penjualan' }" class="btn btn-post">
            <AppIcon name="receipt" :size="18" />
            <span>Penjualan baru</span>
          </RouterLink>
          <RouterLink
            v-if="isGudangUtama"
            :to="{ name: 'pengiriman' }"
            class="btn btn-get"
          >
            <AppIcon name="truck" :size="18" />
            <span>Pengiriman</span>
          </RouterLink>
          <RouterLink
            v-else
            :to="{ name: 'permintaan' }"
            class="btn btn-post"
          >
            <AppIcon name="clipboard" :size="18" />
            <span>Ajukan permintaan</span>
          </RouterLink>
        </template>

        <button type="button" class="btn btn-secondary" :disabled="loading" @click="loadDashboard">
          <span v-if="loading" class="btn-spinner" aria-hidden="true"></span>
          <AppIcon v-else name="refresh" :size="18" />
          <span>{{ loading ? 'Memuat...' : 'Muat ulang' }}</span>
        </button>
      </div>
    </header>

    <LoadingState v-if="loading" message="Memuat ringkasan dashboard..." :rows="6" />

    <ErrorState v-else-if="error" :message="error" @retry="loadDashboard" />

    <template v-else-if="dashboard">
      <!-- banner sambutan user -->
      <div class="welcome-banner">
        <span class="welcome-banner-icon">
          <AppIcon name="check" :size="18" :stroke="2.5" />
        </span>
        <div class="welcome-banner-content">
          <strong class="welcome-banner-title">Selamat datang kembali, {{ auth.user?.name }}!</strong>
        </div>
      </div>

      <!-- tampilan admin -->
      <template v-if="dashboard.peran === 'admin'">
        <div class="dash-tile-grid">
          <RouterLink :to="{ name: 'monitoring' }" class="dash-tile">
            <div class="dash-tile-icon-box dash-icon-kopi">
              <AppIcon name="box" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Nilai Persediaan</span>
              <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_persediaan)">
                {{ formatRupiahCompact(dashboard.ringkasan.nilai_persediaan) }}
              </strong>
              <span class="dash-tile-meta num">
                {{ formatRupiah(dashboard.ringkasan.nilai_persediaan) }} · {{ dashboard.per_lokasi.length }} lokasi
              </span>
            </div>
          </RouterLink>

          <RouterLink :to="{ name: 'penjualan', query: { status: 'diposting' } }" class="dash-tile">
            <div class="dash-tile-icon-box dash-icon-hijau">
              <AppIcon name="receipt" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Omzet 30 Hari</span>
              <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.omzet_30_hari)">
                {{ formatRupiahCompact(dashboard.ringkasan.omzet_30_hari) }}
              </strong>
              <span class="dash-tile-meta num">
                {{ formatRupiah(dashboard.ringkasan.omzet_30_hari) }}
              </span>
            </div>
          </RouterLink>

          <RouterLink :to="{ name: 'pengiriman', query: { status: 'dikirim' } }" class="dash-tile">
            <div class="dash-tile-icon-box dash-icon-biru">
              <AppIcon name="truck" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Nilai dalam Perjalanan</span>
              <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_dalam_perjalanan)">
                {{ formatRupiahCompact(dashboard.ringkasan.nilai_dalam_perjalanan) }}
              </strong>
              <span class="dash-tile-meta num">
                {{ formatNumber(dashboard.ringkasan.pengiriman_dalam_perjalanan) }} pengiriman aktif
              </span>
            </div>
          </RouterLink>

          <RouterLink :to="{ name: 'pembelian', query: { status: 'dipesan' } }" class="dash-tile">
            <div class="dash-tile-icon-box dash-icon-ungu">
              <AppIcon name="cart" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Nilai PO Terbuka</span>
              <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_po_terbuka)">
                {{ formatRupiahCompact(dashboard.ringkasan.nilai_po_terbuka) }}
              </strong>
              <span class="dash-tile-meta num">
                {{ formatRupiah(dashboard.ringkasan.nilai_po_terbuka) }}
              </span>
            </div>
          </RouterLink>

          <RouterLink
            :to="{ name: 'monitoring', query: { status_stok: 'menipis' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.stok_menipis > 0 }"
          >
            <div class="dash-tile-icon-box dash-icon-amber">
              <AppIcon name="alert-triangle" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Stock Menipis</span>
              <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.stok_menipis) }} SKU</strong>
              <span class="dash-tile-meta">Di atas 0 sampai batas minimum</span>
            </div>
          </RouterLink>

          <RouterLink
            :to="{ name: 'monitoring', query: { status_stok: 'habis' } }"
            class="dash-tile"
            :class="{ 'dash-tile-bahaya': dashboard.ringkasan.stok_habis > 0 }"
          >
            <div class="dash-tile-icon-box dash-icon-merah">
              <AppIcon name="alert" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Stock Habis</span>
              <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.stok_habis) }} SKU</strong>
              <span class="dash-tile-meta">Stock 0 pada SKU wajib tersedia</span>
            </div>
          </RouterLink>

          <RouterLink
            :to="{ name: 'permintaan', query: { status: 'diajukan' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.permintaan_menunggu > 0 }"
          >
            <div class="dash-tile-icon-box dash-icon-biru">
              <AppIcon name="clipboard" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Permintaan Menunggu</span>
              <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.permintaan_menunggu) }}</strong>
              <span class="dash-tile-meta">Menunggu keputusan Gudang Utama</span>
            </div>
          </RouterLink>

          <RouterLink
            :to="{ name: 'users', query: { status: 'menunggu' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.akun_menunggu > 0 }"
          >
            <div class="dash-tile-icon-box dash-icon-cokelat">
              <AppIcon name="user-check" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Akun Menunggu</span>
              <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.akun_menunggu) }}</strong>
              <span class="dash-tile-meta">Registrasi baru perlu disetujui</span>
            </div>
          </RouterLink>
        </div>

        <div class="dash-grid-2">
          <!-- grafik batang nilai persediaan dan omzet 30 hari per lokasi -->
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
              <div class="chart-plot">
                <svg
                  class="chart-svg"
                  viewBox="0 0 680 256"
                  role="img"
                  aria-label="Grafik batang nilai persediaan dan omzet 30 hari per lokasi"
                  @pointerleave="hoverBar = null"
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

                  <g v-for="(bar, idx) in barChartModel.bars" :key="bar.id">
                    <!-- latar tipis menandai kolom lokasi yang sedang disorot -->
                    <rect
                      v-if="hoverBar === idx"
                      :x="bar.groupX"
                      :y="barChartModel.chartTop"
                      :width="barChartModel.groupWidth"
                      :height="barChartModel.chartBottom - barChartModel.chartTop"
                      class="chart-hover-band"
                    />
                    <rect
                      :x="bar.nilaiX"
                      :y="bar.nilaiY"
                      :width="bar.barWidth"
                      :height="bar.nilaiHeight"
                      rx="3"
                      class="chart-bar-kopi"
                    />
                    <rect
                      :x="bar.omzetX"
                      :y="bar.omzetY"
                      :width="bar.barWidth"
                      :height="bar.omzetHeight"
                      rx="3"
                      class="chart-bar-biru"
                    />
                    <text :x="bar.centerX" :y="barChartModel.chartBottom + 18" text-anchor="middle" class="chart-axis-code">
                      {{ bar.kode }}
                    </text>
                    <text :x="bar.centerX" :y="barChartModel.chartBottom + 32" text-anchor="middle" class="chart-axis-sub">
                      {{ bar.sku_ada }} SKU
                    </text>
                    <!-- area sentuh selebar kolom lokasi, lebih besar dari batangnya -->
                    <rect
                      :x="bar.groupX"
                      :y="barChartModel.chartTop"
                      :width="barChartModel.groupWidth"
                      :height="barChartModel.chartBottom - barChartModel.chartTop + 36"
                      class="chart-hit"
                      tabindex="0"
                      :aria-label="`${bar.kode} ${bar.nama}: nilai persediaan ${formatRupiah(bar.nilai)}, omzet 30 hari ${formatRupiah(bar.omzet_30_hari)}`"
                      @pointerenter="hoverBar = idx"
                      @focus="hoverBar = idx"
                      @blur="hoverBar = null"
                    />
                  </g>
                </svg>
                <ChartTooltip
                  v-if="hoveredBar"
                  :x="hoveredBar.centerX"
                  :view-width="680"
                  :title="`${hoveredBar.kode} · ${hoveredBar.nama} · ${hoveredBar.sku_ada} SKU`"
                  :rows="[
                    { key: 'kopi', value: formatRupiah(hoveredBar.nilai), label: 'nilai persediaan' },
                    { key: 'biru', value: formatRupiah(hoveredBar.omzet_30_hari), label: 'omzet 30 hari' },
                  ]"
                />
              </div>
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
                    <tr v-for="lok in dashboard.per_lokasi" :key="lok.id">
                      <td data-label="Lokasi">
                        <strong>{{ lok.kode }}</strong> · {{ lok.nama }}
                      </td>
                      <td data-label="Jenis">{{ LOKASI_TYPE_LABELS[lok.jenis] || lok.jenis }}</td>
                      <td data-label="SKU Ada" class="num">{{ formatNumber(lok.sku_ada) }}</td>
                      <td data-label="Menipis" class="num">{{ formatNumber(lok.menipis) }}</td>
                      <td data-label="Habis" class="num">{{ formatNumber(lok.habis) }}</td>
                      <td data-label="Nilai Persediaan" class="num">{{ formatRupiah(lok.nilai) }}</td>
                      <td data-label="Omzet 30 Hari" class="num">{{ formatRupiah(lok.omzet_30_hari) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </details>
          </article>

          <!-- grafik garis tren mutasi harian -->
          <article class="card chart-card">
            <div class="chart-header">
              <div>
                <h2 class="section-title">Tren Mutasi Stock Harian</h2>
                <p class="field-hint">
                  Masuk <strong class="num">{{ formatNumber(trenTotal.masuk) }}</strong> unit ·
                  Keluar <strong class="num">{{ formatNumber(trenTotal.keluar) }}</strong> unit
                </p>
              </div>
              <div class="chart-controls">
                <label for="adm-tren-lokasi" class="sr-only">Filter Lokasi Tren</label>
                <SearchSelect
                  id="adm-tren-lokasi"
                  v-model="trenFilter.lokasi_id"
                  :options="dashboard.per_lokasi.map((lok) => ({ value: String(lok.id), label: `${lok.kode} · ${lok.nama}` }))"
                  empty-label="Semua lokasi"
                  small
                />
                <label for="adm-tren-hari" class="sr-only">Rentang Hari Tren</label>
                <select id="adm-tren-hari" v-model="trenFilter.hari" class="input input-sm">
                  <option :value="7">7 hari</option>
                  <option :value="14">14 hari</option>
                  <option :value="30">30 hari</option>
                </select>
              </div>
            </div>

            <TrenChart
              :rows="trenData"
              :hari="trenFilter.hari"
              :loading="trenLoading"
              :error="trenError"
              chart-label="Grafik garis tren mutasi barang masuk dan keluar harian"
              @retry="loadTren"
            />
          </article>
        </div>
      </template>

      <!-- tampilan manager (gudang dan outlet) -->
      <template v-else-if="dashboard.peran === 'manager_gudang' || dashboard.peran === 'manager_outlet'">
        <div class="dash-tile-grid">
          <RouterLink :to="{ name: 'stok' }" class="dash-tile">
            <div class="dash-tile-icon-box dash-icon-kopi">
              <AppIcon name="box" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Nilai Persediaan Lokasi</span>
              <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_persediaan)">
                {{ formatRupiahCompact(dashboard.ringkasan.nilai_persediaan) }}
              </strong>
              <span class="dash-tile-meta num">
                {{ formatNumber(dashboard.ringkasan.sku_aktif) }} SKU tersedia di {{ dashboard.lokasi.kode }}
              </span>
            </div>
          </RouterLink>

          <RouterLink :to="{ name: 'penjualan', query: { status: 'diposting' } }" class="dash-tile">
            <div class="dash-tile-icon-box dash-icon-hijau">
              <AppIcon name="receipt" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Omzet 30 Hari</span>
              <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.omzet_30_hari)">
                {{ formatRupiahCompact(dashboard.ringkasan.omzet_30_hari) }}
              </strong>
              <span class="dash-tile-meta num">{{ formatRupiah(dashboard.ringkasan.omzet_30_hari) }}</span>
            </div>
          </RouterLink>

          <RouterLink
            :to="{ name: 'stok', query: { status_stok: 'menipis' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.stok_menipis > 0 }"
          >
            <div class="dash-tile-icon-box dash-icon-amber">
              <AppIcon name="alert-triangle" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Stock Menipis</span>
              <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.stok_menipis) }} SKU</strong>
              <span class="dash-tile-meta">Perlu pengajuan atau pengisian stock</span>
            </div>
          </RouterLink>

          <RouterLink
            :to="{ name: 'stok', query: { status_stok: 'habis' } }"
            class="dash-tile"
            :class="{ 'dash-tile-bahaya': dashboard.ringkasan.stok_habis > 0 }"
          >
            <div class="dash-tile-icon-box dash-icon-merah">
              <AppIcon name="alert" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Stock Habis</span>
              <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.stok_habis) }} SKU</strong>
              <span class="dash-tile-meta">Stock 0 pada SKU wajib tersedia</span>
            </div>
          </RouterLink>

          <RouterLink :to="{ name: 'transaksi' }" class="dash-tile">
            <div class="dash-tile-icon-box dash-icon-biru">
              <AppIcon name="swap" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Mutasi Hari Ini (WIB)</span>
              <strong class="dash-tile-value num">
                +{{ formatNumber(dashboard.ringkasan.masuk_hari_ini) }} / -{{ formatNumber(dashboard.ringkasan.keluar_hari_ini) }}
              </strong>
              <span class="dash-tile-meta">Unit masuk dan keluar hari ini</span>
            </div>
          </RouterLink>

          <RouterLink
            :to="{ name: 'pengiriman', query: { status: 'dikirim' } }"
            class="dash-tile"
            :class="{ 'dash-tile-proses': dashboard.ringkasan.pengiriman_dalam_perjalanan > 0 }"
          >
            <div class="dash-tile-icon-box dash-icon-biru">
              <AppIcon name="truck" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Pengiriman Berjalan</span>
              <strong class="dash-tile-value num">
                {{ formatNumber(dashboard.ringkasan.pengiriman_dalam_perjalanan) }}
              </strong>
              <span class="dash-tile-meta">Dikirim dari atau ke {{ dashboard.lokasi.kode }}</span>
            </div>
          </RouterLink>

          <RouterLink
            v-if="isGudangUtama"
            :to="{ name: 'permintaan', query: { status: 'diajukan' } }"
            class="dash-tile"
            :class="{ 'dash-tile-menunggu': dashboard.ringkasan.permintaan_menunggu > 0 }"
          >
            <div class="dash-tile-icon-box dash-icon-ungu">
              <AppIcon name="clipboard" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Permintaan Cabang/Outlet</span>
              <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.permintaan_menunggu) }}</strong>
              <span class="dash-tile-meta">Menunggu disetujui Gudang Utama</span>
            </div>
          </RouterLink>

          <RouterLink
            v-else
            :to="{ name: 'permintaan' }"
            class="dash-tile"
          >
            <div class="dash-tile-icon-box dash-icon-ungu">
              <AppIcon name="clipboard" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Permintaan Supply Saya</span>
              <strong class="dash-tile-value num">{{ formatNumber(dashboard.ringkasan.permintaan_menunggu) }}</strong>
              <span class="dash-tile-meta">Diajukan dan menunggu gudang utama</span>
            </div>
          </RouterLink>

          <RouterLink
            v-if="isGudangUtama"
            :to="{ name: 'pembelian', query: { status: 'dipesan' } }"
            class="dash-tile"
          >
            <div class="dash-tile-icon-box dash-icon-cokelat">
              <AppIcon name="cart" :size="22" />
            </div>
            <div class="dash-tile-body">
              <span class="dash-tile-label">Nilai PO Terbuka</span>
              <strong class="dash-tile-value num" :title="formatRupiah(dashboard.ringkasan.nilai_po_terbuka)">
                {{ formatRupiahCompact(dashboard.ringkasan.nilai_po_terbuka) }}
              </strong>
              <span class="dash-tile-meta">Pesanan ke supplier belum diterima</span>
            </div>
          </RouterLink>
        </div>

        <div class="dash-grid-2">
          <!-- kartu perlu tindakan -->
          <article class="card">
            <div class="section-header-row">
              <div class="section-title-wrap">
                <span class="section-title-icon section-icon-ungu">
                  <AppIcon name="clipboard" :size="18" />
                </span>
                <div>
                  <h2 class="section-title">Perlu Tindakan</h2>
                  <p class="field-hint">Dokumen aktif yang membutuhkan konfirmasi atau keputusan</p>
                </div>
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

          <!-- grafik tren mutasi lokasi manager -->
          <article class="card chart-card">
            <div class="chart-header">
              <div>
                <h2 class="section-title">Tren Mutasi {{ dashboard.lokasi.kode }}</h2>
                <p class="field-hint">
                  Masuk <strong class="num">{{ formatNumber(trenTotal.masuk) }}</strong> unit ·
                  Keluar <strong class="num">{{ formatNumber(trenTotal.keluar) }}</strong> unit
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

            <TrenChart
              :rows="trenData"
              :hari="trenFilter.hari"
              :loading="trenLoading"
              :error="trenError"
              chart-label="Grafik garis tren mutasi barang masuk dan keluar harian lokasi"
              @retry="loadTren"
            />
          </article>
        </div>
      </template>

      <!-- bagian bersama admin dan manager -->
      <template v-if="dashboard.peran !== 'deliveryman'">
        <div class="dash-grid-2">
          <!-- lima customer teratas (30 hari) -->
          <article class="card">
            <div class="section-header-row">
              <div class="section-title-wrap">
                <span class="section-title-icon section-icon-hijau">
                  <AppIcon name="users" :size="18" />
                </span>
                <div>
                  <h2 class="section-title">Lima Customer Teratas (30 Hari)</h2>
                  <p class="field-hint">Berdasarkan nilai penjualan yang sudah diposting</p>
                </div>
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
                    :key="cust.id ?? `umum-${idx}`"
                  >
                    <td data-label="Customer">
                      <strong>{{ cust.nama }}</strong>
                    </td>
                    <td data-label="Jenis">
                      {{ cust.jenis ? CUSTOMER_TYPE_LABELS[cust.jenis] || cust.jenis : 'Eceran Outlet' }}
                    </td>
                    <td data-label="Nota" class="num">{{ formatNumber(cust.nota) }}</td>
                    <td data-label="Omzet 30 Hari" class="num">
                      <strong>{{ formatRupiah(cust.total) }}</strong>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>

          <!-- stock kritis -->
          <article class="card">
            <div class="section-header-row">
              <div class="section-title-wrap">
                <span class="section-title-icon section-icon-amber">
                  <AppIcon name="alert-triangle" :size="18" />
                </span>
                <div>
                  <h2 class="section-title">Peringatan Stock Menipis</h2>
                  <p class="field-hint">Produk yang berada di bawah atau pada batas minimum</p>
                </div>
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

            <div v-else class="table-wrap dash-scroll">
              <table class="data-table">
                <thead>
                  <tr>
                    <th scope="col">Lokasi</th>
                    <th scope="col">Produk</th>
                    <th scope="col">Sisa</th>
                    <th scope="col" class="col-actions">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="item in dashboard.stok_kritis"
                    :key="`${item.lokasi_id}-${item.produk_id}`"
                  >
                    <td data-label="Lokasi">
                      <strong>{{ item.lokasi }}</strong>
                      <div class="field-hint dash-lokasi-nama" :title="item.lokasi_nama">
                        {{ item.lokasi_nama }}
                      </div>
                    </td>
                    <td data-label="Produk">
                      <div><strong>{{ item.nama }}</strong></div>
                      <div class="field-hint mono">{{ item.sku }}</div>
                    </td>
                    <td data-label="Sisa">
                      <div class="dash-sisa">
                        <span
                          class="stock-sisa-pill"
                          :class="item.jumlah === 0 ? 'stock-sisa-habis' : 'stock-sisa-menipis'"
                        >
                          Sisa: {{ formatNumber(item.jumlah) }}
                        </span>
                        <BadgeStatus :value="item.status_stok" />
                        <span class="field-hint">
                          min {{ formatNumber(item.stok_minimum) }} {{ item.satuan }}
                        </span>
                      </div>
                    </td>
                    <td class="col-actions">
                      <div class="action-group dash-action-stack">
                        <RouterLink :to="restockAction(item).to" class="btn btn-post btn-small">
                          <AppIcon :name="restockAction(item).icon" :size="15" />
                          <span>{{ restockAction(item).label }}</span>
                        </RouterLink>
                        <button
                          type="button"
                          class="btn btn-get-outline btn-small"
                          @click="openKartuFromKritis(item)"
                        >
                          Stock Card
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <!-- aktivitas buku besar terbaru -->
        <article class="card">
          <div class="section-header-row">
            <div class="section-title-wrap">
              <span class="section-title-icon section-icon-biru">
                <AppIcon name="swap" :size="18" />
              </span>
              <div>
                <h2 class="section-title">Aktivitas Mutasi Stock Terbaru</h2>
                <p class="field-hint">Aktivitas pergerakan stock mutasi terkini</p>
              </div>
            </div>
            <RouterLink :to="{ name: 'stok' }" class="btn btn-secondary btn-small">
              Lihat semua riwayat →
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
                  <th scope="col" class="num">Jumlah</th>
                  <th scope="col" class="num">Stock Sesudah</th>
                  <th scope="col">Dokumen</th>
                  <th scope="col">Dicatat Oleh</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="akt in dashboard.aktivitas_terbaru" :key="akt.id">
                  <td data-label="Waktu" class="cell-secondary">{{ formatDateTime(akt.waktu) }}</td>
                  <td data-label="Lokasi">
                    <strong>{{ akt.lokasi_kode }}</strong> · {{ akt.lokasi_nama }}
                  </td>
                  <td data-label="Produk">
                    <div><strong>{{ akt.produk_nama }}</strong></div>
                    <div class="field-hint mono">SKU: {{ akt.produk_sku }}</div>
                  </td>
                  <td data-label="Jenis">
                    <BadgeStatus
                      :value="akt.perubahan >= 0 ? 'masuk' : 'keluar'"
                      :label="MUTASI_TYPE_LABELS[akt.jenis] || (akt.perubahan >= 0 ? 'Masuk (IN)' : 'Keluar (OUT)')"
                    />
                  </td>
                  <td data-label="Jumlah" class="num font-semibold">
                    <span :class="akt.perubahan >= 0 ? 'text-aman' : 'text-bahaya'">
                      {{ akt.perubahan >= 0 ? `+${formatNumber(akt.perubahan)}` : formatNumber(akt.perubahan) }}
                      {{ akt.satuan }}
                    </span>
                  </td>
                  <td data-label="Stock Sesudah" class="num mono">
                    {{ formatNumber(akt.stok_sesudah) }} {{ akt.satuan }}
                  </td>
                  <td data-label="Dokumen">
                    <span class="mono">{{ akt.dokumen_kode || '-' }}</span>
                  </td>
                  <td data-label="Dicatat Oleh">{{ akt.oleh }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>
      </template>

      <!-- tampilan deliveryman -->
      <template v-else>
        <div class="summary-strip">
          <div class="summary-item">
            <span class="detail-label">Pengiriman Sedang Diantar</span>
            <strong class="detail-value num">{{ formatNumber(dashboard.pengiriman_aktif.length) }}</strong>
            <small class="field-hint">Tugas pengantaran aktif dalam perjalanan</small>
          </div>
          <div class="summary-item">
            <span class="detail-label">Riwayat Selesai Diantar</span>
            <strong class="detail-value num">{{ formatNumber(dashboard.riwayat.length) }}</strong>
            <small class="field-hint">Pengiriman yang sudah dikonfirmasi lokasi tujuan</small>
          </div>
        </div>

        <article class="card">
          <div class="section-header-row">
            <div class="section-title-wrap">
              <span class="section-title-icon section-icon-biru">
                <AppIcon name="truck" :size="18" />
              </span>
              <div>
                <h2 class="section-title">Pengiriman yang Sedang Dibawa</h2>
                <p class="field-hint">Cetak atau tunjukkan surat jalan kepada manager lokasi penerima</p>
              </div>
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
                    <strong>{{ item.lokasi_asal.kode }} · {{ item.lokasi_asal.nama }}</strong>
                    <div class="field-hint">{{ item.lokasi_asal_alamat }}</div>
                  </td>
                  <td data-label="Tujuan">
                    <strong>{{ item.lokasi_tujuan.kode }} · {{ item.lokasi_tujuan.nama }}</strong>
                    <div class="field-hint">{{ item.lokasi_tujuan_alamat }}</div>
                  </td>
                  <td data-label="Kendaraan">
                    {{ KENDARAAN_TYPE_LABELS[item.kendaraan_jenis] || item.kendaraan_jenis || '-' }}
                    <div class="mono field-hint">{{ item.kendaraan_nomor || '' }}</div>
                  </td>
                  <td data-label="Muatan" class="num">
                    <strong>{{ formatNumber(item.total_unit) }} unit</strong>
                    <div class="field-hint">{{ formatNumber(item.jumlah_item) }} SKU</div>
                  </td>
                  <td class="col-actions">
                    <div class="action-group">
                      <RouterLink
                        :to="{ name: 'pengiriman-surat-jalan', params: { id: item.id } }"
                        class="btn btn-get btn-small"
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
              <p class="field-hint">20 pengiriman terakhir yang sudah diterima lokasi tujuan</p>
            </div>
          </div>

          <EmptyState
            v-if="!dashboard.riwayat?.length"
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
                <tr v-for="item in dashboard.riwayat" :key="item.id">
                  <td data-label="Kode"><strong class="mono">{{ item.kode }}</strong></td>
                  <td data-label="Tanggal Kirim">{{ formatDate(item.tanggal_kirim) }}</td>
                  <td data-label="Diterima Pada">{{ formatDateTime(item.diterima_pada) }}</td>
                  <td data-label="Rute">
                    {{ item.lokasi_asal.kode }} ({{ item.lokasi_asal.nama }}) &rarr;
                    {{ item.lokasi_tujuan.kode }} ({{ item.lokasi_tujuan.nama }})
                  </td>
                  <td data-label="Muatan" class="num">
                    {{ formatNumber(item.total_unit) }} unit ({{ formatNumber(item.jumlah_item) }} SKU)
                  </td>
                  <td data-label="Status">
                    <BadgeStatus :value="item.status" />
                  </td>
                  <td class="col-actions">
                    <RouterLink
                      :to="{ name: 'pengiriman-surat-jalan', params: { id: item.id } }"
                      class="btn btn-get btn-small"
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
      :stok="kartuModal.stok"
      @close="closeKartuModal"
    />
  </section>
</template>
