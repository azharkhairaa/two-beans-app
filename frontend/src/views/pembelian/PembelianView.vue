<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import DocumentItemsEditor from '@/components/DocumentItemsEditor.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FormField from '@/components/FormField.vue'
import LoadingState from '@/components/LoadingState.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import RiwayatDokumen from '@/components/RiwayatDokumen.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { useDetail } from '@/composables/useDetail'
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { useLokasiOptions, useOptions } from '@/composables/useOptions'
import { usePrefillQuery } from '@/composables/usePrefillQuery'
import { useTerimaForm } from '@/composables/useTerimaForm'
import { pembelianApi, produkApi, supplierApi } from '@/services'
import { useToastStore } from '@/stores/toast'
import { LOKASI_TYPES } from '@/utils/constants'
import {
  DOCUMENT_DATE_RANGE,
  PLAN_DATE_RANGE,
  formatDate,
  formatDateTime,
  formatNumber,
  formatRupiah,
  todayIso,
} from '@/utils/format'

const toast = useToastStore()
const route = useRoute()

const { items: supplierList, load: loadSuppliers } = useOptions(
  () => supplierApi.options(),
  'supplier'
)
const { items: lokasiList, load: loadLokasi } = useLokasiOptions()
const gudangUtama = computed(
  () => lokasiList.value.find((lok) => lok.jenis === LOKASI_TYPES.GUDANG_UTAMA) || null
)
const productOptions = ref([])

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => pembelianApi.list(params),
  {
    initialFilters: {
      q: '',
      supplier_id: '',
      status: route.query.status ? String(route.query.status) : '',
      dari: '',
      sampai: '',
      sort: 'created_at',
      arah: 'desc',
    },
    immediate: false,
  }
)

const prefill = usePrefillQuery()

onMounted(async () => {
  await Promise.all([loadSuppliers(), loadLokasi()])
  await load()
  if (route.query.id) {
    openDetail({ id: Number(route.query.id) })
  }
  // dari tombol "Buat PO" di peringatan stock menipis dashboard, harga awal = HPP produk saat ini
  await prefill.consume(async ({ produkId, jumlah }) => {
    await openCreate()
    const produk = productOptions.value.find((item) => item.id === produkId)
    values.items = [{ produk_id: produkId, jumlah, harga_satuan: produk?.harga_beli || '' }]
  })
})

async function loadPurchasableProducts() {
  if (productOptions.value.length) return
  try {
    const params = gudangUtama.value?.id ? { lokasi_id: gudangUtama.value.id } : {}
    const all = await produkApi.options(params)
    // BR-11: pembelian ke supplier hanya untuk green bean, peralatan dan bahan habis pakai
    productOptions.value = all.filter((p) => p.jenis !== 'roasted_bean')
  } catch {
    productOptions.value = []
  }
}

// formulir buat atau ubah draf pembelian (PO)
const modalOpen = ref(false)
const editingId = ref(null)
const editingKode = ref('')
const saveMode = ref('draf')

const { values, errors, message, submitting, submit, fill } = useForm({
  supplier_id: '',
  tanggal_perkiraan: '',
  catatan: '',
  items: [{ produk_id: '', jumlah: 1, harga_satuan: '' }],
})

async function openCreate() {
  editingId.value = null
  editingKode.value = ''
  await loadPurchasableProducts()
  fill({
    supplier_id: supplierList.value[0]?.id || '',
    tanggal_perkiraan: todayIso(),
    catatan: '',
    items: [{ produk_id: '', jumlah: 1, harga_satuan: '' }],
  })
  modalOpen.value = true
}

async function openEdit(row) {
  try {
    await loadPurchasableProducts()
    const detail = row.items ? row : await pembelianApi.get(row.id)
    editingId.value = detail.id
    editingKode.value = detail.kode
    fill({
      supplier_id: detail.supplier?.id || '',
      tanggal_perkiraan: detail.tanggal_perkiraan || '',
      catatan: detail.catatan || '',
      items: detail.items.map((it) => ({
        produk_id: it.produk.id,
        jumlah: it.jumlah,
        harga_satuan: it.harga_satuan,
      })),
    })
    detailOpen.value = false
    modalOpen.value = true
  } catch (err) {
    toast.show(err?.message || 'Gagal memuat draf pembelian.', 'error')
  }
}

