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
import { useTerimaForm } from '@/composables/useTerimaForm'
import { pengirimanApi, produkApi, userApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import {
  KENDARAAN_TYPE_LABELS,
  LOKASI_TYPE_LABELS,
  LOKASI_TYPES,
  ROLES,
} from '@/utils/constants'
import { formatDate, formatNumber, formatRupiah, todayIso } from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const { items: lokasiList, load: loadLokasi } = useLokasiOptions()
const { items: deliverymanList, load: loadDeliveryman } = useOptions(
  () => userApi.deliveryman(),
  'deliveryman'
)

const isDeliveryman = computed(() => auth.user?.role === ROLES.DELIVERYMAN)
const isManagerGudang = computed(() => auth.user?.role === ROLES.MANAGER_GUDANG)
const isManagerOutlet = computed(() => auth.user?.role === ROLES.MANAGER_OUTLET)
const canCreate = computed(() => auth.isAdmin || isManagerGudang.value)

const gudangAsalOptions = computed(() =>
  lokasiList.value.filter(
    (l) => l.jenis === LOKASI_TYPES.GUDANG_UTAMA || l.jenis === LOKASI_TYPES.GUDANG_CABANG
  )
)

const directionTab = ref('semua')

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => pengirimanApi.list(params),
  {
    initialFilters: {
      q: '',
      lokasi_asal_id: '',
      lokasi_tujuan_id: '',
      status: route.query.status ? String(route.query.status) : '',
      dari: '',
      sampai: '',
      sort: 'tanggal_kirim',
      arah: 'desc',
    },
    immediate: false,
  }
)

function setDirectionTab(tab) {
  directionTab.value = tab
  const myLokasiId = auth.user?.lokasi?.id || ''
  if (tab === 'keluar') {
    filters.lokasi_asal_id = myLokasiId
    filters.lokasi_tujuan_id = ''
  } else if (tab === 'masuk') {
    filters.lokasi_asal_id = ''
    filters.lokasi_tujuan_id = myLokasiId
  } else {
    filters.lokasi_asal_id = ''
    filters.lokasi_tujuan_id = ''
  }
  applyFilters()
}

function handleResetFilters() {
  directionTab.value = 'semua'
  resetFilters()
}

onMounted(async () => {
  if (!isDeliveryman.value) {
    await Promise.all([loadLokasi(), loadDeliveryman()])
  }
  await load()
  if (route.query.id) {
    openDetail({ id: Number(route.query.id) })
  }
})

function canSendRow(row) {
  if (!row || row.status !== 'draf') return false
  if (auth.isAdmin) return true
  return isManagerGudang.value && Number(row.lokasi_asal?.id) === Number(auth.user?.lokasi?.id)
}

function canReceiveRow(row) {
  if (!row || row.status !== 'dikirim') return false
  if (auth.isAdmin) return true
  return (
    (isManagerGudang.value || isManagerOutlet.value) &&
    Number(row.lokasi_tujuan?.id) === Number(auth.user?.lokasi?.id)
  )
}

function needsConfirmation(row) {
  return canReceiveRow(row)
}

function goSuratJalan(row) {
  router.push({ name: 'pengiriman-surat-jalan', params: { id: row.id } })
}

// formulir buat atau ubah draf pengiriman
const modalOpen = ref(false)
const editingId = ref(null)
const editingKode = ref('')
const productOptions = ref([])
const saveMode = ref('draf')

const { values, errors, message, submitting, submit, fill, clearErrors } = useForm({
  lokasi_asal_id: '',
  lokasi_tujuan_id: '',
  tanggal_kirim: todayIso(),
  deliveryman_id: '',
  kendaraan_jenis: '',
  kendaraan_nomor: '',
  catatan: '',
  items: [{ produk_id: '', jumlah: 1 }],
})

const currentAsalId = computed(() =>
  auth.isAdmin ? Number(values.lokasi_asal_id) || '' : auth.user?.lokasi?.id || ''
)

const tujuanOptions = computed(() =>
  lokasiList.value.filter((l) => Number(l.id) !== Number(currentAsalId.value))
)

async function loadProductOptions() {
  const asalId = currentAsalId.value
  if (!asalId) {
    productOptions.value = []
    return
  }
  try {
    productOptions.value = await produkApi.options({ lokasi_id: asalId })
  } catch {
    productOptions.value = []
  }
}

async function onAsalChange(rawId) {
  values.lokasi_asal_id = rawId ? Number(rawId) : ''
  if (Number(values.lokasi_tujuan_id) === Number(values.lokasi_asal_id)) {
    const nextTujuan = tujuanOptions.value[0]
    values.lokasi_tujuan_id = nextTujuan ? nextTujuan.id : ''
  }
  await loadProductOptions()
}

async function openCreate() {
  editingId.value = null
  editingKode.value = ''
  const defaultAsalId = auth.isAdmin
    ? gudangAsalOptions.value[0]?.id || ''
    : auth.user?.lokasi?.id || ''
  const defaultTujuan = lokasiList.value.find((l) => Number(l.id) !== Number(defaultAsalId))
  fill({
    lokasi_asal_id: defaultAsalId,
    lokasi_tujuan_id: defaultTujuan?.id || '',
    tanggal_kirim: todayIso(),
    deliveryman_id: '',
    kendaraan_jenis: '',
    kendaraan_nomor: '',
    catatan: '',
    items: [{ produk_id: '', jumlah: 1 }],
  })
  modalOpen.value = true
  await loadProductOptions()
}

