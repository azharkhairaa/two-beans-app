<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

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
import { customerApi, penjualanApi, produkApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import {
  CUSTOMER_TYPE_LABELS,
  LOKASI_TYPE_LABELS,
  LOKASI_TYPES,
} from '@/utils/constants'
import {
  DOCUMENT_DATE_RANGE,
  formatDate,
  formatDateTime,
  formatMargin,
  formatNumber,
  formatRupiah,
  todayIso,
} from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const { items: lokasiList, load: loadLokasi } = useLokasiOptions()
const { items: customerOptions, load: loadCustomers } = useOptions(
  () => customerApi.options(),
  'customer'
)

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => penjualanApi.list(params),
  {
    initialFilters: {
      q: '',
      lokasi_id: '',
      customer_id: '',
      status: route.query.status ? String(route.query.status) : '',
      dari: '',
      sampai: '',
      sort: 'tanggal',
      arah: 'desc',
    },
    immediate: false,
  }
)

onMounted(async () => {
  await Promise.all([loadCustomers(), auth.isAdmin ? loadLokasi() : null])
  await load()
  if (route.query.id) {
    openDetail({ id: Number(route.query.id) })
  }
})

const postedRows = computed(() => items.value.filter((row) => row.status === 'diposting'))

const omzetHalamanDiposting = computed(() =>
  postedRows.value.reduce((sum, row) => sum + (Number(row.total) || 0), 0)
)

const marginHalamanDiposting = computed(() =>
  postedRows.value.reduce((sum, row) => sum + (Number(row.margin) || 0), 0)
)

const totalHalamanSemua = computed(() =>
  items.value.reduce((sum, row) => sum + (Number(row.total) || 0), 0)
)

function goNota(row) {
  router.push({ name: 'penjualan-nota', params: { id: row.id } })
}

// formulir buat atau ubah draf penjualan
const modalOpen = ref(false)
const editingId = ref(null)
const editingKode = ref('')
const productOptions = ref([])
const saveMode = ref('draf')

const { values, errors, message, submitting, submit, fill } = useForm({
  lokasi_id: '',
  tanggal: todayIso(),
  customer_id: '',
  catatan: '',
  items: [{ produk_id: '', jumlah: 1, harga_satuan: '' }],
})

const selectedLokasi = computed(() => {
  if (auth.isAdmin) {
    return lokasiList.value.find((l) => Number(l.id) === Number(values.lokasi_id)) || null
  }
  return auth.user?.lokasi || null
})

const isOutletSale = computed(() => selectedLokasi.value?.jenis === LOKASI_TYPES.OUTLET)

async function loadProductOptions() {
  const lokasiId = auth.isAdmin ? values.lokasi_id : auth.user?.lokasi?.id
  if (!lokasiId) {
    productOptions.value = []
    return
  }
  try {
    productOptions.value = await produkApi.options({ lokasi_id: lokasiId })
  } catch {
    productOptions.value = []
  }
}

async function onLokasiChange(rawId) {
  values.lokasi_id = rawId ? Number(rawId) : ''
  const lok = lokasiList.value.find((l) => Number(l.id) === Number(rawId))
  if (lok && lok.jenis !== LOKASI_TYPES.OUTLET && !values.customer_id) {
    values.customer_id = customerOptions.value[0]?.id || ''
  }
  await loadProductOptions()
}

async function openCreate() {
  editingId.value = null
  editingKode.value = ''
  const defaultLokasi = auth.isAdmin ? lokasiList.value[0] || null : auth.user?.lokasi || null
  const isOutlet = defaultLokasi?.jenis === LOKASI_TYPES.OUTLET
  fill({
    lokasi_id: defaultLokasi?.id || '',
    tanggal: todayIso(),
    customer_id: isOutlet ? '' : customerOptions.value[0]?.id || '',
    catatan: '',
    items: [{ produk_id: '', jumlah: 1, harga_satuan: '' }],
  })
  modalOpen.value = true
  await loadProductOptions()
}

