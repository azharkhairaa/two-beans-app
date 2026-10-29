<script setup>
import { ref } from 'vue'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FormField from '@/components/FormField.vue'
import LoadingState from '@/components/LoadingState.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import { useDetail } from '@/composables/useDetail'
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { customerApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { CUSTOMER_TYPE_LABELS } from '@/utils/constants'
import { formatDate, formatRupiah } from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => customerApi.list(params),
  {
    initialFilters: {
      q: '',
      jenis: '',
      aktif: 'semua',
      sort: 'nama',
      arah: 'asc',
    },
  }
)

const modalOpen = ref(false)
const editingId = ref(null)

const { values, errors, message, submitting, submit, fill } = useForm({
  nama: '',
  jenis: 'kafe',
  kontak: '',
  telepon: '',
  email: '',
  alamat: '',
  aktif: true,
})

function openCreate() {
  editingId.value = null
  fill({
    nama: '',
    jenis: 'kafe',
    kontak: '',
    telepon: '',
    email: '',
    alamat: '',
    aktif: true,
  })
  modalOpen.value = true
}

function openEdit(row) {
  editingId.value = row.id
  fill({
    nama: row.nama,
    jenis: row.jenis,
    kontak: row.kontak || '',
    telepon: row.telepon || '',
    email: row.email || '',
    alamat: row.alamat || '',
    aktif: Boolean(row.aktif),
  })
  modalOpen.value = true
}

