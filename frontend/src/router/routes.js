import AppLayout from '@/layouts/AppLayout.vue'
import { LOKASI_TYPES, MANAGER_ROLES, ROLES } from '@/utils/constants'

// halaman yang belum dibuat memakai PlaceholderView sampai task-nya dikerjakan
const placeholder = () => import('@/views/PlaceholderView.vue')
const ADMIN_ONLY = [ROLES.ADMIN]

// meta.menu: label, ikon, kelompok dan urutan di sidebar. meta.roles dan meta.lokasiTypes dicek RouteAccess
function page(path, name, title, access = {}, menu = null, component = placeholder) {
  return { path, name, component, meta: { title, ...access, menu } }
}

export const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { title: 'Login', public: true, visitorOnly: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { title: 'Registrasi', public: true, visitorOnly: true },
  },
  {
    path: '/',
    component: AppLayout,
    children: [
      { path: '', redirect: { name: 'dashboard' } },
      page('dashboard', 'dashboard', 'Dashboard', {}, { label: 'Dashboard', icon: 'dashboard', group: 'ringkasan' },
        () => import('@/views/DashboardView.vue')),
      page('monitoring', 'monitoring', 'Monitoring', { roles: MANAGER_ROLES },
        { label: 'Monitoring', icon: 'grid', group: 'ringkasan' },
        () => import('@/views/MonitoringView.vue')),
      page('stok', 'stok', 'Stock', { roles: MANAGER_ROLES },
        { label: 'Stock', icon: 'box', group: 'ringkasan' },
        () => import('@/views/stok/StokView.vue')),
      page('transaksi', 'transaksi', 'Transaksi', { roles: MANAGER_ROLES },
        { label: 'Transaksi', icon: 'swap', group: 'dokumen' },
        () => import('@/views/transaksi/TransaksiView.vue')),
      page('pengiriman', 'pengiriman', 'Pengiriman', {}, { label: 'Pengiriman', icon: 'truck', group: 'dokumen' },
        () => import('@/views/pengiriman/PengirimanView.vue')),
      page('pengiriman/:id/surat-jalan', 'pengiriman-surat-jalan', 'Surat Jalan Pengiriman', {}, null,
        () => import('@/views/pengiriman/SuratJalanView.vue')),
      page('permintaan', 'permintaan', 'Permintaan', { roles: MANAGER_ROLES },
        { label: 'Permintaan', icon: 'clipboard', group: 'dokumen' },
        () => import('@/views/permintaan/PermintaanView.vue')),
      page('pembelian', 'pembelian', 'Pembelian',
        { roles: [ROLES.ADMIN, ROLES.MANAGER_GUDANG], lokasiTypes: [LOKASI_TYPES.GUDANG_UTAMA] },
        { label: 'Pembelian', icon: 'cart', group: 'dokumen' },
        () => import('@/views/pembelian/PembelianView.vue')),
      page('penjualan', 'penjualan', 'Penjualan', { roles: MANAGER_ROLES },
        { label: 'Penjualan', icon: 'receipt', group: 'dokumen' },
        () => import('@/views/penjualan/PenjualanView.vue')),
      page('penjualan/:id/nota', 'penjualan-nota', 'Nota Penjualan', { roles: MANAGER_ROLES }, null,
        () => import('@/views/penjualan/NotaPenjualanView.vue')),
      page('produk', 'produk', 'Produk', { roles: MANAGER_ROLES },
        { label: 'Produk', icon: 'package', group: 'master' },
        () => import('@/views/produk/ProdukView.vue')),
      page('customer', 'customer', 'Customer', { roles: MANAGER_ROLES },
        { label: 'Customer', icon: 'users', group: 'master' },
        () => import('@/views/master/CustomerView.vue')),
      page('lokasi', 'lokasi', 'Lokasi', { roles: ADMIN_ONLY },
        { label: 'Lokasi', icon: 'map-pin', group: 'master' },
        () => import('@/views/master/LokasiView.vue')),
      page('kategori', 'kategori', 'Kategori', { roles: ADMIN_ONLY },
        { label: 'Kategori', icon: 'tag', group: 'master' },
        () => import('@/views/master/KategoriView.vue')),
      page('supplier', 'supplier', 'Supplier', { roles: ADMIN_ONLY },
        { label: 'Supplier', icon: 'factory', group: 'master' },
        () => import('@/views/master/SupplierView.vue')),
      page('users', 'users', 'User', { roles: ADMIN_ONLY },
        { label: 'User', icon: 'user-check', group: 'master' },
        () => import('@/views/user/UserView.vue')),
      page('profil', 'profil', 'Profil', {}, null,
        () => import('@/views/auth/ProfilView.vue')),
    ],
  },
  {
    path: '/forbidden',
    name: 'forbidden',
    component: () => import('@/views/ForbiddenView.vue'),
    meta: { title: 'Akses ditolak', public: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: 'Halaman tidak ditemukan', public: true },
  },
]

export const MENU_GROUPS = [
  { key: 'ringkasan', label: 'Ringkasan' },
  { key: 'dokumen', label: 'Dokumen' },
  { key: 'master', label: 'Master data' },
]