async function openEdit(row) {
  try {
    const detail = row.items ? row : await pengirimanApi.get(row.id)
    editingId.value = detail.id
    editingKode.value = detail.kode
    fill({
      lokasi_asal_id: detail.lokasi_asal?.id || '',
      lokasi_tujuan_id: detail.lokasi_tujuan?.id || '',
      tanggal_kirim: detail.tanggal_kirim,
      deliveryman_id: detail.deliveryman?.id || '',
      kendaraan_jenis: detail.kendaraan_jenis || '',
      kendaraan_nomor: detail.kendaraan_nomor || '',
      catatan: detail.catatan || '',
      items: detail.items.map((it) => ({
        produk_id: it.produk.id,
        jumlah: it.jumlah_dikirim,
      })),
    })
    detailOpen.value = false
    modalOpen.value = true
    await loadProductOptions()
  } catch (err) {
    toast.show(err?.message || 'Gagal memuat draf pengiriman.', 'error')
  }
}

async function onSave(mode = 'draf') {
  saveMode.value = mode
  clearErrors()
  if (mode === 'kirim') {
    const missing = {}
    if (!values.deliveryman_id) missing.deliveryman_id = 'Wajib diisi saat mengirim'
    if (!values.kendaraan_jenis) missing.kendaraan_jenis = 'Wajib diisi saat mengirim'
    if (!values.kendaraan_nomor?.trim()) missing.kendaraan_nomor = 'Wajib diisi saat mengirim'
    if (Object.keys(missing).length) {
      errors.value = missing
      message.value = 'Lengkapi deliveryman serta jenis dan nomor kendaraan sebelum mengirim.'
      return
    }
  }

  const payload = {
    lokasi_asal_id: auth.isAdmin ? Number(values.lokasi_asal_id) || null : null,
    lokasi_tujuan_id: Number(values.lokasi_tujuan_id) || 0,
    tanggal_kirim: values.tanggal_kirim,
    deliveryman_id: values.deliveryman_id ? Number(values.deliveryman_id) : null,
    kendaraan_jenis: values.kendaraan_jenis || null,
    kendaraan_nomor: values.kendaraan_nomor ? values.kendaraan_nomor.trim().toUpperCase() : null,
    catatan: values.catatan || null,
    items: values.items.map((it) => ({
      produk_id: Number(it.produk_id) || 0,
      jumlah_dikirim: Number(it.jumlah) || 0,
    })),
  }

  const saved = await submit(async () => {
    const draft = editingId.value
      ? await pengirimanApi.update(editingId.value, payload)
      : await pengirimanApi.create(payload)
    editingId.value = draft.id
    editingKode.value = draft.kode
    if (mode === 'kirim') {
      return await pengirimanApi.kirim(draft.id, {
        deliveryman_id: payload.deliveryman_id,
        kendaraan_jenis: payload.kendaraan_jenis,
        kendaraan_nomor: payload.kendaraan_nomor,
      })
    }
    return draft
  })

  if (saved) {
    if (mode === 'kirim') {
      toast.show(
        `Pengiriman ${saved.kode} dikirim. Stock ${saved.lokasi_asal?.nama || 'gudang asal'} sudah dikurangi.`
      )
    } else {
      toast.show(`Draf pengiriman ${saved.kode} disimpan.`)
    }
    modalOpen.value = false
    await load()
  }
}

// detail pengiriman
const {
  open: detailOpen,
  loading: detailLoading,
  data: detailData,
  show: openDetail,
  close: closeDetail,
} = useDetail((id) => pengirimanApi.get(id), 'pengiriman')

const detailTimeline = computed(() => {
  const d = detailData.value
  if (!d) return []
  const steps = [
    {
      label: d.permintaan ? `Draf dibuat dari Permintaan ${d.permintaan.kode}` : 'Draf pengiriman dibuat',
      user: d.dibuat_oleh?.name,
      time: d.created_at,
      tone: 'selesai',
    },
  ]
  if (d.status === 'dibatalkan') {
    steps.push({
      label: 'Pengiriman dibatalkan',
      time: d.updated_at,
      tone: 'bahaya',
      note: 'Draf pengiriman dibatalkan dan permintaan dikembalikan ke status diajukan.',
    })
    return steps
  }
  if (d.dikirim_pada) {
    steps.push({
      label: `Dikirim dari ${d.lokasi_asal?.nama || 'Gudang Asal'}`,
      user: d.dikirim_oleh?.name,
      time: d.dikirim_pada,
      tone: d.status === 'dikirim' ? 'proses' : 'selesai',
      note: d.deliveryman
        ? `Diantar oleh ${d.deliveryman.name} (${KENDARAAN_TYPE_LABELS[d.kendaraan_jenis] || d.kendaraan_jenis} · ${d.kendaraan_nomor})`
        : '',
    })
  } else {
    steps.push({
      label: 'Pengiriman dari gudang asal',
      placeholder: 'Menunggu dikirim dari gudang asal',
      tone: 'netral',
    })
  }
  if (d.diterima_pada) {
    steps.push({
      label: `Diterima di ${d.lokasi_tujuan?.nama || 'Lokasi Tujuan'}`,
      user: d.diterima_oleh?.name,
      time: d.diterima_pada,
      tone: 'aman',
      note: d.catatan_penerimaan || '',
    })
  } else {
    steps.push({
      label: `Penerimaan di ${d.lokasi_tujuan?.nama || 'Lokasi Tujuan'}`,
      placeholder:
        d.status === 'dikirim'
          ? 'Dalam perjalanan — menunggu konfirmasi terima di lokasi tujuan'
          : 'Menunggu pengiriman',
      tone: d.status === 'dikirim' ? 'menunggu' : 'netral',
    })
  }
  return steps
})

