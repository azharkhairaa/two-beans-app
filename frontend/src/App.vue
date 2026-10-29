<script setup>
import ToastHost from '@/components/ToastHost.vue'
import { useProgressStore } from '@/stores/progress'

const progress = useProgressStore()
</script>

<template>
  <Transition name="fade">
    <div
      v-if="progress.active"
      class="top-progress-bar"
      role="progressbar"
      aria-label="Memuat halaman"
      aria-valuetext="Memuat..."
      aria-busy="true"
    >
      <div class="top-progress-bar-glow"></div>
    </div>
  </Transition>
  <RouterView />
  <ToastHost />
</template>
