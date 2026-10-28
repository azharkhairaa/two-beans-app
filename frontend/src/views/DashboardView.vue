<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABELS } from '@/utils/constants'
import { RouteAccess } from '@/utils/RouteAccess'

const auth = useAuthStore()
const router = useRouter()

const lokasiText = computed(() => {
  const lokasi = auth.user.lokasi
  if (lokasi) return `${lokasi.kode} · ${lokasi.nama}`
  return auth.isAdmin ? 'Semua lokasi' : 'Tidak terikat lokasi'
})

// pintasan ke halaman yang boleh dibuka, tile ringkasan menyusul bersama API dashboard
const shortcuts = computed(() =>
  router
    .getRoutes()
    .filter((r) => r.meta.menu && r.name !== 'dashboard' && RouteAccess.allows(r.meta, auth.user)),
)
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Halo, {{ auth.user.name }}.</p>
      </div>
    </header>

    <div class="card">
      <h2 class="section-title">Akun</h2>
      <dl class="detail-list">
        <div>
          <dt>Peran</dt>
          <dd>{{ ROLE_LABELS[auth.user.role] }}</dd>
        </div>
        <div>
          <dt>Lokasi</dt>
          <dd>{{ lokasiText }}</dd>
        </div>
        <div>
          <dt>Email</dt>
          <dd>{{ auth.user.email }}</dd>
        </div>
      </dl>
    </div>

    <h2 class="section-title">Menu yang bisa dibuka</h2>
    <div class="shortcut-grid">
      <RouterLink v-for="item in shortcuts" :key="item.name" :to="{ name: item.name }" class="shortcut">
        <AppIcon :name="item.meta.menu.icon" />
        <span>{{ item.meta.menu.label }}</span>
      </RouterLink>
    </div>
  </section>
</template>