async function onSave(mode = 'draf') {
  saveMode.value = mode
  const payload = {
    supplier_id: Number(values.supplier_id) || 0,
    tanggal_perkiraan: values.tanggal_perkiraan || null,
    catatan: values.catatan || null,
    items: values.items.map((it) => ({
      produk_id: Number(it.produk_id) || 0,
      jumlah: Number(it.jumlah) || 0,
      harga_satuan: Number(it.harga_satuan) || 0,
    })),
  }

  const saved = await submit(async () => {
    const draft = editingId.value
      ? await pembelianApi.update(editingId.value, payload)
      : await pembelianApi.create(payload)
    editingId.value = draft.id
    editingKode.value = draft.kode
    if (mode === 'pesan') {
      return await pembelianApi.pesan(draft.id, {
        tanggal_pesan: todayIso(),
        tanggal_perkiraan: payload.tanggal_perkiraan,
      })
    }
    return draft
  })

  if (saved) {
    if (mode === 'pesan') {
      toast.show(`Pesanan pembelian ${saved.kode} berhasil dikirim ke ${saved.supplier?.nama}.`)
    } else {
      toast.show(`Draf pembelian ${saved.kode} disimpan.`)
    }
    modalOpen.value = false
    await load()
  }
}

// detail pembelian
const {
  open: detailOpen,
  loading: detailLoading,
  data: detailData,
  show: openDetail,
  close: closeDetail,
} = useDetail((id) => pembelianApi.get(id), 'pembelian')

const detailTimeline = computed(() => {
  const d = detailData.value
  if (!d) return []
  const steps = [
    {
      label: 'Draf pesanan pembelian (PO) dibuat',
      user: d.dibuat_oleh?.name,
      time: d.created_at,
      tone: 'selesai',
    },
  ]
  if (d.status === 'dibatalkan') {
    steps.push({
      label: 'Pesanan pembelian dibatalkan',
      time: d.updated_at,
      tone: 'bahaya',
    })
    return steps
  }
  if (d.tanggal_pesan || d.dipesan_oleh) {
    steps.push({
      label: `Dipesan ke ${d.supplier?.nama || 'Supplier'}`,
      user: d.dipesan_oleh?.name,
      tone: d.status === 'dipesan' ? 'menunggu' : 'selesai',
      note: d.tanggal_pesan ? `Tanggal pesan: ${formatDate(d.tanggal_pesan)}` : '',
    })
  } else {
    steps.push({
      label: 'Pengiriman PO ke Supplier',
      placeholder: 'Masih berstatus draf — belum dikirim ke supplier',
      tone: 'netral',
    })
  }
  if (d.diterima_pada) {
    steps.push({
      label: `Barang diterima di ${d.lokasi?.nama || 'Gudang Utama'}`,
      user: d.diterima_oleh?.name,
      time: d.diterima_pada,
      tone: 'aman',
      note: `Total nilai diterima: ${formatRupiah(d.total_diterima || 0)}`,
    })
  } else {
    steps.push({
      label: 'Penerimaan Barang di Gudang Utama',
      placeholder:
        d.status === 'dipesan'
          ? 'Menunggu kedatangan barang dari supplier'
          : 'Menunggu pesanan dikirim',
      tone: 'netral',
    })
  }
  return steps
})

// modal pesan ke supplier
const pesanModalOpen = ref(false)
const pesanTarget = ref(null)
const pesanForm = useForm({
  tanggal_pesan: todayIso(),
  tanggal_perkiraan: '',
})

