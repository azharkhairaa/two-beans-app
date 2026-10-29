<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
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
import { useLokasiOptions } from '@/composables/useOptions'
import { permintaanApi, produkApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { LOKASI_TYPE_LABELS, LOKASI_TYPES, ROLES } from '@/utils/constants'
import { PLAN_DATE_RANGE, formatDate, formatDateTime, formatNumber, todayIso } from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const { items: lokasiList, load: loadLokasi } = useLokasiOptions()

const isGudangUtamaManager = computed(
  () =>
    auth.user?.role === ROLES.MANAGER_GUDANG &&
    auth.user?.lokasi?.jenis === LOKASI_TYPES.GUDANG_UTAMA
)

const canProcessAny = computed(() => auth.isAdmin || isGudangUtamaManager.value)

const canCreate = computed(() => {
  if (auth.isAdmin) return true
  const jenis = auth.user?.lokasi?.jenis
  return jenis === LOKASI_TYPES.GUDANG_CABANG || jenis === LOKASI_TYPES.OUTLET
})

const requesterLokasiOptions = computed(() =>
  lokasiList.value.filter(
    (l) => l.jenis === LOKASI_TYPES.GUDANG_CABANG || l.jenis === LOKASI_TYPES.OUTLET
  )
)

const gudangUtama = computed(
  () => lokasiList.value.find((l) => l.jenis === LOKASI_TYPES.GUDANG_UTAMA) || null
)

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => permintaanApi.list(params),
  {
    initialFilters: {
      q: '',
      lokasi_peminta_id: '',
      status: route.query.status ? String(route.query.status) : '',
      dari: '',
      sampai: '',
      sort: 'created_at',
      arah: 'desc',
    },
    immediate: false,
  }
)

onMounted(async () => {
  await loadLokasi()
  await load()
  if (route.query.id) {
    openDetail({ id: Number(route.query.id) })
  }
})

function canEditOrCancelRow(row) {
  if (!row || row.status !== 'diajukan') return false
  if (auth.isAdmin) return true
  return Number(row.lokasi_peminta?.id) === Number(auth.user?.lokasi?.id)
}

function canProcessRow(row) {
  if (!row || row.status !== 'diajukan') return false
  return canProcessAny.value
}

function goPengiriman(pengiriman) {
  if (!pengiriman?.id) return
  router.push({ name: 'pengiriman', query: { id: pengiriman.id } })
}

// formulir ajukan atau ubah permintaan
const modalOpen = ref(false)
const editingId = ref(null)
const editingKode = ref('')
const productOptions = ref([])

const { values, errors, message, submitting, submit, fill } = useForm({
  lokasi_peminta_id: '',
  tanggal_butuh: todayIso(),
  catatan: '',
  items: [{ produk_id: '', jumlah: 1 }],
})

async function loadGudangUtamaProducts() {
  const sumberId = gudangUtama.value?.id
  if (!sumberId) {
    productOptions.value = []
    return
  }
  try {
    productOptions.value = await produkApi.options({ lokasi_id: sumberId })
  } catch {
    productOptions.value = []
  }
}

async function openCreate() {
  editingId.value = null
  editingKode.value = ''
  const defaultPemintaId = auth.isAdmin
    ? requesterLokasiOptions.value[0]?.id || ''
    : auth.user?.lokasi?.id || ''
  fill({
    lokasi_peminta_id: defaultPemintaId,
    tanggal_butuh: todayIso(),
    catatan: '',
    items: [{ produk_id: '', jumlah: 1 }],
  })
  modalOpen.value = true
  await loadGudangUtamaProducts()
}

async function openEdit(row) {
  try {
    const detail = row.items ? row : await permintaanApi.get(row.id)
    editingId.value = detail.id
    editingKode.value = detail.kode
    fill({
      lokasi_peminta_id: detail.lokasi_peminta?.id || '',
      tanggal_butuh: detail.tanggal_butuh || '',
      catatan: detail.catatan || '',
      items: detail.items.map((it) => ({
        produk_id: it.produk.id,
        jumlah: it.jumlah_diminta,
      })),
    })
    detailOpen.value = false
    modalOpen.value = true
    await loadGudangUtamaProducts()
  } catch (err) {
    toast.show(err?.message || 'Gagal memuat detail permintaan.', 'error')
  }
}

