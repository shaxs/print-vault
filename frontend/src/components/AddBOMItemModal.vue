<script setup>
/**
 * AddBOMItemModal.vue
 * Modal for adding a single BOM item to an existing project BOM.
 * Uses the standard BaseModal pattern per DESIGN_SYSTEM.md.
 */
import { ref, computed, watch } from 'vue'
import BaseModal from './BaseModal.vue'
import APIService from '../services/APIService'

const props = defineProps({
  show: { type: Boolean, required: true },
  projectId: { type: [Number, String], required: true },
  preSelectedInventoryItem: { type: Object, default: null },
  editItem: { type: Object, default: null },
})

const emit = defineEmits(['close', 'added', 'updated'])

const isEditMode = computed(() => props.editItem !== null)

// ── Form state ────────────────────────────────────────────────────────────────
const description = ref('')
const quantityNeeded = ref(1)
const needsPurchase = ref(false)
const notes = ref('')

// ── Inventory search ──────────────────────────────────────────────────────────
const inventoryQuery = ref('')
const searchResults = ref([])
const selectedInventoryItem = ref(null)
const showDropdown = ref(false)
const isSearching = ref(false)
let searchTimer = null

const searchInventory = async (query) => {
  if (query.length < 2) {
    searchResults.value = []
    showDropdown.value = false
    return
  }
  isSearching.value = true
  try {
    const response = await APIService.getInventoryItems({ search: query })
    searchResults.value = response.data.results ?? response.data
    showDropdown.value = searchResults.value.length > 0
  } catch {
    searchResults.value = []
  } finally {
    isSearching.value = false
  }
}

watch(inventoryQuery, (val) => {
  if (needsPurchase.value) return
  if (selectedInventoryItem.value && val !== selectedInventoryItem.value.title) {
    selectedInventoryItem.value = null
  }
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => searchInventory(val), 250)
})

const selectItem = (item) => {
  selectedInventoryItem.value = item
  inventoryQuery.value = item.title
  showDropdown.value = false
}

const closeDropdown = () => {
  setTimeout(() => { showDropdown.value = false }, 150)
}

// ── Needs-purchase toggle ─────────────────────────────────────────────────────
watch(needsPurchase, (val) => {
  if (val) {
    selectedInventoryItem.value = null
    inventoryQuery.value = ''
    showDropdown.value = false
  }
})

// ── Submit ───────────────────────────────────────────────────────────────────
const isSaving = ref(false)
const errorMessage = ref('')

const handleSubmit = async () => {
  if (!description.value.trim()) {
    errorMessage.value = 'Description is required.'
    return
  }
  if (!quantityNeeded.value || quantityNeeded.value < 1) {
    errorMessage.value = 'Quantity must be at least 1.'
    return
  }
  errorMessage.value = ''
  isSaving.value = true
  try {
    const payload = {
      description: description.value.trim(),
      quantity_needed: quantityNeeded.value,
      status: needsPurchase.value
        ? 'needs_purchase'
        : selectedInventoryItem.value
          ? 'linked'
          : 'unlinked',
      inventory_item: needsPurchase.value ? null : (selectedInventoryItem.value?.id ?? null),
      notes: notes.value.trim(),
    }
    if (isEditMode.value) {
      const response = await APIService.updateBOMItem(props.editItem.id, payload)
      emit('updated', response.data)
    } else {
      payload.project = props.projectId
      const response = await APIService.createBOMItem(payload)
      emit('added', response.data)
    }
    resetForm()
    emit('close')
  } catch (err) {
    errorMessage.value = err?.response?.data?.detail ?? (isEditMode.value ? 'Failed to update BOM item.' : 'Failed to add BOM item.')
  } finally {
    isSaving.value = false
  }
}

const resetForm = () => {
  description.value = ''
  quantityNeeded.value = 1
  needsPurchase.value = false
  notes.value = ''
  inventoryQuery.value = ''
  selectedInventoryItem.value = null
  searchResults.value = []
  showDropdown.value = false
  errorMessage.value = ''
}

// Reset form when modal opens; pre-fill from editItem or preSelectedInventoryItem.
// { immediate: true } is required so the form populates when the component is first
// mounted with show already true (e.g. via v-if + :show set in the same tick).
watch(() => props.show, (val) => {
  if (val) {
    resetForm()
    if (props.editItem) {
      // Edit existing BOM item
      description.value = props.editItem.description ?? ''
      quantityNeeded.value = props.editItem.quantity_needed ?? 1
      notes.value = props.editItem.notes ?? ''
      if (props.editItem.status === 'needs_purchase') {
        needsPurchase.value = true
      } else if (props.editItem.inventory_item) {
        selectedInventoryItem.value = {
          id: props.editItem.inventory_item,
          title: props.editItem.inventory_item_title ?? '',
          quantity: props.editItem.inventory_item_qty ?? 0,
        }
        inventoryQuery.value = props.editItem.inventory_item_title ?? ''
      }
    } else if (props.preSelectedInventoryItem) {
      description.value = props.preSelectedInventoryItem.title
      selectedInventoryItem.value = props.preSelectedInventoryItem
      inventoryQuery.value = props.preSelectedInventoryItem.title
    }
  }
}, { immediate: true })
</script>

