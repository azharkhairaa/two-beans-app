<script setup>
import { computed } from 'vue'

import AppIcon from '@/components/AppIcon'
import { formatNumber, formatRupiah } from '@/utils/format'

const props = defineProps({
  modelValue: { type: Array, required: true },
  products: { type: Array, default: () => [] },
  stockMap: { type: Object, default: () => ({}) },
  showStock: { type: Boolean, default: true },
  withPrice: { type: Boolean, default: false },
  defaultPriceField: { type: String, default: '' },
  errors: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue'])

const groupedProducts = computed(() => {
  const groups = new Map()
  for (const prod of props.products) {
    const groupName = prod.kategori?.nama || 'Tanpa kategori'
    if (!groups.has(groupName)) groups.set(groupName, [])
    groups.get(groupName).push(prod)
  }
  return Array.from(groups.entries()).map(([kategori, items]) => ({ kategori, items }))
})

const productById = computed(() => {
  const map = new Map()
  for (const prod of props.products) {
    map.set(Number(prod.id), prod)
  }
  return map
})

const totalUnits = computed(() =>
  props.modelValue.reduce((sum, row) => sum + (Number(row.jumlah) || 0), 0)
)

const totalAmount = computed(() =>
  props.modelValue.reduce(
    (sum, row) => sum + (Number(row.jumlah) || 0) * (Number(row.harga_satuan) || 0),
    0
  )
)

function updateRow(index, patch) {
  const next = props.modelValue.map((row, idx) => (idx === index ? { ...row, ...patch } : row))
  emit('update:modelValue', next)
}

function onSelectProduct(index, rawValue) {
  const produkId = rawValue ? Number(rawValue) : ''
  const prod = productById.value.get(Number(produkId))
  const patch = { produk_id: produkId }
  if (props.withPrice && props.defaultPriceField && prod) {
    const defaultPrice = Number(prod[props.defaultPriceField]) || 0
    if (!props.modelValue[index]?.harga_satuan && defaultPrice > 0) {
      patch.harga_satuan = defaultPrice
    }
  }
  updateRow(index, patch)
}

function addRow() {
  const base = { produk_id: '', jumlah: 1 }
  if (props.withPrice) base.harga_satuan = ''
  emit('update:modelValue', [...props.modelValue, base])
}

function removeRow(index) {
  if (props.modelValue.length <= 1) return
  emit(
    'update:modelValue',
    props.modelValue.filter((_, idx) => idx !== index)
  )
}

function rowProduct(row) {
  return productById.value.get(Number(row.produk_id)) || null
}

function rowStock(row) {
  if (!row.produk_id) return null
  const val = props.stockMap[Number(row.produk_id)]
  return val === undefined ? 0 : Number(val)
}

function fieldError(index, field) {
  return props.errors[`items.${index}.${field}`] || ''
}
</script>

<template>
  <div class="doc-items-editor">
    <div class="doc-items-header">
      <span class="field-label">Daftar item produk</span>
      <button type="button" class="btn btn-secondary btn-sm" @click="addRow">
        <AppIcon name="plus" :size="15" />
        <span>Tambah baris</span>
      </button>
    </div>

    <p v-if="errors.items" class="field-error" role="alert">{{ errors.items }}</p>

    <div class="doc-items-list">
      <div v-for="(row, idx) in modelValue" :key="idx" class="doc-item-row">
        <div class="doc-item-col doc-item-product">
          <label class="field-label-sm" :for="`item-prod-${idx}`">Produk</label>
          <select
            :id="`item-prod-${idx}`"
            class="input"
            :value="row.produk_id"
            :aria-invalid="Boolean(fieldError(idx, 'produk_id'))"
            @change="onSelectProduct(idx, $event.target.value)"
          >
            <option value="">Pilih produk...</option>
            <optgroup v-for="grp in groupedProducts" :key="grp.kategori" :label="grp.kategori">
              <option v-for="prod in grp.items" :key="prod.id" :value="prod.id">
                {{ prod.sku }} - {{ prod.nama }} ({{ prod.satuan }})
              </option>
            </optgroup>
          </select>
          <p v-if="fieldError(idx, 'produk_id')" class="field-error">
            {{ fieldError(idx, 'produk_id') }}
          </p>
        </div>

        <div v-if="showStock" class="doc-item-col doc-item-stock">
          <span class="field-label-sm">Stok asal</span>
          <div class="doc-item-readonly mono">
            <template v-if="rowProduct(row)">
              {{ formatNumber(rowStock(row)) }} {{ rowProduct(row).satuan }}
            </template>
            <template v-else>-</template>
          </div>
        </div>

        <div class="doc-item-col doc-item-qty">
          <label class="field-label-sm" :for="`item-qty-${idx}`">Jumlah</label>
          <div class="doc-qty-wrap">
            <input
              :id="`item-qty-${idx}`"
              type="number"
              min="1"
              step="1"
              class="input mono"
              :value="row.jumlah"
              :aria-invalid="Boolean(fieldError(idx, 'jumlah'))"
              @input="updateRow(idx, { jumlah: $event.target.value === '' ? '' : Number($event.target.value) })"
            />
            <span v-if="rowProduct(row)" class="badge badge-draf">{{ rowProduct(row).satuan }}</span>
          </div>
          <p v-if="fieldError(idx, 'jumlah')" class="field-error">
            {{ fieldError(idx, 'jumlah') }}
          </p>
        </div>

        <div v-if="withPrice" class="doc-item-col doc-item-price">
          <label class="field-label-sm" :for="`item-price-${idx}`">Harga satuan (Rp)</label>
          <input
            :id="`item-price-${idx}`"
            type="number"
            min="1"
            step="1"
            class="input mono"
            :value="row.harga_satuan"
            :aria-invalid="Boolean(fieldError(idx, 'harga_satuan'))"
            @input="
              updateRow(idx, {
                harga_satuan: $event.target.value === '' ? '' : Number($event.target.value),
              })
            "
          />
          <p v-if="fieldError(idx, 'harga_satuan')" class="field-error">
            {{ fieldError(idx, 'harga_satuan') }}
          </p>
        </div>

        <div v-if="withPrice" class="doc-item-col doc-item-subtotal">
          <span class="field-label-sm">Subtotal</span>
          <div class="doc-item-readonly mono">
            {{ formatRupiah((Number(row.jumlah) || 0) * (Number(row.harga_satuan) || 0)) }}
          </div>
        </div>

        <div class="doc-item-col doc-item-action">
          <button
            type="button"
            class="btn-icon"
            :disabled="modelValue.length <= 1"
            :aria-label="`Hapus baris ${idx + 1}`"
            @click="removeRow(idx)"
          >
            <AppIcon name="trash" :size="16" />
          </button>
        </div>
      </div>
    </div>

    <div class="doc-items-summary">
      <span>Total baris: <strong class="mono">{{ modelValue.length }}</strong></span>
      <span>Total unit: <strong class="mono">{{ formatNumber(totalUnits) }}</strong></span>
      <span v-if="withPrice">
        Total nilai: <strong class="mono">{{ formatRupiah(totalAmount) }}</strong>
      </span>
    </div>
  </div>
</template>