async function onSave() {
  const payload = {
    lokasi_peminta_id: auth.isAdmin ? Number(values.lokasi_peminta_id) || null : null,
    tanggal_butuh: values.tanggal_butuh || null,
    catatan: values.catatan || null,
    items: values.items.map((it) => ({
      produk_id: Number(it.produk_id) || 0,
      jumlah_diminta: Number(it.jumlah) || 0,
    })),
  }
  const saved = await submit(() =>
    editingId.value ? permintaanApi.update(editingId.value, payload) : permintaanApi.create(payload)
  )
  if (saved) {
    toast.show(
      editingId.value
        ? `Permintaan ${saved.kode} berhasil diperbarui.`
        : `Permintaan ${saved.kode} berhasil diajukan ke Gudang Utama.`
    )
    modalOpen.value = false
    await load()
  }
}

// detail permintaan
const {
  open: detailOpen,
  loading: detailLoading,
  data: detailData,
  show: openDetail,
  close: closeDetail,
} = useDetail((id) => permintaanApi.get(id), 'permintaan')

const detailTimeline = computed(() => {
  const d = detailData.value
  if (!d) return []
  const steps = [
    {
      label: `Diajukan dari ${d.lokasi_peminta?.nama || 'Lokasi Peminta'}`,
      user: d.diajukan_oleh?.name,
      time: d.created_at,
      tone: 'selesai',
      note: d.catatan || '',
    },
  ]
  if (d.status === 'dibatalkan') {
    steps.push({
      label: 'Permintaan dibatalkan oleh peminta',
      time: d.updated_at,
      tone: 'netral',
    })
    return steps
  }
  if (d.status === 'ditolak') {
    steps.push({
      label: 'Permintaan ditolak oleh Gudang Utama',
      user: d.diproses_oleh?.name,
      time: d.diproses_pada,
      tone: 'bahaya',
      note: d.alasan_penolakan ? `Alasan: ${d.alasan_penolakan}` : '',
    })
    return steps
  }
  if (d.diproses_pada) {
    steps.push({
      label: 'Disetujui oleh Gudang Utama',
      user: d.diproses_oleh?.name,
      time: d.diproses_pada,
      tone: d.status === 'disetujui' ? 'proses' : 'selesai',
      note: d.pengiriman ? `Draf pengiriman ${d.pengiriman.kode} dibuat` : '',
    })
  } else {
    steps.push({
      label: 'Keputusan Gudang Utama',
      placeholder: 'Menunggu persetujuan atau penolakan Gudang Utama',
      tone: 'menunggu',
    })
  }
  if (d.status === 'selesai') {
    steps.push({
      label: 'Pengiriman diterima & permintaan selesai',
      time: d.updated_at,
      tone: 'aman',
      note: d.pengiriman ? `Pengiriman ${d.pengiriman.kode} telah diterima` : '',
    })
  } else {
    steps.push({
      label: 'Penyelesaian Pengiriman',
      placeholder: d.pengiriman
        ? `Pengiriman ${d.pengiriman.kode} berstatus ${d.pengiriman.status}`
        : 'Menunggu pengiriman barang',
      tone: 'netral',
    })
  }
  return steps
})

// modal setujui permintaan
const setujuiModalOpen = ref(false)
const setujuiTarget = ref(null)
const setujuiLoadingDetail = ref(false)
const setujuiSubmitting = ref(false)
const setujuiMessage = ref('')
const setujuiErrors = reactive({})
const setujuiForm = reactive({
  tanggal_kirim: todayIso(),
  catatan: '',
  items: [],
})

const totalUnitDisetujui = computed(() =>
  setujuiForm.items.reduce((sum, it) => sum + (Number(it.jumlah_disetujui) || 0), 0)
)

