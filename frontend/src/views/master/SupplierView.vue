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
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { supplierApi } from '@/services'
import { useToastStore } from '@/stores/toast'
import { formatDate } from '@/utils/format'

const toast = useToastStore()

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => supplierApi.list(params),
  {
    initialFilters: {
      q: '',
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
    kontak: values.kontak || null,
    telepon: values.telepon || null,
    email: values.email || null,
    alamat: values.alamat || null,
    aktif: Boolean(values.aktif),
  }
  const ok = await submit(() =>
    editingId.value ? supplierApi.update(editingId.value, payload) : supplierApi.create(payload)
  )
  if (ok) {
    toast.show(
      editingId.value ? 'Supplier berhasil diperbarui.' : 'Supplier baru berhasil ditambahkan.'
    )
    modalOpen.value = false
    await load()
  }
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
    await supplierApi.remove(deletingRow.value.id)
    toast.show(`Supplier ${deletingRow.value.nama} dihapus.`)
    deletingRow.value = null
    await load()
  } catch (err) {
    deleteError.value = err?.message || 'Gagal menghapus supplier.'
  } finally {
    deleteLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Supplier</h2>
        <p class="page-subtitle">Mitra pemasok biji kopi, bahan baku, kemasan dan peralatan</p>
      </div>
      <button type="button" class="btn btn-primary" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Tambah supplier</span>
      </button>
    </header>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="sup-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="sup-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari nama, kontak atau email..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div class="toolbar-field">
          <label class="toolbar-label" for="sup-aktif">Status</label>
          <select
            id="sup-aktif"
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
          <label class="toolbar-label" for="sup-sort">Sort</label>
          <select
            id="sup-sort"
            v-model="filters.sort"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="nama">Nama</option>
            <option value="updated_at">Terakhir diubah</option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="sup-arah">Order</label>
          <select
            id="sup-arah"
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
      title="Supplier tidak ditemukan"
      description="Belum ada supplier yang cocok dengan filter pencarian."
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
            <th>Narahubung</th>
            <th>Telepon &amp; Email</th>
            <th>Status</th>
            <th>Diperbarui</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td data-label="Nama & Alamat">
              <div class="cell-primary">{{ row.nama }}</div>
              <div v-if="row.alamat" class="cell-secondary">{{ row.alamat }}</div>
            </td>
            <td data-label="Narahubung">{{ row.kontak || '-' }}</td>
            <td data-label="Telepon & Email">
              <div class="mono">{{ row.telepon || '-' }}</div>
              <div v-if="row.email" class="cell-secondary">{{ row.email }}</div>
            </td>
            <td data-label="Status">
              <BadgeStatus :status="row.aktif ? 'aktif' : 'nonaktif'" />
            </td>
            <td data-label="Diperbarui" class="cell-secondary">{{ formatDate(row.updated_at) }}</td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button type="button" class="btn btn-secondary btn-sm" @click="openEdit(row)">
                  Ubah
                </button>
                <button
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
      :title="editingId ? 'Ubah Supplier' : 'Tambah Supplier'"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="supplier-form" class="form-stack" novalidate @submit.prevent="onSave">
        <FormField id="sup-nama" label="Nama supplier" :error="errors.nama">
          <template #default="{ describedBy }">
            <input
              id="sup-nama"
              v-model.trim="values.nama"
              class="input"
              required
              :aria-invalid="Boolean(errors.nama)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <div class="form-row-2">
          <FormField id="sup-kontak" label="Narahubung (opsional)" :error="errors.kontak">
            <template #default="{ describedBy }">
              <input
                id="sup-kontak"
                v-model.trim="values.kontak"
                class="input"
                :aria-invalid="Boolean(errors.kontak)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>

          <FormField id="sup-telepon" label="Telepon (opsional)" :error="errors.telepon">
            <template #default="{ describedBy }">
              <input
                id="sup-telepon"
                v-model.trim="values.telepon"
                class="input mono"
                :aria-invalid="Boolean(errors.telepon)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField id="sup-email" label="Email (opsional)" :error="errors.email">
          <template #default="{ describedBy }">
            <input
              id="sup-email"
              v-model.trim="values.email"
              type="email"
              class="input"
              :aria-invalid="Boolean(errors.email)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <FormField id="sup-alamat" label="Alamat (opsional)" :error="errors.alamat">
          <template #default="{ describedBy }">
            <textarea
              id="sup-alamat"
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
          <span>Supplier aktif</span>
        </label>
      </form>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="modalOpen = false">Batal</button>
        <button type="submit" form="supplier-form" class="btn btn-primary" :disabled="submitting">
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting ? 'Menyimpan...' : 'Simpan' }}</span>
        </button>
      </template>
    </BaseModal>

    <ConfirmModal
      :open="Boolean(deletingRow)"
      title="Hapus Supplier"
      :message="
        deletingRow
          ? `Hapus supplier ${deletingRow.nama}? Supplier yang sudah memiliki dokumen pembelian hanya dapat dinonaktifkan.`
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
