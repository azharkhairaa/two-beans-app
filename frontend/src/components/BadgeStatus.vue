<script setup>
import { computed } from 'vue'

import {
  COFFEE_TYPE_LABELS,
  CUSTOMER_TYPE_LABELS,
  DOKUMEN_STATUS_LABELS,
  KATEGORI_TYPE_LABELS,
  LOKASI_TYPE_LABELS,
  ROLE_LABELS,
  STOK_STATUS_LABELS,
  TRANSAKSI_REASON_LABELS,
  TRANSAKSI_TYPE_LABELS,
  USER_STATUS_LABELS,
} from '@/utils/constants'

const props = defineProps({
  status: { type: [String, Boolean], default: '' },
  value: { type: [String, Boolean], default: '' },
  label: { type: String, default: '' },
  tone: { type: String, default: '' },
})

const LABELS = {
  ...STOK_STATUS_LABELS,
  ...USER_STATUS_LABELS,
  ...DOKUMEN_STATUS_LABELS,
  ...TRANSAKSI_TYPE_LABELS,
  ...TRANSAKSI_REASON_LABELS,
  ...LOKASI_TYPE_LABELS,
  ...KATEGORI_TYPE_LABELS,
  ...CUSTOMER_TYPE_LABELS,
  ...COFFEE_TYPE_LABELS,
  ...ROLE_LABELS,
  kirim: 'Kirim',
  terima: 'Terima',
  pembelian: 'Pembelian',
  penjualan: 'Penjualan',
}

// pemetaan warna semantik sesuai tabel Desain UI bagian 2
const TONES = {
  aman: 'aman',
  aktif: 'aman',
  masuk: 'aman',
  terima: 'aman',
  pembelian: 'aman',
  menipis: 'menunggu',
  menunggu: 'menunggu',
  diajukan: 'menunggu',
  dipesan: 'menunggu',
  dikirim: 'proses',
  disetujui: 'proses',
  penyesuaian: 'proses',
  gudang_utama: 'proses',
  gudang_cabang: 'proses',
  roasted_bean: 'proses',
  kafe: 'proses',
  reseller: 'proses',
  admin: 'proses',
  diposting: 'selesai',
  diterima: 'selesai',
  selesai: 'selesai',
  outlet: 'selesai',
  green_bean: 'selesai',
  peralatan: 'selesai',
  habis_pakai: 'selesai',
  perorangan: 'selesai',
  lainnya: 'selesai',
  habis: 'bahaya',
  ditolak: 'bahaya',
  keluar: 'bahaya',
  kirim: 'bahaya',
  penjualan: 'bahaya',
  draf: 'netral',
  nonaktif: 'netral',
  dibatalkan: 'netral',
}

const key = computed(() => {
  const raw = props.status !== '' ? props.status : props.value
  if (typeof raw === 'boolean') return raw ? 'aktif' : 'nonaktif'
  return String(raw || '')
})

const resolvedTone = computed(() => props.tone || TONES[key.value] || 'netral')
const resolvedLabel = computed(() => props.label || LABELS[key.value] || key.value || '-')
</script>

<template>
  <span class="badge" :class="`badge-${resolvedTone}`">{{ resolvedLabel }}</span>
</template>
