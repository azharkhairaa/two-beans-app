import { reactive, ref } from 'vue'

import { ApiError } from '@/services/ApiClient'

function clone(value) {
  return Array.isArray(value) ? value.map((item) => ({ ...item })) : value
}

function copyShape(source) {
  const result = {}
  for (const [key, value] of Object.entries(source)) {
    result[key] = clone(value)
  }
  return result
}

// state formulir: nilai, error per field dari 422/409, pesan umum dan status menyimpan
export function useForm(initial) {
  const defaults = copyShape(initial)
  const values = reactive(copyShape(initial))
  const errors = ref({})
  const message = ref('')
  const submitting = ref(false)

  async function submit(action) {
    submitting.value = true
    errors.value = {}
    message.value = ''
    try {
      await action(values)
      return true
    } catch (error) {
      if (!(error instanceof ApiError)) throw error
      errors.value = error.errors
      message.value = error.message
      return false
    } finally {
      submitting.value = false
    }
  }

  function fill(next = {}) {
    Object.assign(values, copyShape(defaults), copyShape(next))
    errors.value = {}
    message.value = ''
  }

  function reset() {
    fill()
  }

  return { values, errors, message, submitting, submit, fill, reset }
}
