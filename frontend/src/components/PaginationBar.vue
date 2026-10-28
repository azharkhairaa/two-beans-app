<script setup>
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon'

const props = defineProps({
  meta: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update:page', 'update:perPage', 'page', 'per-page'])

const start = computed(() => {
  if (!props.meta.total) return 0
  return (props.meta.page - 1) * props.meta.per_page + 1
})

const end = computed(() => Math.min(props.meta.page * props.meta.per_page, props.meta.total))

function changePage(nextPage) {
  emit('page', nextPage)
  emit('update:page', nextPage)
}

function changePerPage(nextPerPage) {
  const val = Number(nextPerPage)
  emit('per-page', val)
  emit('update:perPage', val)
}
</script>

<template>
  <div v-if="meta.total > 0" class="pagination-bar">
    <p class="pagination-summary">
      Menampilkan <strong>{{ start }}</strong> sampai <strong>{{ end }}</strong> dari
      <strong>{{ meta.total }}</strong> data
    </p>
    <div class="pagination-controls">
      <label class="pagination-size">
        <span>Baris</span>
        <select
          class="input input-sm"
          :value="meta.per_page"
          aria-label="Jumlah baris per halaman"
          @change="changePerPage($event.target.value)"
        >
          <option :value="10">10</option>
          <option :value="15">15</option>
          <option :value="20">20</option>
          <option :value="50">50</option>
        </select>
      </label>
      <button
        type="button"
        class="btn btn-secondary btn-sm"
        :disabled="meta.page <= 1"
        @click="changePage(meta.page - 1)"
      >
        <AppIcon name="chevron-left" :size="16" />
        <span>Sebelumnya</span>
      </button>
      <span class="pagination-page mono">{{ meta.page }} / {{ meta.total_pages || 1 }}</span>
      <button
        type="button"
        class="btn btn-secondary btn-sm"
        :disabled="meta.page >= (meta.total_pages || 1)"
        @click="changePage(meta.page + 1)"
      >
        <span>Berikutnya</span>
        <AppIcon name="chevron-right" :size="16" />
      </button>
    </div>
  </div>
</template>
