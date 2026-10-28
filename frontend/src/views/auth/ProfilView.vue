<script setup>
import { computed, ref } from 'vue'

import AppIcon from '@/components/AppIcon'
import BadgeStatus from '@/components/BadgeStatus.vue'
import FormField from '@/components/FormField.vue'
import { useForm } from '@/composables/useForm'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { LOKASI_TYPE_LABELS, ROLE_LABELS } from '@/utils/constants'
import { formatDateTime } from '@/utils/format'

const auth = useAuthStore()
const toast = useToastStore()

const showCurrent = ref(false)
const showNew = ref(false)
const showConfirm = ref(false)

const { values, errors, message, submitting, submit, reset } = useForm({
  current_password: '',
  new_password: '',
  new_password_confirmation: '',
})

const lokasiText = computed(() => {
  const lokasi = auth.user?.lokasi
  if (lokasi) {
    const jenis = LOKASI_TYPE_LABELS[lokasi.jenis] || lokasi.jenis
    return `${lokasi.kode} · ${lokasi.nama} (${jenis})`
  }
  return auth.isAdmin ? 'Semua lokasi' : 'Tidak terikat lokasi'
})

async function onSubmit() {
  const ok = await submit(async (data) => {
    await auth.changePassword({
      current_password: data.current_password,
      new_password: data.new_password,
      new_password_confirmation: data.new_password_confirmation,
    })
  })
  if (ok) {
    reset()
    toast.success('Password berhasil diubah. Sesi perangkat lain telah dicabut.')
  }
}
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">Profil Akun</h1>
        <p class="page-subtitle">Informasi akun yang sedang aktif dan pengaturan password.</p>
      </div>
    </header>

    <div class="dash-grid-2">
      <article class="card">
        <div class="section-header-row">
          <div>
            <h2 class="section-title">Data Akun</h2>
            <p class="field-hint">Peran dan penempatan lokasi diatur oleh Admin</p>
          </div>
          <BadgeStatus v-if="auth.user?.status" :value="auth.user.status" />
        </div>

        <dl v-if="auth.user" class="detail-list">
          <div>
            <dt>Nama Lengkap</dt>
            <dd>{{ auth.user.name }}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{{ auth.user.email }}</dd>
          </div>
          <div>
            <dt>Peran</dt>
            <dd>{{ ROLE_LABELS[auth.user.role] || auth.user.role }}</dd>
          </div>
          <div>
            <dt>Lokasi Penugasan</dt>
            <dd>{{ lokasiText }}</dd>
          </div>
          <div>
            <dt>Login Terakhir</dt>
            <dd>{{ formatDateTime(auth.user.last_login_at) }}</dd>
          </div>
        </dl>
      </article>

      <article class="card">
        <div>
          <h2 class="section-title">Ubah Password</h2>
          <p class="field-hint">
            Mengubah password akan mencabut seluruh sesi login pada perangkat atau browser lain.
          </p>
        </div>

        <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>

        <form class="form-stack" novalidate @submit.prevent="onSubmit">
          <FormField
            id="current_password"
            label="Password Saat Ini"
            :error="errors.current_password"
          >
            <template #default="{ describedBy }">
              <div class="input-group">
                <input
                  id="current_password"
                  v-model="values.current_password"
                  class="input"
                  :type="showCurrent ? 'text' : 'password'"
                  autocomplete="current-password"
                  required
                  :aria-invalid="Boolean(errors.current_password)"
                  :aria-describedby="describedBy"
                />
                <button
                  type="button"
                  class="btn-icon input-addon"
                  :aria-pressed="showCurrent"
                  :aria-label="showCurrent ? 'Sembunyikan password saat ini' : 'Lihat password saat ini'"
                  @click="showCurrent = !showCurrent"
                >
                  <AppIcon :name="showCurrent ? 'eye-off' : 'eye'" :size="18" />
                </button>
              </div>
            </template>
          </FormField>

          <FormField
            id="new_password"
            label="Password Baru"
            hint="8 sampai 72 byte, wajib berisi huruf dan angka serta berbeda dari password lama"
            :error="errors.new_password"
          >
            <template #default="{ describedBy }">
              <div class="input-group">
                <input
                  id="new_password"
                  v-model="values.new_password"
                  class="input"
                  :type="showNew ? 'text' : 'password'"
                  autocomplete="new-password"
                  required
                  :aria-invalid="Boolean(errors.new_password)"
                  :aria-describedby="describedBy"
                />
                <button
                  type="button"
                  class="btn-icon input-addon"
                  :aria-pressed="showNew"
                  :aria-label="showNew ? 'Sembunyikan password baru' : 'Lihat password baru'"
                  @click="showNew = !showNew"
                >
                  <AppIcon :name="showNew ? 'eye-off' : 'eye'" :size="18" />
                </button>
              </div>
            </template>
          </FormField>

          <FormField
            id="new_password_confirmation"
            label="Konfirmasi Password Baru"
            :error="errors.new_password_confirmation"
          >
            <template #default="{ describedBy }">
              <div class="input-group">
                <input
                  id="new_password_confirmation"
                  v-model="values.new_password_confirmation"
                  class="input"
                  :type="showConfirm ? 'text' : 'password'"
                  autocomplete="new-password"
                  required
                  :aria-invalid="Boolean(errors.new_password_confirmation)"
                  :aria-describedby="describedBy"
                />
                <button
                  type="button"
                  class="btn-icon input-addon"
                  :aria-pressed="showConfirm"
                  :aria-label="showConfirm ? 'Sembunyikan konfirmasi password' : 'Lihat konfirmasi password'"
                  @click="showConfirm = !showConfirm"
                >
                  <AppIcon :name="showConfirm ? 'eye-off' : 'eye'" :size="18" />
                </button>
              </div>
            </template>
          </FormField>

          <div class="action-group">
            <button type="submit" class="btn btn-primary" :disabled="submitting">
              <AppIcon name="lock" :size="18" />
              <span>{{ submitting ? 'Menyimpan...' : 'Simpan password baru' }}</span>
            </button>
          </div>
        </form>
      </article>
    </div>
  </section>
</template>
