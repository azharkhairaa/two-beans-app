<script setup>
import { ref } from 'vue'

import FormField from '@/components/FormField.vue'
import { useForm } from '@/composables/useForm'
import AuthLayout from '@/layouts/AuthLayout.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const { values, errors, message, submitting, submit, reset } = useForm({
  name: '',
  email: '',
  password: '',
  password_confirmation: '',
})
const done = ref('')

async function onSubmit() {
  const ok = await submit(async (data) => {
    done.value = (await auth.register({ ...data })).pesan
  })
  if (ok) reset()
}
</script>

<template>
  <AuthLayout title="Registrasi akun">
    <template v-if="done">
      <p class="alert alert-success" role="status">{{ done }}</p>
      <RouterLink :to="{ name: 'login' }" class="btn btn-primary btn-block">Ke halaman login</RouterLink>
    </template>
    <template v-else>
      <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
      <form class="form-stack" novalidate @submit.prevent="onSubmit">
        <FormField id="name" label="Nama" :error="errors.name">
          <template #default="{ describedBy }">
            <input
              id="name"
              v-model.trim="values.name"
              class="input"
              autocomplete="name"
              required
              :aria-invalid="Boolean(errors.name)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
        <FormField id="email" label="Email" :error="errors.email">
          <template #default="{ describedBy }">
            <input
              id="email"
              v-model.trim="values.email"
              class="input"
              type="email"
              autocomplete="email"
              required
              :aria-invalid="Boolean(errors.email)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
        <FormField
          id="password"
          label="Password"
          hint="8 sampai 72 byte, berisi huruf dan angka"
          :error="errors.password"
        >
          <template #default="{ describedBy }">
            <input
              id="password"
              v-model="values.password"
              class="input"
              type="password"
              autocomplete="new-password"
              required
              :aria-invalid="Boolean(errors.password)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
        <FormField id="password_confirmation" label="Konfirmasi password" :error="errors.password_confirmation">
          <template #default="{ describedBy }">
            <input
              id="password_confirmation"
              v-model="values.password_confirmation"
              class="input"
              type="password"
              autocomplete="new-password"
              required
              :aria-invalid="Boolean(errors.password_confirmation)"
              :aria-describedby="describedBy"
            />
          </template>
        </FormField>
        <p class="form-note">Akun bisa dipakai setelah admin menetapkan peran dan lokasi.</p>
        <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
          <span v-if="submitting" class="btn-spinner" aria-hidden="true"></span>
          <span>{{ submitting ? 'Mengirim...' : 'Registrasi' }}</span>
        </button>
      </form>
    </template>
    <p class="auth-footer">Sudah punya akun? <RouterLink :to="{ name: 'login' }">Login</RouterLink></p>
  </AuthLayout>
</template>
