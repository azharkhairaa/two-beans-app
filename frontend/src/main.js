import './style.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { apiClient } from './services'
import { useAuthStore } from './stores/auth'
import { useToastStore } from './stores/toast'

const app = createApp(App)
app.use(createPinia())
app.use(router)

const auth = useAuthStore()
const toast = useToastStore()
apiClient.csrfTokenProvider = () => auth.csrfToken
// 401 di tengah pemakaian berarti sesi berakhir, 401 dari endpoint sesi ditangani pemanggilnya
const SESSION_PATHS = new Set(['/auth/me', '/auth/login', '/auth/logout'])
apiClient.onUnauthorized = (path) => {
  if (!auth.isLoggedIn || SESSION_PATHS.has(path)) return
  auth.sessionExpired()
  toast.error('Sesi berakhir, silakan login lagi.')
  router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
}

app.mount('#app')
