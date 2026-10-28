<script setup>
import AppIcon from '@/components/AppIcon'
</script>

<template>
  <main class="status-page">
    <AppIcon name="search" :size="40" />
    <h1 class="page-title">Halaman tidak ditemukan</h1>
    <p>Alamat yang dibuka tidak ada. Periksa kembali tautannya.</p>
    <RouterLink :to="{ name: 'dashboard' }" class="btn btn-primary">Kembali ke dashboard</RouterLink>
  </main>
</template>
