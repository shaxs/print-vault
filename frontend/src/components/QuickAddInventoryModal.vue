<script setup>
/**
 * QuickAddInventoryModal.vue
 *
 * One-step "buy and link" flow for BOM items flagged as Needs Purchase.
 * Creates a new InventoryItem pre-populated from the BOM item description,
 * then immediately links it back to the BOM item — setting status to 'linked'
 * and triggering the reservation model automatically.
 *
 * DESIGN_SYSTEM.md: Uses BaseModal. CSS variables only.
 *
 * Props:
 *   show (Boolean)    — controls modal visibility
 *   bomItem (Object)  — the ProjectBOMItem record:
 *                         { id, description, quantity_needed, project_id }
 *
 * Emits:
 *   close             — user closed or cancelled
 *   linked(bomItem)   — inventory created + BOM item linked; payload is the
 *                       updated BOM item from the PATCH response
 */
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import BaseModal from './BaseModal.vue'
import APIService from '../services/APIService'

const props = defineProps({
  show: { type: Boolean, required: true },
  bomItem: { type: Object, default: null },
})

const emit = defineEmits(['close', 'linked'])

const router = useRouter()

// ── Lookup data ───────────────────────────────────────────────────────────────
const partTypes = ref([])
const locations = ref([])

const loadLookups = async () => {
  try {
    const [ptRes, locRes] = await Promise.all([
      APIService.getPartTypes(),
      APIService.getLocations(),
    ])
    partTypes.value = ptRes.data.results ?? ptRes.data
    locations.value = locRes.data.results ?? locRes.data
  } catch {
    // non-fatal — selects remain empty and fields are optional
  }
}

// Load lookups the first time the modal opens
watch(
  () => props.show,
  (isOpen) => {
    if (isOpen) {
      resetForm()
      if (partTypes.value.length === 0 || locations.value.length === 0) {
        loadLookups()
      }
    }
  },
)

// ── Form state ────────────────────────────────────────────────────────────────
const title = ref('')
const quantity = ref(1)
const selectedPartTypeId = ref('')
const selectedLocationId = ref('')
const cost = ref('')
const photoFile = ref(null)
const photoPreview = ref(null)
const photoInputRef = ref(null)
const saving = ref(false)
const errorMsg = ref('')

const handlePhotoChange = (e) => {
  const file = e.target.files[0]
  if (file) {
    photoFile.value = file
    photoPreview.value = URL.createObjectURL(file)
  }
}

const clearPhoto = () => {
  if (photoPreview.value) URL.revokeObjectURL(photoPreview.value)
  photoFile.value = null
  photoPreview.value = null
  if (photoInputRef.value) photoInputRef.value.value = ''
}

const resetForm = () => {
  title.value = props.bomItem?.description ?? ''
  quantity.value = props.bomItem?.quantity_needed ?? 1
  selectedPartTypeId.value = ''
  selectedLocationId.value = ''
  cost.value = ''
  clearPhoto()
  errorMsg.value = ''
}

// ── Save ──────────────────────────────────────────────────────────────────────
const buildFormData = () => {
  const formData = new FormData()
  formData.append('title', title.value.trim())
  formData.append('quantity', quantity.value)
  if (cost.value) formData.append('cost', cost.value)
  if (photoFile.value) formData.append('photo', photoFile.value)

  if (selectedPartTypeId.value) {
    const pt = partTypes.value.find((p) => p.id === Number(selectedPartTypeId.value))
    if (pt) formData.append('part_type', JSON.stringify({ name: pt.name }))
  }
  if (selectedLocationId.value) {
    const loc = locations.value.find((l) => l.id === Number(selectedLocationId.value))
    if (loc) formData.append('location', JSON.stringify({ name: loc.name }))
  }
  return formData
}

const performSave = async () => {
  if (!title.value.trim()) { errorMsg.value = 'Name is required.'; return null }
  if (!quantity.value || quantity.value < 1) { errorMsg.value = 'Quantity must be at least 1.'; return null }

  saving.value = true
  errorMsg.value = ''

  try {
    const createRes = await APIService.createInventoryItem(buildFormData())
    const newInventoryItem = createRes.data

    const patchRes = await APIService.updateBOMItem(props.bomItem.id, {
      inventory_item: newInventoryItem.id,
      status: 'linked',
    })

    return { newInventoryItem, updatedBomItem: patchRes.data }
  } catch (err) {
    console.error('QuickAddInventoryModal error:', err)
    const detail =
      err.response?.data?.title?.[0] ||
      err.response?.data?.detail ||
      err.response?.data?.non_field_errors?.[0] ||
      null
    errorMsg.value = detail ? `Save failed: ${detail}` : 'Something went wrong. Please try again.'
    return null
  } finally {
    saving.value = false
  }
}

const handleSave = async () => {
  const result = await performSave()
  if (result) emit('linked', result.updatedBomItem)
}

