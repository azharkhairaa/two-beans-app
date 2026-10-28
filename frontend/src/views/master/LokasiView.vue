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
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { lokasiApi } from '@/services'
import { useToastStore } from '@/stores/toast'
import { LOKASI_TYPE_LABELS } from '@/utils/constants'
import { formatRupiah } from '@/utils/format'

const toast = useToastStore()

const { items, loading, error, filters, load, applyFilters } = useList(
  (params) => lokasiApi.list(params),
  { initialFilters: { aktif: 'semua' }, paginated: false }
)

const PREFIX_MAP = {
  gudang_utama: 'GU-',
  gudang_cabang: 'GC-',
  outlet: 'OT-',
}

const modalOpen = ref(false)
const editingId = ref(null)

const { values, errors, message, submitting, submit, fill } = useForm({
  jenis: 'gudang_utama',
  kode: 'GU-',
  nama: '',
  telepon: '',
  alamat: '',
  aktif: true,
})

function onJenisChange(nextJenis) {
  values.jenis = nextJenis
  const nextPrefix = PREFIX_MAP[nextJenis] || ''
  if (!editingId.value && (!values.kode || /^(GU|GC|OT)-?$/.test(values.kode))) {
    values.kode = nextPrefix
  }
}

function openCreate() {
  editingId.value = null
  fill({
    jenis: 'gudang_utama',
    kode: 'GU-',
    nama: '',
    telepon: '',
    alamat: '',
    aktif: true,
  })
  modalOpen.value = true
}

function openEdit(row) {
  editingId.value = row.id
  fill({
    jenis: row.jenis,
    kode: row.kode,
    nama: row.nama,
    telepon: row.telepon || '',
    alamat: row.alamat || '',
    aktif: Boolean(row.aktif),
  })
  modalOpen.value = true
}

