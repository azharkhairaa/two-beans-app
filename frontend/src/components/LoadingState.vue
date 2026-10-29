<script setup>
defineProps({
  rows: { type: Number, default: 4 },
  label: { type: String, default: 'Memuat data...' },
  message: { type: String, default: '' },
})
</script>

<template>
  <div class="loading-state card" role="status" aria-live="polite">
    <div class="loading-state-header">
      <span class="loading-spinner" aria-hidden="true"></span>
      <p class="loading-label">{{ message || label }}</p>
    </div>
    <div class="skeleton-list">
      <div
        v-for="index in rows"
        :key="index"
        class="skeleton-row"
        :style="{ width: `${75 + ((index * 17) % 25)}%` }"
        aria-hidden="true"
      ></div>
    </div>
  </div>
</template>
