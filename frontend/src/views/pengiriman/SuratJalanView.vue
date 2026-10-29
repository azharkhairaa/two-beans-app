<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import ErrorState from '@/components/ErrorState.vue'
import LoadingState from '@/components/LoadingState.vue'
import { pengirimanApi } from '@/services'
import { KENDARAAN_TYPE_LABELS, LOKASI_TYPE_LABELS } from '@/utils/constants'
import { formatDate, formatDateTime, formatNumber } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const data = ref(null)

async function loadSuratJalan() {
  loading.value = true
  error.value = ''
  try {
    data.value = await pengirimanApi.get(Number(route.params.id))
  } catch (err) {
    error.value = err?.message || 'Gagal memuat surat jalan pengiriman.'
  } finally {
    loading.value = false
  }
}

onMounted(loadSuratJalan)

const totalUnitDikirim = computed(() =>
  (data.value?.items || []).reduce((sum, it) => sum + (Number(it.jumlah_dikirim) || 0), 0)
)

const totalUnitDiterima = computed(() => {
  if (!data.value || data.value.status !== 'diterima') return null
  return (data.value.items || []).reduce((sum, it) => sum + (Number(it.jumlah_diterima) || 0), 0)
})

function onPrint() {
  window.print()
}

function goBack() {
  router.push({ name: 'pengiriman' })
}
</script>

