import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi } from '@/services'
import { ApiError } from '@/services/ApiClient'
import { ROLES } from '@/utils/constants'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  // token CSRF hanya di memori, setelah reload diminta lagi lewat GET /api/auth/me
  const csrfToken = ref(null)
  const checked = ref(false)
  const sessionEnded = ref(false)
  let checking = null

  const isLoggedIn = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === ROLES.ADMIN)
  const lokasiType = computed(() => user.value?.lokasi?.jenis ?? null)

  function applySession(data) {
    user.value = data.user
    csrfToken.value = data.csrf_token
    checked.value = true
  }

  function clear() {
    user.value = null
    csrfToken.value = null
  }

  // cek sesi cukup sekali per muat halaman, guard router menunggu hasilnya
  function ensureChecked() {
    checking ||= authApi
      .me()
      .then(applySession)
      .catch(clear)
      .finally(() => {
        checked.value = true
      })
    return checking
  }

  async function login(email, password) {
    applySession(await authApi.login(email, password))
    sessionEnded.value = false
  }

  function register(data) {
    return authApi.register(data)
  }

  function changePassword(data) {
    return authApi.changePassword(data)
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch (error) {
      // 401 berarti sesi di server sudah tidak ada, hasil akhirnya tetap logout
      if (!(error instanceof ApiError) || error.status !== 401) throw error
    } finally {
      clear()
    }
  }

  function sessionExpired() {
    clear()
    sessionEnded.value = true
  }

  return {
    user,
    csrfToken,
    checked,
    sessionEnded,
    isLoggedIn,
    isAdmin,
    lokasiType,
    ensureChecked,
    login,
    register,
    changePassword,
    logout,
    sessionExpired,
  }
})