async function openSetujui(row) {
  setujuiModalOpen.value = true
  setujuiMessage.value = ''
  for (const k of Object.keys(setujuiErrors)) delete setujuiErrors[k]

  let detail = row.items ? row : null
  if (!detail) {
    setujuiLoadingDetail.value = true
    try {
      detail = await permintaanApi.get(row.id)
    } catch (err) {
      toast.show(err?.message || 'Gagal memuat detail permintaan.', 'error')
      setujuiModalOpen.value = false
      setujuiLoadingDetail.value = false
      return
    }
    setujuiLoadingDetail.value = false
  }

  setujuiTarget.value = detail
  const today = todayIso()
  setujuiForm.tanggal_kirim =
    detail.tanggal_butuh && detail.tanggal_butuh >= today ? detail.tanggal_butuh : today
  setujuiForm.catatan = detail.catatan || ''
  setujuiForm.items = detail.items.map((it) => {
    const maxAvail = Math.min(Number(it.jumlah_diminta) || 0, Number(it.produk.stok_sumber) || 0)
    return {
      produk_id: it.produk.id,
      sku: it.produk.sku,
      nama: it.produk.nama,
      satuan: it.produk.satuan,
      stok_sumber: Number(it.produk.stok_sumber) || 0,
      jumlah_diminta: Number(it.jumlah_diminta) || 0,
      jumlah_disetujui: maxAvail,
    }
  })
}

async function onConfirmSetujui() {
  if (!setujuiTarget.value) return
  setujuiSubmitting.value = true
  setujuiMessage.value = ''
  for (const k of Object.keys(setujuiErrors)) delete setujuiErrors[k]

  try {
    const payload = {
      tanggal_kirim: setujuiForm.tanggal_kirim,
      catatan: setujuiForm.catatan?.trim() || null,
      items: setujuiForm.items.map((it) => ({
        produk_id: Number(it.produk_id),
        jumlah_disetujui: it.jumlah_disetujui === '' ? -1 : Number(it.jumlah_disetujui),
      })),
    }
    const res = await permintaanApi.setujui(setujuiTarget.value.id, payload)
    toast.show(
      `Permintaan ${res.kode} disetujui. Draf pengiriman ${res.pengiriman?.kode || ''} dibuat.`
    )
    setujuiModalOpen.value = false
    if (detailOpen.value && detailData.value?.id === res.id) {
      detailData.value = res
    }
    await load()
  } catch (err) {
    setujuiMessage.value = err?.message || 'Gagal menyetujui permintaan.'
    if (err?.errors && typeof err.errors === 'object') {
      Object.assign(setujuiErrors, err.errors)
    }
  } finally {
    setujuiSubmitting.value = false
  }
}

// modal tolak permintaan
const tolakModalOpen = ref(false)
const tolakTarget = ref(null)
const tolakForm = useForm({
  alasan_penolakan: '',
})

function openTolak(row) {
  tolakTarget.value = row
  tolakForm.fill({ alasan_penolakan: '' })
  tolakModalOpen.value = true
}

async function onConfirmTolak() {
  if (!tolakTarget.value) return
  const res = await tolakForm.submit(() =>
    permintaanApi.tolak(tolakTarget.value.id, {
      alasan_penolakan: tolakForm.values.alasan_penolakan,
    })
  )
  if (res) {
    toast.show(`Permintaan ${res.kode} ditolak.`)
    tolakModalOpen.value = false
    if (detailOpen.value && detailData.value?.id === res.id) {
      detailData.value = res
    }
    await load()
  }
}

// modal batalkan permintaan oleh peminta
const batalRow = ref(null)
const batalLoading = ref(false)
const batalError = ref('')

function openBatal(row) {
  batalRow.value = row
  batalError.value = ''
}

