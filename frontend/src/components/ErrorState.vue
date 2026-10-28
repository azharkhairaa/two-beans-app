<script setup>
import AppIcon from '@/components/AppIcon'

defineProps({
  message: { type: String, default: 'Gagal memuat data.' },
})

defineEmits(['retry'])
</script>

<template>
  <div class="empty-state error-state" role="alert">
    <AppIcon name="alert" :size="32" />
    <p class="state-message">{{ message }}</p>
    <button type="button" class="btn btn-secondary btn-small" @click="$emit('retry')">
      <AppIcon name="refresh" :size="16" />
      <span>Coba lagi</span>
    </button>
  </div>
</template>