// modal kirim pengiriman
const kirimModalOpen = ref(false)
const kirimTarget = ref(null)
const kirimForm = useForm({
  deliveryman_id: '',
  kendaraan_jenis: 'mobil_box',
  kendaraan_nomor: '',
})

function openKirim(row) {
  kirimTarget.value = row
  kirimForm.fill({
    deliveryman_id: row.deliveryman?.id || deliverymanList.value[0]?.id || '',
    kendaraan_jenis: row.kendaraan_jenis || 'mobil_box',
    kendaraan_nomor: row.kendaraan_nomor || '',
  })
  kirimModalOpen.value = true
}

async function onConfirmKirim() {
  if (!kirimTarget.value) return
  const payload = {
    deliveryman_id: kirimForm.values.deliveryman_id
      ? Number(kirimForm.values.deliveryman_id)
      : null,
    kendaraan_jenis: kirimForm.values.kendaraan_jenis || null,
    kendaraan_nomor: kirimForm.values.kendaraan_nomor
      ? kirimForm.values.kendaraan_nomor.trim().toUpperCase()
      : null,
  }
  const res = await kirimForm.submit(() => pengirimanApi.kirim(kirimTarget.value.id, payload))
  if (res) {
    toast.show(
      `Pengiriman ${res.kode} dikirim. Stock ${res.lokasi_asal?.nama || 'gudang asal'} sudah dikurangi.`
    )
    kirimModalOpen.value = false
    if (detailOpen.value && detailData.value?.id === res.id) {
      detailData.value = res
    }
    await load()
  }
}

// modal terima pengiriman
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
  label: 'pengiriman',
  fetchDetail: (id) => pengirimanApi.get(id),
  toForm: (detail) => ({
    catatan_penerimaan: detail.catatan_penerimaan || '',
    items: detail.items.map((it) => ({
      produk_id: it.produk.id,
      sku: it.produk.sku,
      nama: it.produk.nama,
      satuan: it.produk.satuan,
      jumlah_dikirim: it.jumlah_dikirim,
      jumlah_diterima: it.jumlah_dikirim,
      catatan: it.catatan || '',
    })),
  }),
  toPayload: (form) => ({
    catatan_penerimaan: form.catatan_penerimaan || null,
    items: form.items.map((it) => ({
      produk_id: Number(it.produk_id),
      jumlah_diterima: it.jumlah_diterima === '' ? -1 : Number(it.jumlah_diterima),
      catatan: it.catatan?.trim() || null,
    })),
  }),
  submit: (id, payload) => pengirimanApi.terima(id, payload),
  successMessage: (res) =>
    `Pengiriman ${res.kode} diterima. ` +
    `Stock ${res.lokasi_tujuan?.nama || 'lokasi tujuan'} sudah ditambah.`,
  onSaved: async (res) => {
    if (detailOpen.value && detailData.value?.id === res.id) detailData.value = res
    await load()
  },
})

const terimaSelisihCount = computed(() =>
  terimaForm.items.filter((it) => Number(it.jumlah_diterima) < Number(it.jumlah_dikirim)).length
)

// modal hapus atau batalkan draf
const deleteRow = ref(null)
const deleteLoading = ref(false)
const deleteError = ref('')

function openDelete(row) {
  deleteRow.value = row
  deleteError.value = ''
}