async function onConfirmBatal() {
  if (!batalRow.value) return
  batalLoading.value = true
  batalError.value = ''
  try {
    const res = await permintaanApi.batal(batalRow.value.id)
    toast.show(`Permintaan ${res.kode} dibatalkan.`)
    batalRow.value = null
    if (detailOpen.value && detailData.value?.id === res.id) {
      detailData.value = res
    }
    await load()
  } catch (err) {
    batalError.value = err?.message || 'Gagal membatalkan permintaan.'
  } finally {
    batalLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Permintaan Supply</h2>
        <p class="page-subtitle">
          Pengajuan pasokan barang dari gudang cabang dan outlet ke Gudang Utama beserta persetujuannya
        </p>
      </div>
      <button v-if="canCreate" type="button" class="btn btn-post" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Ajukan permintaan</span>
      </button>
    </header>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="pmt-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="pmt-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari kode PM-... atau catatan..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div v-if="canProcessAny" class="toolbar-field toolbar-field-lokasi">
          <label class="toolbar-label" for="pmt-filter-peminta">Lokasi Peminta</label>
          <SearchSelect
            id="pmt-filter-peminta"
            v-model="filters.lokasi_peminta_id"
            :options="requesterLokasiOptions.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama}` }))"
            empty-label="Semua peminta"
            small
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pmt-filter-status">Status</label>
          <select
            id="pmt-filter-status"
            v-model="filters.status"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua status</option>
            <option value="diajukan">Diajukan (Menunggu)</option>
            <option value="disetujui">Disetujui</option>
            <option value="selesai">Selesai</option>
            <option value="ditolak">Ditolak</option>
            <option value="dibatalkan">Dibatalkan</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pmt-filter-dari">Dari Tanggal</label>
          <input
            id="pmt-filter-dari"
            v-model="filters.dari"
            type="date"
            :max="filters.sampai || undefined"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pmt-filter-sampai">Sampai Tanggal</label>
          <input
            id="pmt-filter-sampai"
            v-model="filters.sampai"
            type="date"
            :min="filters.dari || undefined"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pmt-filter-sort">Sort</label>
          <select
            id="pmt-filter-sort"
            v-model="filters.sort"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="created_at">Waktu diajukan</option>
            <option value="tanggal_butuh">Tanggal butuh</option>
            <option value="kode">Kode dokumen</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="pmt-filter-arah">Order</label>
          <select
            id="pmt-filter-arah"
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
      title="Belum ada permintaan supply"
      description="Tidak ada dokumen permintaan yang cocok dengan filter saat ini."
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
            <th>Waktu Diajukan</th>
            <th>Lokasi Peminta</th>
            <th>Tanggal Butuh</th>
            <th class="num">Baris</th>
            <th>Status &amp; Pengiriman</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in items"
            :key="row.id"
            :class="{ 'row-highlight': canProcessRow(row) }"
          >
            <td data-label="Kode">
              <div class="mono font-semibold">{{ row.kode }}</div>
              <div class="cell-secondary">Oleh {{ row.diajukan_oleh?.name }}</div>
            </td>
            <td data-label="Waktu Diajukan" class="mono">{{ formatDateTime(row.created_at) }}</td>
            <td data-label="Lokasi Peminta">
              <div class="cell-primary">{{ row.lokasi_peminta?.nama }}</div>
              <div class="cell-secondary mono">{{ row.lokasi_peminta?.kode }}</div>
            </td>
            <td data-label="Tanggal Butuh" class="mono">
              {{ row.tanggal_butuh ? formatDate(row.tanggal_butuh) : '-' }}
            </td>
            <td data-label="Baris" class="num mono">{{ row.jumlah_item }} item</td>
            <td data-label="Status & Pengiriman">
              <div class="sku-summary">
                <BadgeStatus :status="row.status" />
                <BadgeStatus
                  v-if="canProcessRow(row)"
                  tone="menunggu"
                  label="Perlu diproses"
                />
              </div>
              <div v-if="row.pengiriman" class="cell-secondary mono">
                Pengiriman: {{ row.pengiriman.kode }} ({{ row.pengiriman.status }})
              </div>
            </td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button type="button" class="btn btn-get-outline btn-sm" @click="openDetail(row)">
                  Detail
                </button>
                <button
                  v-if="row.pengiriman"
                  type="button"
                  class="btn btn-get btn-sm"
                  @click="goPengiriman(row.pengiriman)"
                >
                  Pengiriman
                </button>
                <template v-if="canProcessRow(row)">
                  <button type="button" class="btn btn-post btn-sm" @click="openSetujui(row)">
                    Setujui
                  </button>
                  <button
                    type="button"
                    class="btn btn-delete btn-sm"
                    @click="openTolak(row)"
                  >
                    Tolak
                  </button>
                </template>
                <template v-if="canEditOrCancelRow(row)">
                  <button type="button" class="btn btn-put btn-sm" @click="openEdit(row)">
                    Ubah
                  </button>
                  <button
                    type="button"
                    class="btn btn-delete btn-sm"
                    @click="openBatal(row)"
                  >
                    Batalkan
                  </button>
                </template>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <PaginationBar :meta="meta" @page="setPage" @per-page="setPerPage" />
    </div>

    <!-- modal ajukan atau ubah permintaan -->
    <BaseModal
      :open="modalOpen"
      :title="editingId ? `Ubah Permintaan: ${editingKode}` : 'Ajukan Permintaan Supply ke Gudang Utama'"
      size="xl"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="permintaan-form" class="form-stack" novalidate @submit.prevent="onSave">
        <div class="form-row-2">
          <FormField
            v-if="auth.isAdmin"
            id="pmt-peminta"
            label="Lokasi peminta"
            :error="errors.lokasi_peminta_id"
          >
            <template #default="{ describedBy }">
              <SearchSelect
                id="pmt-peminta"
                v-model="values.lokasi_peminta_id"
                :options="requesterLokasiOptions.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama} (${LOKASI_TYPE_LABELS[lok.jenis]})` }))"
                required
                :disabled="Boolean(editingId)"
                :invalid="Boolean(errors.lokasi_peminta_id)"
                :described-by="describedBy"
              />
            </template>
          </FormField>
          <div v-else class="field">
            <span class="field-label">Lokasi peminta</span>
            <div class="doc-item-readonly">
              <span class="mono font-semibold">{{ auth.user?.lokasi?.kode }}</span>
              <span>&nbsp;- {{ auth.user?.lokasi?.nama }}</span>
            </div>
          </div>

          <!-- permintaan selalu ke gudang utama (BR-08), ditampilkan agar peminta tahu tujuannya -->
          <div class="field">
            <span class="field-label">Tujuan permintaan</span>
            <div class="doc-item-readonly" aria-readonly="true">
              <template v-if="gudangUtama">
                <span class="mono font-semibold">{{ gudangUtama.kode }}</span>
                <span>&nbsp;- {{ gudangUtama.nama }}</span>
              </template>
              <span v-else>Gudang utama</span>
            </div>
          </div>
        </div>

        <div class="form-row-2">
          <FormField
            id="pmt-tanggal-butuh"
            label="Tanggal dibutuhkan (opsional)"
            :error="errors.tanggal_butuh"
          >
            <template #default="{ describedBy }">
              <input
                id="pmt-tanggal-butuh"
                v-model="values.tanggal_butuh"
                type="date"
                :min="PLAN_DATE_RANGE.min()"
                :max="PLAN_DATE_RANGE.max()"
                class="input mono"
                :aria-invalid="Boolean(errors.tanggal_butuh)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField id="pmt-catatan" label="Catatan permintaan (opsional)" :error="errors.catatan">
          <template #default="{ describedBy }">
            <textarea
              id="pmt-catatan"
              v-model.trim="values.catatan"
              rows="2"
              class="input"
              placeholder="Kebutuhan stock harian, jadwal promosi atau keterangan tambahan..."
              :aria-invalid="Boolean(errors.catatan)"
              :aria-describedby="describedBy"
            ></textarea>
          </template>
        </FormField>

        <DocumentItemsEditor
          v-model="values.items"
          :products="productOptions"
          :show-stock="true"
          stock-label="Stock gudang utama"
          :disable-zero-stock="true"
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
        <button type="submit" form="permintaan-form" class="btn btn-post" :disabled="submitting">
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <span>
            {{
              submitting
                ? 'Menyimpan...'
                : editingId
                  ? 'Simpan perubahan'
                  : 'Ajukan permintaan'
            }}
          </span>
        </button>
      </template>
    </BaseModal>

    <!-- modal detail permintaan -->
    <BaseModal
      :open="detailOpen"
      :title="detailData ? `Detail Permintaan: ${detailData.kode}` : 'Detail Permintaan'"
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
              Diajukan pada <strong class="mono">{{ formatDateTime(detailData.created_at) }}</strong>
              oleh <strong>{{ detailData.diajukan_oleh?.name }}</strong>
            </p>
          </div>
          <div v-if="detailData.pengiriman" class="num">
            <span class="detail-label">Dokumen Pengiriman</span>
            <div class="sku-summary">
              <strong class="mono">{{ detailData.pengiriman.kode }}</strong>
              <BadgeStatus :status="detailData.pengiriman.status" />
            </div>
          </div>
        </div>

        <div class="summary-strip">
          <div class="summary-item">
            <span class="detail-label">Lokasi Peminta</span>
            <strong class="cell-primary">{{ detailData.lokasi_peminta?.nama }}</strong>
            <span class="cell-secondary mono">{{ detailData.lokasi_peminta?.kode }}</span>
          </div>
          <div class="summary-item">
            <span class="detail-label">Lokasi Sumber</span>
            <strong class="cell-primary">{{ detailData.lokasi_sumber?.nama }}</strong>
            <span class="cell-secondary mono">{{ detailData.lokasi_sumber?.kode }}</span>
          </div>
          <div class="summary-item">
            <span class="detail-label">Tanggal Dibutuhkan</span>
            <strong class="cell-primary mono">
              {{ detailData.tanggal_butuh ? formatDate(detailData.tanggal_butuh) : 'Fleksibel' }}
            </strong>
            <span class="cell-secondary">{{ detailData.jumlah_item }} jenis produk</span>
          </div>
        </div>

        <p v-if="detailData.catatan" class="cell-secondary">
          <strong>Catatan peminta:</strong> {{ detailData.catatan }}
        </p>
        <p v-if="detailData.alasan_penolakan" class="alert alert-error">
          <strong>Alasan penolakan:</strong> {{ detailData.alasan_penolakan }}
        </p>

        <RiwayatDokumen :steps="detailTimeline" />

        <div class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Produk</th>
                <th class="num">Stock Gudang Utama</th>
                <th class="num">Jumlah Diminta</th>
                <th class="num">Jumlah Disetujui</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in detailData.items" :key="item.id">
                <td data-label="SKU" class="mono font-semibold">{{ item.produk.sku }}</td>
                <td data-label="Produk">
                  <div class="cell-primary">{{ item.produk.nama }}</div>
                  <BadgeStatus :status="item.produk.jenis" />
                </td>
                <td data-label="Stock Gudang Utama" class="num mono">
                  {{ formatNumber(item.produk.stok_sumber) }} {{ item.produk.satuan }}
                </td>
                <td data-label="Jumlah Diminta" class="num mono font-semibold">
                  {{ formatNumber(item.jumlah_diminta) }} {{ item.produk.satuan }}
                </td>
                <td data-label="Jumlah Disetujui" class="num mono">
                  <template
                    v-if="item.jumlah_disetujui !== null && item.jumlah_disetujui !== undefined"
                  >
                    <span class="font-semibold">
                      {{ formatNumber(item.jumlah_disetujui) }} {{ item.produk.satuan }}
                    </span>
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
        <button
          v-if="detailData?.pengiriman"
          type="button"
          class="btn btn-get"
          @click="goPengiriman(detailData.pengiriman)"
        >
          <AppIcon name="truck" :size="15" />
          <span>Buka Pengiriman {{ detailData.pengiriman.kode }}</span>
        </button>
        <template v-if="detailData && canEditOrCancelRow(detailData)">
          <button
            type="button"
            class="btn btn-delete"
            @click="openBatal(detailData)"
          >
            Batalkan permintaan
          </button>
          <button type="button" class="btn btn-put" @click="openEdit(detailData)">
            Ubah permintaan
          </button>
        </template>
        <template v-if="detailData && canProcessRow(detailData)">
          <button
            type="button"
            class="btn btn-delete"
            @click="openTolak(detailData)"
          >
            Tolak
          </button>
          <button type="button" class="btn btn-post" @click="openSetujui(detailData)">
            Setujui &amp; Buat Pengiriman
          </button>
        </template>
      </template>
    </BaseModal>

    <!-- modal setujui permintaan -->
    <BaseModal
      :open="setujuiModalOpen"
      :title="setujuiTarget ? `Setujui Permintaan: ${setujuiTarget.kode}` : 'Setujui Permintaan'"
      size="xl"
      @close="setujuiModalOpen = false"
    >
      <LoadingState v-if="setujuiLoadingDetail" :rows="3" />
      <template v-else-if="setujuiTarget">
        <p v-if="setujuiMessage" class="alert alert-error" role="alert">{{ setujuiMessage }}</p>
        <p v-if="setujuiErrors.items" class="alert alert-error" role="alert">
          {{ setujuiErrors.items }}
        </p>
        <p class="confirm-message">
          Setujui permintaan pasokan dari
          <strong>{{ setujuiTarget.lokasi_peminta?.nama }}</strong>. Draf pengiriman dari
          <strong>{{ setujuiTarget.lokasi_sumber?.nama }}</strong> akan otomatis dibuat untuk semua
          baris dengan jumlah disetujui lebih dari 0.
        </p>

        <form id="setujui-form" class="form-stack" novalidate @submit.prevent="onConfirmSetujui">
          <div class="form-row-2">
            <FormField
              id="setujui-tanggal-kirim"
              label="Rencana tanggal kirim"
              :error="setujuiErrors.tanggal_kirim"
            >
              <template #default="{ describedBy }">
                <input
                  id="setujui-tanggal-kirim"
                  v-model="setujuiForm.tanggal_kirim"
                  type="date"
                  :min="PLAN_DATE_RANGE.min()"
                  :max="PLAN_DATE_RANGE.max()"
                  class="input mono"
                  required
                  :aria-invalid="Boolean(setujuiErrors.tanggal_kirim)"
                  :aria-describedby="describedBy"
                />
              </template>
            </FormField>

            <FormField
              id="setujui-catatan"
              label="Catatan pengiriman (opsional)"
              :error="setujuiErrors.catatan"
            >
              <template #default="{ describedBy }">
                <input
                  id="setujui-catatan"
                  v-model.trim="setujuiForm.catatan"
                  class="input"
                  placeholder="Catatan untuk surat jalan / kurir..."
                  :aria-invalid="Boolean(setujuiErrors.catatan)"
                  :aria-describedby="describedBy"
                />
              </template>
            </FormField>
          </div>

          <div class="table-card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Produk</th>
                  <th class="num">Stock Gudang Utama</th>
                  <th class="num">Diminta</th>
                  <th class="num">Jumlah Disetujui</th>
                  <th>Pemenuhan</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, idx) in setujuiForm.items" :key="item.produk_id">
                  <td data-label="Produk">
                    <div class="cell-primary">{{ item.nama }}</div>
                    <div class="cell-secondary mono">{{ item.sku }}</div>
                  </td>
                  <td data-label="Stock Gudang Utama" class="num mono">
                    {{ formatNumber(item.stok_sumber) }} {{ item.satuan }}
                  </td>
                  <td data-label="Diminta" class="num mono font-semibold">
                    {{ formatNumber(item.jumlah_diminta) }} {{ item.satuan }}
                  </td>
                  <td data-label="Jumlah Disetujui" class="num">
                    <div class="doc-qty-wrap">
                      <input
                        :id="`setujui-qty-${idx}`"
                        v-model.number="item.jumlah_disetujui"
                        type="number"
                        min="0"
                        :max="Math.min(item.jumlah_diminta, item.stok_sumber)"
                        step="1"
                        class="input input-sm mono"
                        :aria-label="`Jumlah disetujui ${item.nama}`"
                        :aria-invalid="Boolean(setujuiErrors[`items.${idx}.jumlah_disetujui`])"
                      />
                      <span class="badge badge-draf">{{ item.satuan }}</span>
                    </div>
                    <p v-if="setujuiErrors[`items.${idx}.jumlah_disetujui`]" class="field-error">
                      {{ setujuiErrors[`items.${idx}.jumlah_disetujui`] }}
                    </p>
                  </td>
                  <td data-label="Pemenuhan">
                    <BadgeStatus
                      v-if="Number(item.jumlah_disetujui) === Number(item.jumlah_diminta)"
                      tone="aman"
                      label="Penuh"
                    />
                    <BadgeStatus
                      v-else-if="Number(item.jumlah_disetujui) > 0"
                      tone="menunggu"
                      label="Sebagian"
                    />
                    <BadgeStatus v-else tone="netral" label="Tidak dikirim (0)" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="doc-items-summary">
            <span>
              Total unit disetujui:
              <strong class="mono">{{ formatNumber(totalUnitDisetujui) }}</strong>
            </span>
          </div>
        </form>
      </template>

      <template #footer>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="setujuiSubmitting"
          @click="setujuiModalOpen = false"
        >
          Batal
        </button>
        <button
          type="submit"
          form="setujui-form"
          class="btn btn-post"
          :disabled="setujuiSubmitting || setujuiLoadingDetail"
        >
          {{ setujuiSubmitting ? 'Memproses...' : 'Setujui & Buat Draf Pengiriman' }}
        </button>
      </template>
    </BaseModal>

    <!-- modal tolak permintaan -->
    <BaseModal
      :open="tolakModalOpen"
      :title="tolakTarget ? `Tolak Permintaan: ${tolakTarget.kode}` : 'Tolak Permintaan'"
      size="md"
      @close="tolakModalOpen = false"
    >
      <p v-if="tolakForm.message.value" class="alert alert-error" role="alert">
        {{ tolakForm.message.value }}
      </p>
      <p v-if="tolakTarget" class="confirm-message">
        Tolak permintaan <strong class="mono">{{ tolakTarget.kode }}</strong> dari
        <strong>{{ tolakTarget.lokasi_peminta?.nama }}</strong>? Tindakan ini tidak dapat dibatalkan.
      </p>
      <form id="tolak-form" class="form-stack" novalidate @submit.prevent="onConfirmTolak">
        <FormField
          id="tolak-alasan"
          label="Alasan penolakan"
          hint="Wajib diisi (3 sampai 300 karakter)"
          :error="tolakForm.errors.value.alasan_penolakan"
        >
          <template #default="{ describedBy }">
            <textarea
              id="tolak-alasan"
              v-model.trim="tolakForm.values.alasan_penolakan"
              rows="3"
              class="input"
              required
              placeholder="Jelaskan alasan penolakan permintaan ini..."
              :aria-invalid="Boolean(tolakForm.errors.value.alasan_penolakan)"
              :aria-describedby="describedBy"
            ></textarea>
          </template>
        </FormField>
      </form>

      <template #footer>
        <button
          type="button"
          class="btn btn-secondary"
          :disabled="tolakForm.submitting.value"
          @click="tolakModalOpen = false"
        >
          Batal
        </button>
        <button
          type="submit"
          form="tolak-form"
          class="btn btn-delete"
          :disabled="tolakForm.submitting.value"
        >
          {{ tolakForm.submitting.value ? 'Menolak...' : 'Tolak permintaan' }}
        </button>
      </template>
    </BaseModal>

    <!-- modal batalkan permintaan -->
    <ConfirmModal
      :open="Boolean(batalRow)"
      title="Batalkan Permintaan Supply"
      :message="`Batalkan permintaan ${batalRow?.kode || ''}? Permintaan yang sudah dibatalkan tidak akan diproses oleh Gudang Utama.`"
      confirm-label="Batalkan Permintaan"
      variant="danger"
      :loading="batalLoading"
      :error="batalError"
      @close="batalRow = null"
      @confirm="onConfirmBatal"
    />
  </section>
</template>
