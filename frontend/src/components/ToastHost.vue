<script setup>
import AppIcon from '@/components/AppIcon'
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
const ICONS = { success: 'check', info: 'info', error: 'alert' }
</script>

<template>
  <div class="toast-host" role="status" aria-live="polite">
    <TransitionGroup name="toast">
      <div v-for="item in toast.items" :key="item.id" class="toast" :class="`toast-${item.kind}`">
        <AppIcon :name="ICONS[item.kind]" :size="18" class="toast-icon" />
        <p class="toast-message">{{ item.message }}</p>
        <button type="button" class="btn-icon toast-close" aria-label="Tutup notifikasi" @click="toast.dismiss(item.id)">
          <AppIcon name="close" :size="16" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>
