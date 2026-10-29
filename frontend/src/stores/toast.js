import { ref } from 'vue'
import { defineStore } from 'pinia'

let counter = 0

export const useToastStore = defineStore('toast', () => {
  const items = ref([])

  function dismiss(id) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  // pesan berhasil hilang setelah 4 detik, pesan error bertahan sampai ditutup
  function show(message, kind = 'success') {
    const id = ++counter
    items.value.push({ id, message, kind })
    if (kind !== 'error') setTimeout(() => dismiss(id), 4000)
  }

  return {
    items,
    dismiss,
    show,
    success: (message) => show(message, 'success'),
    info: (message) => show(message, 'info'),
    error: (message) => show(message, 'error'),
  }
})
