<script setup>
import { computed, onMounted, ref } from 'vue'

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
import SearchSelect from '@/components/SearchSelect.vue'
import { useDetail } from '@/composables/useDetail'
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { useLokasiOptions } from '@/composables/useOptions'
import { produkApi, transaksiApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import {
  KATEGORI_TYPE_LABELS,
  REDUCING_REASONS,
  TRANSAKSI_REASONS,
  TRANSAKSI_REASON_LABELS,
  TRANSAKSI_TYPE_LABELS,
} from '@/utils/constants'
import {
  DOCUMENT_DATE_RANGE,
  formatDate,
  formatDateTime,
  formatNumber,
  todayIso,
} from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()

const { items: lokasiList, load: loadLokasi } = useLokasiOptions()

onMounted(() => {
  if (auth.isAdmin) loadLokasi()
})

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => transaksiApi.list(params),
  {
    initialFilters: {
      q: '',
      lokasi_id: '',
      jenis: '',
      status: '',
      alasan: '',
      dari: '',
      sampai: '',
      sort: 'tanggal',
      arah: 'desc',
    },
  }
)

const modalOpen = ref(false)
const editingId = ref(null)
const editingKode = ref('')
const productOptions = ref([])

const { values, errors, message, submitting, submit, fill } = useForm({
  jenis: 'masuk',
  lokasi_id: '',
  tanggal: todayIso(),
  alasan: 'hasil_roasting',
  keterangan: '',
  catatan: '',
  items: [{ produk_id: '', jumlah: 1 }],
})

const reasonOptions = computed(() => TRANSAKSI_REASONS[values.jenis] || [])

// cara isi jumlah: rusak, hilang dan kedaluwarsa cukup jumlah yang berkurang,
// opname dan lainnya diisi stock fisik lalu selisihnya dihitung dari stock tercatat
const quantityMode = computed(() => {
  if (values.jenis !== 'penyesuaian') return 'jumlah'
  return REDUCING_REASONS.includes(values.alasan) ? 'kurangi' : 'hitung'
})

const ALASAN_HINTS = {
  roasting: 'Roasting hanya untuk produk kategori Green Bean',
  hasil_roasting: 'Hasil roasting hanya untuk produk kategori Roasted Bean',
  kurangi: 'Alasan ini selalu mengurangi stock, isi jumlah barang yang berkurang',
  hitung: 'Isi stock fisik hasil hitung, selisihnya dihitung otomatis',
}

const alasanHint = computed(
  () => ALASAN_HINTS[values.alasan] || ALASAN_HINTS[quantityMode.value] || ''
)

// efek baris ke stock: keluar mengurangi, penyesuaian sudah bertanda
function stockChange(item) {
  return detailData.value?.jenis === 'keluar' ? -item.jumlah : item.jumlah
}

const requiredProductJenis = computed(() => {
  if (values.alasan === 'roasting') return 'green_bean'
  if (values.alasan === 'hasil_roasting') return 'roasted_bean'
  return ''
})

async function loadProductOptions() {
  const lokasiId = auth.isAdmin ? values.lokasi_id : auth.user?.lokasi?.id
  if (!lokasiId) {
    productOptions.value = []
    return
  }
  const params = { lokasi_id: lokasiId }
  if (requiredProductJenis.value) {
    params.jenis = requiredProductJenis.value
  }
  try {
    productOptions.value = await produkApi.options(params)
  } catch {
    productOptions.value = []
  }
}

async function onJenisChange(nextJenis) {
  values.jenis = nextJenis
  const validReasons = TRANSAKSI_REASONS[nextJenis] || []
  if (!validReasons.includes(values.alasan)) {
    values.alasan = validReasons[0] || 'lainnya'
  }
  await loadProductOptions()
}

async function onAlasanChange(nextAlasan) {
  values.alasan = nextAlasan
  await loadProductOptions()
}

async function onLokasiChange(nextLokasiId) {
  values.lokasi_id = nextLokasiId ? Number(nextLokasiId) : ''
  await loadProductOptions()
}

async function openCreate() {
  editingId.value = null
  editingKode.value = ''
  const defaultLokasiId = auth.isAdmin
    ? lokasiList.value[0]?.id || ''
    : auth.user?.lokasi?.id || ''
  fill({
    jenis: 'masuk',
    lokasi_id: defaultLokasiId,
    tanggal: todayIso(),
    alasan: 'hasil_roasting',
    keterangan: '',
    catatan: '',
    items: [{ produk_id: '', jumlah: 1 }],
  })
  modalOpen.value = true
  await loadProductOptions()
}

