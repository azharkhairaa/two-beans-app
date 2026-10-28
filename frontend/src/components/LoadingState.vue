<script setup>
defineProps({
  rows: { type: Number, default: 4 },
  label: { type: String, default: 'Memuat data...' },
})
</script>

<template>
  <div class="loading-state card" role="status" aria-live="polite">
    <p class="loading-label">{{ label }}</p>
    <div v-for="index in rows" :key="index" class="skeleton-row" aria-hidden="true"></div>
  </div>
</template>
