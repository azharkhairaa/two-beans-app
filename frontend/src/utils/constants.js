export const ROLES = Object.freeze({
  ADMIN: 'admin',
  MANAGER_GUDANG: 'manager_gudang',
  MANAGER_OUTLET: 'manager_outlet',
  DELIVERYMAN: 'deliveryman',
})

// admin ikut dihitung manager untuk menu dan aksi
export const MANAGER_ROLES = Object.freeze([ROLES.ADMIN, ROLES.MANAGER_GUDANG, ROLES.MANAGER_OUTLET])

export const LOKASI_TYPES = Object.freeze({
  GUDANG_UTAMA: 'gudang_utama',
  GUDANG_CABANG: 'gudang_cabang',
  OUTLET: 'outlet',
})

export const ROLE_LABELS = Object.freeze({
  [ROLES.ADMIN]: 'Admin',
  [ROLES.MANAGER_GUDANG]: 'Manager Gudang',
  [ROLES.MANAGER_OUTLET]: 'Manager Outlet',
  [ROLES.DELIVERYMAN]: 'Deliveryman',
})
