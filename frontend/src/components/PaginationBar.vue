<script setup>
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon'

const props = defineProps({
  meta: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update:page', 'update:perPage'])

const start = computed(() => {
  if (!props.meta.total) return 0
  return (props.meta.page - 1) * props.meta.per_page + 1
})

const end = computed(() => Math.min(props.meta.page * props.meta.per_page, props.meta.total))
</script>

<template>
  <div v-if="meta.total > 0" class="pagination-bar">
    <p class="pagination-summary">
      Menampilkan {{ start }} sampai {{ end }} dari {{ meta.total }}
    </p>
    <div class="pagination-controls">
      <label class="pagination-size">
        <span>Baris</span>
        <select
          class="input input-small"
          :value="meta.per_page"
          aria-label="Jumlah baris per halaman"
          @change="emit('update:perPage', Number($event.target.value))"
        >
          <option :value="10">10</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
      </label>
      <button
        type="button"
        class="btn btn-secondary btn-small"
        :disabled="meta.page <= 1"
        @click="emit('update:page', meta.page - 1)"
      >
        <AppIcon name="chevron-left" :size="16" />
        <span>Sebelumnya</span>
      </button>
      <span class="pagination-page">{{ meta.page }} / {{ meta.total_pages || 1 }}</span>
      <button
        type="button"
        class="btn btn-secondary btn-small"
        :disabled="meta.page >= meta.total_pages"
        @click="emit('update:page', meta.page + 1)"
      >
        <span>Berikutnya</span>
        <AppIcon name="chevron-right" :size="16" />
      </button>
    </div>
  </div>
</template>
