<script setup>
import { computed, watch } from 'vue'

import AppIcon from '@/components/AppIcon'
import SearchSelect from '@/components/SearchSelect.vue'
import { KATEGORI_TYPE_LABELS } from '@/utils/constants'
import { formatMargin, formatNumber, formatRupiah } from '@/utils/format'

const props = defineProps({
  modelValue: { type: Array, required: true },
  products: { type: Array, default: () => [] },
  stockMap: { type: Object, default: () => ({}) },
  showStock: { type: Boolean, default: true },
  withPrice: { type: Boolean, default: false },
  defaultPriceField: { type: String, default: '' },
  // jumlah = angka positif, kurangi = diisi positif lalu disimpan negatif, hitung = stock fisik
  mode: { type: String, default: 'jumlah' },
  // dokumen yang mengeluarkan barang dari lokasi asal, jumlah di atas stock diberi peringatan
  outbound: { type: Boolean, default: false },
  stockLabel: { type: String, default: 'Stock asal' },
  disableZeroStock: { type: Boolean, default: false },
  errors: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue'])

const QTY_LABELS = { jumlah: 'Jumlah', kurangi: 'Jumlah berkurang', hitung: 'Stock fisik' }
const DEFAULT_QTY = { jumlah: 1, kurangi: -1, hitung: 0 }

// opsi produk dikelompokkan per kategori, stok tampil sebagai keterangan supaya mudah dipilih
const productOptions = computed(() => {
  const groups = new Map()
  for (const prod of props.products) {
    const groupName =
      prod.kategori?.nama || KATEGORI_TYPE_LABELS[prod.jenis] || 'Tanpa kategori'
    if (!groups.has(groupName)) groups.set(groupName, [])
    groups.get(groupName).push(prod)
  }
  return Array.from(groups.entries()).flatMap(([group, items]) =>
    items.map((prod) => {
      const blocked = props.disableZeroStock && Number(prod.stok || 0) <= 0
      const stock = prod.stok ?? null
      return {
        value: prod.id,
        label: `${prod.sku} - ${prod.nama} (${prod.satuan})`,
        hint: blocked ? 'Stock habis' : stock === null ? '' : `Stock ${formatNumber(stock)}`,
        group,
        disabled: blocked,
      }
    })
  )
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

// ganti mode ikut membalik tanda jumlah, opname tidak diubah karena selisihnya sudah bertanda
watch(
  () => props.mode,
  (mode) => {
    if (mode === 'hitung') return
    const sign = mode === 'kurangi' ? -1 : 1
    const next = props.modelValue.map((row) =>
      row.jumlah === '' ? row : { ...row, jumlah: sign * (Math.abs(Number(row.jumlah)) || 1) }
    )
    emit('update:modelValue', next)
  }
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
  // stock fisik mulai dari stock tercatat, jadi selisih awalnya 0 sampai user mengubahnya
  if (props.mode === 'hitung') patch.jumlah = 0
  if (props.withPrice && props.defaultPriceField && prod) {
    const defaultPrice = Number(prod[props.defaultPriceField]) || 0
    if (defaultPrice > 0) {
      patch.harga_satuan = defaultPrice
    }
  }
  updateRow(index, patch)
}

function addRow() {
  const base = { produk_id: '', jumlah: DEFAULT_QTY[props.mode] ?? 1 }
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
  if (val !== undefined) return Number(val)
  const prod = rowProduct(row)
  if (prod && prod.stok !== undefined && prod.stok !== null) return Number(prod.stok)
  return 0
}

// produk yang sudah ada di baris lain tidak bisa dipilih lagi (detail dokumen unik per produk)
function optionsFor(index) {
  const taken = new Set(
    props.modelValue
      .filter((row, idx) => idx !== index && row.produk_id)
      .map((row) => Number(row.produk_id))
  )
  if (!taken.size) return productOptions.value
  return productOptions.value.map((opt) =>
    taken.has(Number(opt.value))
      ? { ...opt, disabled: true, hint: 'Sudah dipilih di baris lain' }
      : opt
  )
}

// angka di input, row.jumlah selalu menyimpan selisih bertanda yang dikirim ke API
function displayQty(row) {
  if (row.jumlah === '') return ''
  if (props.mode === 'kurangi') return Math.abs(Number(row.jumlah))
  if (props.mode === 'hitung') return row.produk_id ? rowStock(row) + Number(row.jumlah) : ''
  return row.jumlah
}

function onQtyInput(index, raw) {
  if (raw === '') return updateRow(index, { jumlah: '' })
  const value = Number(raw)
  if (props.mode === 'kurangi') return updateRow(index, { jumlah: -Math.abs(value) })
  if (props.mode === 'hitung') {
    return updateRow(index, { jumlah: value - (rowStock(props.modelValue[index]) ?? 0) })
  }
  updateRow(index, { jumlah: value })
}

// keterangan di bawah jumlah: stock sesudahnya, atau peringatan bila melebihi stock
function qtyNote(row) {
  const product = rowProduct(row)
  if (!product || row.jumlah === '') return null
  const stock = rowStock(row)
  const delta = Number(row.jumlah)
  const exceeded = { warn: true, text: `Melebihi stock (${formatNumber(stock)} ${product.satuan})` }
  if (props.mode === 'jumlah') return props.outbound && delta > stock ? exceeded : null
  if (stock + delta < 0) return exceeded
  const after = `${formatNumber(stock + delta)} ${product.satuan}`
  if (props.mode === 'kurangi') return { warn: false, text: `Stock jadi ${after}` }
  if (delta === 0) return { warn: true, text: 'Sama dengan stock tercatat' }
  return { warn: false, text: `Selisih ${delta > 0 ? '+' : ''}${formatNumber(delta)}` }
}

const isSale = computed(() => props.defaultPriceField === 'harga_jual')

// harga acuan tetap tampil sebagai label (satu baris per harga), juga saat draf diubah
function priceRefs(row) {
  const product = rowProduct(row)
  if (!product) return []
  if (isSale.value) {
    return [`Standar ${formatRupiah(product.harga_jual)}`, `HPP ${formatRupiah(product.harga_beli)}`]
  }
  if (props.defaultPriceField === 'harga_beli') {
    return [`Harga beli terakhir ${formatRupiah(product.harga_beli)}`]
  }
  return []
}

function rowMargin(row) {
  const product = rowProduct(row)
  if (!isSale.value || !product || row.harga_satuan === '') return null
  const unitMargin = Number(row.harga_satuan) - (Number(product.harga_beli) || 0)
  return unitMargin * (Number(row.jumlah) || 0)
}

// harga di bawah HPP tetap boleh (BR-27), marginnya ditandai sebagai peringatan
function marginNote(row) {
  const margin = rowMargin(row)
  if (margin === null) return null
  const revenue = Number(row.harga_satuan) * (Number(row.jumlah) || 0)
  return { warn: margin < 0, text: `Margin ${formatMargin(margin, revenue)}` }
}

const totalMargin = computed(() =>
  props.modelValue.reduce((sum, row) => sum + (rowMargin(row) ?? 0), 0)
)

function fieldError(index, field) {
  if (field === 'jumlah') {
    return (
      props.errors[`items.${index}.jumlah`] ||
      props.errors[`items.${index}.jumlah_dikirim`] ||
      props.errors[`items.${index}.jumlah_diminta`] ||
      ''
    )
  }
  return props.errors[`items.${index}.${field}`] || ''
}
</script>

<template>
  <div class="doc-items-editor">
    <div class="doc-items-header">
      <span class="field-label">Daftar item produk</span>
      <button type="button" class="btn btn-post btn-sm" @click="addRow">
        <AppIcon name="plus" :size="15" />
        <span>Tambah baris</span>
      </button>
    </div>

    <p v-if="errors.items" class="field-error" role="alert">{{ errors.items }}</p>

    <div class="doc-items-list">
      <div v-for="(row, idx) in modelValue" :key="idx" class="doc-item-row">
        <div class="doc-item-col doc-item-product">
          <label class="field-label-sm" :for="`item-prod-${idx}`">Produk</label>
          <SearchSelect
            :id="`item-prod-${idx}`"
            :model-value="row.produk_id"
            :options="optionsFor(idx)"
            placeholder="Ketik SKU atau nama produk..."
            :invalid="Boolean(fieldError(idx, 'produk_id'))"
            @change="onSelectProduct(idx, $event)"
          />
          <p v-if="fieldError(idx, 'produk_id')" class="field-error">
            {{ fieldError(idx, 'produk_id') }}
          </p>
        </div>

        <div v-if="showStock" class="doc-item-col doc-item-stock">
          <span class="field-label-sm">{{ stockLabel }}</span>
          <div class="doc-item-readonly mono">
            <template v-if="rowProduct(row)">
              {{ formatNumber(rowStock(row)) }} {{ rowProduct(row).satuan }}
            </template>
            <template v-else>-</template>
          </div>
        </div>

        <div class="doc-item-col doc-item-qty">
          <label class="field-label-sm" :for="`item-qty-${idx}`">{{ QTY_LABELS[mode] }}</label>
          <div class="doc-qty-wrap">
            <input
              :id="`item-qty-${idx}`"
              type="number"
              :min="mode === 'hitung' ? 0 : 1"
              step="1"
              class="input mono"
              :value="displayQty(row)"
              :disabled="mode === 'hitung' && !row.produk_id"
              :aria-invalid="Boolean(fieldError(idx, 'jumlah'))"
              :aria-describedby="`item-qty-note-${idx}`"
              @input="onQtyInput(idx, $event.target.value)"
            />
            <span v-if="rowProduct(row)" class="badge badge-draf">{{ rowProduct(row).satuan }}</span>
          </div>
          <p v-if="fieldError(idx, 'jumlah')" class="field-error">
            {{ fieldError(idx, 'jumlah') }}
          </p>
          <p
            v-else-if="qtyNote(row)"
            :id="`item-qty-note-${idx}`"
            class="doc-item-note"
            :class="{ 'doc-item-note-warn': qtyNote(row).warn }"
          >
            {{ qtyNote(row).text }}
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
          <p v-for="line in priceRefs(row)" :key="line" class="doc-item-note">{{ line }}</p>
          <p
            v-if="marginNote(row)"
            class="doc-item-note"
            :class="{ 'doc-item-note-warn': marginNote(row).warn }"
          >
            {{ marginNote(row).text }}
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
      <span v-if="mode === 'jumlah'">
        Total unit: <strong class="mono">{{ formatNumber(totalUnits) }}</strong>
      </span>
      <span v-else>
        Total selisih:
        <strong class="mono">{{ totalUnits > 0 ? '+' : '' }}{{ formatNumber(totalUnits) }}</strong>
      </span>
      <span v-if="withPrice">
        Total nilai: <strong class="mono">{{ formatRupiah(totalAmount) }}</strong>
      </span>
      <span v-if="isSale">
        Margin:
        <strong class="mono" :class="{ 'text-danger': totalMargin < 0 }">
          {{ formatRupiah(totalMargin) }}
        </strong>
      </span>
    </div>
  </div>
</template>
