<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon'

// dropdown yang bisa diketik untuk mencari, pola combobox ARIA, daftar di-teleport ke body agar tidak terpotong modal
const props = defineProps({
  id: { type: String, required: true },
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Pilih...' },
  emptyLabel: { type: String, default: '' },
  small: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  required: { type: Boolean, default: false },
  invalid: { type: Boolean, default: false },
  describedBy: { type: String, default: undefined },
  noResultsText: { type: String, default: 'Tidak ada yang cocok' },
})

const emit = defineEmits(['update:modelValue', 'change'])

const MAX_HEIGHT = 280
const inputRef = ref(null)
const listRef = ref(null)
const open = ref(false)
const query = ref('')
const activeIndex = ref(-1)
const position = ref({})
const listboxId = `${props.id}-listbox`

const allOptions = computed(() => {
  const empty = props.emptyLabel ? [{ value: '', label: props.emptyLabel }] : []
  return [...empty, ...props.options]
})

const selected = computed(
  () => allOptions.value.find((opt) => String(opt.value) === String(props.modelValue ?? '')) || null
)

function normalize(text) {
  return String(text ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
}

// semua kata yang diketik harus ada di label, keterangan atau grup
const filtered = computed(() => {
  const words = normalize(query.value).split(/\s+/).filter(Boolean)
  if (!words.length) return allOptions.value
  return allOptions.value.filter((opt) => {
    const haystack = normalize(`${opt.label} ${opt.hint ?? ''} ${opt.group ?? ''}`)
    return words.every((word) => haystack.includes(word))
  })
})

// baris tampilan: judul grup disisipkan setiap kali grup berganti
const rows = computed(() => {
  const result = []
  let lastGroup = null
  filtered.value.forEach((opt, index) => {
    if (opt.group && opt.group !== lastGroup) {
      result.push({ type: 'group', key: `g-${opt.group}`, label: opt.group })
    }
    lastGroup = opt.group ?? null
    result.push({ type: 'option', key: `o-${opt.value}`, index, opt })
  })
  return result
})

const activeId = computed(() =>
  open.value && activeIndex.value >= 0 ? `${props.id}-opt-${activeIndex.value}` : undefined
)

function updatePosition() {
  const rect = inputRef.value?.getBoundingClientRect()
  if (!rect) return
  const below = window.innerHeight - rect.bottom
  const upward = below < 200 && rect.top > below
  position.value = {
    left: `${rect.left}px`,
    width: `${Math.max(rect.width, 220)}px`,
    maxHeight: `${Math.min(MAX_HEIGHT, (upward ? rect.top : below) - 12)}px`,
    ...(upward
      ? { bottom: `${window.innerHeight - rect.top + 4}px` }
      : { top: `${rect.bottom + 4}px` }),
  }
}

function openList() {
  if (props.disabled || open.value) return
  open.value = true
  query.value = ''
  const current = filtered.value.findIndex((opt) => opt === selected.value)
  activeIndex.value = current >= 0 ? current : firstEnabled(0, 1)
  updatePosition()
  window.addEventListener('scroll', updatePosition, true)
  window.addEventListener('resize', updatePosition)
  scrollActiveIntoView()
}

function closeList() {
  if (!open.value) return
  open.value = false
  query.value = ''
  activeIndex.value = -1
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
}

function choose(opt) {
  if (!opt || opt.disabled) return
  closeList()
  if (String(opt.value) !== String(props.modelValue ?? '')) {
    emit('update:modelValue', opt.value)
    emit('change', opt.value, opt)
  }
}

function firstEnabled(start, step) {
  const list = filtered.value
  for (let i = start; i >= 0 && i < list.length; i += step) {
    if (!list[i].disabled) return i
  }
  return -1
}

function move(step) {
  const next = firstEnabled(activeIndex.value + step, step)
  if (next >= 0) activeIndex.value = next
  scrollActiveIntoView()
}

function scrollActiveIntoView() {
  nextTick(() => {
    listRef.value?.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' })
  })
}

// teks terpilih diblok saat fokus, jadi ketikan pertama mengganti label lama dan tidak ikut dicari
function onFocus(event) {
  event.target.select()
  event.target.scrollLeft = 0
}

function onInput(event) {
  if (!open.value) openList()
  query.value = event.target.value
  activeIndex.value = firstEnabled(0, 1)
}

function onKeydown(event) {
  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      open.value ? move(1) : openList()
      break
    case 'ArrowUp':
      event.preventDefault()
      if (open.value) move(-1)
      break
    case 'Enter':
      if (open.value) {
        event.preventDefault()
        choose(filtered.value[activeIndex.value])
      }
      break
    case 'Escape':
      if (open.value) {
        event.stopPropagation()
        closeList()
      }
      break
    case 'Tab':
      closeList()
      break
  }
}

function toggle() {
  if (open.value) {
    closeList()
    return
  }
  inputRef.value?.focus()
  openList()
}

watch(
  () => props.disabled,
  (value) => value && closeList()
)

onBeforeUnmount(closeList)
</script>

<template>
  <div class="search-select" :class="{ 'search-select-open': open, 'search-select-sm': small }">
    <input
      :id="id"
      ref="inputRef"
      class="input search-select-input"
      :class="{ 'input-sm': small }"
      type="text"
      role="combobox"
      autocomplete="off"
      spellcheck="false"
      aria-autocomplete="list"
      :aria-expanded="open"
      :aria-controls="listboxId"
      :aria-activedescendant="activeId"
      :aria-invalid="invalid || undefined"
      :aria-required="required || undefined"
      :aria-describedby="describedBy"
      :value="open ? query : (selected?.label ?? '')"
      :placeholder="open && selected ? selected.label : placeholder"
      :disabled="disabled"
      @focus="onFocus"
      @click="openList"
      @input="onInput"
      @keydown="onKeydown"
      @blur="closeList"
    />
    <button
      type="button"
      class="search-select-toggle"
      tabindex="-1"
      aria-hidden="true"
      :disabled="disabled"
      @mousedown.prevent="toggle"
    >
      <AppIcon :name="open ? 'search' : 'chevron-down'" :size="16" />
    </button>
    <Teleport to="body">
      <ul
        v-show="open"
        :id="listboxId"
        ref="listRef"
        class="search-select-list"
        role="listbox"
        :style="position"
        @mousedown.prevent
      >
        <template v-for="row in rows" :key="row.key">
          <li v-if="row.type === 'group'" class="search-select-group" role="presentation">
            {{ row.label }}
          </li>
          <li
            v-else
            :id="`${id}-opt-${row.index}`"
            class="search-select-option"
            :class="{
              'search-select-option-active': row.index === activeIndex,
              'search-select-option-selected': row.opt === selected,
            }"
            role="option"
            :data-active="row.index === activeIndex"
            :aria-selected="row.opt === selected"
            :aria-disabled="row.opt.disabled || undefined"
            @mouseenter="!row.opt.disabled && (activeIndex = row.index)"
            @click="choose(row.opt)"
          >
            <span class="search-select-label">{{ row.opt.label }}</span>
            <span v-if="row.opt.hint" class="search-select-hint">{{ row.opt.hint }}</span>
          </li>
        </template>
        <li v-if="!filtered.length" class="search-select-empty" role="presentation">
          {{ noResultsText }}
        </li>
      </ul>
    </Teleport>
  </div>
</template>
