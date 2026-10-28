import { reactive, ref } from 'vue'

import { ApiError } from '@/services/ApiClient'

// state formulir: nilai, error per field dari 422, pesan umum dan status menyimpan
export function useForm(initial) {
  const values = reactive({ ...initial })
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

  function reset() {
    Object.assign(values, initial)
    errors.value = {}
  }

  return { values, errors, message, submitting, submit, reset }
}