const handleSaveAndView = async () => {
  const result = await performSave()
  if (result) {
    emit('linked', result.updatedBomItem)
    router.push(`/item/${result.newInventoryItem.id}`)
  }
}
</script>

<template>
  <BaseModal
    :show="show"
    title="Add to Inventory"
    @close="emit('close')"
  >
    <div class="quick-add-content">

      <!-- Context hint -->
      <div class="context-hint">
        Adding inventory for BOM item:
        <strong>{{ bomItem?.description }}</strong>
        — it will be automatically linked once saved.
      </div>

      <!-- Error message -->
      <div v-if="errorMsg" class="form-error">{{ errorMsg }}</div>

      <!-- Name -->
      <div class="form-group">
        <label class="form-label" for="qa-title">Name <span class="required">*</span></label>
        <input
          id="qa-title"
          v-model="title"
          type="text"
          class="form-input"
          placeholder="e.g. M3×8 SHCS"
        />
      </div>

      <!-- Quantity -->
      <div class="form-group">
        <label class="form-label" for="qa-qty">
          Quantity <span class="required">*</span>
        </label>
        <input
          id="qa-qty"
          v-model.number="quantity"
          type="number"
          min="1"
          class="form-input form-input-narrow"
        />
        <p class="form-hint">
          BOM needs {{ bomItem?.quantity_needed }}. Enter the actual amount you received.
        </p>
      </div>

      <!-- Part Type (optional) -->
      <div class="form-group">
        <label class="form-label" for="qa-part-type">Part Type <span class="optional">(optional)</span></label>
        <select id="qa-part-type" v-model="selectedPartTypeId" class="form-select">
          <option value="">— None —</option>
          <option v-for="pt in partTypes" :key="pt.id" :value="pt.id">{{ pt.name }}</option>
        </select>
      </div>

      <!-- Location (optional) -->
      <div class="form-group">
        <label class="form-label" for="qa-location">Storage Location <span class="optional">(optional)</span></label>
        <select id="qa-location" v-model="selectedLocationId" class="form-select">
          <option value="">— None —</option>
          <option v-for="loc in locations" :key="loc.id" :value="loc.id">{{ loc.name }}</option>
        </select>
      </div>

      <!-- Photo (optional) -->
      <div class="form-group">
        <label class="form-label" for="qa-photo">Photo <span class="optional">(optional)</span></label>
        <input
          id="qa-photo"
          ref="photoInputRef"
          type="file"
          accept="image/*"
          class="form-file-input"
          @change="handlePhotoChange"
        />
        <div v-if="photoPreview" class="photo-preview">
          <img :src="photoPreview" alt="Preview" />
          <button type="button" class="photo-clear-btn" @click="clearPhoto">Remove</button>
        </div>
      </div>

      <!-- Cost (optional) -->
      <div class="form-group">
        <label class="form-label" for="qa-cost">Cost per Unit <span class="optional">(optional)</span></label>
        <input
          id="qa-cost"
          v-model="cost"
          type="number"
          min="0"
          step="0.01"
          class="form-input form-input-narrow"
          placeholder="0.00"
        />
      </div>

    </div>

    <template #footer>
      <button :disabled="saving" class="btn btn-secondary" @click="emit('close')">
        Cancel
      </button>
      <button :disabled="saving" class="btn btn-success" @click="handleSaveAndView">
        {{ saving ? 'Saving…' : 'Add &amp; View' }}
      </button>
      <button :disabled="saving" class="btn btn-primary" @click="handleSave">
        {{ saving ? 'Saving…' : 'Add to Inventory' }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.quick-add-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.context-hint {
  padding: 0.75rem 1rem;
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: 6px;
  font-size: 0.875rem;
  color: var(--color-text);
  line-height: 1.5;
}

.form-error {
  padding: 0.75rem 1rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 6px;
  font-size: 0.875rem;
  color: rgb(220, 38, 38);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-heading);
}

.required {
  color: rgb(239, 68, 68);
}

.optional {
  font-weight: 400;
  color: var(--color-text-muted);
  font-size: 0.8rem;
}

.form-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
  width: 100%;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-brand);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}

.form-input-narrow {
  max-width: 140px;
}

.form-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
  width: 100%;
  box-sizing: border-box;
}

.form-select:focus {
  outline: none;
  border-color: var(--color-brand);
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.15);
}

.form-hint {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  margin: 0;
  font-style: italic;
}

.form-file-input {
  font-size: 0.875rem;
  color: var(--color-text);
}

.photo-preview {
  margin-top: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.photo-preview img {
  max-width: 100%;
  max-height: 180px;
  object-fit: contain;
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.photo-clear-btn {
  align-self: flex-start;
  padding: 3px 10px;
  font-size: 0.78rem;
  background: var(--color-background-mute);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
}
.photo-clear-btn:hover {
  background: var(--color-background-soft);
  color: var(--color-text);
}
</style>