async function onSave() {
  const payload = {
    nama: values.nama,
    jenis: values.jenis,
    kontak: values.kontak || null,
    telepon: values.telepon || null,
    email: values.email || null,
    alamat: values.alamat || null,
    aktif: Boolean(values.aktif),
  }
  const ok = await submit(() =>
    editingId.value ? customerApi.update(editingId.value, payload) : customerApi.create(payload)
  )
  if (ok) {
    toast.show(
      editingId.value ? 'Customer berhasil diperbarui.' : 'Customer baru berhasil ditambahkan.'
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
} = useDetail((id) => customerApi.get(id), 'customer', { previewRow: true })

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
    await customerApi.remove(deletingRow.value.id)
    toast.show(`Customer ${deletingRow.value.nama} dihapus.`)
    deletingRow.value = null
    await load()
  } catch (err) {
    deleteError.value = err?.message || 'Gagal menghapus customer.'
  } finally {
    deleteLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Customer</h2>
        <p class="page-subtitle">Pelanggan retail, grosir dan mitra kafe Two Beans</p>
      </div>
      <button type="button" class="btn btn-post" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Tambah customer</span>
      </button>
    </header>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="cust-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="cust-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari nama, kontak atau email..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div class="toolbar-field">
          <label class="toolbar-label" for="cust-filter-jenis">Jenis Customer</label>
          <select
            id="cust-filter-jenis"
            v-model="filters.jenis"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua jenis</option>
            <option v-for="(lbl, key) in CUSTOMER_TYPE_LABELS" :key="key" :value="key">
              {{ lbl }}
            </option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="cust-filter-aktif">Status</label>
          <select
            id="cust-filter-aktif"
            v-model="filters.aktif"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="semua">Semua status</option>
            <option value="true">Aktif saja</option>
            <option value="false">Nonaktif saja</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="cust-filter-sort">Sort</label>
          <select
            id="cust-filter-sort"
            v-model="filters.sort"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="nama">Nama</option>
            <option value="updated_at">Terakhir diubah</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="cust-filter-arah">Order</label>
          <select
            id="cust-filter-arah"
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

    <LoadingState v-if="loading" :rows="5" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState
      v-else-if="!items.length"
      title="Customer tidak ditemukan"
      description="Belum ada customer yang cocok dengan filter pencarian."
    >
      <button type="button" class="btn btn-secondary btn-sm" @click="resetFilters">
        Reset filter
      </button>
    </EmptyState>

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nama &amp; Alamat</th>
            <th>Jenis</th>
            <th>Narahubung</th>
            <th>Telepon &amp; Email</th>
            <th>Status</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td data-label="Nama & Alamat">
              <div class="cell-primary">{{ row.nama }}</div>
              <div v-if="row.alamat" class="cell-secondary">{{ row.alamat }}</div>
            </td>
            <td data-label="Jenis">
              <BadgeStatus :status="row.jenis" />
            </td>
            <td data-label="Narahubung">{{ row.kontak || '-' }}</td>
            <td data-label="Telepon & Email">
              <div class="mono">{{ row.telepon || '-' }}</div>
              <div v-if="row.email" class="cell-secondary">{{ row.email }}</div>
            </td>
            <td data-label="Status">
              <BadgeStatus :status="row.aktif ? 'aktif' : 'nonaktif'" />
            </td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button type="button" class="btn btn-get-outline btn-sm" @click="openDetail(row)">
                  Detail
                </button>
                <button type="button" class="btn btn-put btn-sm" @click="openEdit(row)">
                  Ubah
                </button>
                <button
                  v-if="auth.isAdmin"
                  type="button"
                  class="btn btn-delete btn-sm"
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
      :title="editingId ? 'Ubah Customer' : 'Tambah Customer'"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="customer-form" class="form-stack" novalidate @submit.prevent="onSave">
        <div class="form-row-2">
          <FormField id="cust-nama" label="Nama customer" :error="errors.nama">
            <template #default="{ describedBy }">
              <input
                id="cust-nama"
                v-model.trim="values.nama"
                class="input"
                required
                :aria-invalid="Boolean(errors.nama)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField id="cust-jenis" label="Jenis customer" :error="errors.jenis">
            <template #default="{ describedBy }">
              <select
                id="cust-jenis"
                v-model="values.jenis"
                class="input"
                :aria-invalid="Boolean(errors.jenis)"
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
          <FormField id="cust-kontak" label="Narahubung (opsional)" :error="errors.kontak">
            <template #default="{ describedBy }">
              <input
                id="cust-kontak"
                v-model.trim="values.kontak"
                class="input"
                :aria-invalid="Boolean(errors.kontak)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField id="cust-telepon" label="Telepon (opsional)" :error="errors.telepon">
            <template #default="{ describedBy }">
              <input
                id="cust-telepon"
                v-model.trim="values.telepon"
                class="input mono"
                :aria-invalid="Boolean(errors.telepon)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField id="cust-email" label="Email (opsional)" :error="errors.email">
          <template #default="{ describedBy }">
            <input
              id="cust-email"
              v-model.trim="values.email"
              type="email"
              class="input"
              :aria-invalid="Boolean(errors.email)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <FormField id="cust-alamat" label="Alamat (opsional)" :error="errors.alamat">
          <template #default="{ describedBy }">
            <textarea
              id="cust-alamat"
              v-model.trim="values.alamat"
              class="input"
              rows="2"
              :aria-invalid="Boolean(errors.alamat)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <label class="checkbox-field">
          <input v-model="values.aktif" type="checkbox" />
          <span>Customer aktif</span>
        </label>
      </form>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="modalOpen = false">Batal</button>
        <button type="submit" form="customer-form" class="btn btn-post" :disabled="submitting">
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting ? 'Menyimpan...' : 'Simpan' }}</span>
        </button>
      </template>
    </BaseModal>

    <BaseModal
      :open="detailOpen"
      :title="detailData ? `Detail Customer: ${detailData.nama}` : 'Detail Customer'"
      @close="closeDetail"
    >
      <LoadingState v-if="detailLoading" :rows="3" />
      <div v-else-if="detailData" class="detail-grid">
        <div class="detail-highlight">
          <span class="detail-label">Total Pembelian 30 Hari Terakhir</span>
          <strong class="detail-value mono">
            {{ formatRupiah(detailData.total_pembelian_30_hari || 0) }}
          </strong>
        </div>
        <dl class="detail-list">
          <div>
            <dt>Jenis</dt>
            <dd>{{ CUSTOMER_TYPE_LABELS[detailData.jenis] || detailData.jenis }}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd><BadgeStatus :status="detailData.aktif ? 'aktif' : 'nonaktif'" /></dd>
          </div>
          <div>
            <dt>Narahubung</dt>
            <dd>{{ detailData.kontak || '-' }}</dd>
          </div>
          <div>
            <dt>Telepon</dt>
            <dd class="mono">{{ detailData.telepon || '-' }}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{{ detailData.email || '-' }}</dd>
          </div>
          <div>
            <dt>Alamat</dt>
            <dd>{{ detailData.alamat || '-' }}</dd>
          </div>
          <div>
            <dt>Terakhir diperbarui</dt>
            <dd>{{ formatDate(detailData.updated_at) }}</dd>
          </div>
        </dl>
      </div>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="closeDetail">Tutup</button>
      </template>
    </BaseModal>

    <ConfirmModal
      :open="Boolean(deletingRow)"
      title="Hapus Customer"
      :message="
        deletingRow
          ? `Hapus customer ${deletingRow.nama}? Customer yang sudah memiliki dokumen penjualan hanya dapat dinonaktifkan.`
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
