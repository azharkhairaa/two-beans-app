<script setup>
import BadgeStatus from '@/components/BadgeStatus.vue'
import { LOKASI_TYPE_LABELS, STOK_STATUS_LABELS } from '@/utils/constants'
import { formatNumber, formatRupiah } from '@/utils/format'

const props = defineProps({
  lokasi: { type: Array, default: () => [] },
  baris: { type: Array, default: () => [] },
  totalPerLokasi: { type: Object, default: () => ({}) },
  totalJumlah: { type: Number, default: 0 },
  totalNilai: { type: Number, default: 0 },
})

const emit = defineEmits(['select-cell'])

function getSel(row, lokasiKode) {
  return (
    row.sel?.[lokasiKode] || {
      jumlah: 0,
      stok_minimum: 0,
      status: 'aman',
    }
  )
}

function getTotalLokasi(lokasiKode) {
  return (
    props.totalPerLokasi?.[lokasiKode] || {
      total_jumlah: 0,
      total_nilai: 0,
    }
  )
}

function cellClass(status) {
  if (status === 'habis') return 'matrix-cell matrix-cell-habis'
  if (status === 'menipis') return 'matrix-cell matrix-cell-menipis'
  return 'matrix-cell matrix-cell-aman'
}

function handleSelect(produk, lok) {
  emit('select-cell', {
    produk: {
      id: produk.id,
      sku: produk.sku,
      nama: produk.nama,
      satuan: produk.satuan,
    },
    lokasi: {
      id: lok.id,
      kode: lok.kode,
      nama: lok.nama,
    },
  })
}
</script>

<template>
  <div class="matrix-card">
    <div class="matrix-legend">
      <div class="matrix-legend-items">
        <span class="matrix-legend-title">Keterangan status sel</span>
        <span class="matrix-legend-chip matrix-cell-aman">Aman (di atas minimum)</span>
        <span class="matrix-legend-chip matrix-cell-menipis">Menipis (1 sampai batas minimum)</span>
        <span class="matrix-legend-chip matrix-cell-habis">Habis (0 saat minimum &gt; 0)</span>
      </div>
      <span class="matrix-legend-hint">Klik sel untuk melihat kartu stok produk di lokasi tersebut</span>
    </div>

    <div class="matrix-wrap" role="region" aria-label="Matriks stok produk per lokasi" tabindex="0">
      <table class="matrix-table">
        <thead>
          <tr>
            <th scope="col" class="matrix-sticky-col matrix-corner">Produk</th>
            <th
              v-for="lok in lokasi"
              :key="lok.id"
              scope="col"
              class="matrix-loc-header"
            >
              <span class="matrix-loc-code">{{ lok.kode }}</span>
              <span class="matrix-loc-name">{{ lok.nama }}</span>
              <span class="matrix-loc-type">{{ LOKASI_TYPE_LABELS[lok.jenis] || lok.jenis }}</span>
            </th>
            <th scope="col" class="matrix-total-header">Total Produk</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in baris" :key="row.produk.id">
            <th scope="row" class="matrix-sticky-col matrix-row-header">
              <div class="matrix-prod-meta">
                <span class="mono matrix-prod-sku">{{ row.produk.sku }}</span>
                <BadgeStatus :value="row.produk.kategori_jenis" />
              </div>
              <strong class="matrix-prod-name">{{ row.produk.nama }}</strong>
              <span class="matrix-prod-sub">
                {{ row.produk.kategori_nama }} · {{ row.produk.satuan }} · HPP {{ formatRupiah(row.produk.harga_beli) }}
              </span>
            </th>

            <td
              v-for="lok in lokasi"
              :key="lok.id"
              class="matrix-td"
            >
              <button
                type="button"
                :class="cellClass(getSel(row, lok.kode).status)"
                :aria-label="`${row.produk.nama} di ${lok.nama}: stok ${getSel(row, lok.kode).jumlah} ${row.produk.satuan}, minimum ${getSel(row, lok.kode).stok_minimum}, status ${STOK_STATUS_LABELS[getSel(row, lok.kode).status] || getSel(row, lok.kode).status}. Klik untuk kartu stok`"
                @click="handleSelect(row.produk, lok)"
              >
                <span class="matrix-cell-qty num">
                  {{ formatNumber(getSel(row, lok.kode).jumlah) }}
                  <small>{{ row.produk.satuan }}</small>
                </span>
                <span class="matrix-cell-meta">
                  <span>{{ STOK_STATUS_LABELS[getSel(row, lok.kode).status] || getSel(row, lok.kode).status }}</span>
                  <span class="num">min {{ formatNumber(getSel(row, lok.kode).stok_minimum) }}</span>
                </span>
              </button>
            </td>

            <td class="matrix-row-total">
              <strong class="num">{{ formatNumber(row.total_jumlah) }} {{ row.produk.satuan }}</strong>
              <span class="matrix-total-val num">{{ formatRupiah(row.total_nilai) }}</span>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <th scope="row" class="matrix-sticky-col matrix-foot-label">
              Total per Lokasi
            </th>
            <td
              v-for="lok in lokasi"
              :key="lok.id"
              class="matrix-foot-cell"
            >
              <strong class="num">{{ formatNumber(getTotalLokasi(lok.kode).total_jumlah) }} unit</strong>
              <span class="matrix-total-val num">{{ formatRupiah(getTotalLokasi(lok.kode).total_nilai) }}</span>
            </td>
            <td class="matrix-foot-cell matrix-grand-total">
              <strong class="num">{{ formatNumber(totalJumlah) }} unit</strong>
              <span class="matrix-total-val num">{{ formatRupiah(totalNilai) }}</span>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>