async function onSave() {
  const payload = {
    jenis: values.jenis,
    kode: values.kode,
    nama: values.nama,
    telepon: values.telepon || null,
    alamat: values.alamat || null,
    aktif: Boolean(values.aktif),
  }
  const ok = await submit(() =>
    editingId.value ? lokasiApi.update(editingId.value, payload) : lokasiApi.create(payload)
  )
  if (ok) {
    toast.show(editingId.value ? 'Lokasi berhasil diperbarui.' : 'Lokasi baru berhasil ditambahkan.')
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
    await lokasiApi.remove(deletingRow.value.id)
    toast.show(`Lokasi ${deletingRow.value.nama} dihapus.`)
    deletingRow.value = null
    await load()
  } catch (err) {
    deleteError.value = err?.message || 'Gagal menghapus lokasi.'
  } finally {
    deleteLoading.value = false
  }
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Lokasi Operasional</h2>
        <p class="page-subtitle">Gudang utama, gudang cabang dan outlet Two Beans</p>
      </div>
      <button type="button" class="btn btn-primary" @click="openCreate">
        <AppIcon name="plus" :size="16" />
        <span>Tambah lokasi</span>
      </button>
    </header>

    <div class="toolbar">
      <div class="toolbar-group">
        <div class="toolbar-field">
          <label class="toolbar-label" for="filter-aktif">Status Lokasi</label>
          <select
            id="filter-aktif"
            v-model="filters.aktif"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="semua">Semua status</option>
            <option value="ya">Aktif saja</option>
            <option value="tidak">Nonaktif saja</option>
          </select>
        </div>
      </div>
    </div>

    <LoadingState v-if="loading" :rows="4" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState
      v-else-if="!items.length"
      title="Belum ada lokasi"
      description="Tambahkan lokasi gudang atau outlet untuk mulai mencatat stok."
    >
      <button type="button" class="btn btn-primary" @click="openCreate">Tambah lokasi</button>
    </EmptyState>

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Kode</th>
            <th>Nama &amp; Alamat</th>
            <th>Jenis</th>
            <th>Telepon</th>
            <th>Ringkasan SKU</th>
            <th class="num">Nilai Stok</th>
            <th>Status</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in items" :key="row.id">
            <td data-label="Kode" class="mono font-semibold">{{ row.kode }}</td>
            <td data-label="Nama & Alamat">
              <div class="cell-primary">{{ row.nama }}</div>
              <div v-if="row.alamat" class="cell-secondary">{{ row.alamat }}</div>
            </td>
            <td data-label="Jenis">{{ LOKASI_TYPE_LABELS[row.jenis] || row.jenis }}</td>
            <td data-label="Telepon" class="mono">{{ row.telepon || '-' }}</td>
            <td data-label="Ringkasan SKU">
              <div class="sku-summary">
                <span class="badge badge-aman">{{ row.ringkasan.sku_ada }} ada</span>
                <span v-if="row.ringkasan.menipis" class="badge badge-menunggu">
                  {{ row.ringkasan.menipis }} menipis
                </span>
                <span v-if="row.ringkasan.habis" class="badge badge-error">
                  {{ row.ringkasan.habis }} habis
                </span>
              </div>
            </td>
            <td data-label="Nilai Stok" class="num mono">{{ formatRupiah(row.ringkasan.nilai) }}</td>
            <td data-label="Status">
              <BadgeStatus :status="row.aktif ? 'aktif' : 'nonaktif'" />
            </td>
            <td data-label="Aksi" class="col-actions">
              <div class="action-group">
                <button
                  type="button"
                  class="btn btn-secondary btn-sm"
                  @click="openEdit(row)"
                >
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
      :title="editingId ? 'Ubah Lokasi' : 'Tambah Lokasi'"
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="lokasi-form" class="form-stack" novalidate @submit.prevent="onSave">
        <div class="form-row-2">
          <FormField id="lok-jenis" label="Jenis lokasi" :error="errors.jenis">
            <template #default="{ describedBy }">
              <select
                id="lok-jenis"
                :value="values.jenis"
                class="input"
                :aria-invalid="Boolean(errors.jenis)"
                :aria-describedby="describedBy"
                @change="onJenisChange($event.target.value)"
              >
                <option v-for="(lbl, key) in LOKASI_TYPE_LABELS" :key="key" :value="key">
                  {{ lbl }}
                </option>
              </select>
            </template>
          </FormField>

          <FormField
            id="lok-kode"
            label="Kode"
            hint="Diawali GU-, GC- atau OT-"
            :error="errors.kode"
          >
            <template #default="{ describedBy }">
              <input
                id="lok-kode"
                v-model.trim="values.kode"
                class="input mono"
                required
                :aria-invalid="Boolean(errors.kode)"
                :aria-describedby="describedBy"
              />
            </template>
          </FormField>
        </div>

        <FormField id="lok-nama" label="Nama lokasi" :error="errors.nama">
          <template #default="{ describedBy }">
            <input
              id="lok-nama"
              v-model.trim="values.nama"
              class="input"
              required
              :aria-invalid="Boolean(errors.nama)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <FormField id="lok-telepon" label="Telepon (opsional)" :error="errors.telepon">
          <template #default="{ describedBy }">
            <input
              id="lok-telepon"
              v-model.trim="values.telepon"
              class="input mono"
              :aria-invalid="Boolean(errors.telepon)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>

        <FormField id="lok-alamat" label="Alamat (opsional)" :error="errors.alamat">
          <template #default="{ describedBy }">
            <textarea
              id="lok-alamat"
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
          <span>Lokasi aktif beroperasi</span>
        </label>
      </form>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="modalOpen = false">Batal</button>
        <button type="submit" form="lokasi-form" class="btn btn-primary" :disabled="submitting">
          {{ submitting ? 'Menyimpan...' : 'Simpan' }}
        </button>
      </template>
    </BaseModal>

    <ConfirmModal
      :open="Boolean(deletingRow)"
      title="Hapus Lokasi"
      :message="
        deletingRow
          ? `Hapus lokasi ${deletingRow.kode} - ${deletingRow.nama}? Lokasi yang sudah memiliki riwayat stok atau dokumen hanya dapat dinonaktifkan.`
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
