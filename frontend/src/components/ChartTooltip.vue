<script setup>
import { computed } from 'vue'

// bubble nilai saat grafik di-hover atau difokus, posisinya mengikuti titik x di viewBox SVG
const props = defineProps({
  x: { type: Number, required: true },
  viewWidth: { type: Number, required: true },
  title: { type: String, default: '' },
  // tiap baris { key, value, label }: key memilih warna garis kunci seri
  rows: { type: Array, default: () => [] },
})

// bubble digeser sebanding posisi titik: rata kiri di tepi kiri, rata kanan di tepi kanan,
// jadi selalu berada di dalam area grafik berapa pun lebar layarnya
const style = computed(() => {
  const ratio = Math.min(1, Math.max(0, props.x / props.viewWidth))
  return { left: `${ratio * 100}%`, transform: `translateX(-${ratio * 100}%)` }
})
</script>

<template>
  <div class="chart-tooltip" :style="style" role="status">
    <span class="chart-tooltip-title">{{ title }}</span>
    <span v-for="row in rows" :key="row.label" class="chart-tooltip-row">
      <span class="chart-key" :class="`chart-key-${row.key}`" aria-hidden="true"></span>
      <strong class="num">{{ row.value }}</strong>
      <span>{{ row.label }}</span>
    </span>
  </div>
</template>