function openPesan(row) {
  pesanTarget.value = row
  const today = todayIso()
  pesanForm.fill({
    tanggal_pesan: today,
    tanggal_perkiraan:
      row.tanggal_perkiraan && row.tanggal_perkiraan >= today ? row.tanggal_perkiraan : today,
  })
  pesanModalOpen.value = true
}

async function onConfirmPesan() {
  if (!pesanTarget.value) return
  const payload = {
    tanggal_pesan: pesanForm.values.tanggal_pesan || null,
    tanggal_perkiraan: pesanForm.values.tanggal_perkiraan || null,
  }
  const res = await pesanForm.submit(() => pembelianApi.pesan(pesanTarget.value.id, payload))
  if (res) {
    toast.show(`Pesanan pembelian ${res.kode} dikirim ke ${res.supplier?.nama}.`)
    pesanModalOpen.value = false
    if (detailOpen.value && detailData.value?.id === res.id) {
      detailData.value = res
    }
    await load()
  }
}

// modal terima barang pembelian
const {
  open: terimaModalOpen,
  target: terimaTarget,
  loadingDetail: terimaLoadingDetail,
  submitting: terimaSubmitting,
  message: terimaMessage,
  errors: terimaErrors,
  form: terimaForm,
  show: openTerima,
  confirm: onConfirmTerima,
  close: closeTerima,
} = useTerimaForm({
  label: 'pembelian',
  fetchDetail: (id) => pembelianApi.get(id),
  toForm: (detail) => ({
    catatan: detail.catatan || '',
    items: detail.items.map((it) => ({
      produk_id: it.produk.id,
      sku: it.produk.sku,
      nama: it.produk.nama,
      satuan: it.produk.satuan,
      harga_satuan: it.harga_satuan,
      jumlah: it.jumlah,
      jumlah_diterima: it.jumlah,
    })),
  }),
  toPayload: (form) => ({
    catatan: form.catatan?.trim() || null,
    items: form.items.map((it) => ({
      produk_id: Number(it.produk_id),
      jumlah_diterima: it.jumlah_diterima === '' ? -1 : Number(it.jumlah_diterima),
    })),
  }),
  submit: (id, payload) => pembelianApi.terima(id, payload),
  successMessage: (res) =>
    `Pembelian ${res.kode} diterima. ` +
    'Stock Gudang Utama bertambah dan HPP produk telah diperbarui.',
  onSaved: async (res) => {
    if (detailOpen.value && detailData.value?.id === res.id) detailData.value = res
    await load()
  },
})

const terimaTotalNilai = computed(() =>
  terimaForm.items.reduce(
    (sum, it) => sum + (Number(it.jumlah_diterima) || 0) * (Number(it.harga_satuan) || 0),
    0
  )
)

// modal konfirmasi batal atau hapus
const confirmAction = ref(null)
const confirmLoading = ref(false)
const confirmError = ref('')

function openBatal(row) {
  confirmAction.value = {
    type: 'batal',
    row,
    title: 'Batalkan Pesanan Pembelian',
    message: `Batalkan pembelian ${row.kode} ke ${row.supplier?.nama || 'supplier'}? Status dokumen akan berubah menjadi dibatalkan.`,
    confirmLabel: 'Batalkan PO',
    variant: 'danger',
  }
  confirmError.value = ''
}

function openDelete(row) {
  confirmAction.value = {
    type: 'delete',
    row,
    title: 'Hapus Draf Pembelian',
    message: `Hapus draf pembelian ${row.kode}? Tindakan ini tidak bisa dibatalkan.`,
    confirmLabel: 'Hapus Draf',
    variant: 'danger',
  }
  confirmError.value = ''
}

