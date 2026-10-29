<script setup>
import { computed, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import BaseModal from '@/components/BaseModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FormField from '@/components/FormField.vue'
import KartuStokModal from '@/components/KartuStokModal.vue'
import LoadingState from '@/components/LoadingState.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { useKategoriOptions, useLokasiOptions } from '@/composables/useOptions'
import { produkApi, stokApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { KATEGORI_TYPE_LABELS, STOK_STATUS_LABELS } from '@/utils/constants'
import { formatDate, formatNumber, formatRupiah } from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()

const { items: lokasiList, load: loadLokasi } = useLokasiOptions()
const { items: kategoriList, load: loadKategori } = useKategoriOptions()
const currentLokasi = ref(auth.user?.lokasi || null)

onMounted(() => Promise.all([loadLokasi(), loadKategori()]))

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  async (params) => {
    const res = await stokApi.list(params)
    if (res?.lokasi) {
      currentLokasi.value = res.lokasi
      if (!filters.lokasi_id) {
        filters.lokasi_id = res.lokasi.id
      }
    }
    return res
  },
  {
    initialFilters: {
      lokasi_id: auth.user?.lokasi?.id || '',
      q: '',
      kategori_id: '',
      jenis: '',
      status_stok: '',
      sort: 'nama',
      arah: 'asc',
    },
  }
)

const canManageCurrentLokasi = computed(() => {
  if (auth.isAdmin) return true
  if (!currentLokasi.value || !auth.user?.lokasi) return false
  return Number(currentLokasi.value.id) === Number(auth.user.lokasi.id)
})

const settingModalOpen = ref(false)
const isNewProductSetting = ref(false)
const targetProduk = ref(null)
const produkOptions = ref([])

const { values, errors, message, submitting, submit, fill } = useForm({
  produk_id: '',
  stok_minimum: 0,
  rak: '',
})

async function openNewSetting() {
  isNewProductSetting.value = true
  targetProduk.value = null
  if (!produkOptions.value.length) {
    try {
      produkOptions.value = await produkApi.options()
    } catch {
      produkOptions.value = []
    }
  }
  fill({
    produk_id: produkOptions.value[0]?.id || '',
    stok_minimum: 5,
    rak: '',
  })
  settingModalOpen.value = true
}

function openEditSetting(row) {
  isNewProductSetting.value = false
  targetProduk.value = row.produk
  fill({
    produk_id: row.produk.id,
    stok_minimum: row.stok_minimum ?? 0,
    rak: row.rak || '',
  })
  settingModalOpen.value = true
}

async function onSaveSetting() {
  const lokasiId = currentLokasi.value?.id || filters.lokasi_id
  const produkId = isNewProductSetting.value ? Number(values.produk_id) : targetProduk.value?.id
  if (!lokasiId || !produkId) return
  const payload = {
    stok_minimum: Number(values.stok_minimum) || 0,
    rak: values.rak ? values.rak.toUpperCase() : null,
  }
  const ok = await submit(() => stokApi.updateSetting(lokasiId, produkId, payload))
  if (ok) {
    toast.show('Pengaturan stok minimum dan rak berhasil disimpan.')
    settingModalOpen.value = false
    await load()
  }
}

const kartuOpen = ref(false)
const kartuProduk = ref(null)

function openKartu(row) {
  kartuProduk.value = row.produk
  kartuOpen.value = true
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">
          Stock Lokasi
          <template v-if="currentLokasi">
            : {{ currentLokasi.kode }} - {{ currentLokasi.nama }}
          </template>
        </h2>
        <p class="page-subtitle">
          Pemantauan buku besar stock, batas minimum, posisi rak dan Stock Card per produk
        </p>
      </div>
      <button
        v-if="canManageCurrentLokasi"
        type="button"
        class="btn btn-put"
        @click="openNewSetting"
      >
        <AppIcon name="plus" :size="16" />
        <span>Atur batas &amp; rak produk</span>
      </button>
    </header>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="stk-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="stk-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari SKU atau nama produk..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div class="toolbar-field toolbar-field-lokasi">
          <label class="toolbar-label" for="stk-filter-lokasi">Lokasi</label>
          <SearchSelect
            id="stk-filter-lokasi"
            v-model="filters.lokasi_id"
            :options="lokasiList.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama}` }))"
            small
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="stk-filter-kategori">Kategori</label>
          <SearchSelect
            id="stk-filter-kategori"
            v-model="filters.kategori_id"
            :options="kategoriList.map((kat) => ({ value: kat.id, label: `${kat.nama}` }))"
            empty-label="Semua kategori"
            small
            @change="applyFilters()"
          />
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="stk-filter-jenis">Jenis</label>
          <select
            id="stk-filter-jenis"
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
          <label class="toolbar-label" for="stk-filter-status">Status Stock</label>
          <select
            id="stk-filter-status"
            v-model="filters.status_stok"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua status</option>
            <option v-for="(lbl, key) in STOK_STATUS_LABELS" :key="key" :value="key">
              {{ lbl }}
            </option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="stk-filter-sort">Sort</label>
          <select
            id="stk-filter-sort"
            v-model="filters.sort"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="nama">Nama produk</option>
            <option value="jumlah">Jumlah stock</option>
            <option value="nilai">Nilai stock</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="stk-filter-arah">Order</label>
          <select
            id="stk-filter-arah"
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
      title="Data stok tidak ditemukan"
      description="Belum ada baris stok yang cocok dengan filter di lokasi ini."
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
            <th>Produk &amp; Kategori</th>
            <th>Rak</th>
            <th class="num">Jumlah</th>
            <th class="num">Minimum</th>
            <th>Status</th>
            <th class="num">Nilai Stock</th>
            <th>Diperbarui</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.produk.id">
            <td data-label="SKU" class="mono font-semibold">{{ row.produk.sku }}</td>
            <td data-label="Produk & Kategori">
              <div class="cell-primary">{{ row.produk.nama }}</div>
              <div class="cell-secondary">
                {{ row.produk.kategori }} ({{ KATEGORI_TYPE_LABELS[row.produk.jenis] }})
              </div>
            </td>
            <td data-label="Rak" class="mono">{{ row.rak || '-' }}</td>
            <td data-label="Jumlah" class="num mono font-semibold">
              <span :class="{ 'text-bahaya': row.jumlah === 0, 'text-menunggu': row.jumlah > 0 && row.jumlah <= row.stok_minimum }">
                {{ formatNumber(row.jumlah) }} {{ row.produk.satuan }}
              </span>
            </td>
            <td data-label="Minimum" class="num mono">
              {{ formatNumber(row.stok_minimum) }} {{ row.produk.satuan }}
            </td>
            <td data-label="Status">
              <BadgeStatus :status="row.status_stok" />
            </td>
            <td data-label="Nilai Stock" class="num mono">{{ formatRupiah(row.nilai) }}</td>
            <td data-label="Diperbarui" class="cell-secondary">{{ formatDate(row.updated_at) }}</td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button type="button" class="btn btn-get btn-sm" @click="openKartu(row)">
                  Stock Card
                </button>
                <button
                  v-if="canManageCurrentLokasi"
                  type="button"
                  class="btn btn-put btn-sm"
                  @click="openEditSetting(row)"
                >
                  Atur
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <PaginationBar :meta="meta" @page="setPage" @per-page="setPerPage" />
    </div>

    <BaseModal
      :open="settingModalOpen"
      :title="
        isNewProductSetting
          ? `Atur Produk di ${currentLokasi?.kode || 'Lokasi'}`
          : `Atur Batas & Rak: ${targetProduk?.sku || ''}`
      "
      size="sm"
      @close="settingModalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="stok-setting-form" class="form-stack" novalidate @submit.prevent="onSaveSetting">
        <FormField
          v-if="isNewProductSetting"
          id="stk-produk"
          label="Pilih produk"
          :error="errors.produk_id"
        >
          <template #default="{ describedBy }">
            <SearchSelect
              id="stk-produk"
              v-model="values.produk_id"
              :options="produkOptions.map((prd) => ({ value: prd.id, label: `${prd.sku} - ${prd.nama} (${prd.satuan})` }))"
              required
              :invalid="Boolean(errors.produk_id)"
              :described-by="describedBy"
            />
          </template>
        </FormField>
        <div v-else-if="targetProduk" class="detail-highlight">
          <div>
            <span class="detail-label">{{ targetProduk.sku }}</span>
            <div class="font-semibold">{{ targetProduk.nama }}</div>
          </div>
          <span class="badge badge-draf mono">{{ targetProduk.satuan }}</span>
        </div>

        <FormField
          id="stk-min"
          label="Batas stock minimum"
          hint="Stock berstatus Menipis bila jumlah berada pada atau di bawah angka ini"
          :error="errors.stok_minimum"
        >
          <template #default="{ describedBy }">
            <input
              id="stk-min"
              v-model.number="values.stok_minimum"
              type="number"
              min="0"
              max="100000"
              step="1"
              class="input mono"
              required
              :aria-invalid="Boolean(errors.stok_minimum)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <FormField
          id="stk-rak"
          label="Kode rak penyimpanan (opsional)"
          hint="Huruf kapital, angka atau tanda hubung (contoh: A-01, GB-02)"
          :error="errors.rak"
        >
          <template #default="{ describedBy }">
            <input
              id="stk-rak"
              v-model.trim="values.rak"
              class="input mono"
              :aria-invalid="Boolean(errors.rak)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </form>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="settingModalOpen = false">
          Batal
        </button>
        <button
          type="submit"
          form="stok-setting-form"
          class="btn btn-post"
          :disabled="submitting"
        >
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting ? 'Menyimpan...' : 'Simpan' }}</span>
        </button>
      </template>
    </BaseModal>

    <KartuStokModal
      :open="kartuOpen"
      :produk="kartuProduk"
      :lokasi="currentLokasi"
      @close="kartuOpen = false"
    />
  </section>
</template>