async function openEdit(row) {
  try {
    const detail = row.items ? row : await penjualanApi.get(row.id)
    editingId.value = detail.id
    editingKode.value = detail.kode
    fill({
      lokasi_id: detail.lokasi?.id || '',
      tanggal: detail.tanggal,
      customer_id: detail.customer?.id || '',
      catatan: detail.catatan || '',
      items: detail.items.map((it) => ({
        produk_id: it.produk.id,
        jumlah: it.jumlah,
        harga_satuan: it.harga_satuan,
      })),
    })
    detailOpen.value = false
    modalOpen.value = true
    await loadProductOptions()
  } catch (err) {
    toast.show(err?.message || 'Gagal memuat draf penjualan.', 'error')
  }
}

async function onSave(mode = 'draf') {
  saveMode.value = mode
  const payload = {
    lokasi_id: auth.isAdmin ? Number(values.lokasi_id) || null : null,
    tanggal: values.tanggal,
    customer_id: values.customer_id ? Number(values.customer_id) : null,
    catatan: values.catatan || null,
    items: values.items.map((it) => ({
      produk_id: Number(it.produk_id) || 0,
      jumlah: Number(it.jumlah) || 0,
      harga_satuan: it.harga_satuan === '' ? null : Number(it.harga_satuan) || 0,
    })),
  }

  const saved = await submit(async () => {
    const draft = editingId.value
      ? await penjualanApi.update(editingId.value, payload)
      : await penjualanApi.create(payload)
    editingId.value = draft.id
    editingKode.value = draft.kode
    if (mode === 'posting') {
      return await penjualanApi.posting(draft.id)
    }
    return draft
  })

  if (saved) {
    if (mode === 'posting') {
      toast.show(
        `Penjualan ${saved.kode} diposting. Stock ${saved.lokasi?.nama || 'lokasi penjual'} sudah dikurangi.`
      )
    } else {
      toast.show(`Draf penjualan ${saved.kode} disimpan.`)
    }
    modalOpen.value = false
    await load()
  }
}

// modal cepat tambah customer baru
const newCustomerOpen = ref(false)
const customerForm = useForm({
  nama: '',
  jenis: 'kafe',
  kontak: '',
  telepon: '',
  email: '',
  alamat: '',
  aktif: true,
})

function openNewCustomer() {
  customerForm.fill({
    nama: '',
    jenis: 'kafe',
    kontak: '',
    telepon: '',
    email: '',
    alamat: '',
    aktif: true,
  })
  newCustomerOpen.value = true
}

async function onSaveNewCustomer() {
  const payload = {
    nama: customerForm.values.nama,
    jenis: customerForm.values.jenis,
    kontak: customerForm.values.kontak || null,
    telepon: customerForm.values.telepon || null,
    email: customerForm.values.email || null,
    alamat: customerForm.values.alamat || null,
    aktif: true,
  }
  const created = await customerForm.submit(() => customerApi.create(payload))
  if (created) {
    customerOptions.value = [
      ...customerOptions.value,
      { id: created.id, nama: created.nama },
    ].sort((a, b) => a.nama.localeCompare(b.nama))
    values.customer_id = created.id
    newCustomerOpen.value = false
    toast.show(`Customer ${created.nama} ditambahkan dan dipilih.`)
  }
}

// detail penjualan
const {
  open: detailOpen,
  loading: detailLoading,
  data: detailData,
  show: openDetail,
  close: closeDetail,
} = useDetail((id) => penjualanApi.get(id), 'penjualan')

