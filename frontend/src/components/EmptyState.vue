<script setup>
import AppIcon from '@/components/AppIcon'

defineProps({
  icon: { type: String, default: 'box' },
  title: { type: String, default: '' },
  message: { type: String, required: true },
})
</script>

<template>
  <div class="empty-state">
    <AppIcon :name="icon" :size="32" />
    <h2 v-if="title" class="section-title">{{ title }}</h2>
    <p class="state-message">{{ message }}</p>
    <slot name="action" />
  </div>
</template>
