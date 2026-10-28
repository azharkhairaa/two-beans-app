import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { RouteAccess } from '@/utils/RouteAccess'

import { routes } from './routes'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

// guard hanya mengatur tampilan, pengamanan sebenarnya tetap di backend (401, 403, 404)
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.ensureChecked()
  if (to.meta.visitorOnly && auth.isLoggedIn) return { name: 'dashboard' }
  if (to.meta.public) return true
  if (!auth.isLoggedIn) return { name: 'login', query: { redirect: to.fullPath } }
  if (!RouteAccess.allows(to.meta, auth.user)) return { name: 'forbidden' }
  return true
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · Two Beans App` : 'Two Beans App'
})

export default router