async function openEdit(row) {
  try {
    const detail = row.items ? row : await transaksiApi.get(row.id)
    editingId.value = detail.id
    editingKode.value = detail.kode
    fill({
      jenis: detail.jenis,
      lokasi_id: detail.lokasi?.id || '',
      tanggal: detail.tanggal,
      alasan: detail.alasan,
      keterangan: detail.keterangan || '',
      catatan: detail.catatan || '',
      items: detail.items.map((it) => ({
        produk_id: it.produk.id,
        jumlah: it.jumlah,
      })),
    })
    detailOpen.value = false
    modalOpen.value = true
    await loadProductOptions()
  } catch (err) {
    toast.show(err?.message || 'Gagal memuat draf transaksi.', 'error')
  }
}

async function onSave() {
  const payload = {
    jenis: values.jenis,
    lokasi_id: auth.isAdmin ? Number(values.lokasi_id) || null : null,
    tanggal: values.tanggal,
    alasan: values.alasan,
    keterangan: values.keterangan || null,
    catatan: values.catatan || null,
    items: values.items.map((it) => ({
      produk_id: Number(it.produk_id) || 0,
      jumlah: Number(it.jumlah) || 0,
    })),
  }
  const ok = await submit(() =>
    editingId.value ? transaksiApi.update(editingId.value, payload) : transaksiApi.create(payload)
  )
  if (ok) {
    toast.show(
      editingId.value
        ? `Draf transaksi ${editingKode.value} diperbarui.`
        : 'Draf transaksi berhasil dibuat.'
    )
    modalOpen.value = false
    await load()
  }
}

const {
  open: detailOpen,
  loading: detailLoading,
  data: detailData,
  show: openDetail,
  close: closeDetail,
} = useDetail((id) => transaksiApi.get(id), 'transaksi')

const confirmAction = ref(null)
const confirmLoading = ref(false)
const confirmError = ref('')

const POSTING_EFFECTS = {
  masuk: 'Stock lokasi bertambah',
  keluar: 'Stock lokasi berkurang',
  penyesuaian: 'Stock lokasi disesuaikan sebesar selisih tiap baris',
}

function openPosting(row) {
  const alasan = TRANSAKSI_REASON_LABELS[row.alasan] || row.alasan
  confirmAction.value = {
    type: 'posting',
    row,
    title: 'Posting Transaksi Stock',
    message:
      `Posting ${row.kode} (${TRANSAKSI_TYPE_LABELS[row.jenis]}, ${alasan}) ` +
      `di ${row.lokasi?.nama}? ${POSTING_EFFECTS[row.jenis]} dan dokumen tidak bisa diubah lagi.`,
    confirmLabel: 'Posting Sekarang',
    variant: 'primary',
  }
  confirmError.value = ''
}

