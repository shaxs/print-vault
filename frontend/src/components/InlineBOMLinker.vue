<script setup>
/**
 * InlineBOMLinker.vue
 *
 * Inline inventory-search widget that renders inside a BOM table cell.
 * Clicking "— Link item" activates a search input; selecting a result
 * PATCHes the BOM item with inventory_item + status='linked'.
 *
 * DESIGN_SYSTEM.md: CSS variables only. No modal (inline UX).
 *
 * Props:
 *   bomItem (Object) — the ProjectBOMItem row: { id, description, ... }
 *
 * Emits:
 *   linked(updatedBomItem) — full BOM item from PATCH response
 */
import { ref, nextTick } from 'vue'
import APIService from '../services/APIService'

const props = defineProps({
  bomItem: { type: Object, required: true },
})

const emit = defineEmits(['linked'])

// ── State ─────────────────────────────────────────────────────────────────────
const isActive = ref(false)
const inputRef = ref(null)
const query = ref('')
const results = ref([])
const isSearching = ref(false)
const isSaving = ref(false)
const dropdownStyle = ref({})
let searchTimer = null

// ── Position dropdown below the input (Teleport to body avoids overflow clip) ─
const computeDropdownPosition = () => {
  if (!inputRef.value) return
  const rect = inputRef.value.getBoundingClientRect()
  dropdownStyle.value = {
    top: (rect.bottom + window.scrollY) + 'px',
    left: (rect.left + window.scrollX) + 'px',
    width: Math.max(rect.width, 240) + 'px',
  }
}

// ── Activate / deactivate ─────────────────────────────────────────────────────
const activate = async () => {
  isActive.value = true
  query.value = ''
  results.value = []
  await nextTick()
  computeDropdownPosition()
  inputRef.value?.focus()
}

const deactivate = () => {
  clearTimeout(searchTimer)
  isActive.value = false
  query.value = ''
  results.value = []
  isSearching.value = false
}

// ── Inventory search ──────────────────────────────────────────────────────────
const search = async (q) => {
  if (q.length < 2) { results.value = []; return }
  isSearching.value = true
  try {
    const res = await APIService.getInventoryItems({ search: q })
    results.value = res.data.results ?? res.data
    await nextTick()
    computeDropdownPosition()
  } catch {
    results.value = []
  } finally {
    isSearching.value = false
  }
}

const handleInput = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => search(query.value), 250)
}

// ── Link selection ────────────────────────────────────────────────────────────
const selectItem = async (inventoryItem) => {
  isSaving.value = true
  try {
    const res = await APIService.updateBOMItem(props.bomItem.id, {
      inventory_item: inventoryItem.id,
      status: 'linked',
    })
    emit('linked', res.data)
    deactivate()
  } catch {
    deactivate()
  } finally {
    isSaving.value = false
  }
}

// ── Keyboard + blur ───────────────────────────────────────────────────────────
const handleKeydown = (e) => {
  if (e.key === 'Escape') deactivate()
}

const handleBlur = () => {
  // Delay so @mousedown.prevent on dropdown items can fire first
  setTimeout(deactivate, 160)
}
</script>

<template>
  <!-- Inactive: show trigger text -->
  <span v-if="!isActive" class="bom-linker-trigger" @click="activate">
    <span class="bom-linker-trigger-text">— Link item</span>
  </span>

  <!-- Active: show search input -->
  <div v-else class="bom-linker-wrap">
    <div class="bom-linker-input-row">
      <input
        ref="inputRef"
        v-model="query"
        type="text"
        class="bom-linker-input"
        placeholder="Search inventory…"
        autocomplete="off"
        :disabled="isSaving"
        @input="handleInput"
        @keydown="handleKeydown"
        @blur="handleBlur"
      />
      <span v-if="isSearching || isSaving" class="bom-linker-spinner">…</span>
      <button
        v-if="!isSaving"
        class="bom-linker-cancel"
        type="button"
        title="Cancel"
        @click="deactivate"
      >✕</button>
    </div>

    <!-- Teleport dropdown to body so it isn't clipped by table overflow -->
    <Teleport to="body">
      <ul
        v-if="results.length && isActive"
        class="bom-linker-dropdown"
        :style="dropdownStyle"
      >
        <li
          v-for="item in results"
          :key="item.id"
          class="bom-linker-dropdown-item"
          @mousedown.prevent="selectItem(item)"
        >
          <span class="bom-linker-result-title">{{ item.title }}</span>
          <span
            class="bom-linker-result-qty"
            :class="{ 'bom-linker-result-qty-over': item.quantity <= 0 }"
          >
            {{ item.quantity <= 0 ? '0 avail' : item.quantity + ' avail' }}
          </span>
        </li>
      </ul>
    </Teleport>
  </div>
</template>

<style scoped>
/* ── Trigger ─────────────────────────────────────────────────────────────────── */
.bom-linker-trigger {
  cursor: pointer;
  display: inline-block;
}

.bom-linker-trigger-text {
  color: var(--color-text-soft);
  font-size: 0.85rem;
  text-decoration: underline dotted;
  transition: color 0.15s;
}

.bom-linker-trigger:hover .bom-linker-trigger-text {
  color: var(--color-heading);
}

/* ── Input wrap ──────────────────────────────────────────────────────────────── */
.bom-linker-wrap {
  display: inline-flex;
  align-items: center;
}

.bom-linker-input-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.bom-linker-input {
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  color: var(--color-text);
  font-size: 0.82rem;
  padding: 0.2rem 1.6rem 0.2rem 0.4rem;
  width: 150px;
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.bom-linker-input:focus {
  border-color: var(--color-green, #48bb78);
  box-shadow: 0 0 0 2px rgba(72, 187, 120, 0.15);
}

.bom-linker-spinner {
  position: absolute;
  right: 1.6rem;
  color: var(--color-text-soft);
  font-size: 0.75rem;
  pointer-events: none;
}

.bom-linker-cancel {
  background: none;
  border: none;
  color: var(--color-text-soft);
  cursor: pointer;
  font-size: 0.75rem;
  padding: 0 0.15rem;
  line-height: 1;
  flex-shrink: 0;
}

.bom-linker-cancel:hover {
  color: var(--color-red, #e53e3e);
}
</style>

<!-- Dropdown is Teleported to <body> — scoped styles won't reach it.
     These rules use globally-unique class names so they're safe to be global. -->
<style>
.bom-linker-dropdown {
  position: absolute;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 0 0 4px 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  list-style: none;
  margin: 0;
  max-height: 200px;
  overflow-y: auto;
  padding: 0;
  z-index: 9999;
}

.bom-linker-dropdown-item {
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  display: flex;
  font-size: 0.875rem;
  gap: 0.5rem;
  justify-content: space-between;
  padding: 0.4rem 0.75rem;
}

.bom-linker-dropdown-item:last-child {
  border-bottom: none;
}

.bom-linker-dropdown-item:hover {
  background: var(--color-background-mute);
}

.bom-linker-result-title {
  color: var(--color-heading);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bom-linker-result-qty {
  color: var(--color-text-soft);
  font-size: 0.8rem;
  flex-shrink: 0;
}

.bom-linker-result-qty-over {
  color: var(--color-red, #e53e3e);
  font-weight: 600;
}
</style>
