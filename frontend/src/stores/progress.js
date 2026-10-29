import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useProgressStore = defineStore('progress', () => {
  const active = ref(false)
  let timer = null

  function start() {
    clearTimeout(timer)
    active.value = true
  }

  function finish() {
    clearTimeout(timer)
    timer = setTimeout(() => {
      active.value = false
    }, 120)
  }

  return { active, start, finish }
})
