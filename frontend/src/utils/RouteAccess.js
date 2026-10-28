import { ROLES } from './constants'

export class RouteAccess {
  // dipakai guard router dan sidebar sehingga aturan peran dan jenis lokasi cukup ditulis di meta route
  static allows(meta, user) {
    if (!user) return false
    if (meta.roles && !meta.roles.includes(user.role)) return false
    if (meta.lokasiTypes && user.role !== ROLES.ADMIN && !meta.lokasiTypes.includes(user.lokasi?.jenis)) {
      return false
    }
    return true
  }

  // redirect hanya ke path internal, "//evil.example" atau "/\evil.example" ditolak (open redirect)
  static safeRedirect(value, fallback = '/dashboard') {
    if (typeof value !== 'string' || !value.startsWith('/')) return fallback
    if (value.startsWith('//') || value.startsWith('/\\')) return fallback
    return value
  }
}
