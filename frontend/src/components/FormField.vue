<script setup>
// label, petunjuk dan pesan error satu field, input diisi lewat slot dengan id yang sama
defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
})
</script>

<template>
  <div class="field" :class="{ 'field-invalid': error }">
    <label class="field-label" :for="id">{{ label }}</label>
    <p v-if="hint" :id="`${id}-hint`" class="field-hint">{{ hint }}</p>
    <slot :describedBy="[hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') || undefined" />
    <p v-if="error" :id="`${id}-error`" class="field-error" role="alert">{{ error }}</p>
  </div>
</template>
