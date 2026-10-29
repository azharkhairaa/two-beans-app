<script setup>
import { computed, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import BaseModal from '@/components/BaseModal.vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import EmptyState from '@/components/EmptyState.vue'
import ErrorState from '@/components/ErrorState.vue'
import FormField from '@/components/FormField.vue'
import LoadingState from '@/components/LoadingState.vue'
import PaginationBar from '@/components/PaginationBar.vue'
import SearchSelect from '@/components/SearchSelect.vue'
import { useForm } from '@/composables/useForm'
import { useList } from '@/composables/useList'
import { useLokasiOptions } from '@/composables/useOptions'
import { userApi } from '@/services'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { LOKASI_TYPE_LABELS, ROLE_LABELS, USER_STATUS_LABELS } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()

const { items: lokasiList, load: loadLokasi } = useLokasiOptions()

onMounted(loadLokasi)

const { items, meta, loading, error, filters, load, setPage, setPerPage, applyFilters, resetFilters } = useList(
  (params) => userApi.list(params),
  {
    initialFilters: {
      q: '',
      status: '',
      role: '',
      lokasi_id: '',
    },
  }
)

const modalOpen = ref(false)
const targetUser = ref(null)
const isApprovalMode = ref(false)

const { values, errors, message, submitting, submit, fill } = useForm({
  role: 'manager_outlet',
  lokasi_id: '',
  status: 'aktif',
})

const requiresLokasi = computed(
  () => values.role === 'manager_gudang' || values.role === 'manager_outlet'
)

const matchingLokasi = computed(() => {
  if (values.role === 'manager_gudang') {
    return lokasiList.value.filter(
      (lok) => lok.jenis === 'gudang_utama' || lok.jenis === 'gudang_cabang'
    )
  }
  if (values.role === 'manager_outlet') {
    return lokasiList.value.filter((lok) => lok.jenis === 'outlet')
  }
  return []
})

function onRoleChange(nextRole) {
  values.role = nextRole
  if (nextRole === 'manager_gudang' || nextRole === 'manager_outlet') {
    const validIds = new Set(matchingLokasi.value.map((l) => Number(l.id)))
    if (!validIds.has(Number(values.lokasi_id))) {
      values.lokasi_id = matchingLokasi.value[0]?.id || ''
    }
  } else {
    values.lokasi_id = ''
  }
}

function openApprove(row) {
  targetUser.value = row
  isApprovalMode.value = true
  const defaultOutlet = lokasiList.value.find((l) => l.jenis === 'outlet')
  fill({
    role: 'manager_outlet',
    lokasi_id: defaultOutlet ? defaultOutlet.id : '',
    status: 'aktif',
  })
  modalOpen.value = true
}

function openEditRole(row) {
  targetUser.value = row
  isApprovalMode.value = false
  fill({
    role: row.role || 'manager_outlet',
    lokasi_id: row.lokasi?.id || '',
    status: row.status === 'menunggu' ? 'aktif' : row.status,
  })
  modalOpen.value = true
}

async function onSaveRole() {
  if (!targetUser.value) return
  const payload = {
    role: values.role,
    lokasi_id: requiresLokasi.value && values.lokasi_id ? Number(values.lokasi_id) : null,
    status: isApprovalMode.value ? 'aktif' : values.status,
  }
  const ok = await submit(() => userApi.patch(targetUser.value.id, payload))
  if (ok) {
    toast.show(
      isApprovalMode.value
        ? `Akun ${targetUser.value.name} disetujui dan diaktifkan.`
        : `Peran dan lokasi ${targetUser.value.name} diperbarui.`
    )
    modalOpen.value = false
    await load()
  }
}

const confirmAction = ref(null)
const confirmLoading = ref(false)
const confirmError = ref('')

function openToggleStatus(row) {
  const nextStatus = row.status === 'aktif' ? 'nonaktif' : 'aktif'
  confirmAction.value = {
    type: 'status',
    user: row,
    nextStatus,
    title: nextStatus === 'nonaktif' ? 'Nonaktifkan Akun' : 'Aktifkan Kembali Akun',
    message:
      nextStatus === 'nonaktif'
        ? `Nonaktifkan akun ${row.name} (${row.email})? Seluruh sesi login aktif pengguna ini akan langsung diakhiri.`
        : `Aktifkan kembali akun ${row.name} (${row.email})?`,
    confirmLabel: nextStatus === 'nonaktif' ? 'Nonaktifkan' : 'Aktifkan',
    variant: nextStatus === 'nonaktif' ? 'danger' : 'primary',
  }
  confirmError.value = ''
}

function openDelete(row, isReject = false) {
  confirmAction.value = {
    type: 'delete',
    user: row,
    title: isReject ? 'Tolak Registrasi Akun' : 'Hapus Akun Pengguna',
    message: isReject
      ? `Tolak dan hapus registrasi akun ${row.name} (${row.email})?`
      : `Hapus akun ${row.name} (${row.email})? Akun yang sudah pernah membuat dokumen hanya dapat dinonaktifkan.`,
    confirmLabel: isReject ? 'Tolak & Hapus' : 'Hapus',
    variant: 'danger',
  }
  confirmError.value = ''
}

async function onConfirmExecute() {
  if (!confirmAction.value) return
  const { type, user, nextStatus } = confirmAction.value
  confirmLoading.value = true
  confirmError.value = ''
  try {
    if (type === 'status') {
      await userApi.patch(user.id, { status: nextStatus })
      toast.show(`Status akun ${user.name} diubah menjadi ${nextStatus}.`)
    } else {
      await userApi.remove(user.id)
      toast.show(`Akun ${user.name} dihapus.`)
    }
    confirmAction.value = null
    await load()
  } catch (err) {
    confirmError.value = err?.message || 'Gagal memproses perubahan akun.'
  } finally {
    confirmLoading.value = false
  }
}

function isSelf(row) {
  return Number(row.id) === Number(auth.user?.id)
}
</script>

<template>
  <section class="page-section">
    <header class="page-header">
      <div>
        <h2 class="page-heading">Manajemen User</h2>
        <p class="page-subtitle">Persetujuan registrasi akun baru, pengaturan peran dan penempatan lokasi</p>
      </div>
    </header>

    <form class="toolbar" @submit.prevent="applyFilters()">
      <div class="toolbar-search">
        <label class="toolbar-label" for="usr-search">Pencarian</label>
        <div class="toolbar-search-box">
          <AppIcon name="search" :size="16" class="toolbar-search-icon" />
          <input
            id="usr-search"
            v-model.trim="filters.q"
            type="search"
            class="input input-sm"
            placeholder="Cari nama atau email..."
          />
        </div>
      </div>
      <div class="toolbar-group">
        <div class="toolbar-field">
          <label class="toolbar-label" for="usr-filter-status">Status Akun</label>
          <select
            id="usr-filter-status"
            v-model="filters.status"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua status</option>
            <option v-for="(lbl, key) in USER_STATUS_LABELS" :key="key" :value="key">
              {{ lbl }}
            </option>
          </select>
        </div>
        <div class="toolbar-field">
          <label class="toolbar-label" for="usr-filter-role">Peran</label>
          <select
            id="usr-filter-role"
            v-model="filters.role"
            class="input input-sm"
            @change="applyFilters()"
          >
            <option value="">Semua peran</option>
            <option v-for="(lbl, key) in ROLE_LABELS" :key="key" :value="key">
              {{ lbl }}
            </option>
          </select>
        </div>
        <div class="toolbar-field toolbar-field-lokasi">
          <label class="toolbar-label" for="usr-filter-lokasi">Lokasi Tugas</label>
          <SearchSelect
            id="usr-filter-lokasi"
            v-model="filters.lokasi_id"
            :options="lokasiList.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama}` }))"
            empty-label="Semua lokasi"
            small
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
      title="User tidak ditemukan"
      description="Tidak ada akun pengguna yang sesuai dengan filter saat ini."
    >
      <button type="button" class="btn btn-secondary btn-sm" @click="resetFilters">
        Reset filter
      </button>
    </EmptyState>

    <div v-else class="table-card">
      <table class="data-table">
        <thead>
          <tr>
            <th>Nama &amp; Email</th>
            <th>Peran</th>
            <th>Lokasi Tugas</th>
            <th>Status</th>
            <th>Login Terakhir</th>
            <th class="col-actions">Aksi</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in items"
            :key="row.id"
            :class="{ 'row-highlight': row.status === 'menunggu' }"
          >
            <td data-label="Nama & Email">
              <div class="cell-primary">
                {{ row.name }}
                <span v-if="isSelf(row)" class="badge badge-draf">Anda</span>
              </div>
              <div class="cell-secondary">{{ row.email }}</div>
            </td>
            <td data-label="Peran">
              <span v-if="row.role">{{ ROLE_LABELS[row.role] || row.role }}</span>
              <span v-else class="cell-secondary">Belum ditetapkan</span>
            </td>
            <td data-label="Lokasi Tugas">
              <template v-if="row.lokasi">
                <span class="mono font-semibold">{{ row.lokasi.kode }}</span>
                <span class="cell-secondary"> - {{ row.lokasi.nama }}</span>
              </template>
              <span v-else class="cell-secondary">Lintas lokasi</span>
            </td>
            <td data-label="Status">
              <BadgeStatus :status="row.status" />
            </td>
            <td data-label="Login Terakhir" class="cell-secondary">
              {{ formatDateTime(row.last_login_at) }}
            </td>
            <td data-label="Aksi" class="col-actions">
              <div v-if="row.status === 'menunggu'" class="action-group">
                <button type="button" class="btn btn-post btn-sm" @click="openApprove(row)">
                  Setujui
                </button>
                <button
                  type="button"
                  class="btn btn-delete btn-sm"
                  @click="openDelete(row, true)"
                >
                  Tolak
                </button>
              </div>
              <div v-else class="action-group">
                <button
                  type="button"
                  class="btn btn-put btn-sm"
                  :disabled="isSelf(row)"
                  @click="openEditRole(row)"
                >
                  Ubah peran
                </button>
                <button
                  type="button"
                  class="btn btn-put btn-sm"
                  :disabled="isSelf(row)"
                  @click="openToggleStatus(row)"
                >
                  {{ row.status === 'aktif' ? 'Nonaktifkan' : 'Aktifkan' }}
                </button>
                <button
                  type="button"
                  class="btn btn-delete btn-sm"
                  :disabled="isSelf(row)"
                  @click="openDelete(row, false)"
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
      :title="
        isApprovalMode
          ? `Setujui Akun: ${targetUser?.name || ''}`
          : `Ubah Peran & Lokasi: ${targetUser?.name || ''}`
      "
      @close="modalOpen = false"
    >
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form id="user-role-form" class="form-stack" novalidate @submit.prevent="onSaveRole">
        <FormField id="usr-role" label="Peran pengguna" :error="errors.role">
          <template #default="{ describedBy }">
            <select
              id="usr-role"
              :value="values.role"
              class="input"
              :aria-invalid="Boolean(errors.role)"
              :aria-describedby="describedBy"
              @change="onRoleChange($event.target.value)"
            >
              <option v-for="(lbl, key) in ROLE_LABELS" :key="key" :value="key">
                {{ lbl }}
              </option>
            </select>
          </template>
        </FormField>

        <FormField
          v-if="requiresLokasi"
          id="usr-lokasi"
          label="Lokasi penempatan"
          :hint="
            values.role === 'manager_gudang'
              ? 'Manager Gudang ditempatkan di Gudang Utama atau Gudang Cabang'
              : 'Manager Outlet ditempatkan di lokasi bertipe Outlet'
          "
          :error="errors.lokasi_id"
        >
          <template #default="{ describedBy }">
            <SearchSelect
              id="usr-lokasi"
              v-model="values.lokasi_id"
              :options="matchingLokasi.map((lok) => ({ value: lok.id, label: `${lok.kode} - ${lok.nama} (${LOKASI_TYPE_LABELS[lok.jenis]})` }))"
              placeholder="Pilih lokasi..."
              required
              :invalid="Boolean(errors.lokasi_id)"
              :described-by="describedBy"
            />
          </template>
        </FormField>

        <p v-else class="form-note">
          Peran {{ ROLE_LABELS[values.role] }} bekerja lintas lokasi dan tidak terikat ke satu lokasi tertentu.
        </p>

        <FormField
          v-if="!isApprovalMode"
          id="usr-status"
          label="Status akun"
          :error="errors.status"
        >
          <template #default="{ describedBy }">
            <select
              id="usr-status"
              v-model="values.status"
              class="input"
              :aria-invalid="Boolean(errors.status)"
              :aria-describedby="describedBy"
            >
              <option value="aktif">Aktif</option>
              <option value="nonaktif">Nonaktif</option>
            </select>
          </template>
        </FormField>
      </form>
      <template #footer>
        <button type="button" class="btn btn-secondary" @click="modalOpen = false">Batal</button>
        <button type="submit" form="user-role-form" class="btn btn-post" :disabled="submitting">
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting ? 'Menyimpan...' : isApprovalMode ? 'Setujui & Aktifkan' : 'Simpan' }}</span>
        </button>
      </template>
    </BaseModal>

    <ConfirmModal
      :open="Boolean(confirmAction)"
      :title="confirmAction?.title || 'Konfirmasi'"
      :message="confirmAction?.message || ''"
      :confirm-label="confirmAction?.confirmLabel || 'Lanjutkan'"
      :variant="confirmAction?.variant || 'danger'"
      :loading="confirmLoading"
      :error="confirmError"
      @close="confirmAction = null"
      @confirm="onConfirmExecute"
    />
  </section>
</template>
