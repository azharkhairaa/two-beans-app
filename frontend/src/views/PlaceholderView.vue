<script setup>
import AppIcon from '@/components/AppIcon'
</script>

<template>
  <section class="page">
    <header class="page-header">
      <h1 class="page-title">{{ $route.meta.title }}</h1>
    </header>
    <div class="empty-state">
      <AppIcon name="clock" :size="32" />
      <p>Halaman {{ $route.meta.title }} sedang disiapkan.</p>
      <RouterLink :to="{ name: 'dashboard' }" class="btn btn-secondary">Kembali ke dashboard</RouterLink>
    </div>
  </section>
</template>