<template>
  <section class="page-section print-page">
    <div class="print-toolbar no-print">
      <button type="button" class="btn btn-secondary" @click="goBack">
        <AppIcon name="arrow-left" :size="16" />
        <span>Kembali ke Pengiriman</span>
      </button>
      <button
        v-if="data"
        type="button"
        class="btn btn-get"
        @click="onPrint"
      >
        <AppIcon name="printer" :size="16" />
        <span>Cetak Surat Jalan</span>
      </button>
    </div>

    <LoadingState v-if="loading" :rows="6" />
    <ErrorState v-else-if="error" :message="error" @retry="loadSuratJalan" />

    <article v-else-if="data" class="print-sheet" aria-label="Surat Jalan Pengiriman">
      <header class="print-header">
        <div class="print-brand">
          <div class="print-brand-mark">
            <AppIcon name="coffee" :size="24" />
          </div>
          <div>
            <h1 class="print-company">TWO BEANS COFFEE</h1>
            <p class="print-tagline">Roastery, Gudang Distribusi &amp; Jaringan Outlet Kopi</p>
          </div>
        </div>
        <div class="print-doc-meta">
          <p class="print-doc-type">SURAT JALAN PENGIRIMAN</p>
          <p class="print-doc-code mono">{{ data.kode }}</p>
          <div class="print-doc-sub">
            <span>Tanggal Kirim: <strong class="mono">{{ formatDate(data.tanggal_kirim) }}</strong></span>
            <span>·</span>
            <BadgeStatus :status="data.status" />
          </div>
          <p v-if="data.permintaan" class="print-doc-ref mono">
            Referensi Permintaan: {{ data.permintaan.kode }}
          </p>
        </div>
      </header>

      <div class="print-parties">
        <div class="print-party-box">
          <h2 class="print-party-title">Pengirim (Lokasi Asal)</h2>
          <p class="print-party-name">
            {{ data.lokasi_asal?.nama }}
            <span class="mono">({{ data.lokasi_asal?.kode }})</span>
          </p>
          <p class="print-party-detail">
            {{ LOKASI_TYPE_LABELS[data.lokasi_asal?.jenis] || data.lokasi_asal?.jenis }}
          </p>
          <p v-if="data.lokasi_asal?.alamat" class="print-party-detail">
            {{ data.lokasi_asal.alamat }}
          </p>
          <p v-if="data.lokasi_asal?.telepon" class="print-party-detail mono">
            Telp: {{ data.lokasi_asal.telepon }}
          </p>
          <p v-if="data.dikirim_pada" class="print-party-time mono">
            Dikirim: {{ formatDateTime(data.dikirim_pada) }}
          </p>
        </div>

        <div class="print-party-box">
          <h2 class="print-party-title">Penerima (Lokasi Tujuan)</h2>
          <p class="print-party-name">
            {{ data.lokasi_tujuan?.nama }}
            <span class="mono">({{ data.lokasi_tujuan?.kode }})</span>
          </p>
          <p class="print-party-detail">
            {{ LOKASI_TYPE_LABELS[data.lokasi_tujuan?.jenis] || data.lokasi_tujuan?.jenis }}
          </p>
          <p v-if="data.lokasi_tujuan?.alamat" class="print-party-detail">
            {{ data.lokasi_tujuan.alamat }}
          </p>
          <p v-if="data.lokasi_tujuan?.telepon" class="print-party-detail mono">
            Telp: {{ data.lokasi_tujuan.telepon }}
          </p>
          <p v-if="data.diterima_pada" class="print-party-time mono">
            Diterima: {{ formatDateTime(data.diterima_pada) }}
          </p>
        </div>

        <div class="print-party-box">
          <h2 class="print-party-title">Pengantaran &amp; Kendaraan</h2>
          <p class="print-party-name">
            {{ data.deliveryman?.name || 'Belum ditentukan' }}
          </p>
          <p class="print-party-detail">
            Jenis Armada:
            <strong>
              {{ KENDARAAN_TYPE_LABELS[data.kendaraan_jenis] || data.kendaraan_jenis || '-' }}
            </strong>
          </p>
          <p class="print-party-detail">
            Nomor Polisi: <strong class="mono">{{ data.kendaraan_nomor || '-' }}</strong>
          </p>
          <p v-if="data.catatan" class="print-party-detail">
            Catatan: {{ data.catatan }}
          </p>
        </div>
      </div>

      <table class="print-table">
        <thead>
          <tr>
            <th class="print-col-no">No</th>
            <th>SKU</th>
            <th>Nama Barang</th>
            <th>Satuan</th>
            <th class="num">Jumlah Dikirim</th>
            <th class="num">Jumlah Diterima</th>
            <th>Catatan Pemeriksaan</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in data.items" :key="item.id">
            <td class="print-col-no mono">{{ idx + 1 }}</td>
            <td class="mono font-semibold">{{ item.produk.sku }}</td>
            <td>{{ item.produk.nama }}</td>
            <td>{{ item.produk.satuan }}</td>
            <td class="num mono font-semibold">{{ formatNumber(item.jumlah_dikirim) }}</td>
            <td class="num mono">
              <template v-if="item.jumlah_diterima !== null && item.jumlah_diterima !== undefined">
                {{ formatNumber(item.jumlah_diterima) }}
              </template>
              <span v-else class="print-blank-line">..........</span>
            </td>
            <td>
              <template v-if="item.catatan">{{ item.catatan }}</template>
              <template v-else-if="item.selisih === 0">Lengkap &amp; sesuai</template>
              <span v-else class="print-blank-line">....................</span>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td colspan="4" class="num font-semibold">Total Unit Barang</td>
            <td class="num mono font-semibold">{{ formatNumber(totalUnitDikirim) }}</td>
            <td class="num mono font-semibold">
              <template v-if="totalUnitDiterima !== null">
                {{ formatNumber(totalUnitDiterima) }}
              </template>
              <span v-else class="print-blank-line">..........</span>
            </td>
            <td>{{ data.jumlah_item }} jenis produk</td>
          </tr>
        </tfoot>
      </table>

      <div v-if="data.catatan_penerimaan" class="print-notes">
        <strong>Catatan Penerimaan Lokasi Tujuan:</strong>
        <p>{{ data.catatan_penerimaan }}</p>
      </div>

      <footer class="print-signatures">
        <div class="print-sign-box">
          <p class="print-sign-role">Pengirim (Gudang Asal)</p>
          <div class="print-sign-space"></div>
          <p class="print-sign-name">
            {{ data.dikirim_oleh?.name || data.dibuat_oleh?.name || '( ................................. )' }}
          </p>
          <p class="print-sign-sub">{{ data.lokasi_asal?.nama }}</p>
        </div>

        <div class="print-sign-box">
          <p class="print-sign-role">Pengantar (Deliveryman)</p>
          <div class="print-sign-space"></div>
          <p class="print-sign-name">
            {{ data.deliveryman?.name || '( ................................. )' }}
          </p>
          <p class="print-sign-sub">
            {{ data.kendaraan_nomor ? `Armada ${data.kendaraan_nomor}` : 'Kurir Internal Two Beans' }}
          </p>
        </div>

        <div class="print-sign-box">
          <p class="print-sign-role">Penerima (Lokasi Tujuan)</p>
          <div class="print-sign-space"></div>
          <p class="print-sign-name">
            {{ data.diterima_oleh?.name || '( ................................. )' }}
          </p>
          <p class="print-sign-sub">{{ data.lokasi_tujuan?.nama }}</p>
        </div>
      </footer>
    </article>
  </section>
</template>
