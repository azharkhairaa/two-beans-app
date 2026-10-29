<script setup>
import { computed, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import BaseModal from '@/components/BaseModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import LoadingState from '@/components/LoadingState.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import { produkApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { MUTASI_TYPE_LABELS } from '@/utils/constants'
import { formatDateTime, formatNumber } from '@/utils/format'
import { canRestock, restockLink } from '@/utils/restock'

const props = defineProps({
  open: { type: Boolean, default: false },
  produk: { type: Object, default: null },
  lokasi: { type: Object, default: null },
  // stock saat ini { jumlah, stokMinimum, status, lokasiJenis, produkJenis }, opsional
  stok: { type: Object, default: null },
})

const emit = defineEmits(['close'])
const auth = useAuthStore()

// stock menipis atau habis di lokasi yang boleh dikelola user diberi tombol isi ulang
const restock = computed(() => {
  const stok = props.stok
  if (!stok || !props.produk || !props.lokasi) return null
  if (!['menipis', 'habis'].includes(stok.status)) return null
  if (!canRestock(auth.user, props.lokasi.id)) return null
  return restockLink({
    lokasiId: props.lokasi.id,
    lokasiJenis: stok.lokasiJenis,
    produkId: props.produk.id,
    produkJenis: stok.produkJenis,
    jumlah: stok.jumlah,
    stokMinimum: stok.stokMinimum,
  })
})

const items = ref([])
const meta = ref({ page: 1, per_page: 15, total: 0, total_pages: 1 })
const perPage = ref(15)
const loading = ref(false)
const error = ref('')

async function loadKartu(page = 1) {
  if (!props.produk?.id || !props.lokasi?.id) return
  loading.value = true
  error.value = ''
  try {
    const res = await produkApi.kartuStok(props.produk.id, {
      lokasi_id: props.lokasi.id,
      page,
      per_page: perPage.value,
    })
    items.value = res?.data || []
    meta.value = res?.meta || { page, per_page: perPage.value, total: items.value.length, total_pages: 1 }
  } catch (err) {
    error.value = err?.message || 'Gagal memuat Stock Card.'
  } finally {
    loading.value = false
  }
}

function changePerPage(value) {
  perPage.value = value
  loadKartu(1)
}

watch(
  () => [props.open, props.produk?.id, props.lokasi?.id],
  ([isOpen]) => {
    if (isOpen) {
      loadKartu(1)
    } else {
      items.value = []
      error.value = ''
    }
  }
)
</script>

<template>
  <BaseModal
    :open="open"
    :title="produk ? `Stock Card: ${produk.sku} - ${produk.nama}` : 'Stock Card'"
    size="lg"
    @close="emit('close')"
  >
    <div v-if="lokasi" class="detail-highlight">
      <div>
        <span class="detail-label">Lokasi</span>
        <div class="font-semibold">
          <span class="mono">{{ lokasi.kode }}</span> - {{ lokasi.nama }}
        </div>
      </div>
      <div v-if="stok">
        <span class="detail-label">Stock saat ini</span>
        <div class="font-semibold kartu-stock-now">
          <span class="mono">{{ formatNumber(stok.jumlah) }} {{ produk?.satuan }}</span>
          <BadgeStatus :value="stok.status" />
        </div>
        <span class="field-hint">Batas minimum {{ formatNumber(stok.stokMinimum) }}</span>
      </div>
      <div v-else-if="produk?.satuan">
        <span class="detail-label">Satuan</span>
        <div class="font-semibold mono">{{ produk.satuan }}</div>
      </div>
    </div>

    <LoadingState v-if="loading" :rows="4" />
    <ErrorState v-else-if="error" :message="error" @retry="loadKartu(meta.page)" />
    <EmptyState
      v-else-if="!items.length"
      title="Belum ada mutasi stock"
      description="Belum ada riwayat dokumen yang mengubah stock produk ini di lokasi terpilih."
    />

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Waktu</th>
            <th>Jenis</th>
            <th>Dokumen</th>
            <th class="num">Perubahan</th>
            <th class="num">Stock Sebelum</th>
            <th class="num">Stock Sesudah</th>
            <th>Oleh</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td data-label="Waktu" class="cell-secondary">{{ formatDateTime(row.created_at) }}</td>
            <td data-label="Jenis">
              <BadgeStatus :status="row.jenis" :label="MUTASI_TYPE_LABELS[row.jenis] || row.jenis" />
            </td>
            <td data-label="Dokumen" class="mono font-semibold">{{ row.dokumen }}</td>
            <td
              data-label="Perubahan"
              class="num mono font-semibold"
              :class="row.perubahan > 0 ? 'text-success' : 'text-danger'"
            >
              {{ row.perubahan > 0 ? `+${formatNumber(row.perubahan)}` : formatNumber(row.perubahan) }}
            </td>
            <td data-label="Stock Sebelum" class="num mono">{{ formatNumber(row.stok_sebelum) }}</td>
            <td data-label="Stock Sesudah" class="num mono font-semibold">
              {{ formatNumber(row.stok_sesudah) }}
            </td>
            <td data-label="Oleh">{{ row.oleh }}</td>
          </tr>
        </tbody>
      </table>
      <PaginationBar :meta="meta" @page="loadKartu" @per-page="changePerPage" />
    </div>

    <template #footer>
      <button type="button" class="btn btn-secondary" @click="emit('close')">Tutup</button>
      <RouterLink v-if="restock" :to="restock.to" class="btn btn-post" @click="emit('close')">
        <AppIcon :name="restock.icon" :size="16" />
        <span>{{ restock.label }}</span>
      </RouterLink>
    </template>
  </BaseModal>
</template>
