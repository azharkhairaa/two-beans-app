<script setup>
import { computed, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FormField from '@/components/FormField.vue'
import KartuStokModal from '@/components/KartuStokModal.vue'
import LoadingState from '@/components/LoadingState.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { kategoriApi, produkApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import {
  COFFEE_TYPE_LABELS,
  KATEGORI_TYPE_LABELS,
  PRODUK_UNIT_LABELS,
  PRODUK_WEIGHTS,
  ROAST_LEVEL_LABELS,
} from '@/utils/constants'
import { formatNumber, formatRupiah } from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()

const kategoriList = ref([])

onMounted(async () => {
  try {
    kategoriList.value = await kategoriApi.list()
  } catch {
    kategoriList.value = []
  }
})

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => produkApi.list(params),
  {
    initialFilters: {
      q: '',
      kategori_id: '',
      jenis: '',
      jenis_kopi: '',
      aktif: auth.isAdmin ? 'semua' : 'ya',
      sort: 'nama',
      arah: 'asc',
    },
  }
)

const modalOpen = ref(false)
const editingId = ref(null)

const { values, errors, message, submitting, submit, fill } = useForm({
  sku: '',
  nama: '',
  kategori_id: '',
  merek: '',
  satuan: 'pack',
  berat_gram: 250,
  tingkat_sangrai: 'medium',
  jenis_kopi: 'arabika',
  harga_beli: 0,
  harga_jual: 0,
  deskripsi: '',
  aktif: true,
})

const selectedKategori = computed(() =>
  kategoriList.value.find((k) => Number(k.id) === Number(values.kategori_id)) || null
)

const selectedJenis = computed(() => selectedKategori.value?.jenis || '')
const isGreenBean = computed(() => selectedJenis.value === 'green_bean')
const isRoastedBean = computed(() => selectedJenis.value === 'roasted_bean')
const isCoffee = computed(() => isGreenBean.value || isRoastedBean.value)

function onKategoriChange(rawId) {
  values.kategori_id = rawId ? Number(rawId) : ''
  const kat = kategoriList.value.find((k) => Number(k.id) === Number(rawId))
  if (!kat) return
  if (kat.jenis === 'green_bean') {
    values.satuan = 'kg'
    values.berat_gram = ''
    values.tingkat_sangrai = ''
    if (!values.jenis_kopi) values.jenis_kopi = 'arabika'
  } else if (kat.jenis === 'roasted_bean') {
    values.satuan = 'pack'
    if (!values.berat_gram) values.berat_gram = 250
    if (!values.jenis_kopi) values.jenis_kopi = 'arabika'
  } else {
    if (values.satuan === 'kg') values.satuan = 'pcs'
    values.berat_gram = ''
    values.tingkat_sangrai = ''
    values.jenis_kopi = ''
  }
}

function openCreate() {
  editingId.value = null
  const firstKat = kategoriList.value[0] || null
  const jenis = firstKat?.jenis || 'roasted_bean'
  fill({
    sku: '',
    nama: '',
    kategori_id: firstKat ? firstKat.id : '',
    merek: 'Two Beans',
    satuan: jenis === 'green_bean' ? 'kg' : jenis === 'roasted_bean' ? 'pack' : 'pcs',
    berat_gram: jenis === 'roasted_bean' ? 250 : '',
    tingkat_sangrai: jenis === 'roasted_bean' ? 'medium' : '',
    jenis_kopi: jenis === 'green_bean' || jenis === 'roasted_bean' ? 'arabika' : '',
    harga_beli: 0,
    harga_jual: 0,
    deskripsi: '',
    aktif: true,
  })
  modalOpen.value = true
}

function openEdit(row) {
  editingId.value = row.id
  fill({
    sku: row.sku,
    nama: row.nama,
    kategori_id: row.kategori?.id || '',
    merek: row.merek || '',
    satuan: row.satuan,
    berat_gram: row.berat_gram || '',
    tingkat_sangrai: row.tingkat_sangrai || '',
    jenis_kopi: row.jenis_kopi || '',
    harga_beli: row.harga_beli ?? 0,
    harga_jual: row.harga_jual ?? 0,
    deskripsi: row.deskripsi || '',
    aktif: Boolean(row.aktif),
  })
  modalOpen.value = true
}

