import { ApiClient } from './ApiClient'
import { AuthApi } from './AuthApi'

// satu ApiClient dipakai semua kelas API resource
export const apiClient = new ApiClient('/api')
export const authApi = new AuthApi(apiClient)
