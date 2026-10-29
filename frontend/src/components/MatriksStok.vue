<script setup>
import BadgeStatus from '@/components/BadgeStatus.vue'
import { LOKASI_TYPE_LABELS, STOK_STATUS_LABELS } from '@/utils/constants'
import { formatNumber, formatRupiah } from '@/utils/format'

const props = defineProps({
  lokasi: { type: Array, default: () => [] },
  baris: { type: Array, default: () => [] },
  totalPerLokasi: { type: Array, default: () => [] },
  totalNilai: { type: Number, default: null },
  // false untuk manager cabang dan outlet: kolom nilai rupiah tidak ditampilkan
  showValues: { type: Boolean, default: true },
  // lokasi yang kartu stock-nya boleh dibuka, sel lain hanya menampilkan jumlah
  canOpen: { type: Function, default: () => true },
  // lokasi user yang login, kolomnya ditandai supaya stock miliknya mudah dikenali
  ownLokasiId: { type: Number, default: null },
})

const emit = defineEmits(['select-cell'])

// sel dan total per lokasi dikirim backend sebagai list berkunci lokasi_id
function getSel(row, lokasiId) {
  return (
    row.sel?.find((sel) => sel.lokasi_id === lokasiId) || {
      jumlah: 0,
      stok_minimum: 0,
      status_stok: 'habis',
    }
  )
}

function getTotalLokasi(lokasiId) {
  return props.totalPerLokasi.find((item) => item.lokasi_id === lokasiId) || { nilai: 0 }
}

function cellClass(status) {
  if (status === 'habis') return 'matrix-cell matrix-cell-habis'
  if (status === 'menipis') return 'matrix-cell matrix-cell-menipis'
  return 'matrix-cell matrix-cell-aman'
}

// sel yang diklik dikirim bersama stock-nya supaya kartu stock bisa menawarkan isi ulang
function handleSelect(row, lok) {
  const sel = getSel(row, lok.id)
  emit('select-cell', {
    produk: {
      id: row.produk.id,
      sku: row.produk.sku,
      nama: row.produk.nama,
      satuan: row.produk.satuan,
    },
    lokasi: { id: lok.id, kode: lok.kode, nama: lok.nama },
    stok: {
      jumlah: sel.jumlah,
      stokMinimum: sel.stok_minimum,
      status: sel.status_stok,
      lokasiJenis: lok.jenis,
      produkJenis: row.produk.jenis,
    },
  })
}
</script>

<template>
  <div class="matrix-card">
    <div class="matrix-legend">
      <div class="matrix-legend-items">
        <span class="matrix-legend-title">Keterangan status sel stock</span>
        <span class="matrix-legend-chip matrix-cell-aman">Aman (di atas minimum)</span>
        <span class="matrix-legend-chip matrix-cell-menipis">Menipis (1 sampai batas minimum)</span>
        <span class="matrix-legend-chip matrix-cell-habis">Habis (0 saat minimum &gt; 0)</span>
      </div>
      <span class="matrix-legend-hint">
        {{
          showValues
            ? 'Klik sel untuk melihat Stock Card produk di lokasi tersebut'
            : 'Klik sel di lokasi Anda untuk melihat Stock Card produk'
        }}
      </span>
    </div>

    <div class="matrix-wrap" role="region" aria-label="Matriks stock produk per lokasi" tabindex="0">
      <table class="matrix-table">
        <thead>
          <tr>
            <th scope="col" class="matrix-sticky-col matrix-corner">Produk</th>
            <th
              v-for="lok in lokasi"
              :key="lok.id"
              scope="col"
              class="matrix-loc-header"
              :class="{ 'matrix-own-col': lok.id === ownLokasiId }"
            >
              <span v-if="lok.id === ownLokasiId" class="matrix-own-tag">Lokasi Anda</span>
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
                <BadgeStatus :value="row.produk.jenis" />
              </div>
              <strong class="matrix-prod-name">{{ row.produk.nama }}</strong>
              <span class="matrix-prod-sub">
                {{ row.produk.kategori_nama }} · {{ row.produk.satuan }}
                <template v-if="row.produk.harga_beli !== null">
                  · HPP {{ formatRupiah(row.produk.harga_beli) }}
                </template>
              </span>
            </th>

            <td
              v-for="lok in lokasi"
              :key="lok.id"
              class="matrix-td"
              :class="{ 'matrix-own-col': lok.id === ownLokasiId }"
            >
              <button
                type="button"
                :class="cellClass(getSel(row, lok.id).status_stok)"
                :disabled="!canOpen(lok.id)"
                :aria-label="`${row.produk.nama} di ${lok.nama}: stock ${getSel(row, lok.id).jumlah} ${row.produk.satuan}, minimum ${getSel(row, lok.id).stok_minimum}, status ${STOK_STATUS_LABELS[getSel(row, lok.id).status_stok] || getSel(row, lok.id).status_stok}${canOpen(lok.id) ? '. Klik untuk Stock Card' : ''}`"
                @click="handleSelect(row, lok)"
              >
                <span class="matrix-cell-qty num">
                  {{ formatNumber(getSel(row, lok.id).jumlah) }}
                  <small>{{ row.produk.satuan }}</small>
                </span>
                <span class="matrix-cell-meta">
                  <span>{{ STOK_STATUS_LABELS[getSel(row, lok.id).status_stok] || getSel(row, lok.id).status_stok }}</span>
                  <span class="num">min {{ formatNumber(getSel(row, lok.id).stok_minimum) }}</span>
                </span>
              </button>
            </td>

            <td class="matrix-row-total">
              <strong class="num">{{ formatNumber(row.total) }} {{ row.produk.satuan }}</strong>
              <span v-if="row.nilai !== null" class="matrix-total-val num">
                {{ formatRupiah(row.nilai) }}
              </span>
            </td>
          </tr>
        </tbody>
        <!-- jumlah unit per lokasi tidak dijumlahkan karena satuan produknya berbeda -->
        <tfoot v-if="showValues">
          <tr>
            <th scope="row" class="matrix-sticky-col matrix-foot-label">
              Total per Lokasi
            </th>
            <td
              v-for="lok in lokasi"
              :key="lok.id"
              class="matrix-foot-cell"
              :class="{ 'matrix-own-col': lok.id === ownLokasiId }"
            >
              <strong class="num">{{ formatRupiah(getTotalLokasi(lok.id).nilai) }}</strong>
            </td>
            <td class="matrix-foot-cell matrix-grand-total">
              <strong class="num">{{ formatRupiah(totalNilai) }}</strong>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>
