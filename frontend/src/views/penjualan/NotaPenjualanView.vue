<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import ErrorState from '@/components/ErrorState.vue'
import LoadingState from '@/components/LoadingState.vue'
import { penjualanApi } from '@/services'
import { CUSTOMER_TYPE_LABELS, LOKASI_TYPE_LABELS } from '@/utils/constants'
import { formatDate, formatDateTime, formatNumber, formatRupiah } from '@/utils/format'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const data = ref(null)

async function loadNota() {
  loading.value = true
  error.value = ''
  try {
    data.value = await penjualanApi.get(Number(route.params.id))
  } catch (err) {
    error.value = err?.message || 'Gagal memuat nota penjualan.'
  } finally {
    loading.value = false
  }
}

onMounted(loadNota)

const totalUnit = computed(() =>
  (data.value?.items || []).reduce((sum, it) => sum + (Number(it.jumlah) || 0), 0)
)

function onPrint() {
  window.print()
}

function goBack() {
  router.push({ name: 'penjualan' })
}
</script>

<template>
  <section class="page-section print-page">
    <div class="print-toolbar no-print">
      <button type="button" class="btn btn-secondary" @click="goBack">
        <AppIcon name="arrow-left" :size="16" />
        <span>Kembali ke Penjualan</span>
      </button>
      <button v-if="data" type="button" class="btn btn-get" @click="onPrint">
        <AppIcon name="printer" :size="16" />
        <span>Cetak Nota Penjualan</span>
      </button>
    </div>

    <LoadingState v-if="loading" :rows="6" />
    <ErrorState v-else-if="error" :message="error" @retry="loadNota" />

    <article v-else-if="data" class="print-sheet" aria-label="Nota Penjualan">
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
          <p class="print-doc-type">NOTA PENJUALAN</p>
          <p class="print-doc-code mono">{{ data.kode }}</p>
          <div class="print-doc-sub">
            <span>Tanggal: <strong class="mono">{{ formatDate(data.tanggal) }}</strong></span>
            <span>·</span>
            <BadgeStatus :status="data.status" />
          </div>
        </div>
      </header>

      <div class="print-parties">
        <div class="print-party-box">
          <h2 class="print-party-title">Lokasi Penjual</h2>
          <p class="print-party-name">
            {{ data.lokasi?.nama }}
            <span class="mono">({{ data.lokasi?.kode }})</span>
          </p>
          <p class="print-party-detail">
            {{ LOKASI_TYPE_LABELS[data.lokasi?.jenis] || data.lokasi?.jenis }}
          </p>
          <p v-if="data.lokasi?.alamat" class="print-party-detail">
            {{ data.lokasi.alamat }}
          </p>
          <p v-if="data.lokasi?.telepon" class="print-party-detail mono">
            Telp: {{ data.lokasi.telepon }}
          </p>
        </div>

        <div class="print-party-box">
          <h2 class="print-party-title">Customer / Pembeli</h2>
          <p class="print-party-name">{{ data.nama_customer }}</p>
          <template v-if="data.customer">
            <p class="print-party-detail">
              Jenis: {{ CUSTOMER_TYPE_LABELS[data.customer.jenis] || data.customer.jenis }}
            </p>
            <p v-if="data.customer.alamat" class="print-party-detail">
              {{ data.customer.alamat }}
            </p>
            <p v-if="data.customer.telepon" class="print-party-detail mono">
              Telp: {{ data.customer.telepon }}
            </p>
          </template>
          <p v-else class="print-party-detail">Pembelian langsung di outlet</p>
        </div>

        <div class="print-party-box">
          <h2 class="print-party-title">Petugas &amp; Pencatatan</h2>
          <p class="print-party-name">{{ data.diposting_oleh || data.dibuat_oleh }}</p>
          <p class="print-party-detail">
            Dibuat oleh: <strong>{{ data.dibuat_oleh }}</strong>
          </p>
          <p v-if="data.diposting_pada" class="print-party-time mono">
            Diposting: {{ formatDateTime(data.diposting_pada) }}
          </p>
        </div>
      </div>

      <table class="print-table">
        <thead>
          <tr>
            <th class="print-col-no">No</th>
            <th>SKU</th>
            <th>Nama Produk</th>
            <th>Satuan</th>
            <th class="num">Harga Satuan</th>
            <th class="num">Jumlah</th>
            <th class="num">Subtotal</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in data.items" :key="item.id">
            <td class="print-col-no mono">{{ idx + 1 }}</td>
            <td class="mono font-semibold">{{ item.produk.sku }}</td>
            <td>{{ item.produk.nama }}</td>
            <td>{{ item.produk.satuan }}</td>
            <td class="num mono">{{ formatRupiah(item.harga_satuan) }}</td>
            <td class="num mono font-semibold">{{ formatNumber(item.jumlah) }}</td>
            <td class="num mono font-semibold">{{ formatRupiah(item.subtotal) }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td colspan="5" class="num font-semibold">Total Penjualan</td>
            <td class="num mono font-semibold">{{ formatNumber(totalUnit) }} unit</td>
            <td class="num mono font-semibold">{{ formatRupiah(data.total) }}</td>
          </tr>
        </tfoot>
      </table>

      <div v-if="data.catatan" class="print-notes">
        <strong>Catatan Penjualan:</strong>
        <p>{{ data.catatan }}</p>
      </div>

      <!-- nota berfungsi sebagai invoice, jadi tanpa tanda tangan customer -->
      <footer class="print-signatures print-signatures-invoice">
        <div class="print-sign-box">
          <p class="print-sign-role">Pemeriksa Barang</p>
          <div class="print-sign-space"></div>
          <p class="print-sign-name">( ................................. )</p>
          <p class="print-sign-sub">Bagian Gudang / Outlet</p>
        </div>

        <div class="print-sign-box">
          <p class="print-sign-role">Petugas Penjualan</p>
          <div class="print-sign-space"></div>
          <p class="print-sign-name">{{ data.diposting_oleh || data.dibuat_oleh }}</p>
          <p class="print-sign-sub">{{ data.lokasi?.nama }}</p>
        </div>
      </footer>
    </article>
  </section>
</template>