async function onSave() {
  const payload = {
    sku: values.sku.toUpperCase(),
    nama: values.nama,
    kategori_id: Number(values.kategori_id) || 0,
    merek: values.merek || null,
    satuan: values.satuan,
    berat_gram: isRoastedBean.value && values.berat_gram ? Number(values.berat_gram) : null,
    tingkat_sangrai: isRoastedBean.value && values.tingkat_sangrai ? values.tingkat_sangrai : null,
    jenis_kopi: isCoffee.value && values.jenis_kopi ? values.jenis_kopi : null,
    harga_beli: Number(values.harga_beli) || 0,
    harga_jual: Number(values.harga_jual) || 0,
    deskripsi: values.deskripsi || null,
    aktif: Boolean(values.aktif),
  }
  const ok = await submit(() =>
    editingId.value ? produkApi.update(editingId.value, payload) : produkApi.create(payload)
  )
  if (ok) {
    toast.show(
      editingId.value ? 'Produk berhasil diperbarui.' : 'Produk baru berhasil ditambahkan.'
    )
    modalOpen.value = false
    await load()
  }
}

const detailOpen = ref(false)
const detailLoading = ref(false)
const detailData = ref(null)

async function openDetail(row) {
  detailOpen.value = true
  detailLoading.value = true
  detailData.value = null
  try {
    detailData.value = await produkApi.get(row.id)
  } catch (err) {
    toast.show(err?.message || 'Gagal memuat detail produk.', 'error')
    detailOpen.value = false
  } finally {
    detailLoading.value = false
  }
}

const kartuOpen = ref(false)
const kartuLokasi = ref(null)

function openKartuFromDetail(lokasi) {
  kartuLokasi.value = lokasi
  kartuOpen.value = true
}

const deletingRow = ref(null)
const deleteLoading = ref(false)
const deleteError = ref('')

function openDelete(row) {
  deletingRow.value = row
  deleteError.value = ''
}