const detailTimeline = computed(() => {
  const d = detailData.value
  if (!d) return []
  const steps = [
    {
      label: `Draf penjualan dibuat di ${d.lokasi?.nama || 'Lokasi'}`,
      user: d.dibuat_oleh,
      time: d.created_at,
      tone: 'selesai',
    },
  ]
  if (d.diposting_pada) {
    steps.push({
      label: 'Penjualan diposting & stok dikurangi',
      user: d.diposting_oleh,
      time: d.diposting_pada,
      tone: 'aman',
      note: `Total penjualan: ${formatRupiah(d.total)}`,
    })
  } else {
    steps.push({
      label: 'Posting Penjualan',
      placeholder: 'Masih berstatus draf — stok lokasi belum dikurangi',
      tone: 'menunggu',
    })
  }
  return steps
})

// modal konfirmasi posting atau hapus
const confirmAction = ref(null)
const confirmLoading = ref(false)
const confirmError = ref('')

function openPosting(row) {
  confirmAction.value = {
    type: 'posting',
    row,
    title: 'Posting Penjualan',
    message: `Posting penjualan ${row.kode} senilai ${formatRupiah(row.total)}? Stock ${row.jumlah_item} produk di ${row.lokasi?.nama || 'lokasi penjual'} akan berkurang dan penjualan tidak bisa diedit lagi.`,
    confirmLabel: 'Posting Sekarang',
    variant: 'primary',
  }
  confirmError.value = ''
}

