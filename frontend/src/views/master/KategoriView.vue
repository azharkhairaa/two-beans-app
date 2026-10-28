<script setup>
import { ref } from 'vue'

import AppIcon from '@/components/AppIcon'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FormField from '@/components/FormField.vue'
import LoadingState from '@/components/LoadingState.vue'
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { kategoriApi } from '@/services'
import { useToastStore } from '@/stores/toast'
import { KATEGORI_TYPE_LABELS } from '@/utils/constants'
import { formatDate, formatNumber } from '@/utils/format'

const toast = useToastStore()

const { items, loading, error, load } = useList(() => kategoriApi.list(), { paginated: false })

const modalOpen = ref(false)
const editingId = ref(null)

const { values, errors, message, submitting, submit, fill } = useForm({
  nama: '',
  jenis: 'roasted_bean',
  deskripsi: '',
})

function openCreate() {
  editingId.value = null
  fill({ nama: '', jenis: 'roasted_bean', deskripsi: '' })
  modalOpen.value = true
}

function openEdit(row) {
  editingId.value = row.id
  fill({
    nama: row.nama,
    jenis: row.jenis,
    deskripsi: row.deskripsi || '',
  })
  modalOpen.value = true
}

async function onSave() {
  const payload = {
    nama: values.nama,
    jenis: values.jenis,
    deskripsi: values.deskripsi || null,
  }
  const ok = await submit(() =>
    editingId.value ? kategoriApi.update(editingId.value, payload) : kategoriApi.create(payload)
  )
  if (ok) {
    toast.show(
      editingId.value ? 'Kategori berhasil diperbarui.' : 'Kategori baru berhasil ditambahkan.'
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
    await kategoriApi.remove(deletingRow.value.id)
    toast.show(`Kategori ${deletingRow.value.nama} dihapus.`)
    deletingRow.value = null
    await load()
  } catch (err) {
    deleteError.value = err?.message || 'Gagal menghapus kategori.'
  } finally {
    deleteLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Kategori Produk</h2>
        <p class="page-subtitle">Pengelompokan biji kopi, bahan baku, kemasan dan peralatan</p>
      </div>
      <button type="button" class="btn btn-primary" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Tambah kategori</span>
      </button>
    </header>

    <LoadingState v-if="loading" :rows="4" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState
      v-else-if="!items.length"
      title="Belum ada kategori"
      description="Tambahkan kategori produk untuk mengelompokkan katalog."
    >
      <button type="button" class="btn btn-primary" @click="openCreate">Tambah kategori</button>
    </EmptyState>

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nama Kategori</th>
            <th>Jenis</th>
            <th>Deskripsi</th>
            <th class="num">Jumlah Produk</th>
            <th>Diperbarui</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td data-label="Nama Kategori" class="font-semibold">{{ row.nama }}</td>
            <td data-label="Jenis">
              <span class="badge badge-draf">{{ KATEGORI_TYPE_LABELS[row.jenis] || row.jenis }}</span>
            </td>
            <td data-label="Deskripsi" class="cell-secondary">{{ row.deskripsi || '-' }}</td>
            <td data-label="Jumlah Produk" class="num mono">{{ formatNumber(row.jumlah_produk) }}</td>
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
    </div>

    <BaseModal
      :open="modalOpen"
      :title="editingId ? 'Ubah Kategori' : 'Tambah Kategori'"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="kategori-form" class="form-stack" novalidate @submit.prevent="onSave">
        <FormField id="kat-nama" label="Nama kategori" :error="errors.nama">
          <template #default="{ describedBy }">
            <input
              id="kat-nama"
              v-model.trim="values.nama"
              class="input"
              required
              :aria-invalid="Boolean(errors.nama)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <FormField id="kat-jenis" label="Jenis kategori" :error="errors.jenis">
          <template #default="{ describedBy }">
            <select
              id="kat-jenis"
              v-model="values.jenis"
              class="input"
              :aria-invalid="Boolean(errors.jenis)"
              :aria-describedby="describedBy"
            >
              <option v-for="(lbl, key) in KATEGORI_TYPE_LABELS" :key="key" :value="key">
                {{ lbl }}
              </option>
            </select>
          </template>
        </FormField>

        <FormField id="kat-deskripsi" label="Deskripsi (opsional)" :error="errors.deskripsi">
          <template #default="{ describedBy }">
            <textarea
              id="kat-deskripsi"
              v-model.trim="values.deskripsi"
              class="input"
              rows="2"
              :aria-invalid="Boolean(errors.deskripsi)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
      </form>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="modalOpen = false">Batal</button>
        <button type="submit" form="kategori-form" class="btn btn-primary" :disabled="submitting">
          {{ submitting ? 'Menyimpan...' : 'Simpan' }}
        </button>
      </template>
    </BaseModal>

    <ConfirmModal
      :open="Boolean(deletingRow)"
      title="Hapus Kategori"
      :message="
        deletingRow
          ? `Hapus kategori ${deletingRow.nama}? Kategori yang masih dipakai produk tidak dapat dihapus.`
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
