const integerFormat = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 })

const dateFormat = new Intl.DateTimeFormat('id-ID', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'Asia/Jakarta',
})

const dateTimeFormat = new Intl.DateTimeFormat('id-ID', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  timeZone: 'Asia/Jakarta',
})

const isoDateWib = new Intl.DateTimeFormat('sv-SE', {
  timeZone: 'Asia/Jakarta',
})

export function formatNumber(value) {
  return integerFormat.format(Number(value || 0))
}

export function formatRupiah(value) {
  return `Rp ${integerFormat.format(Number(value || 0))}`
}

export function formatRupiahCompact(value) {
  const num = Number(value || 0)
  const abs = Math.abs(num)
  const sign = num < 0 ? '-' : ''
  if (abs >= 1_000_000_000) {
    const scaled = (abs / 1_000_000_000).toLocaleString('id-ID', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })
    return `${sign}Rp ${scaled} M`
  }
  if (abs >= 1_000_000) {
    const scaled = (abs / 1_000_000).toLocaleString('id-ID', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })
    return `${sign}Rp ${scaled} jt`
  }
  return formatRupiah(num)
}

export function formatDate(value) {
  if (!value) return '-'
  const parsed = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? new Date(`${value}T00:00:00+07:00`)
    : new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return dateFormat.format(parsed)
}

export function formatDateTime(value) {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return String(value)
  return `${dateTimeFormat.format(parsed)} WIB`
}

export function todayIso() {
  return isoDateWib.format(new Date())
}