async function onConfirmDelete() {
  if (!deletingRow.value) return
  deleteLoading.value = true
  deleteError.value = ''
  try {
    await produkApi.remove(deletingRow.value.id)
    toast.show(`Produk ${deletingRow.value.nama} dihapus.`)
    deletingRow.value = null
    await load()
  } catch (err) {
    deleteError.value = err?.message || 'Gagal menghapus produk.'
  } finally {
    deleteLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Katalog Produk</h2>
        <p class="page-subtitle">Green bean, roasted bean, peralatan seduh dan bahan habis pakai</p>
      </div>
      <button v-if="auth.isAdmin" type="button" class="btn btn-primary" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Tambah produk</span>
      </button>
    </header>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="prd-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="prd-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari SKU, nama produk atau merek..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div class="toolbar-field">
          <label class="toolbar-label" for="prd-filter-kategori">Kategori</label>
          <select
            id="prd-filter-kategori"
            v-model="filters.kategori_id"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua kategori</option>
            <option v-for="kat in kategoriList" :key="kat.id" :value="kat.id">
              {{ kat.nama }}
            </option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="prd-filter-jenis">Jenis</label>
          <select
            id="prd-filter-jenis"
            v-model="filters.jenis"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua jenis</option>
            <option v-for="(lbl, key) in KATEGORI_TYPE_LABELS" :key="key" :value="key">
              {{ lbl }}
            </option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="prd-filter-kopi">Jenis Kopi</label>
          <select
            id="prd-filter-kopi"
            v-model="filters.jenis_kopi"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua kopi</option>
            <option v-for="(lbl, key) in COFFEE_TYPE_LABELS" :key="key" :value="key">
              {{ lbl }}
            </option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="prd-filter-aktif">Status</label>
          <select
            id="prd-filter-aktif"
            v-model="filters.aktif"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="semua">Semua status</option>
            <option value="ya">Aktif saja</option>
            <option value="tidak">Nonaktif saja</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="prd-filter-sort">Sort</label>
          <select
            id="prd-filter-sort"
            v-model="filters.sort"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="nama">Nama</option>
            <option value="sku">SKU</option>
            <option value="harga_beli">Harga beli</option>
            <option value="harga_jual">Harga jual</option>
            <option value="updated_at">Diperbarui</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="prd-filter-arah">Order</label>
          <select
            id="prd-filter-arah"
            v-model="filters.arah"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>
        <button type="submit" class="btn btn-secondary btn-sm">Filter</button>
      </div>
    </form>

    <LoadingState v-if="loading" :rows="6" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState
      v-else-if="!items.length"
      title="Produk tidak ditemukan"
      description="Tidak ada produk yang cocok dengan filter pencarian saat ini."
    >
      <button type="button" class="btn btn-secondary btn-sm" @click="resetFilters">
        Reset filter
      </button>
    </EmptyState>

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Nama &amp; Merek</th>
            <th>Kategori</th>
            <th>Spesifikasi</th>
            <th class="num">Harga Beli</th>
            <th class="num">Harga Jual</th>
            <th>Status</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td data-label="SKU" class="mono font-semibold">{{ row.sku }}</td>
            <td data-label="Nama & Merek">
              <div class="cell-primary">{{ row.nama }}</div>
              <div v-if="row.merek" class="cell-secondary">{{ row.merek }}</div>
            </td>
            <td data-label="Kategori">
              <div class="cell-primary">{{ row.kategori?.nama }}</div>
              <BadgeStatus :status="row.kategori?.jenis" />
            </td>
            <td data-label="Spesifikasi">
              <div class="sku-summary">
                <span class="badge badge-draf mono">{{ row.satuan }}</span>
                <span v-if="row.jenis_kopi" class="badge badge-proses">
                  {{ COFFEE_TYPE_LABELS[row.jenis_kopi] || row.jenis_kopi }}
                </span>
                <span v-if="row.tingkat_sangrai" class="badge badge-selesai">
                  {{ ROAST_LEVEL_LABELS[row.tingkat_sangrai] || row.tingkat_sangrai }}
                </span>
                <span v-if="row.berat_gram" class="badge badge-draf mono">
                  {{ row.berat_gram }} g
                </span>
              </div>
            </td>
            <td data-label="Harga Beli" class="num mono">{{ formatRupiah(row.harga_beli) }}</td>
            <td data-label="Harga Jual" class="num mono">{{ formatRupiah(row.harga_jual) }}</td>
            <td data-label="Status">
              <BadgeStatus :status="row.aktif ? 'aktif' : 'nonaktif'" />
            </td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button type="button" class="btn btn-secondary btn-sm" @click="openDetail(row)">
                  Detail
                </button>
                <button
                  v-if="auth.isAdmin"
                  type="button"
                  class="btn btn-secondary btn-sm"
                  @click="openEdit(row)"
                >
                  Ubah
                </button>
                <button
                  v-if="auth.isAdmin"
                  type="button"
                  class="btn btn-secondary btn-sm text-danger"
                  @click="openDelete(row)"
                >
                  Hapus
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <PaginationBar :meta="meta" @page="setPage" @per-page="setPerPage" />
    </div>

    <BaseModal
      :open="modalOpen"
      :title="editingId ? 'Ubah Produk' : 'Tambah Produk'"
      size="lg"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="produk-form" class="form-stack" novalidate @submit.prevent="onSave">
        <div class="form-row-2">
          <FormField id="prd-kategori" label="Kategori produk" :error="errors.kategori_id">
            <template #default="{ describedBy }">
              <select
                id="prd-kategori"
                :value="values.kategori_id"
                class="input"
                required
                :aria-invalid="Boolean(errors.kategori_id)"
                :aria-describedby="describedBy"
                @change="onKategoriChange($event.target.value)"
              >
                <option value="">Pilih kategori...</option>
                <option v-for="kat in kategoriList" :key="kat.id" :value="kat.id">
                  {{ kat.nama }} ({{ KATEGORI_TYPE_LABELS[kat.jenis] || kat.jenis }})
                </option>
              </select>
            </template>
          </FormField>

          <FormField
            id="prd-sku"
            label="Kode SKU"
            hint="Huruf kapital, angka dan tanda hubung (contoh: RB-ARA-GAYO-250)"
            :error="errors.sku"
          >
            <template #default="{ describedBy }">
              <input
                id="prd-sku"
                v-model.trim="values.sku"
                class="input mono"
                required
                :aria-invalid="Boolean(errors.sku)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <div class="form-row-2">
          <FormField id="prd-nama" label="Nama produk" :error="errors.nama">
            <template #default="{ describedBy }">
              <input
                id="prd-nama"
                v-model.trim="values.nama"
                class="input"
                required
                :aria-invalid="Boolean(errors.nama)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField id="prd-merek" label="Merek (opsional)" :error="errors.merek">
            <template #default="{ describedBy }">
              <input
                id="prd-merek"
                v-model.trim="values.merek"
                class="input"
                :aria-invalid="Boolean(errors.merek)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <div class="form-row-2">
          <FormField
            id="prd-satuan"
            label="Satuan"
            :hint="
              isGreenBean
                ? 'Green bean wajib memakai satuan kg'
                : isRoastedBean
                  ? 'Roasted bean wajib memakai satuan pack'
                  : ''
            "
            :error="errors.satuan"
          >
            <template #default="{ describedBy }">
              <select
                id="prd-satuan"
                v-model="values.satuan"
                class="input"
                :disabled="isGreenBean || isRoastedBean"
                :aria-invalid="Boolean(errors.satuan)"
                :aria-describedby="describedBy"
              >
                <option v-for="(lbl, key) in PRODUK_UNIT_LABELS" :key="key" :value="key">
                  {{ lbl }} ({{ key }})
                </option>
              </select>
            </template>
          </FormField>

          <FormField
            v-if="isCoffee"
            id="prd-jenis-kopi"
            label="Jenis kopi"
            :error="errors.jenis_kopi"
          >
            <template #default="{ describedBy }">
              <select
                id="prd-jenis-kopi"
                v-model="values.jenis_kopi"
                class="input"
                required
                :aria-invalid="Boolean(errors.jenis_kopi)"
                :aria-describedby="describedBy"
              >
                <option value="">Pilih jenis kopi...</option>
                <option v-for="(lbl, key) in COFFEE_TYPE_LABELS" :key="key" :value="key">
                  {{ lbl }}
                </option>
              </select>
            </template>
          </FormField>
        </div>

        <div v-if="isRoastedBean" class="form-row-2">
          <FormField id="prd-berat" label="Berat kemasan (gram)" :error="errors.berat_gram">
            <template #default="{ describedBy }">
              <select
                id="prd-berat"
                v-model.number="values.berat_gram"
                class="input mono"
                required
                :aria-invalid="Boolean(errors.berat_gram)"
                :aria-describedby="describedBy"
              >
                <option v-for="w in PRODUK_WEIGHTS" :key="w" :value="w">{{ w }} gram</option>
              </select>
            </template>
          </FormField>

          <FormField
            id="prd-sangrai"
            label="Tingkat sangrai (opsional)"
            :error="errors.tingkat_sangrai"
          >
            <template #default="{ describedBy }">
              <select
                id="prd-sangrai"
                v-model="values.tingkat_sangrai"
                class="input"
                :aria-invalid="Boolean(errors.tingkat_sangrai)"
                :aria-describedby="describedBy"
              >
                <option value="">Tanpa tingkat sangrai</option>
                <option v-for="(lbl, key) in ROAST_LEVEL_LABELS" :key="key" :value="key">
                  {{ lbl }}
                </option>
              </select>
            </template>
          </FormField>
        </div>

        <div class="form-row-2">
          <FormField
            id="prd-harga-beli"
            label="Harga beli standar (Rp)"
            hint="Diperbarui otomatis saat pembelian supplier diterima"
            :error="errors.harga_beli"
          >
            <template #default="{ describedBy }">
              <input
                id="prd-harga-beli"
                v-model.number="values.harga_beli"
                type="number"
                min="0"
                step="1"
                class="input mono"
                :aria-invalid="Boolean(errors.harga_beli)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField
            id="prd-harga-jual"
            label="Harga jual standar (Rp)"
            hint="Harga bawaan saat membuat dokumen penjualan"
            :error="errors.harga_jual"
          >
            <template #default="{ describedBy }">
              <input
                id="prd-harga-jual"
                v-model.number="values.harga_jual"
                type="number"
                min="0"
                step="1"
                class="input mono"
                :aria-invalid="Boolean(errors.harga_jual)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField id="prd-deskripsi" label="Deskripsi (opsional)" :error="errors.deskripsi">
          <template #default="{ describedBy }">
            <textarea
              id="prd-deskripsi"
              v-model.trim="values.deskripsi"
              class="input"
              rows="2"
              :aria-invalid="Boolean(errors.deskripsi)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <label class="checkbox-field">
          <input v-model="values.aktif" type="checkbox" />
          <span>Produk aktif di katalog</span>
        </label>
      </form>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="modalOpen = false">Batal</button>
        <button type="submit" form="produk-form" class="btn btn-primary" :disabled="submitting">
          {{ submitting ? 'Menyimpan...' : 'Simpan' }}
        </button>
      </template>
    </BaseModal>

    <BaseModal
      :open="detailOpen"
      :title="detailData ? `${detailData.sku} - ${detailData.nama}` : 'Detail Produk'"
      size="lg"
      @close="detailOpen = false"
    >
      <LoadingState v-if="detailLoading" :rows="4" />
      <div v-else-if="detailData" class="detail-grid">
        <div class="summary-strip">
          <div class="summary-item">
            <span class="detail-label">Total Stok Seluruh Lokasi</span>
            <strong class="detail-value mono">
              {{ formatNumber(detailData.total_stok) }} {{ detailData.satuan }}
            </strong>
          </div>
          <div class="summary-item">
            <span class="detail-label">Dalam Perjalanan</span>
            <strong class="detail-value mono">
              {{ formatNumber(detailData.dalam_perjalanan) }} {{ detailData.satuan }}
            </strong>
          </div>
          <div class="summary-item">
            <span class="detail-label">Total Nilai Stok</span>
            <strong class="detail-value mono">{{ formatRupiah(detailData.total_nilai) }}</strong>
          </div>
        </div>

        <dl class="detail-list">
          <div>
            <dt>Kategori</dt>
            <dd>
              {{ detailData.kategori?.nama }} ({{
                KATEGORI_TYPE_LABELS[detailData.kategori?.jenis]
              }})
            </dd>
          </div>
          <div>
            <dt>Merek</dt>
            <dd>{{ detailData.merek || '-' }}</dd>
          </div>
          <div v-if="detailData.jenis_kopi">
            <dt>Jenis Kopi</dt>
            <dd>{{ COFFEE_TYPE_LABELS[detailData.jenis_kopi] || detailData.jenis_kopi }}</dd>
          </div>
          <div v-if="detailData.tingkat_sangrai">
            <dt>Tingkat Sangrai</dt>
            <dd>{{ ROAST_LEVEL_LABELS[detailData.tingkat_sangrai] || detailData.tingkat_sangrai }}</dd>
          </div>
          <div v-if="detailData.berat_gram">
            <dt>Berat Kemasan</dt>
            <dd class="mono">{{ detailData.berat_gram }} gram</dd>
          </div>
          <div>
            <dt>Harga Beli / Jual</dt>
            <dd class="mono">
              {{ formatRupiah(detailData.harga_beli) }} / {{ formatRupiah(detailData.harga_jual) }}
            </dd>
          </div>
          <div v-if="detailData.deskripsi">
            <dt>Deskripsi</dt>
            <dd>{{ detailData.deskripsi }}</dd>
          </div>
        </dl>

        <h3 class="section-title">Sebaran Stok per Lokasi</h3>
        <EmptyState
          v-if="!detailData.stok?.length"
          title="Belum ada baris stok"
          description="Produk ini belum memiliki pencatatan stok di lokasi mana pun."
        />
        <div v-else class="table-card">
          <table class="data-table">
            <thead>
              <tr>
                <th>Lokasi</th>
                <th>Rak</th>
                <th class="num">Jumlah</th>
                <th class="num">Minimum</th>
                <th>Status</th>
                <th class="num">Nilai</th>
                <th class="col-actions">Aksi</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="st in detailData.stok" :key="st.lokasi.id">
                <td data-label="Lokasi">
                  <span class="mono font-semibold">{{ st.lokasi.kode }}</span> - {{ st.lokasi.nama }}
                </td>
                <td data-label="Rak" class="mono">{{ st.rak || '-' }}</td>
                <td data-label="Jumlah" class="num mono font-semibold">
                  {{ formatNumber(st.jumlah) }} {{ detailData.satuan }}
                </td>
                <td data-label="Minimum" class="num mono">
                  {{ formatNumber(st.stok_minimum) }} {{ detailData.satuan }}
                </td>
                <td data-label="Status">
                  <BadgeStatus :status="st.status_stok" />
                </td>
                <td data-label="Nilai" class="num mono">{{ formatRupiah(st.nilai) }}</td>
                <td data-label="Aksi" class="col-actions">
                  <button
                    type="button"
                    class="btn btn-secondary btn-sm"
                    @click="openKartuFromDetail(st.lokasi)"
                  >
                    Kartu stok
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="detailOpen = false">Tutup</button>
      </template>
    </BaseModal>

    <KartuStokModal
      :open="kartuOpen"
      :produk="detailData"
      :lokasi="kartuLokasi"
      @close="kartuOpen = false"
    />

    <ConfirmModal
      :open="Boolean(deletingRow)"
      title="Hapus Produk"
      :message="
        deletingRow
          ? `Hapus produk ${deletingRow.sku} - ${deletingRow.nama}? Produk yang sudah memiliki riwayat stok atau dokumen hanya dapat dinonaktifkan.`
          : ''
      "
      confirm-label="Hapus"
      :loading="deleteLoading"
      :error="deleteError"
      @close="deletingRow = null"
      @confirm="onConfirmDelete"
    />
  </section>
</template>