function openDelete(row) {
  confirmAction.value = {
    type: 'delete',
    row,
    title: 'Hapus Draf Transaksi',
    message: `Hapus draf transaksi ${row.kode}? Tindakan ini tidak dapat dibatalkan.`,
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
      await transaksiApi.posting(row.id)
      toast.show(`Transaksi ${row.kode} berhasil diposting dan stok telah diperbarui.`)
    } else {
      await transaksiApi.remove(row.id)
      toast.show(`Draf transaksi ${row.kode} dihapus.`)
    }
    confirmAction.value = null
    detailOpen.value = false
    await load()
  } catch (err) {
    const fieldMsg = err?.errors ? Object.values(err.errors).join(' | ') : ''
    confirmError.value = fieldMsg
      ? `${err.message}: ${fieldMsg}`
      : err?.message || 'Gagal memproses transaksi.'
  } finally {
    confirmLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Transaksi Stok</h2>
        <p class="page-subtitle">
          Pencatatan barang masuk, pemakaian keluar, roasting dan penyesuaian stock opname
        </p>
      </div>
      <button type="button" class="btn btn-post" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Buat transaksi</span>
      </button>
    </header>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="trx-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="trx-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari kode dokumen atau keterangan..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div v-if="auth.isAdmin" class="toolbar-field toolbar-field-lokasi">
          <label class="toolbar-label" for="trx-filter-lokasi">Lokasi</label>
          <SearchSelect
            id="trx-filter-lokasi"
            v-model="filters.lokasi_id"
            :options="lokasiList.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama}` }))"
            empty-label="Semua lokasi"
            small
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="trx-filter-jenis">Jenis</label>
          <select
            id="trx-filter-jenis"
            v-model="filters.jenis"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua jenis</option>
            <option v-for="(lbl, key) in TRANSAKSI_TYPE_LABELS" :key="key" :value="key">
              {{ lbl }}
            </option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="trx-filter-status">Status</label>
          <select
            id="trx-filter-status"
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
          <label class="toolbar-label" for="trx-filter-alasan">Alasan</label>
          <select
            id="trx-filter-alasan"
            v-model="filters.alasan"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua alasan</option>
            <option v-for="(lbl, key) in TRANSAKSI_REASON_LABELS" :key="key" :value="key">
              {{ lbl }}
            </option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="trx-filter-dari">Dari Tanggal</label>
          <input
            id="trx-filter-dari"
            v-model="filters.dari"
            type="date"
            :max="filters.sampai || undefined"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="trx-filter-sampai">Sampai Tanggal</label>
          <input
            id="trx-filter-sampai"
            v-model="filters.sampai"
            type="date"
            :min="filters.dari || undefined"
            class="input input-sm mono"
            @change="applyFilters()"
          />
        </div>
        <button type="submit" class="btn btn-secondary btn-sm">Filter</button>
      </div>
    </form>

    <LoadingState v-if="loading" :rows="5" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState
      v-else-if="!items.length"
      title="Belum ada dokumen transaksi"
      description="Buat draf transaksi masuk, keluar atau penyesuaian stok untuk lokasi Anda."
    >
      <button type="button" class="btn btn-post btn-sm" @click="openCreate">
        Buat transaksi
      </button>
    </EmptyState>

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Kode</th>
            <th>Tanggal</th>
            <th>Jenis</th>
            <th>Lokasi</th>
            <th>Alasan &amp; Keterangan</th>
            <th class="num">Baris</th>
            <th>Status</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td data-label="Kode" class="mono font-semibold">{{ row.kode }}</td>
            <td data-label="Tanggal" class="mono">{{ formatDate(row.tanggal) }}</td>
            <td data-label="Jenis">
              <BadgeStatus :status="row.jenis" />
            </td>
            <td data-label="Lokasi">
              <span class="mono font-semibold">{{ row.lokasi?.kode }}</span>
              <span class="cell-secondary"> - {{ row.lokasi?.nama }}</span>
            </td>
            <td data-label="Alasan & Keterangan">
              <div class="cell-primary">{{ TRANSAKSI_REASON_LABELS[row.alasan] || row.alasan }}</div>
              <div v-if="row.keterangan" class="cell-secondary">{{ row.keterangan }}</div>
            </td>
            <td data-label="Baris" class="num mono">{{ row.jumlah_item }} item</td>
            <td data-label="Status">
              <BadgeStatus :status="row.status" />
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

    <BaseModal
      :open="modalOpen"
      :title="editingId ? `Ubah Draf Transaksi: ${editingKode}` : 'Buat Draf Transaksi Stok'"
      size="xl"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="transaksi-form" class="form-stack" novalidate @submit.prevent="onSave">
        <div class="form-row-2">
          <FormField id="trx-jenis" label="Jenis transaksi" :error="errors.jenis">
            <template #default="{ describedBy }">
              <select
                id="trx-jenis"
                :value="values.jenis"
                class="input"
                :disabled="Boolean(editingId)"
                :aria-invalid="Boolean(errors.jenis)"
                :aria-describedby="describedBy"
                @change="onJenisChange($event.target.value)"
              >
                <option v-for="(lbl, key) in TRANSAKSI_TYPE_LABELS" :key="key" :value="key">
                  {{ lbl }}
                </option>
              </select>
            </template>
          </FormField>

          <FormField id="trx-tanggal" label="Tanggal dokumen" :error="errors.tanggal">
            <template #default="{ describedBy }">
              <input
                id="trx-tanggal"
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

        <div class="form-row-2">
          <FormField
            v-if="auth.isAdmin"
            id="trx-lokasi"
            label="Lokasi transaksi"
            :error="errors.lokasi_id"
          >
            <template #default="{ describedBy }">
              <SearchSelect
                id="trx-lokasi"
                :model-value="values.lokasi_id"
                :options="lokasiList.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama}` }))"
                placeholder="Pilih lokasi..."
                required
                :invalid="Boolean(errors.lokasi_id)"
                :described-by="describedBy"
                @change="onLokasiChange($event)"
              />
            </template>
          </FormField>
          <div v-else class="field">
            <span class="field-label">Lokasi transaksi</span>
            <div class="doc-item-readonly">
              <span class="mono font-semibold">{{ auth.user?.lokasi?.kode }}</span>
              <span>&nbsp;- {{ auth.user?.lokasi?.nama }}</span>
            </div>
          </div>

          <FormField
            id="trx-alasan"
            label="Alasan transaksi"
            :hint="alasanHint"
            :error="errors.alasan"
          >
            <template #default="{ describedBy }">
              <select
                id="trx-alasan"
                :value="values.alasan"
                class="input"
                required
                :aria-invalid="Boolean(errors.alasan)"
                :aria-describedby="describedBy"
                @change="onAlasanChange($event.target.value)"
              >
                <option v-for="rsn in reasonOptions" :key="rsn" :value="rsn">
                  {{ TRANSAKSI_REASON_LABELS[rsn] || rsn }}
                </option>
              </select>
            </template>
          </FormField>
        </div>

        <FormField id="trx-keterangan" label="Keterangan ringkas (opsional)" :error="errors.keterangan">
          <template #default="{ describedBy }">
            <input
              id="trx-keterangan"
              v-model.trim="values.keterangan"
              class="input"
              placeholder="Contoh: Batch sangrai pagi Gayo & Toraja"
              :aria-invalid="Boolean(errors.keterangan)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <DocumentItemsEditor
          v-model="values.items"
          :products="productOptions"
          :mode="quantityMode"
          :outbound="values.jenis === 'keluar'"
          stock-label="Stock saat ini"
          :errors="errors"
        />

        <FormField id="trx-catatan" label="Catatan tambahan (opsional)" :error="errors.catatan">
          <template #default="{ describedBy }">
            <textarea
              id="trx-catatan"
              v-model.trim="values.catatan"
              class="input"
              rows="2"
              :aria-invalid="Boolean(errors.catatan)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </form>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="modalOpen = false">Batal</button>
        <button type="submit" form="transaksi-form" class="btn btn-post" :disabled="submitting">
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting ? 'Menyimpan...' : 'Simpan Draf' }}</span>
        </button>
      </template>
    </BaseModal>

    <BaseModal
      :open="detailOpen"
      :title="detailData ? `Transaksi ${detailData.kode}` : 'Detail Transaksi'"
      size="xl"
      @close="closeDetail"
    >
      <LoadingState v-if="detailLoading" :rows="4" />
      <div v-else-if="detailData" class="detail-grid">
        <div class="detail-highlight">
          <div class="sku-summary">
            <BadgeStatus :status="detailData.jenis" />
            <BadgeStatus :status="detailData.status" />
          </div>
          <div class="mono font-semibold">{{ formatDate(detailData.tanggal) }}</div>
        </div>

        <dl class="detail-list">
          <div>
            <dt>Lokasi</dt>
            <dd>
              <span class="mono">{{ detailData.lokasi?.kode }}</span> -
              {{ detailData.lokasi?.nama }}
            </dd>
          </div>
          <div>
            <dt>Alasan</dt>
            <dd>{{ TRANSAKSI_REASON_LABELS[detailData.alasan] || detailData.alasan }}</dd>
          </div>
          <div>
            <dt>Keterangan</dt>
            <dd>{{ detailData.keterangan || '-' }}</dd>
          </div>
          <div>
            <dt>Dibuat Oleh</dt>
            <dd>{{ detailData.dibuat_oleh }} ({{ formatDateTime(detailData.created_at) }})</dd>
          </div>
          <div v-if="detailData.diposting_oleh">
            <dt>Diposting Oleh</dt>
            <dd>
              {{ detailData.diposting_oleh }} ({{ formatDateTime(detailData.diposting_pada) }})
            </dd>
          </div>
          <div v-if="detailData.catatan">
            <dt>Catatan</dt>
            <dd>{{ detailData.catatan }}</dd>
          </div>
        </dl>

        <h3 class="section-title">Rincian Item Produk</h3>
        <div class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Nama Produk</th>
                <th>Jenis</th>
                <th class="num">Perubahan stock</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="it in detailData.items" :key="it.id">
                <td data-label="SKU" class="mono font-semibold">{{ it.produk.sku }}</td>
                <td data-label="Nama Produk">{{ it.produk.nama }}</td>
                <td data-label="Jenis">
                  {{ KATEGORI_TYPE_LABELS[it.produk.jenis] || it.produk.jenis }}
                </td>
                <td
                  data-label="Perubahan stock"
                  class="num mono font-semibold"
                  :class="stockChange(it) < 0 ? 'text-danger' : 'text-success'"
                >
                  {{ stockChange(it) > 0 ? '+' : '' }}{{ formatNumber(stockChange(it)) }}
                  {{ it.produk.satuan }}
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
            Hapus Draf
          </button>
          <button type="button" class="btn btn-put" @click="openEdit(detailData)">
            Ubah Draf
          </button>
          <button type="button" class="btn btn-post" @click="openPosting(detailData)">
            Posting Transaksi
          </button>
        </template>
      </template>
    </BaseModal>

    <ConfirmModal
      :open="Boolean(confirmAction)"
      :title="confirmAction?.title || 'Konfirmasi'"
      :message="confirmAction?.message || ''"
      :confirm-label="confirmAction?.confirmLabel || 'Lanjutkan'"
      :variant="confirmAction?.variant || 'primary'"
      :loading="confirmLoading"
      :error="confirmError"
      @close="confirmAction = null"
      @confirm="onConfirmExecute"
    />
  </section>
</template>