async function onConfirmDelete() {
  if (!deleteRow.value) return
  deleteLoading.value = true
  deleteError.value = ''
  try {
    const target = deleteRow.value
    await pengirimanApi.remove(target.id)
    if (target.permintaan) {
      toast.show(
        `Pengiriman ${target.kode} dibatalkan dan permintaan ${target.permintaan.kode} dikembalikan ke status diajukan.`
      )
    } else {
      toast.show(`Draf pengiriman ${target.kode} dihapus.`)
    }
    deleteRow.value = null
    detailOpen.value = false
    await load()
  } catch (err) {
    deleteError.value = err?.message || 'Gagal menghapus draf pengiriman.'
  } finally {
    deleteLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Pengiriman Antarlokasi</h2>
        <p class="page-subtitle">
          <template v-if="isDeliveryman">
            Daftar pengantaran barang yang ditugaskan kepada Anda beserta surat jalan cetak
          </template>
          <template v-else>
            Distribusi produk dari gudang asal ke gudang cabang dan outlet beserta konfirmasi penerimaan
          </template>
        </p>
      </div>
      <button v-if="canCreate" type="button" class="btn btn-post" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Buat pengiriman</span>
      </button>
    </header>

    <div v-if="isManagerGudang" class="tab-bar" role="tablist" aria-label="Filter arah pengiriman">
      <button
        type="button"
        role="tab"
        class="tab-btn"
        :class="{ 'tab-btn-active': directionTab === 'semua' }"
        :aria-selected="directionTab === 'semua'"
        @click="setDirectionTab('semua')"
      >
        Semua Pengiriman
      </button>
      <button
        type="button"
        role="tab"
        class="tab-btn"
        :class="{ 'tab-btn-active': directionTab === 'keluar' }"
        :aria-selected="directionTab === 'keluar'"
        @click="setDirectionTab('keluar')"
      >
        Keluar (Dari Lokasi Saya)
      </button>
      <button
        type="button"
        role="tab"
        class="tab-btn"
        :class="{ 'tab-btn-active': directionTab === 'masuk' }"
        :aria-selected="directionTab === 'masuk'"
        @click="setDirectionTab('masuk')"
      >
        Masuk (Ke Lokasi Saya)
      </button>
    </div>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="krm-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="krm-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari kode KR-... atau catatan..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div v-if="auth.isAdmin" class="toolbar-field">
          <label class="toolbar-label" for="krm-filter-asal">Lokasi Asal</label>
          <SearchSelect
            id="krm-filter-asal"
            v-model="filters.lokasi_asal_id"
            :options="gudangAsalOptions.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama}` }))"
            empty-label="Semua asal"
            small
            @change="applyFilters()"
          />
        </div>
        <div v-if="auth.isAdmin" class="toolbar-field">
          <label class="toolbar-label" for="krm-filter-tujuan">Lokasi Tujuan</label>
          <SearchSelect
            id="krm-filter-tujuan"
            v-model="filters.lokasi_tujuan_id"
            :options="lokasiList.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama}` }))"
            empty-label="Semua tujuan"
            small
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="krm-filter-status">Status</label>
          <select
            id="krm-filter-status"
            v-model="filters.status"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua status</option>
            <option value="draf">Draf</option>
            <option value="dikirim">Dikirim (Dalam Perjalanan)</option>
            <option value="diterima">Diterima</option>
            <option value="dibatalkan">Dibatalkan</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="krm-filter-dari">Dari Tanggal</label>
          <input
            id="krm-filter-dari"
            v-model="filters.dari"
            type="date"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="krm-filter-sampai">Sampai Tanggal</label>
          <input
            id="krm-filter-sampai"
            v-model="filters.sampai"
            type="date"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="krm-filter-sort">Sort</label>
          <select
            id="krm-filter-sort"
            v-model="filters.sort"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="tanggal_kirim">Tanggal kirim</option>
            <option value="kode">Kode dokumen</option>
            <option value="created_at">Waktu dibuat</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="krm-filter-arah">Order</label>
          <select
            id="krm-filter-arah"
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
      title="Belum ada dokumen pengiriman"
      description="Tidak ada pengiriman yang cocok dengan filter saat ini."
    >
      <button type="button" class="btn btn-secondary btn-sm" @click="handleResetFilters">
        Reset filter
      </button>
    </EmptyState>

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Kode</th>
            <th>Tanggal Kirim</th>
            <th>Lokasi Asal</th>
            <th>Lokasi Tujuan</th>
            <th>Pengantaran</th>
            <th>Status</th>
            <th class="num">{{ isDeliveryman ? 'Barang' : 'Nilai' }}</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in items"
            :key="row.id"
            :class="{ 'row-highlight': needsConfirmation(row) }"
          >
            <td data-label="Kode">
              <div class="mono font-semibold">{{ row.kode }}</div>
              <div v-if="row.permintaan" class="cell-secondary mono">
                Ref: {{ row.permintaan.kode }}
              </div>
            </td>
            <td data-label="Tanggal Kirim" class="mono">{{ formatDate(row.tanggal_kirim) }}</td>
            <td data-label="Lokasi Asal">
              <div class="cell-primary">{{ row.lokasi_asal?.nama }}</div>
              <div class="cell-secondary mono">{{ row.lokasi_asal?.kode }}</div>
            </td>
            <td data-label="Lokasi Tujuan">
              <div class="cell-primary">{{ row.lokasi_tujuan?.nama }}</div>
              <div class="cell-secondary mono">{{ row.lokasi_tujuan?.kode }}</div>
            </td>
            <td data-label="Pengantaran">
              <template v-if="row.deliveryman">
                <div class="cell-primary">{{ row.deliveryman.name }}</div>
                <div v-if="row.kendaraan_jenis || row.kendaraan_nomor" class="cell-secondary">
                  {{ KENDARAAN_TYPE_LABELS[row.kendaraan_jenis] || row.kendaraan_jenis }}
                  <span v-if="row.kendaraan_nomor" class="mono">· {{ row.kendaraan_nomor }}</span>
                </div>
              </template>
              <span v-else class="cell-secondary">Belum ditentukan</span>
            </td>
            <td data-label="Status">
              <div class="sku-summary">
                <BadgeStatus :status="row.status" />
                <BadgeStatus
                  v-if="needsConfirmation(row)"
                  tone="menunggu"
                  label="Perlu dikonfirmasi"
                />
              </div>
            </td>
            <td :data-label="isDeliveryman ? 'Barang' : 'Nilai'" class="num">
              <div v-if="!isDeliveryman" class="mono font-semibold">{{ formatRupiah(row.nilai_dikirim) }}</div>
              <div class="cell-secondary mono">{{ row.jumlah_item }} item</div>
            </td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button type="button" class="btn btn-get-outline btn-sm" @click="openDetail(row)">
                  Detail
                </button>
                <button
                  v-if="row.status === 'dikirim' || row.status === 'diterima'"
                  type="button"
                  class="btn btn-get btn-sm"
                  @click="goSuratJalan(row)"
                >
                  <AppIcon name="printer" :size="14" />
                  <span>Surat jalan</span>
                </button>
                <template v-if="canSendRow(row)">
                  <button type="button" class="btn btn-put btn-sm" @click="openEdit(row)">
                    Ubah
                  </button>
                  <button type="button" class="btn btn-post btn-sm" @click="openKirim(row)">
                    Kirim
                  </button>
                  <button
                    type="button"
                    class="btn btn-delete btn-sm"
                    @click="openDelete(row)"
                  >
                    {{ row.permintaan ? 'Batalkan' : 'Hapus' }}
                  </button>
                </template>
                <button
                  v-if="canReceiveRow(row)"
                  type="button"
                  class="btn btn-post btn-sm"
                  @click="openTerima(row)"
                >
                  Terima
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <PaginationBar :meta="meta" @page="setPage" @per-page="setPerPage" />
    </div>

    <!-- modal buat atau ubah draf pengiriman -->
    <BaseModal
      :open="modalOpen"
      :title="editingId ? `Ubah Draf Pengiriman: ${editingKode}` : 'Buat Pengiriman Antarlokasi'"
      size="lg"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="pengiriman-form" class="form-stack" novalidate @submit.prevent="onSave('draf')">
        <div class="form-row-2">
          <FormField
            v-if="auth.isAdmin"
            id="krm-asal"
            label="Gudang asal"
            :error="errors.lokasi_asal_id"
          >
            <template #default="{ describedBy }">
              <SearchSelect
                id="krm-asal"
                :model-value="values.lokasi_asal_id"
                :options="gudangAsalOptions.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama} (${LOKASI_TYPE_LABELS[lok.jenis]})` }))"
                required
                :invalid="Boolean(errors.lokasi_asal_id)"
                :described-by="describedBy"
                @change="onAsalChange($event)"
              />
            </template>
          </FormField>
          <div v-else class="form-field">
            <span class="field-label">Gudang asal</span>
            <div class="doc-item-readonly">
              <span class="mono font-semibold">{{ auth.user?.lokasi?.kode }}</span>
              <span>&nbsp;- {{ auth.user?.lokasi?.nama }}</span>
            </div>
          </div>

          <FormField id="krm-tujuan" label="Lokasi tujuan" :error="errors.lokasi_tujuan_id">
            <template #default="{ describedBy }">
              <SearchSelect
                id="krm-tujuan"
                v-model="values.lokasi_tujuan_id"
                :options="tujuanOptions.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama} (${LOKASI_TYPE_LABELS[lok.jenis]})` }))"
                placeholder="Pilih lokasi tujuan..."
                required
                :invalid="Boolean(errors.lokasi_tujuan_id)"
                :described-by="describedBy"
              />
            </template>
          </FormField>
        </div>

        <div class="form-row-2">
          <FormField id="krm-tanggal" label="Tanggal kirim" :error="errors.tanggal_kirim">
            <template #default="{ describedBy }">
              <input
                id="krm-tanggal"
                v-model="values.tanggal_kirim"
                type="date"
                class="input mono"
                required
                :aria-invalid="Boolean(errors.tanggal_kirim)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField
            id="krm-deliveryman"
            label="Deliveryman (opsional saat draf)"
            :error="errors.deliveryman_id"
          >
            <template #default="{ describedBy }">
              <SearchSelect
                id="krm-deliveryman"
                v-model="values.deliveryman_id"
                :options="deliverymanList.map((kurir) => ({ value: kurir.id, label: `${kurir.nama}` }))"
                placeholder="Pilih saat mengirim..."
                :invalid="Boolean(errors.deliveryman_id)"
                :described-by="describedBy"
              />
            </template>
          </FormField>
        </div>

        <div class="form-row-2">
          <FormField
            id="krm-kendaraan-jenis"
            label="Jenis kendaraan (opsional saat draf)"
            :error="errors.kendaraan_jenis"
          >
            <template #default="{ describedBy }">
              <select
                id="krm-kendaraan-jenis"
                v-model="values.kendaraan_jenis"
                class="input"
                :aria-invalid="Boolean(errors.kendaraan_jenis)"
                :aria-describedby="describedBy"
              >
                <option value="">Pilih jenis kendaraan...</option>
                <option v-for="(lbl, key) in KENDARAAN_TYPE_LABELS" :key="key" :value="key">
                  {{ lbl }}
                </option>
              </select>
            </template>
          </FormField>

          <FormField
            id="krm-kendaraan-nomor"
            label="Nomor polisi kendaraan"
            hint="Format plat: huruf, angka dan seri belakang (contoh: B 1234 TBC)"
            :error="errors.kendaraan_nomor"
          >
            <template #default="{ describedBy }">
              <input
                id="krm-kendaraan-nomor"
                v-model.trim="values.kendaraan_nomor"
                class="input mono"
                placeholder="B 1234 TBC"
                maxlength="12"
                :aria-invalid="Boolean(errors.kendaraan_nomor)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField id="krm-catatan" label="Catatan pengiriman (opsional)" :error="errors.catatan">
          <template #default="{ describedBy }">
            <textarea
              id="krm-catatan"
              v-model.trim="values.catatan"
              rows="2"
              class="input"
              placeholder="Instruksi penanganan barang atau pengantaran..."
              :aria-invalid="Boolean(errors.catatan)"
              :aria-describedby="describedBy"
            ></textarea>
          </template>
        </FormField>

        <DocumentItemsEditor
          v-model="values.items"
          :products="productOptions"
          :show-stock="true"
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
          @click="onSave('kirim')"
        >
          <span v-if="submitting && saveMode === 'kirim'" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting && saveMode === 'kirim' ? 'Mengirim...' : 'Simpan lalu kirim' }}</span>
        </button>
      </template>
    </BaseModal>

    <!-- modal detail pengiriman -->
    <BaseModal
      :open="detailOpen"
      :title="detailData ? `Detail Pengiriman: ${detailData.kode}` : 'Detail Pengiriman'"
      size="lg"
      @close="closeDetail"
    >
      <LoadingState v-if="detailLoading" :rows="4" />
      <div v-else-if="detailData" class="detail-grid">
        <div class="detail-highlight">
          <div>
            <div class="sku-summary">
              <span class="mono font-semibold">{{ detailData.kode }}</span>
              <BadgeStatus :status="detailData.status" />
              <BadgeStatus
                v-if="needsConfirmation(detailData)"
                tone="menunggu"
                label="Perlu dikonfirmasi"
              />
            </div>
            <p class="cell-secondary">
              Tanggal kirim: <strong class="mono">{{ formatDate(detailData.tanggal_kirim) }}</strong>
              <template v-if="detailData.permintaan">
                · Referensi Permintaan:
                <strong class="mono">{{ detailData.permintaan.kode }}</strong>
              </template>
            </p>
          </div>
          <div v-if="!isDeliveryman" class="num">
            <span class="detail-label">Nilai Barang Dikirim</span>
            <div class="detail-value mono font-semibold">
              {{ formatRupiah(detailData.nilai_dikirim) }}
            </div>
          </div>
        </div>

        <div class="summary-strip">
          <div class="summary-item">
            <span class="detail-label">Lokasi Asal (Pengirim)</span>
            <strong class="cell-primary">{{ detailData.lokasi_asal?.nama }}</strong>
            <span class="cell-secondary mono">{{ detailData.lokasi_asal?.kode }}</span>
          </div>
          <div class="summary-item">
            <span class="detail-label">Lokasi Tujuan (Penerima)</span>
            <strong class="cell-primary">{{ detailData.lokasi_tujuan?.nama }}</strong>
            <span class="cell-secondary mono">{{ detailData.lokasi_tujuan?.kode }}</span>
          </div>
          <div class="summary-item">
            <span class="detail-label">Deliveryman &amp; Armada</span>
            <strong class="cell-primary">
              {{ detailData.deliveryman?.name || 'Belum ditentukan' }}
            </strong>
            <span v-if="detailData.kendaraan_jenis || detailData.kendaraan_nomor" class="cell-secondary">
              {{ KENDARAAN_TYPE_LABELS[detailData.kendaraan_jenis] || detailData.kendaraan_jenis }}
              <span v-if="detailData.kendaraan_nomor" class="mono">
                · {{ detailData.kendaraan_nomor }}
              </span>
            </span>
          </div>
        </div>

        <p v-if="detailData.catatan" class="cell-secondary">
          <strong>Catatan pengiriman:</strong> {{ detailData.catatan }}
        </p>
        <p v-if="detailData.catatan_penerimaan" class="cell-secondary">
          <strong>Catatan penerimaan:</strong> {{ detailData.catatan_penerimaan }}
        </p>

        <RiwayatDokumen :steps="detailTimeline" />

        <div class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Produk</th>
                <th class="num">Dikirim</th>
                <th class="num">Diterima</th>
                <th class="num">Selisih</th>
                <th>Catatan Baris</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in detailData.items" :key="item.id">
                <td data-label="SKU" class="mono font-semibold">{{ item.produk.sku }}</td>
                <td data-label="Produk">
                  <div class="cell-primary">{{ item.produk.nama }}</div>
                  <BadgeStatus :status="item.produk.jenis" />
                </td>
                <td data-label="Dikirim" class="num mono font-semibold">
                  {{ formatNumber(item.jumlah_dikirim) }} {{ item.produk.satuan }}
                </td>
                <td data-label="Diterima" class="num mono">
                  <template v-if="item.jumlah_diterima !== null && item.jumlah_diterima !== undefined">
                    {{ formatNumber(item.jumlah_diterima) }} {{ item.produk.satuan }}
                  </template>
                  <span v-else class="cell-secondary">-</span>
                </td>
                <td data-label="Selisih" class="num mono">
                  <BadgeStatus
                    v-if="item.selisih > 0"
                    tone="bahaya"
                    :label="`-${formatNumber(item.selisih)} ${item.produk.satuan}`"
                  />
                  <span v-else-if="item.selisih === 0" class="text-success font-semibold">
                    Sesuai
                  </span>
                  <span v-else class="cell-secondary">-</span>
                </td>
                <td data-label="Catatan Baris" class="cell-secondary">
                  {{ item.catatan || '-' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <template #footer>
        <button type="button" class="btn btn-secondary" @click="closeDetail">Tutup</button>
        <button
          v-if="detailData"
          type="button"
          class="btn btn-get"
          @click="goSuratJalan(detailData)"
        >
          <AppIcon name="printer" :size="15" />
          <span>Surat jalan</span>
        </button>
        <template v-if="detailData && canSendRow(detailData)">
          <button
            type="button"
            class="btn btn-delete"
            @click="openDelete(detailData)"
          >
            {{ detailData.permintaan ? 'Batalkan draf' : 'Hapus draf' }}
          </button>
          <button type="button" class="btn btn-put" @click="openEdit(detailData)">
            Ubah draf
          </button>
          <button type="button" class="btn btn-post" @click="openKirim(detailData)">
            Kirim barang
          </button>
        </template>
        <button
          v-if="detailData && canReceiveRow(detailData)"
          type="button"
          class="btn btn-post"
          @click="openTerima(detailData)"
        >
          Konfirmasi terima
        </button>
      </template>
    </BaseModal>

    <!-- modal konfirmasi dan data kirim -->
    <BaseModal
      :open="kirimModalOpen"
      :title="kirimTarget ? `Kirim Pengiriman: ${kirimTarget.kode}` : 'Kirim Pengiriman'"
      size="md"
      @close="kirimModalOpen = false"
    >
      <p v-if="kirimForm.message.value" class="alert alert-error" role="alert">
        {{ kirimForm.message.value }}
      </p>
      <p v-if="kirimTarget" class="confirm-message">
        Kirim pengiriman <strong class="mono">{{ kirimTarget.kode }}</strong> dari
        <strong>{{ kirimTarget.lokasi_asal?.nama }}</strong> ke
        <strong>{{ kirimTarget.lokasi_tujuan?.nama }}</strong>? Stok
        <strong class="mono">{{ kirimTarget.jumlah_item }}</strong> produk di
        <strong>{{ kirimTarget.lokasi_asal?.nama }}</strong> akan berkurang dan pengiriman tidak
        bisa diedit lagi.
      </p>

      <form
        id="kirim-form"
        class="form-stack"
        novalidate
        @submit.prevent="onConfirmKirim"
      >
        <FormField
          id="modal-kirim-kurir"
          label="Deliveryman pengantar"
          :error="kirimForm.errors.value.deliveryman_id"
        >
          <template #default="{ describedBy }">
            <SearchSelect
              id="modal-kirim-kurir"
              v-model="kirimForm.values.deliveryman_id"
              :options="deliverymanList.map((kurir) => ({ value: kurir.id, label: `${kurir.nama}` }))"
              placeholder="Pilih deliveryman aktif..."
              required
              :invalid="Boolean(kirimForm.errors.value.deliveryman_id)"
              :described-by="describedBy"
            />
          </template>
        </FormField>

        <div class="form-row-2">
          <FormField
            id="modal-kirim-jenis"
            label="Jenis kendaraan"
            :error="kirimForm.errors.value.kendaraan_jenis"
          >
            <template #default="{ describedBy }">
              <select
                id="modal-kirim-jenis"
                v-model="kirimForm.values.kendaraan_jenis"
                class="input"
                required
                :aria-invalid="Boolean(kirimForm.errors.value.kendaraan_jenis)"
                :aria-describedby="describedBy"
              >
                <option v-for="(lbl, key) in KENDARAAN_TYPE_LABELS" :key="key" :value="key">
                  {{ lbl }}
                </option>
              </select>
            </template>
          </FormField>

          <FormField
            id="modal-kirim-nopol"
            label="Nomor polisi"
            hint="Contoh: B 1234 TBC"
            :error="kirimForm.errors.value.kendaraan_nomor"
          >
            <template #default="{ describedBy }">
              <input
                id="modal-kirim-nopol"
                v-model.trim="kirimForm.values.kendaraan_nomor"
                class="input mono"
                placeholder="B 1234 TBC"
                maxlength="12"
                required
                :aria-invalid="Boolean(kirimForm.errors.value.kendaraan_nomor)"
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
          :disabled="kirimForm.submitting.value"
          @click="kirimModalOpen = false"
        >
          Batal
        </button>
        <button
          type="submit"
          form="kirim-form"
          class="btn btn-post"
          :disabled="kirimForm.submitting.value"
        >
          {{ kirimForm.submitting.value ? 'Mengirim...' : 'Kirim sekarang' }}
        </button>
      </template>
    </BaseModal>

    <!-- modal konfirmasi terima pengiriman -->
    <BaseModal
      :open="terimaModalOpen"
      :title="terimaTarget ? `Terima Pengiriman: ${terimaTarget.kode}` : 'Terima Pengiriman'"
      size="lg"
      @close="closeTerima"
    >
      <LoadingState v-if="terimaLoadingDetail" :rows="3" />
      <template v-else-if="terimaTarget">
        <p v-if="terimaMessage" class="alert alert-error" role="alert">{{ terimaMessage }}</p>
        <p class="confirm-message">
          Konfirmasi penerimaan barang dari
          <strong>{{ terimaTarget.lokasi_asal?.nama }}</strong> di
          <strong>{{ terimaTarget.lokasi_tujuan?.nama }}</strong>. Periksa jumlah fisik setiap baris
          sebelum menyimpan karena stok lokasi tujuan akan langsung bertambah.
        </p>

        <p v-if="terimaSelisihCount > 0" class="alert alert-error" role="status">
          Ada selisih penerimaan pada {{ terimaSelisihCount }} produk. Pastikan catatan selisih pada
          baris tersebut sudah diisi.
        </p>

        <form id="terima-form" class="form-stack" novalidate @submit.prevent="onConfirmTerima">
          <div class="table-card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Produk</th>
                  <th class="num">Dikirim</th>
                  <th class="num">Jumlah Diterima</th>
                  <th class="num">Selisih</th>
                  <th>Catatan Selisih / Baris</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in terimaForm.items" :key="item.produk_id">
                  <td data-label="Produk">
                    <div class="cell-primary">{{ item.nama }}</div>
                    <div class="cell-secondary mono">{{ item.sku }}</div>
                  </td>
                  <td data-label="Dikirim" class="num mono font-semibold">
                    {{ formatNumber(item.jumlah_dikirim) }} {{ item.satuan }}
                  </td>
                  <td data-label="Jumlah Diterima" class="num">
                    <div class="doc-qty-wrap">
                      <input
                        :id="`terima-qty-${idx}`"
                        v-model.number="item.jumlah_diterima"
                        type="number"
                        min="0"
                        :max="item.jumlah_dikirim"
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
                  <td data-label="Selisih" class="num mono">
                    <BadgeStatus
                      v-if="Number(item.jumlah_diterima) < Number(item.jumlah_dikirim)"
                      tone="bahaya"
                      :label="`Kurang ${formatNumber(
                        Number(item.jumlah_dikirim) - Number(item.jumlah_diterima)
                      )}`"
                    />
                    <span v-else class="text-success font-semibold">Penuh</span>
                  </td>
                  <td data-label="Catatan Baris">
                    <input
                      :id="`terima-note-${idx}`"
                      v-model.trim="item.catatan"
                      class="input input-sm"
                      :placeholder="
                        Number(item.jumlah_diterima) < Number(item.jumlah_dikirim)
                          ? 'Wajib: alasan selisih...'
                          : 'Catatan (opsional)'
                      "
                      :aria-label="`Catatan baris ${item.nama}`"
                      :aria-invalid="Boolean(terimaErrors[`items.${idx}.catatan`])"
                    />
                    <p v-if="terimaErrors[`items.${idx}.catatan`]" class="field-error">
                      {{ terimaErrors[`items.${idx}.catatan`] }}
                    </p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <FormField
            id="terima-catatan-umum"
            label="Catatan penerimaan dokumen (opsional)"
            :error="terimaErrors.catatan_penerimaan"
          >
            <template #default="{ describedBy }">
              <textarea
                id="terima-catatan-umum"
                v-model.trim="terimaForm.catatan_penerimaan"
                rows="2"
                class="input"
                placeholder="Kondisi kemasan, berita acara serah terima atau keterangan lain..."
                :aria-invalid="Boolean(terimaErrors.catatan_penerimaan)"
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
          form="terima-form"
          class="btn btn-post"
          :disabled="terimaSubmitting || terimaLoadingDetail"
        >
          {{ terimaSubmitting ? 'Menyimpan...' : 'Konfirmasi terima' }}
        </button>
      </template>
    </BaseModal>

    <!-- modal hapus atau batalkan draf -->
    <ConfirmModal
      :open="Boolean(deleteRow)"
      :title="deleteRow?.permintaan ? 'Batalkan Draf Pengiriman' : 'Hapus Draf Pengiriman'"
      :message="
        deleteRow?.permintaan
          ? `Batalkan draf pengiriman ${deleteRow.kode}? Permintaan ${deleteRow.permintaan.kode} akan dikembalikan ke status diajukan agar dapat diproses ulang.`
          : `Hapus draf pengiriman ${deleteRow?.kode || ''}? Tindakan ini tidak bisa dibatalkan.`
      "
      :confirm-label="deleteRow?.permintaan ? 'Batalkan Draf' : 'Hapus Draf'"
      variant="danger"
      :loading="deleteLoading"
      :error="deleteError"
      @close="deleteRow = null"
      @confirm="onConfirmDelete"
    />
  </section>
</template>
