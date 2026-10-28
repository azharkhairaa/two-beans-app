<script setup>
import AppIcon from '@/components/AppIcon'
</script>

<template>
  <main class="status-page">
    <AppIcon name="lock" :size="40" />
    <h1 class="page-title">Akses ditolak</h1>
    <p>Halaman ini tidak tersedia untuk peran Anda.</p>
    <RouterLink :to="{ name: 'dashboard' }" class="btn btn-primary">Kembali ke dashboard</RouterLink>
  </main>
</template>
