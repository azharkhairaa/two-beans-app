<script setup>
import { formatDateTime } from '@/utils/format'

defineProps({
  steps: { type: Array, required: true },
})
</script>

<template>
  <div class="doc-timeline" aria-label="Riwayat status dokumen">
    <div
      v-for="(step, idx) in steps"
      :key="idx"
      class="doc-timeline-item"
      :class="`doc-timeline-${step.tone || 'netral'}`"
    >
      <span class="doc-timeline-dot" aria-hidden="true"></span>
      <div class="doc-timeline-content">
        <div class="doc-timeline-title">{{ step.label }}</div>
        <div v-if="step.user || step.time" class="doc-timeline-meta">
          <span v-if="step.user" class="font-semibold">{{ step.user }}</span>
          <span v-if="step.user && step.time"> · </span>
          <span v-if="step.time" class="mono">{{ formatDateTime(step.time) }}</span>
        </div>
        <div v-else-if="step.placeholder" class="doc-timeline-meta">
          {{ step.placeholder }}
        </div>
        <div v-if="step.note" class="doc-timeline-note">{{ step.note }}</div>
      </div>
    </div>
  </div>
</template>
