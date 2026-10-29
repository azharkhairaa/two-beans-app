<script setup>
import AppIcon from '@/components/AppIcon'

defineProps({
  icon: { type: String, default: 'box' },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  description: { type: String, default: '' },
  actionLabel: { type: String, default: '' },
})

const emit = defineEmits(['action'])
</script>

<template>
  <div class="empty-state">
    <AppIcon :name="icon" :size="32" />
    <h2 v-if="title" class="section-title">{{ title }}</h2>
    <p v-if="message || description" class="state-message">{{ message || description }}</p>
    <slot />
    <slot name="action">
      <button v-if="actionLabel" type="button" class="btn btn-secondary btn-sm" @click="emit('action')">
        {{ actionLabel }}
      </button>
    </slot>
  </div>
</template>
