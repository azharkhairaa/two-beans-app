import { reactive, ref } from 'vue'

import { useToastStore } from '@/stores/toast'

// modal terima barang: muat detail bila perlu, isi jumlah diterima, kirim lalu tampilkan error
export function useTerimaForm(options) {
  const { label, fetchDetail, toForm, toPayload, submit, successMessage, onSaved } = options
  const toast = useToastStore()
  const open = ref(false)
  const target = ref(null)
  const loadingDetail = ref(false)
  const submitting = ref(false)
  const message = ref('')
  const errors = reactive({})
  const form = reactive({ items: [] })

  function clearErrors() {
    message.value = ''
    for (const key of Object.keys(errors)) delete errors[key]
  }

  async function show(row) {
    open.value = true
    clearErrors()
    let detail = row.items ? row : null
    if (!detail) {
      loadingDetail.value = true
      try {
        detail = await fetchDetail(row.id)
      } catch (err) {
        toast.show(err?.message || `Gagal memuat detail ${label}.`, 'error')
        open.value = false
        return
      } finally {
        loadingDetail.value = false
      }
    }
    target.value = detail
    Object.assign(form, toForm(detail))
  }

  async function confirm() {
    if (!target.value) return
    submitting.value = true
    clearErrors()
    try {
      const res = await submit(target.value.id, toPayload(form))
      toast.show(successMessage(res))
      open.value = false
      await onSaved(res)
    } catch (err) {
      message.value = err?.message || 'Gagal mengonfirmasi penerimaan barang.'
      if (err?.errors && typeof err.errors === 'object') Object.assign(errors, err.errors)
    } finally {
      submitting.value = false
    }
  }

  function close() {
    open.value = false
  }

  return { open, target, loadingDetail, submitting, message, errors, form, show, confirm, close }
}