<template>
  <BaseModal :show="show" :title="isEditMode ? 'Edit BOM Item' : 'Add BOM Item'" @close="emit('close')">
    <div class="bom-modal-form">
      <p v-if="errorMessage" class="form-error">{{ errorMessage }}</p>

      <!-- Description -->
      <div class="form-group">
        <label class="form-label" for="bom-desc">Description <span class="required">*</span></label>
        <input
          id="bom-desc"
          v-model="description"
          type="text"
          class="form-control"
          placeholder="e.g. M3×8 SHCS"
          maxlength="255"
          @keydown.enter.prevent="handleSubmit"
        />
      </div>

      <!-- Quantity -->
      <div class="form-group">
        <label class="form-label" for="bom-qty">Quantity Needed <span class="required">*</span></label>
        <input
          id="bom-qty"
          v-model.number="quantityNeeded"
          type="number"
          min="1"
          class="form-control qty-input"
          @keydown.enter.prevent="handleSubmit"
        />
      </div>

      <!-- Need to Purchase toggle -->
      <div class="form-group checkbox-group">
        <label class="checkbox-label">
          <input v-model="needsPurchase" type="checkbox" />
          <span>Need to Purchase (not in inventory)</span>
        </label>
      </div>

      <!-- Inventory search — hidden when needs_purchase checked -->
      <div v-if="!needsPurchase" class="form-group inventory-search-group">
        <label class="form-label" for="bom-inv">Link to Inventory Item</label>
        <div class="search-wrapper">
          <input
            id="bom-inv"
            v-model="inventoryQuery"
            type="text"
            class="form-control"
            placeholder="Search inventory…"
            autocomplete="off"
            @blur="closeDropdown"
          />
          <span v-if="isSearching" class="search-spinner">…</span>
          <ul v-if="showDropdown" class="search-dropdown">
            <li
              v-for="result in searchResults"
              :key="result.id"
              class="dropdown-item"
              @mousedown.prevent="selectItem(result)"
            >
              <span class="item-title">{{ result.title }}</span>
              <span class="item-qty">Qty: {{ result.quantity }}</span>
            </li>
          </ul>
        </div>
      </div>

      <!-- Notes -->
      <div class="form-group">
        <label class="form-label" for="bom-notes">Notes (optional)</label>
        <textarea
          id="bom-notes"
          v-model="notes"
          class="form-control"
          rows="2"
          placeholder="e.g. x4 per unit for 300mm build"
        />
      </div>
    </div>

    <template #footer>
      <button type="button" class="btn btn-secondary btn-sm" @click="emit('close')">Cancel</button>
      <button
        type="button"
        class="btn btn-primary btn-sm"
        :disabled="isSaving"
        @click="handleSubmit"
      >
        {{ isSaving ? (isEditMode ? 'Saving…' : 'Adding…') : (isEditMode ? 'Save Changes' : 'Add Item') }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.bom-modal-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.25rem 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--color-heading);
}

.required {
  color: var(--color-red);
}

.form-control {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.95rem;
  width: 100%;
  box-sizing: border-box;
}

.form-control:focus {
  outline: none;
  border-color: var(--color-blue);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.qty-input {
  max-width: 120px;
}

.checkbox-group {
  flex-direction: row;
  align-items: center;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--color-text);
}

.inventory-search-group {
  position: relative;
}

.search-wrapper {
  position: relative;
}

.search-spinner {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.8rem;
  color: var(--color-text-soft);
}

.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-top: none;
  border-radius: 0 0 4px 4px;
  max-height: 180px;
  overflow-y: auto;
  list-style: none;
  margin: 0;
  padding: 0;
  z-index: 100;
}

.dropdown-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 0.9rem;
  border-bottom: 1px solid var(--color-border);
}

.dropdown-item:last-child {
  border-bottom: none;
}

.dropdown-item:hover {
  background: var(--color-background-mute);
}

.item-title {
  color: var(--color-heading);
}

.item-qty {
  font-size: 0.8rem;
  color: var(--color-text-soft);
}

.selected-indicator {
  font-size: 0.85rem;
  color: var(--color-green);
  margin: 0.25rem 0 0;
}

.form-error {
  color: var(--color-red);
  font-size: 0.875rem;
  background: color-mix(in srgb, var(--color-red) 10%, transparent);
  padding: 0.5rem 0.75rem;
  border-radius: 4px;
  margin: 0;
}
</style>
