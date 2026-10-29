<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  size: { type: String, default: 'md' },
})

const emit = defineEmits(['close'])
const dialogRef = ref(null)
const titleId = `modal-title-${Math.random().toString(36).slice(2, 9)}`
let previousFocus = null

const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  '[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

function getFocusableElements() {
  if (!dialogRef.value) return []
  return Array.from(dialogRef.value.querySelectorAll(FOCUSABLE_SELECTOR))
}

function handleKeydown(event) {
  if (!props.open) return
  if (event.key === 'Escape') {
    event.stopPropagation()
    emit('close')
    return
  }
  if (event.key === 'Tab') {
    const focusables = getFocusableElements()
    if (!focusables.length) {
      event.preventDefault()
      return
    }
    const first = focusables[0]
    const last = focusables[focusables.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }
}

watch(
  () => props.open,
  async (isOpen) => {
    if (isOpen) {
      previousFocus = document.activeElement
      document.body.style.overflow = 'hidden'
      document.addEventListener('keydown', handleKeydown)
      await nextTick()
      const initial =
        dialogRef.value?.querySelector('[data-initial-focus]') ||
        dialogRef.value?.querySelector('.modal-body ' + FOCUSABLE_SELECTOR) ||
        getFocusableElements()[0]
      initial?.focus?.()
    } else {
      document.body.style.overflow = ''
      document.removeEventListener('keydown', handleKeydown)
      previousFocus?.focus?.()
      previousFocus = null
    }
  }
)

onBeforeUnmount(() => {
  document.body.style.overflow = ''
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="open" class="modal-backdrop" @mousedown.self="emit('close')">
        <div
          ref="dialogRef"
          class="modal-dialog"
          :class="`modal-${size}`"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
        >
          <header class="modal-header">
            <h2 :id="titleId" class="modal-title">{{ title }}</h2>
            <button type="button" class="btn-icon" aria-label="Tutup dialog" @click="emit('close')">
              <AppIcon name="close" :size="18" />
            </button>
          </header>
          <div class="modal-body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="modal-footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