async function onConfirmExecute() {
  if (!confirmAction.value) return
  const { type, row } = confirmAction.value
  confirmLoading.value = true
  confirmError.value = ''
  try {
    if (type === 'batal') {
      const res = await pembelianApi.batal(row.id)
      toast.show(`Pembelian ${res.kode} dibatalkan.`)
      if (detailOpen.value && detailData.value?.id === res.id) {
        detailData.value = res
      }
    } else {
      await pembelianApi.remove(row.id)
      toast.show(`Draf pembelian ${row.kode} dihapus.`)
      detailOpen.value = false
    }
    confirmAction.value = null
    await load()
  } catch (err) {
    confirmError.value = err?.message || 'Gagal memproses pembelian.'
  } finally {
    confirmLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Pembelian ke Supplier</h2>
        <p class="page-subtitle">
          Pesanan pembelian (PO) green bean, peralatan dan bahan habis pakai untuk Gudang Utama
        </p>
      </div>
      <button type="button" class="btn btn-post" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Buat pesanan (PO)</span>
      </button>
    </header>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="po-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="po-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari kode PO-... atau catatan..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div class="toolbar-field">
          <label class="toolbar-label" for="po-filter-supplier">Supplier</label>
          <SearchSelect
            id="po-filter-supplier"
            v-model="filters.supplier_id"
            :options="supplierList.map((sup) => ({ value: sup.id, label: `${sup.nama}` }))"
            empty-label="Semua supplier"
            small
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="po-filter-status">Status</label>
          <select
            id="po-filter-status"
            v-model="filters.status"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua status</option>
            <option value="draf">Draf</option>
            <option value="dipesan">Dipesan (Menunggu Tiba)</option>
            <option value="diterima">Diterima</option>
            <option value="dibatalkan">Dibatalkan</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="po-filter-dari">Dari Tanggal</label>
          <input
            id="po-filter-dari"
            v-model="filters.dari"
            type="date"
            :max="filters.sampai || undefined"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="po-filter-sampai">Sampai Tanggal</label>
          <input
            id="po-filter-sampai"
            v-model="filters.sampai"
            type="date"
            :min="filters.dari || undefined"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="po-filter-sort">Sort</label>
          <select
            id="po-filter-sort"
            v-model="filters.sort"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="created_at">Waktu dibuat</option>
            <option value="tanggal_pesan">Tanggal pesan</option>
            <option value="kode">Kode dokumen</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="po-filter-arah">Order</label>
          <select
            id="po-filter-arah"
            v-model="filters.arah"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
        <button type="submit" class="btn btn-secondary btn-sm">Filter</button>
      </div>
    </form>

    <LoadingState v-if="loading" :rows="5" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState
      v-else-if="!items.length"
      title="Belum ada pesanan pembelian"
      description="Tidak ada dokumen PO yang cocok dengan filter pencarian saat ini."
    >
      <button type="button" class="btn btn-secondary btn-sm" @click="resetFilters">
        Reset filter
      </button>
    </EmptyState>

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Kode</th>
            <th>Supplier</th>
            <th>Tanggal Pesan</th>
            <th>Perkiraan Tiba</th>
            <th>Status</th>
            <th class="num">Total Nilai</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in items"
            :key="row.id"
            :class="{ 'row-highlight': row.status === 'dipesan' }"
          >
            <td data-label="Kode">
              <div class="mono font-semibold">{{ row.kode }}</div>
              <div class="cell-secondary">{{ row.lokasi?.nama }}</div>
            </td>
            <td data-label="Supplier">
              <div class="cell-primary">{{ row.supplier?.nama }}</div>
              <div v-if="row.supplier?.kontak || row.supplier?.telepon" class="cell-secondary">
                {{ row.supplier.kontak }}
                <span v-if="row.supplier.telepon" class="mono">· {{ row.supplier.telepon }}</span>
              </div>
            </td>
            <td data-label="Tanggal Pesan" class="mono">
              {{ row.tanggal_pesan ? formatDate(row.tanggal_pesan) : '-' }}
            </td>
            <td data-label="Perkiraan Tiba" class="mono">
              {{ row.tanggal_perkiraan ? formatDate(row.tanggal_perkiraan) : '-' }}
            </td>
            <td data-label="Status">
              <BadgeStatus :status="row.status" />
            </td>
            <td data-label="Total Nilai" class="num">
              <div class="mono font-semibold">{{ formatRupiah(row.total_pesanan) }}</div>
              <div class="cell-secondary mono">
                {{ row.jumlah_item }} item
                <template v-if="row.total_diterima !== null && row.total_diterima !== undefined">
                  · Diterima {{ formatRupiah(row.total_diterima) }}
                </template>
              </div>
            </td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button type="button" class="btn btn-get-outline btn-sm" @click="openDetail(row)">
                  Detail
                </button>
                <template v-if="row.status === 'draf'">
                  <button type="button" class="btn btn-put btn-sm" @click="openEdit(row)">
                    Ubah
                  </button>
                  <button type="button" class="btn btn-post btn-sm" @click="openPesan(row)">
                    Pesan
                  </button>
                  <button
                    type="button"
                    class="btn btn-delete btn-sm"
                    @click="openDelete(row)"
                  >
                    Hapus
                  </button>
                </template>
                <template v-else-if="row.status === 'dipesan'">
                  <button type="button" class="btn btn-post btn-sm" @click="openTerima(row)">
                    Terima
                  </button>
                  <button
                    type="button"
                    class="btn btn-delete btn-sm"
                    @click="openBatal(row)"
                  >
                    Batal
                  </button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <PaginationBar :meta="meta" @page="setPage" @per-page="setPerPage" />
    </div>

    <!-- modal buat atau ubah draf pembelian -->
    <BaseModal
      :open="modalOpen"
      :title="editingId ? `Ubah Draf Pembelian: ${editingKode}` : 'Buat Pesanan Pembelian (PO)'"
      size="xl"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="pembelian-form" class="form-stack" novalidate @submit.prevent="onSave('draf')">
        <div class="form-row-2">
          <FormField id="po-supplier" label="Supplier pemasok" :error="errors.supplier_id">
            <template #default="{ describedBy }">
              <SearchSelect
                id="po-supplier"
                v-model="values.supplier_id"
                :options="supplierList.map((sup) => ({ value: sup.id, label: `${sup.nama}` }))"
                placeholder="Pilih supplier..."
                required
                :invalid="Boolean(errors.supplier_id)"
                :described-by="describedBy"
              />
            </template>
          </FormField>

          <FormField
            id="po-perkiraan"
            label="Perkiraan tanggal tiba (opsional)"
            :error="errors.tanggal_perkiraan"
          >
            <template #default="{ describedBy }">
              <input
                id="po-perkiraan"
                v-model="values.tanggal_perkiraan"
                type="date"
                :min="PLAN_DATE_RANGE.min()"
                :max="PLAN_DATE_RANGE.max()"
                class="input mono"
                :aria-invalid="Boolean(errors.tanggal_perkiraan)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField id="po-catatan" label="Catatan pesanan (opsional)" :error="errors.catatan">
          <template #default="{ describedBy }">
            <textarea
              id="po-catatan"
              v-model.trim="values.catatan"
              rows="2"
              class="input"
              placeholder="Spesifikasi kadar air green bean, jadwal pengiriman supplier atau catatan PO..."
              :aria-invalid="Boolean(errors.catatan)"
              :aria-describedby="describedBy"
            ></textarea>
          </template>
        </FormField>

        <DocumentItemsEditor
          v-model="values.items"
          :products="productOptions"
          :show-stock="true"
          :with-price="true"
          default-price-field="harga_beli"
          :errors="errors"
        />
      </form>

      <template #footer>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="submitting"
          @click="modalOpen = false"
        >
          Batal
        </button>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="submitting"
          @click="onSave('draf')"
        >
          <span v-if="submitting && saveMode === 'draf'" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting && saveMode === 'draf' ? 'Menyimpan...' : 'Simpan draf' }}</span>
        </button>
        <button
          type="button"
          class="btn btn-post"
          :disabled="submitting"
          @click="onSave('pesan')"
        >
          <span v-if="submitting && saveMode === 'pesan'" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting && saveMode === 'pesan' ? 'Memproses...' : 'Simpan lalu pesan' }}</span>
        </button>
      </template>
    </BaseModal>

    <!-- modal detail pembelian -->
    <BaseModal
      :open="detailOpen"
      :title="detailData ? `Detail Pembelian: ${detailData.kode}` : 'Detail Pembelian'"
      size="xl"
      @close="closeDetail"
    >
      <LoadingState v-if="detailLoading" :rows="4" />
      <div v-else-if="detailData" class="detail-grid">
        <div class="detail-highlight">
          <div>
            <div class="sku-summary">
              <span class="mono font-semibold">{{ detailData.kode }}</span>
              <BadgeStatus :status="detailData.status" />
            </div>
            <p class="cell-secondary">
              Dibuat pada <strong class="mono">{{ formatDateTime(detailData.created_at) }}</strong>
              oleh <strong>{{ detailData.dibuat_oleh?.name }}</strong>
            </p>
          </div>
          <div class="num">
            <span class="detail-label">Total Nilai Pesanan</span>
            <div class="detail-value mono font-semibold">
              {{ formatRupiah(detailData.total_pesanan) }}
            </div>
          </div>
        </div>

        <div class="summary-strip">
          <div class="summary-item">
            <span class="detail-label">Supplier</span>
            <strong class="cell-primary">{{ detailData.supplier?.nama }}</strong>
            <span v-if="detailData.supplier?.telepon" class="cell-secondary mono">
              {{ detailData.supplier.telepon }}
            </span>
          </div>
          <div class="summary-item">
            <span class="detail-label">Lokasi Penerima</span>
            <strong class="cell-primary">{{ detailData.lokasi?.nama }}</strong>
            <span class="cell-secondary mono">{{ detailData.lokasi?.kode }}</span>
          </div>
          <div class="summary-item">
            <span class="detail-label">Jadwal Pesanan</span>
            <strong class="cell-primary mono">
              Pesan: {{ detailData.tanggal_pesan ? formatDate(detailData.tanggal_pesan) : '-' }}
            </strong>
            <span class="cell-secondary mono">
              Tiba: {{ detailData.tanggal_perkiraan ? formatDate(detailData.tanggal_perkiraan) : '-' }}
            </span>
          </div>
        </div>

        <p v-if="detailData.catatan" class="cell-secondary">
          <strong>Catatan PO:</strong> {{ detailData.catatan }}
        </p>

        <RiwayatDokumen :steps="detailTimeline" />

        <div class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Produk</th>
                <th class="num">Harga Satuan</th>
                <th class="num">Dipesan</th>
                <th class="num">Subtotal PO</th>
                <th class="num">Diterima</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in detailData.items" :key="item.id">
                <td data-label="SKU" class="mono font-semibold">{{ item.produk.sku }}</td>
                <td data-label="Produk">
                  <div class="cell-primary">{{ item.produk.nama }}</div>
                  <BadgeStatus :status="item.produk.jenis" />
                </td>
                <td data-label="Harga Satuan" class="num mono">
                  {{ formatRupiah(item.harga_satuan) }}
                </td>
                <td data-label="Dipesan" class="num mono font-semibold">
                  {{ formatNumber(item.jumlah) }} {{ item.produk.satuan }}
                </td>
                <td data-label="Subtotal PO" class="num mono font-semibold">
                  {{ formatRupiah(item.subtotal) }}
                </td>
                <td data-label="Diterima" class="num mono">
                  <template v-if="item.jumlah_diterima !== null && item.jumlah_diterima !== undefined">
                    <div>{{ formatNumber(item.jumlah_diterima) }} {{ item.produk.satuan }}</div>
                    <div class="cell-secondary">{{ formatRupiah(item.subtotal_diterima) }}</div>
                  </template>
                  <span v-else class="cell-secondary">-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <template #footer>
        <button type="button" class="btn btn-secondary" @click="closeDetail">Tutup</button>
        <template v-if="detailData?.status === 'draf'">
          <button
            type="button"
            class="btn btn-delete"
            @click="openDelete(detailData)"
          >
            Hapus draf
          </button>
          <button
            type="button"
            class="btn btn-delete"
            @click="openBatal(detailData)"
          >
            Batalkan
          </button>
          <button type="button" class="btn btn-put" @click="openEdit(detailData)">
            Ubah draf
          </button>
          <button type="button" class="btn btn-post" @click="openPesan(detailData)">
            Kirim pesanan ke supplier
          </button>
        </template>
        <template v-else-if="detailData?.status === 'dipesan'">
          <button
            type="button"
            class="btn btn-delete"
            @click="openBatal(detailData)"
          >
            Batalkan PO
          </button>
          <button type="button" class="btn btn-post" @click="openTerima(detailData)">
            Konfirmasi terima barang
          </button>
        </template>
      </template>
    </BaseModal>

    <!-- modal pesan ke supplier -->
    <BaseModal
      :open="pesanModalOpen"
      :title="pesanTarget ? `Kirim Pesanan: ${pesanTarget.kode}` : 'Kirim Pesanan ke Supplier'"
      size="md"
      @close="pesanModalOpen = false"
    >
      <p v-if="pesanForm.message.value" class="alert alert-error" role="alert">
        {{ pesanForm.message.value }}
      </p>
      <p v-if="pesanTarget" class="confirm-message">
        Kirim pesanan pembelian <strong class="mono">{{ pesanTarget.kode }}</strong> senilai
        <strong class="mono">{{ formatRupiah(pesanTarget.total_pesanan) }}</strong> ke supplier
        <strong>{{ pesanTarget.supplier?.nama }}</strong>? Setelah dipesan, rincian barang pada PO
        tidak dapat diubah lagi.
      </p>
      <form id="pesan-form" class="form-stack" novalidate @submit.prevent="onConfirmPesan">
        <div class="form-row-2">
          <FormField
            id="pesan-tanggal"
            label="Tanggal pesan"
            :error="pesanForm.errors.value.tanggal_pesan"
          >
            <template #default="{ describedBy }">
              <input
                id="pesan-tanggal"
                v-model="pesanForm.values.tanggal_pesan"
                type="date"
                :min="DOCUMENT_DATE_RANGE.min()"
                :max="DOCUMENT_DATE_RANGE.max()"
                class="input mono"
                required
                :aria-invalid="Boolean(pesanForm.errors.value.tanggal_pesan)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField
            id="pesan-perkiraan"
            label="Perkiraan tiba"
            :error="pesanForm.errors.value.tanggal_perkiraan"
          >
            <template #default="{ describedBy }">
              <input
                id="pesan-perkiraan"
                v-model="pesanForm.values.tanggal_perkiraan"
                type="date"
                :min="PLAN_DATE_RANGE.min()"
                :max="PLAN_DATE_RANGE.max()"
                class="input mono"
                :aria-invalid="Boolean(pesanForm.errors.value.tanggal_perkiraan)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>
      </form>

      <template #footer>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="pesanForm.submitting.value"
          @click="pesanModalOpen = false"
        >
          Batal
        </button>
        <button
          type="submit"
          form="pesan-form"
          class="btn btn-post"
          :disabled="pesanForm.submitting.value"
        >
          {{ pesanForm.submitting.value ? 'Mengirim...' : 'Kirim pesanan' }}
        </button>
      </template>
    </BaseModal>

    <!-- modal terima barang pembelian -->
    <BaseModal
      :open="terimaModalOpen"
      :title="terimaTarget ? `Terima Barang PO: ${terimaTarget.kode}` : 'Terima Barang Pembelian'"
      size="xl"
      @close="closeTerima"
    >
      <LoadingState v-if="terimaLoadingDetail" :rows="3" />
      <template v-else-if="terimaTarget">
        <p v-if="terimaMessage" class="alert alert-error" role="alert">{{ terimaMessage }}</p>
        <p v-if="terimaErrors.items" class="alert alert-error" role="alert">
          {{ terimaErrors.items }}
        </p>
        <p class="confirm-message">
          Konfirmasi penerimaan barang dari supplier
          <strong>{{ terimaTarget.supplier?.nama }}</strong> di
          <strong>{{ terimaTarget.lokasi?.nama }}</strong>. Stock Gudang Utama akan langsung
          bertambah sebesar jumlah diterima dan HPP produk akan diperbarui mengikuti harga PO
          ini.
        </p>

        <form id="terima-po-form" class="form-stack" novalidate @submit.prevent="onConfirmTerima">
          <div class="table-card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Produk</th>
                  <th class="num">Harga Satuan</th>
                  <th class="num">Dipesan</th>
                  <th class="num">Jumlah Diterima</th>
                  <th class="num">Subtotal Diterima</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in terimaForm.items" :key="item.produk_id">
                  <td data-label="Produk">
                    <div class="cell-primary">{{ item.nama }}</div>
                    <div class="cell-secondary mono">{{ item.sku }}</div>
                  </td>
                  <td data-label="Harga Satuan" class="num mono">
                    {{ formatRupiah(item.harga_satuan) }}
                  </td>
                  <td data-label="Dipesan" class="num mono font-semibold">
                    {{ formatNumber(item.jumlah) }} {{ item.satuan }}
                  </td>
                  <td data-label="Jumlah Diterima" class="num">
                    <div class="doc-qty-wrap">
                      <input
                        :id="`po-terima-qty-${idx}`"
                        v-model.number="item.jumlah_diterima"
                        type="number"
                        min="0"
                        :max="item.jumlah"
                        step="1"
                        class="input input-sm mono"
                        :aria-label="`Jumlah diterima ${item.nama}`"
                        :aria-invalid="Boolean(terimaErrors[`items.${idx}.jumlah_diterima`])"
                      />
                      <span class="badge badge-draf">{{ item.satuan }}</span>
                    </div>
                    <p v-if="terimaErrors[`items.${idx}.jumlah_diterima`]" class="field-error">
                      {{ terimaErrors[`items.${idx}.jumlah_diterima`] }}
                    </p>
                  </td>
                  <td data-label="Subtotal Diterima" class="num mono font-semibold">
                    {{
                      formatRupiah(
                        (Number(item.jumlah_diterima) || 0) * (Number(item.harga_satuan) || 0)
                      )
                    }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="doc-items-summary">
            <span>
              Total nilai diterima:
              <strong class="mono">{{ formatRupiah(terimaTotalNilai) }}</strong>
            </span>
          </div>

          <FormField
            id="po-terima-catatan"
            label="Catatan penerimaan PO (opsional)"
            :error="terimaErrors.catatan"
          >
            <template #default="{ describedBy }">
              <textarea
                id="po-terima-catatan"
                v-model.trim="terimaForm.catatan"
                rows="2"
                class="input"
                placeholder="Nomor surat jalan supplier, hasil cek kualitas bahan atau keterangan lain..."
                :aria-invalid="Boolean(terimaErrors.catatan)"
                :aria-describedby="describedBy"
              ></textarea>
            </template>
          </FormField>
        </form>
      </template>

      <template #footer>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="terimaSubmitting"
          @click="closeTerima"
        >
          Batal
        </button>
        <button
          type="submit"
          form="terima-po-form"
          class="btn btn-post"
          :disabled="terimaSubmitting || terimaLoadingDetail"
        >
          {{ terimaSubmitting ? 'Menyimpan...' : 'Konfirmasi terima barang' }}
        </button>
      </template>
    </BaseModal>

    <!-- modal konfirmasi batal atau hapus -->
    <ConfirmModal
      :open="Boolean(confirmAction)"
      :title="confirmAction?.title || 'Konfirmasi'"
      :message="confirmAction?.message || ''"
      :confirm-label="confirmAction?.confirmLabel || 'Konfirmasi'"
      :variant="confirmAction?.variant || 'danger'"
      :loading="confirmLoading"
      :error="confirmError"
      @close="confirmAction = null"
      @confirm="onConfirmExecute"
    />
  </section>
</template>
