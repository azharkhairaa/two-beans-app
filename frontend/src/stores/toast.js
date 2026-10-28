import { ref } from 'vue'
import { defineStore } from 'pinia'

let counter = 0

export const useToastStore = defineStore('toast', () => {
  const items = ref([])

  function dismiss(id) {
    items.value = items.value.filter((item) => item.id !== id)
  }

  // pesan berhasil hilang setelah 4 detik, pesan error bertahan sampai ditutup
  function show(message, kind, timeout) {
    const id = ++counter
    items.value.push({ id, message, kind })
    if (timeout) setTimeout(() => dismiss(id), timeout)
  }

  return {
    items,
    dismiss,
    success: (message) => show(message, 'success', 4000),
    info: (message) => show(message, 'info', 4000),
    error: (message) => show(message, 'error', 0),
  }
})
