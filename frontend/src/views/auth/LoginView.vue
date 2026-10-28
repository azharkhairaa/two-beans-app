<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon'
import FormField from '@/components/FormField.vue'
import { useForm } from '@/composables/useForm'
import AuthLayout from '@/layouts/AuthLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { RouteAccess } from '@/utils/RouteAccess'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { values, errors, message, submitting, submit } = useForm({ email: '', password: '' })
const showPassword = ref(false)

async function onSubmit() {
  const ok = await submit((data) => auth.login(data.email, data.password))
  if (ok) router.replace(RouteAccess.safeRedirect(route.query.redirect))
}
</script>

<template>
  <AuthLayout title="Masuk">
    <p v-if="auth.sessionEnded" class="alert alert-info">Sesi berakhir, silakan login lagi.</p>
    <p v-if="message" class="alert alert-error" role="alert">{{ message }}</p>
    <form class="form-stack" novalidate @submit.prevent="onSubmit">
      <FormField id="email" label="Email" :error="errors.email">
        <template #default="{ describedBy }">
          <input
            id="email"
            v-model.trim="values.email"
            class="input"
            type="email"
            autocomplete="username"
            required
            :aria-invalid="Boolean(errors.email)"
            :aria-describedby="describedBy"
          />
        </template>
      </FormField>
      <FormField id="password" label="Password" :error="errors.password">
        <template #default="{ describedBy }">
          <div class="input-group">
            <input
              id="password"
              v-model="values.password"
              class="input"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              required
              :aria-invalid="Boolean(errors.password)"
              :aria-describedby="describedBy"
            />
            <button
              type="button"
              class="btn-icon input-addon"
              :aria-pressed="showPassword"
              :aria-label="showPassword ? 'Sembunyikan password' : 'Lihat password'"
              @click="showPassword = !showPassword"
            >
              <AppIcon :name="showPassword ? 'eye-off' : 'eye'" :size="18" />
            </button>
          </div>
        </template>
      </FormField>
      <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
        {{ submitting ? 'Memproses...' : 'Masuk' }}
      </button>
    </form>
    <p class="auth-footer">Belum punya akun? <RouterLink :to="{ name: 'register' }">Daftar</RouterLink></p>
  </AuthLayout>
</template>
