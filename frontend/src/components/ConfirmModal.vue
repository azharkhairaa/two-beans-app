<script setup>
import BaseModal from '@/components/BaseModal.vue'

defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: 'Konfirmasi' },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Ya, lanjutkan' },
  cancelLabel: { type: String, default: 'Batal' },
  variant: { type: String, default: 'danger' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['confirm', 'close'])
</script>

<template>
  <BaseModal :open="open" :title="title" size="sm" @close="emit('close')">
    <p v-if="error" class="alert alert-error" role="alert">{{ error }}</p>
    <p v-if="message" class="confirm-message">{{ message }}</p>
    <slot />
    <template #footer>
      <button
        type="button"
        class="btn btn-secondary"
        data-initial-focus
        :disabled="loading"
        @click="emit('close')"
      >
        {{ cancelLabel }}
      </button>
      <button
        type="button"
        class="btn"
        :class="variant === 'danger' ? 'btn-delete' : 'btn-post'"
        :disabled="loading"
        @click="emit('confirm')"
      >
        <span v-if="loading" class="btn-spinner" aria-hidden="true"></span>
        <span>{{ loading ? 'Memproses...' : confirmLabel }}</span>
      </button>
    </template>
  </BaseModal>
</template>
