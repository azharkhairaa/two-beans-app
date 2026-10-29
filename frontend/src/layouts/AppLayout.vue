<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon'
import { MENU_GROUPS } from '@/router/routes'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import { ROLE_LABELS, ROLES } from '@/utils/constants'
import { RouteAccess } from '@/utils/RouteAccess'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()
const drawerOpen = ref(false)

// menu sidebar diambil dari meta route yang boleh dibuka user, jadi sama dengan aturan guard
const menuGroups = computed(() => {
  const items = router.getRoutes().filter((r) => r.meta.menu && RouteAccess.allows(r.meta, auth.user))
  return MENU_GROUPS.map((group) => ({
    ...group,
    items: items.filter((r) => r.meta.menu.group === group.key),
  })).filter((group) => group.items.length)
})

const userContext = computed(() => {
  if (!auth.user) return ''
  const role = ROLE_LABELS[auth.user.role] || 'User'
  if (auth.user.lokasi) return `${role} · ${auth.user.lokasi.nama}`
  return auth.user.role === ROLES.ADMIN ? `${role} · Semua lokasi` : role
})

function isAdminRoute(item) {
  return item.meta?.roles && item.meta.roles.length === 1 && item.meta.roles[0] === ROLES.ADMIN
}

watch(() => route.fullPath, () => {
  drawerOpen.value = false
})

async function logout() {
  await auth.logout()
  toast.success('Anda sudah logout.')
  router.push({ name: 'login' })
}
</script>

<template>
  <!-- user kosong sesaat setelah logout, sebelum pindah ke halaman login -->
  <template v-if="auth.user">
    <a href="#konten" class="skip-link">Lewati ke konten</a>
    <div class="app-shell" :class="{ 'app-drawer-open': drawerOpen }">
      <aside id="navigasi" class="app-sidebar" aria-label="Navigasi utama">
        <RouterLink :to="{ name: 'dashboard' }" class="app-brand">
          <span class="app-brand-mark"><AppIcon name="coffee" :size="20" /></span>
          <span class="app-brand-text">Two Beans App</span>
        </RouterLink>
        <nav class="app-nav">
          <div v-for="group in menuGroups" :key="group.key" class="app-nav-group">
            <p class="app-nav-heading">{{ group.label }}</p>
            <RouterLink
              v-for="item in group.items"
              :key="item.name"
              :to="{ name: item.name }"
              class="app-nav-link"
              :title="item.meta.menu.label"
            >
              <AppIcon :name="item.meta.menu.icon" />
              <span class="app-nav-label">{{ item.meta.menu.label }}</span>
              <span v-if="isAdminRoute(item)" class="nav-admin-badge">ADMIN</span>
            </RouterLink>
          </div>
        </nav>
      </aside>
      <div v-if="drawerOpen" class="app-backdrop" @click="drawerOpen = false"></div>

      <div class="app-main">
        <header class="app-topbar">
          <button
            type="button"
            class="btn-icon app-menu-toggle"
            aria-controls="navigasi"
            :aria-expanded="drawerOpen"
            aria-label="Buka menu navigasi"
            @click="drawerOpen = !drawerOpen"
          >
            <AppIcon name="menu" />
          </button>
          <div class="app-user">
            <div class="app-user-header">
              <strong class="app-user-name">{{ auth.user.name }}</strong>
              <span class="app-user-role-chip">{{ ROLE_LABELS[auth.user.role] || auth.user.role }}</span>
            </div>
            <span class="app-user-context">{{ userContext }}</span>
          </div>
          <RouterLink :to="{ name: 'profil' }" class="btn btn-secondary btn-small">
            <AppIcon name="user" :size="18" /><span class="app-topbar-label">Profil</span>
          </RouterLink>
          <button type="button" class="btn btn-secondary btn-small" @click="logout">
            <AppIcon name="logout" :size="18" /><span class="app-topbar-label">Logout</span>
          </button>
        </header>
        <main id="konten" class="app-content" tabindex="-1">
          <RouterView v-slot="{ Component }">
            <Transition name="page" mode="out-in">
              <component :is="Component" />
            </Transition>
          </RouterView>
        </main>
      </div>
    </div>
  </template>
</template>
