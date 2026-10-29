<script setup>
import { computed, ref } from 'vue'

import ChartTooltip from '@/components/ChartTooltip.vue'
import ErrorState from '@/components/ErrorState.vue'
import { formatDate, formatNumber } from '@/utils/format'

// grafik tren mutasi masuk dan keluar harian beserta tabelnya untuk dashboard admin dan manager
const props = defineProps({
  rows: { type: Array, default: () => [] },
  hari: { type: [Number, String], default: 30 },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  chartLabel: { type: String, default: 'Grafik garis tren mutasi barang masuk dan keluar harian' },
})

const emit = defineEmits(['retry'])

const CHART = { left: 64, right: 656, top: 24, bottom: 204 }
const VIEW_WIDTH = 680

function signed(value) {
  return value >= 0 ? `+${formatNumber(value)}` : formatNumber(value)
}

const model = computed(() => {
  const rows = props.rows
  const plotWidth = CHART.right - CHART.left
  const plotHeight = CHART.bottom - CHART.top
  const frame = { chartLeft: CHART.left, chartRight: CHART.right, chartBottom: CHART.bottom }
  if (!rows.length) return { points: [], masukPath: '', keluarPath: '', ticks: [], ...frame }

  const values = rows.flatMap((row) => [Number(row.masuk || 0), Number(row.keluar || 0)])
  const rawMax = Math.max(4, ...values)
  const niceMax = Math.ceil(rawMax / 4) * 4
  const stepX = rows.length > 1 ? plotWidth / (rows.length - 1) : 0
  const labelStride = rows.length > 20 ? 5 : rows.length > 10 ? 2 : 1
  const toY = (value) => Math.round(CHART.bottom - (value / niceMax) * plotHeight)

  const points = rows.map((row, idx) => {
    const masuk = Number(row.masuk || 0)
    const keluar = Number(row.keluar || 0)
    return {
      tanggal: row.tanggal,
      shortDate: String(row.tanggal || '').slice(5),
      showLabel: idx === 0 || idx === rows.length - 1 || idx % labelStride === 0,
      x: Math.round(rows.length > 1 ? CHART.left + idx * stepX : CHART.left + plotWidth / 2),
      masuk,
      keluar,
      masukY: toY(masuk),
      keluarY: toY(keluar),
    }
  })

  const path = (key) =>
    points.map((pt, idx) => `${idx === 0 ? 'M' : 'L'}${pt.x},${pt[key]}`).join(' ')
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((ratio) => {
    const val = Math.round(niceMax * ratio)
    return { val, y: Math.round(CHART.bottom - ratio * plotHeight), label: formatNumber(val) }
  })

  return { points, masukPath: path('masukY'), keluarPath: path('keluarY'), ticks, ...frame }
})

const hoverIndex = ref(null)
const hovered = computed(() => model.value.points[hoverIndex.value] ?? null)

const tooltipRows = computed(() => [
  { key: 'masuk', value: formatNumber(hovered.value.masuk), label: 'unit masuk' },
  { key: 'keluar', value: formatNumber(hovered.value.keluar), label: 'unit keluar' },
])

// crosshair mengunci ke tanggal terdekat dari posisi kursor, bukan harus tepat di garis
function onPointerMove(event) {
  const points = model.value.points
  if (!points.length) return
  const rect = event.currentTarget.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * VIEW_WIDTH
  let nearest = 0
  points.forEach((pt, idx) => {
    if (Math.abs(pt.x - x) < Math.abs(points[nearest].x - x)) nearest = idx
  })
  hoverIndex.value = nearest
}

// keyboard: fokus menampilkan hari terakhir, panah kiri dan kanan pindah tanggal
function onKeydown(event) {
  const last = model.value.points.length - 1
  if (last < 0 || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return
  event.preventDefault()
  const step = event.key === 'ArrowRight' ? 1 : -1
  hoverIndex.value = Math.min(last, Math.max(0, (hoverIndex.value ?? last) + step))
}

function onFocus() {
  if (hoverIndex.value === null) hoverIndex.value = model.value.points.length - 1
}
</script>

<template>
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

  <ErrorState v-if="error" :message="error" @retry="emit('retry')" />
  <div v-else-if="loading" class="chart-loading-overlay">
    <span class="loading-spinner" aria-hidden="true"></span>
    <span>Memuat tren mutasi harian...</span>
  </div>
  <div v-else class="chart-svg-wrap">
    <div class="chart-plot">
      <svg
        class="chart-svg chart-svg-interactive"
        viewBox="0 0 680 240"
        role="img"
        tabindex="0"
        :aria-label="`${chartLabel}. Gunakan panah kiri dan kanan untuk membaca nilai per hari`"
        @pointermove="onPointerMove"
        @pointerleave="hoverIndex = null"
        @focus="onFocus"
        @blur="hoverIndex = null"
        @keydown="onKeydown"
      >
        <g v-for="t in model.ticks" :key="t.val">
          <line
            :x1="model.chartLeft"
            :y1="t.y"
            :x2="model.chartRight"
            :y2="t.y"
            class="chart-grid-line"
          />
          <text :x="model.chartLeft - 8" :y="t.y + 4" text-anchor="end" class="chart-axis-text">
            {{ t.label }}
          </text>
        </g>

        <line
          v-if="hovered"
          :x1="hovered.x"
          :y1="CHART.top"
          :x2="hovered.x"
          :y2="CHART.bottom"
          class="chart-crosshair"
        />

        <path :d="model.masukPath" class="chart-line-masuk" />
        <path :d="model.keluarPath" class="chart-line-keluar" />

        <g v-for="pt in model.points" :key="pt.tanggal">
          <circle :cx="pt.x" :cy="pt.masukY" :r="pt === hovered ? 5.5 : 3.5" class="chart-dot-masuk" />
          <rect
            :x="pt.x - (pt === hovered ? 4.5 : 3)"
            :y="pt.keluarY - (pt === hovered ? 4.5 : 3)"
            :width="pt === hovered ? 9 : 6"
            :height="pt === hovered ? 9 : 6"
            class="chart-dot-keluar"
          />
          <text
            v-if="pt.showLabel"
            :x="pt.x"
            :y="model.chartBottom + 20"
            text-anchor="middle"
            class="chart-axis-sub"
          >
            {{ pt.shortDate }}
          </text>
        </g>
      </svg>
      <ChartTooltip
        v-if="hovered"
        :x="hovered.x"
        :view-width="VIEW_WIDTH"
        :title="formatDate(hovered.tanggal)"
        :rows="tooltipRows"
      />
    </div>
  </div>

  <details class="chart-alt-details">
    <summary>Tabel data tren mutasi harian ({{ hari }} hari)</summary>
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
          <tr v-for="pt in rows" :key="pt.tanggal">
            <td data-label="Tanggal">{{ formatDate(pt.tanggal) }}</td>
            <td data-label="Barang Masuk" class="num">+{{ formatNumber(pt.masuk) }}</td>
            <td data-label="Barang Keluar" class="num">-{{ formatNumber(pt.keluar) }}</td>
            <td data-label="Selisih" class="num">{{ signed(pt.masuk - pt.keluar) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </details>
</template>