function openDelete(row) {
  confirmAction.value = {
    type: 'delete',
    row,
    title: 'Hapus Draf Penjualan',
    message: `Hapus draf penjualan ${row.kode}? Tindakan ini tidak bisa dibatalkan.`,
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
    if (type === 'posting') {
      const res = await penjualanApi.posting(row.id)
      toast.show(
        `Penjualan ${res.kode} diposting. Stock ${res.lokasi?.nama || 'lokasi penjual'} sudah dikurangi.`
      )
      if (detailOpen.value && detailData.value?.id === res.id) {
        detailData.value = res
      }
    } else {
      await penjualanApi.remove(row.id)
      toast.show(`Draf penjualan ${row.kode} dihapus.`)
      detailOpen.value = false
    }
    confirmAction.value = null
    await load()
  } catch (err) {
    const fieldMsg = err?.errors ? Object.values(err.errors).join(' | ') : ''
    confirmError.value = fieldMsg
      ? `${err.message}: ${fieldMsg}`
      : err?.message || 'Gagal memproses penjualan.'
  } finally {
    confirmLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Penjualan ke Customer</h2>
        <p class="page-subtitle">
          Pencatatan penjualan biji kopi, peralatan dan bahan habis pakai beserta cetak nota penjualan
        </p>
      </div>
      <button type="button" class="btn btn-post" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Penjualan baru</span>
      </button>
    </header>

    <div class="summary-strip">
      <div class="summary-item">
        <span class="detail-label">Total Dokumen Terfilter</span>
        <strong class="detail-value mono">{{ formatNumber(meta.total || 0) }} nota</strong>
      </div>
      <div class="summary-item">
        <span class="detail-label">Omzet Diposting (Halaman Ini)</span>
        <strong class="detail-value mono">{{ formatRupiah(omzetHalamanDiposting) }}</strong>
      </div>
      <div class="summary-item">
        <span class="detail-label">Margin Diposting (Halaman Ini)</span>
        <strong class="detail-value mono" :class="{ 'text-danger': marginHalamanDiposting < 0 }">
          {{ formatMargin(marginHalamanDiposting, omzetHalamanDiposting) }}
        </strong>
      </div>
      <div class="summary-item">
        <span class="detail-label">Total Nilai Termasuk Draf (Halaman Ini)</span>
        <strong class="detail-value mono">{{ formatRupiah(totalHalamanSemua) }}</strong>
      </div>
    </div>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="pjl-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="pjl-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari kode PJ-... atau catatan..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div v-if="auth.isAdmin" class="toolbar-field toolbar-field-lokasi">
          <label class="toolbar-label" for="pjl-filter-lokasi">Lokasi</label>
          <SearchSelect
            id="pjl-filter-lokasi"
            v-model="filters.lokasi_id"
            :options="lokasiList.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama}` }))"
            empty-label="Semua lokasi"
            small
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pjl-filter-customer">Customer</label>
          <SearchSelect
            id="pjl-filter-customer"
            v-model="filters.customer_id"
            :options="customerOptions.map((cust) => ({ value: cust.id, label: `${cust.nama}` }))"
            empty-label="Semua customer"
            small
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pjl-filter-status">Status</label>
          <select
            id="pjl-filter-status"
            v-model="filters.status"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua status</option>
            <option value="draf">Draf</option>
            <option value="diposting">Diposting</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pjl-filter-dari">Dari Tanggal</label>
          <input
            id="pjl-filter-dari"
            v-model="filters.dari"
            type="date"
            :max="filters.sampai || undefined"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pjl-filter-sampai">Sampai Tanggal</label>
          <input
            id="pjl-filter-sampai"
            v-model="filters.sampai"
            type="date"
            :min="filters.dari || undefined"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pjl-filter-sort">Sort</label>
          <select
            id="pjl-filter-sort"
            v-model="filters.sort"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="tanggal">Tanggal</option>
            <option value="total">Total penjualan</option>
            <option value="kode">Kode dokumen</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pjl-filter-arah">Order</label>
          <select
            id="pjl-filter-arah"
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
      title="Belum ada dokumen penjualan"
      description="Tidak ada penjualan yang cocok dengan filter pencarian saat ini."
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
            <th>Tanggal</th>
            <th v-if="auth.isAdmin">Lokasi</th>
            <th>Customer</th>
            <th class="num">Baris</th>
            <th class="num">Total</th>
            <th>Status</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td data-label="Kode">
              <div class="mono font-semibold">{{ row.kode }}</div>
              <div class="cell-secondary">Oleh {{ row.dibuat_oleh }}</div>
            </td>
            <td data-label="Tanggal" class="mono">{{ formatDate(row.tanggal) }}</td>
            <td v-if="auth.isAdmin" data-label="Lokasi">
              <div class="cell-primary">{{ row.lokasi?.nama }}</div>
              <div class="cell-secondary mono">{{ row.lokasi?.kode }}</div>
            </td>
            <td data-label="Customer">
              <div class="cell-primary">{{ row.nama_customer }}</div>
              <div v-if="row.customer?.jenis" class="cell-secondary">
                {{ CUSTOMER_TYPE_LABELS[row.customer.jenis] || row.customer.jenis }}
              </div>
              <div v-else class="cell-secondary">Pembeli eceran outlet</div>
            </td>
            <td data-label="Baris" class="num mono">{{ row.jumlah_item }} item</td>
            <td data-label="Total" class="num mono">
              <div class="font-semibold">{{ formatRupiah(row.total) }}</div>
              <div class="cell-secondary" :class="{ 'text-danger': row.margin < 0 }">
                Margin {{ formatMargin(row.margin, row.total) }}
              </div>
            </td>
            <td data-label="Status">
              <BadgeStatus :status="row.status" />
            </td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button type="button" class="btn btn-get-outline btn-sm" @click="openDetail(row)">
                  Detail
                </button>
                <button
                  v-if="row.status === 'diposting'"
                  type="button"
                  class="btn btn-get btn-sm"
                  @click="goNota(row)"
                >
                  <AppIcon name="printer" :size="14" />
                  <span>Cetak nota</span>
                </button>
                <template v-if="row.status === 'draf'">
                  <button type="button" class="btn btn-put btn-sm" @click="openEdit(row)">
                    Ubah
                  </button>
                  <button type="button" class="btn btn-post btn-sm" @click="openPosting(row)">
                    Posting
                  </button>
                  <button
                    type="button"
                    class="btn btn-delete btn-sm"
                    @click="openDelete(row)"
                  >
                    Hapus
                  </button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <PaginationBar :meta="meta" @page="setPage" @per-page="setPerPage" />
    </div>

    <!-- modal buat atau ubah penjualan -->
    <BaseModal
      :open="modalOpen"
      :title="editingId ? `Ubah Draf Penjualan: ${editingKode}` : 'Buat Penjualan Baru'"
      size="xl"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="penjualan-form" class="form-stack" novalidate @submit.prevent="onSave('draf')">
        <div class="form-row-2">
          <FormField
            v-if="auth.isAdmin"
            id="pjl-lokasi"
            label="Lokasi penjual"
            :error="errors.lokasi_id"
          >
            <template #default="{ describedBy }">
              <SearchSelect
                id="pjl-lokasi"
                :model-value="values.lokasi_id"
                :options="lokasiList.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama} (${LOKASI_TYPE_LABELS[lok.jenis]})` }))"
                required
                :invalid="Boolean(errors.lokasi_id)"
                :described-by="describedBy"
                @change="onLokasiChange($event)"
              />
            </template>
          </FormField>
          <div v-else class="field">
            <span class="field-label">Lokasi penjual</span>
            <div class="doc-item-readonly">
              <span class="mono font-semibold">{{ auth.user?.lokasi?.kode }}</span>
              <span>&nbsp;- {{ auth.user?.lokasi?.nama }}</span>
            </div>
          </div>

          <FormField id="pjl-tanggal" label="Tanggal penjualan" :error="errors.tanggal">
            <template #default="{ describedBy }">
              <input
                id="pjl-tanggal"
                v-model="values.tanggal"
                type="date"
                :min="DOCUMENT_DATE_RANGE.min()"
                :max="DOCUMENT_DATE_RANGE.max()"
                class="input mono"
                required
                :aria-invalid="Boolean(errors.tanggal)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField
          id="pjl-customer"
          :label="isOutletSale ? 'Customer (boleh Umum di outlet)' : 'Customer (wajib untuk gudang)'"
          :error="errors.customer_id"
        >
          <template #default="{ describedBy }">
            <div class="doc-qty-wrap">
              <SearchSelect
                id="pjl-customer"
                v-model="values.customer_id"
                :options="customerOptions.map((cust) => ({ value: cust.id, label: `${cust.nama}` }))"
                :empty-label="isOutletSale ? 'Umum (Pembeli Eceran Outlet)' : ''"
                placeholder="Pilih customer..."
                :required="!isOutletSale"
                :invalid="Boolean(errors.customer_id)"
                :described-by="describedBy"
              />
              <button
                type="button"
                class="btn btn-post btn-sm"
                @click="openNewCustomer"
              >
                <AppIcon name="plus" :size="15" />
                <span>Customer baru</span>
              </button>
            </div>
          </template>
        </FormField>

        <FormField id="pjl-catatan" label="Catatan penjualan (opsional)" :error="errors.catatan">
          <template #default="{ describedBy }">
            <textarea
              id="pjl-catatan"
              v-model.trim="values.catatan"
              rows="2"
              class="input"
              placeholder="Nomor PO customer, permintaan gilingan kopi atau keterangan lain..."
              :aria-invalid="Boolean(errors.catatan)"
              :aria-describedby="describedBy"
            ></textarea>
          </template>
        </FormField>

        <DocumentItemsEditor
          v-model="values.items"
          :products="productOptions"
          :show-stock="true"
          :outbound="true"
          :with-price="true"
          default-price-field="harga_jual"
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
          @click="onSave('posting')"
        >
          <span v-if="submitting && saveMode === 'posting'" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting && saveMode === 'posting' ? 'Memposting...' : 'Simpan lalu posting' }}</span>
        </button>
      </template>
    </BaseModal>

    <!-- modal cepat tambah customer baru -->
    <BaseModal
      :open="newCustomerOpen"
      title="Tambah Customer Baru"
      size="md"
      @close="newCustomerOpen = false"
    >
      <p v-if="customerForm.message.value" class="alert alert-error" role="alert">
        {{ customerForm.message.value }}
      </p>
      <form
        id="quick-customer-form"
        class="form-stack"
        novalidate
        @submit.prevent="onSaveNewCustomer"
      >
        <div class="form-row-2">
          <FormField id="qc-nama" label="Nama customer" :error="customerForm.errors.value.nama">
            <template #default="{ describedBy }">
              <input
                id="qc-nama"
                v-model.trim="customerForm.values.nama"
                class="input"
                required
                :aria-invalid="Boolean(customerForm.errors.value.nama)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField id="qc-jenis" label="Jenis customer" :error="customerForm.errors.value.jenis">
            <template #default="{ describedBy }">
              <select
                id="qc-jenis"
                v-model="customerForm.values.jenis"
                class="input"
                :aria-invalid="Boolean(customerForm.errors.value.jenis)"
                :aria-describedby="describedBy"
              >
                <option v-for="(lbl, key) in CUSTOMER_TYPE_LABELS" :key="key" :value="key">
                  {{ lbl }}
                </option>
              </select>
            </template>
          </FormField>
        </div>

        <div class="form-row-2">
          <FormField id="qc-kontak" label="Nama kontak" :error="customerForm.errors.value.kontak">
            <template #default="{ describedBy }">
              <input
                id="qc-kontak"
                v-model.trim="customerForm.values.kontak"
                class="input"
                :aria-invalid="Boolean(customerForm.errors.value.kontak)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField id="qc-telepon" label="Nomor telepon" :error="customerForm.errors.value.telepon">
            <template #default="{ describedBy }">
              <input
                id="qc-telepon"
                v-model.trim="customerForm.values.telepon"
                class="input mono"
                :aria-invalid="Boolean(customerForm.errors.value.telepon)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField id="qc-alamat" label="Alamat" :error="customerForm.errors.value.alamat">
          <template #default="{ describedBy }">
            <textarea
              id="qc-alamat"
              v-model.trim="customerForm.values.alamat"
              rows="2"
              class="input"
              :aria-invalid="Boolean(customerForm.errors.value.alamat)"
              :aria-describedby="describedBy"
            ></textarea>
          </template>
        </FormField>
      </form>

      <template #footer>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="customerForm.submitting.value"
          @click="newCustomerOpen = false"
        >
          Batal
        </button>
        <button
          type="submit"
          form="quick-customer-form"
          class="btn btn-post"
          :disabled="customerForm.submitting.value"
        >
          <span v-if="customerForm.submitting.value" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ customerForm.submitting.value ? 'Menyimpan...' : 'Simpan & pilih customer' }}</span>
        </button>
      </template>
    </BaseModal>

    <!-- modal detail penjualan -->
    <BaseModal
      :open="detailOpen"
      :title="detailData ? `Detail Penjualan: ${detailData.kode}` : 'Detail Penjualan'"
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
              Tanggal penjualan: <strong class="mono">{{ formatDate(detailData.tanggal) }}</strong>
              · Petugas: <strong>{{ detailData.dibuat_oleh }}</strong>
            </p>
          </div>
          <div class="num">
            <span class="detail-label">Total Penjualan</span>
            <div class="detail-value mono font-semibold">
              {{ formatRupiah(detailData.total) }}
            </div>
          </div>
        </div>

        <div class="summary-strip">
          <div class="summary-item">
            <span class="detail-label">Lokasi Penjual</span>
            <strong class="cell-primary">{{ detailData.lokasi?.nama }}</strong>
            <span class="cell-secondary mono">{{ detailData.lokasi?.kode }}</span>
          </div>
          <div class="summary-item">
            <span class="detail-label">Customer</span>
            <strong class="cell-primary">{{ detailData.nama_customer }}</strong>
            <span v-if="detailData.customer" class="cell-secondary">
              {{ CUSTOMER_TYPE_LABELS[detailData.customer.jenis] || detailData.customer.jenis }}
              <template v-if="detailData.customer.telepon">
                · {{ detailData.customer.telepon }}
              </template>
            </span>
            <span v-else class="cell-secondary">Pembeli eceran outlet</span>
          </div>
          <div class="summary-item">
            <span class="detail-label">Waktu Posting</span>
            <strong class="cell-primary mono">
              {{ detailData.diposting_pada ? formatDateTime(detailData.diposting_pada) : 'Belum diposting' }}
            </strong>
            <span class="cell-secondary">{{ detailData.jumlah_item }} jenis produk</span>
          </div>
        </div>

        <p v-if="detailData.catatan" class="cell-secondary">
          <strong>Catatan:</strong> {{ detailData.catatan }}
        </p>

        <RiwayatDokumen :steps="detailTimeline" />

        <div class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Produk</th>
                <th class="num">HPP</th>
                <th class="num">Harga Satuan</th>
                <th class="num">Jumlah</th>
                <th class="num">Subtotal</th>
                <th class="num">Margin</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in detailData.items" :key="item.id">
                <td data-label="SKU" class="mono font-semibold">{{ item.produk.sku }}</td>
                <td data-label="Produk">
                  <div class="cell-primary">{{ item.produk.nama }}</div>
                  <BadgeStatus :status="item.produk.jenis" />
                </td>
                <td data-label="HPP" class="num mono">{{ formatRupiah(item.harga_beli) }}</td>
                <td data-label="Harga Satuan" class="num mono">
                  <div>{{ formatRupiah(item.harga_satuan) }}</div>
                  <div class="cell-secondary">Standar {{ formatRupiah(item.produk.harga_jual) }}</div>
                </td>
                <td data-label="Jumlah" class="num mono font-semibold">
                  {{ formatNumber(item.jumlah) }} {{ item.produk.satuan }}
                </td>
                <td data-label="Subtotal" class="num mono font-semibold">
                  {{ formatRupiah(item.subtotal) }}
                </td>
                <td
                  data-label="Margin"
                  class="num mono"
                  :class="{ 'text-danger': item.margin < 0 }"
                >
                  {{ formatMargin(item.margin, item.subtotal) }}
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr>
                <th colspan="5" class="num">Total</th>
                <td data-label="Total" class="num mono font-semibold">
                  {{ formatRupiah(detailData.total) }}
                </td>
                <td
                  data-label="Margin"
                  class="num mono font-semibold"
                  :class="{ 'text-danger': detailData.margin < 0 }"
                >
                  {{ formatMargin(detailData.margin, detailData.total) }}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <template #footer>
        <button type="button" class="btn btn-secondary" @click="closeDetail">Tutup</button>
        <button
          v-if="detailData?.status === 'diposting'"
          type="button"
          class="btn btn-get"
          @click="goNota(detailData)"
        >
          <AppIcon name="printer" :size="15" />
          <span>Cetak nota</span>
        </button>
        <template v-if="detailData?.status === 'draf'">
          <button
            type="button"
            class="btn btn-delete"
            @click="openDelete(detailData)"
          >
            Hapus draf
          </button>
          <button type="button" class="btn btn-put" @click="openEdit(detailData)">
            Ubah draf
          </button>
          <button type="button" class="btn btn-post" @click="openPosting(detailData)">
            Posting penjualan
          </button>
        </template>
      </template>
    </BaseModal>

    <!-- modal konfirmasi posting atau hapus -->
    <ConfirmModal
      :open="Boolean(confirmAction)"
      :title="confirmAction?.title || 'Konfirmasi'"
      :message="confirmAction?.message || ''"
      :confirm-label="confirmAction?.confirmLabel || 'Konfirmasi'"
      :variant="confirmAction?.variant || 'primary'"
      :loading="confirmLoading"
      :error="confirmError"
      @close="confirmAction = null"
      @confirm="onConfirmExecute"
    />
  </section>
</template>
