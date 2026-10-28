import { ApiClient } from './ApiClient'
import { AuthApi } from './AuthApi'
import {
  CustomerApi,
  DashboardApi,
  KategoriApi,
  LokasiApi,
  PembelianApi,
  PengirimanApi,
  PenjualanApi,
  PermintaanApi,
  ProdukApi,
  StokApi,
  SupplierApi,
  TransaksiApi,
  UserApi,
} from './ResourceApi'

// satu ApiClient dipakai semua kelas API resource
export const apiClient = new ApiClient('/api')
export const authApi = new AuthApi(apiClient)
export const lokasiApi = new LokasiApi(apiClient)
export const kategoriApi = new KategoriApi(apiClient)
export const supplierApi = new SupplierApi(apiClient)
export const customerApi = new CustomerApi(apiClient)
export const userApi = new UserApi(apiClient)
export const produkApi = new ProdukApi(apiClient)
export const stokApi = new StokApi(apiClient)
export const transaksiApi = new TransaksiApi(apiClient)
export const pengirimanApi = new PengirimanApi(apiClient)
export const permintaanApi = new PermintaanApi(apiClient)
export const pembelianApi = new PembelianApi(apiClient)
export const penjualanApi = new PenjualanApi(apiClient)
export const dashboardApi = new DashboardApi(apiClient)
