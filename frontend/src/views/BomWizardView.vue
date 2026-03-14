<script setup>
/**
 * BomWizardView.vue
 * Rapid-entry BOM wizard for quickly entering many BOM line items at once.
 * Route: /projects/:id/bom/edit
 *
 * 3D printer builder's workflow: user has the creator's BOM open (GitHub README,
 * Google Sheet, PDF), and blasts through entries without interruption.
 * Press Enter to add a row → inputs clear → repeat → Done when finished.
 */
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import DataTable from '../components/DataTable.vue'
import AddBOMItemModal from '../components/AddBOMItemModal.vue'
import QuickAddInventoryModal from '../components/QuickAddInventoryModal.vue'

const route = useRoute()
const router = useRouter()

// ── Project context ───────────────────────────────────────────────────────────
const projectId = computed(() => route.params.id)
const project = ref(null)
const existingItems = ref([])
const isLoading = ref(true)
const errorBanner = ref('')

const loadProject = async () => {
  try {
    const [projRes, bomRes] = await Promise.all([
      APIService.getProject(projectId.value),
      APIService.getBOMItems(projectId.value),
    ])
    project.value = projRes.data
    existingItems.value = bomRes.data.results ?? bomRes.data
  } catch {
    errorBanner.value = 'Failed to load project. Please go back and try again.'
  } finally {
    isLoading.value = false
  }
}

// ── Input row state ───────────────────────────────────────────────────────────
const descInput = ref('')
const qtyInput = ref(1)
const needsPurchase = ref(false)
const notesInput = ref('')
const selectedInventoryItem = ref(null)
const inventoryQuery = ref('')
const searchResults = ref([])
const showDropdown = ref(false)
const isSearching = ref(false)
let searchTimer = null

const descRef = ref(null)
const qtyRef = ref(null)
const invRef = ref(null)

// Inventory search
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

const handleInvInput = () => {
  if (selectedInventoryItem.value && inventoryQuery.value !== selectedInventoryItem.value.title) {
    selectedInventoryItem.value = null
  }
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => searchInventory(inventoryQuery.value), 250)
}

const handleInvFocus = () => {
  if (inventoryQuery.value.length >= 2) showDropdown.value = searchResults.value.length > 0
}

const closeDropdown = () => {
  setTimeout(() => { showDropdown.value = false }, 150)
}

const selectInventoryItem = (item) => {
  selectedInventoryItem.value = item
  inventoryQuery.value = item.title
  showDropdown.value = false
}

const handleInvEnter = () => {
  if (showDropdown.value) {
    showDropdown.value = false
  } else {
    addRow()
  }
}

const handleNeedsPurchaseChange = () => {
  if (needsPurchase.value) {
    selectedInventoryItem.value = null
    inventoryQuery.value = ''
    showDropdown.value = false
  }
}

// ── Validation ────────────────────────────────────────────────────────────────
const inputError = ref('')

const validateRow = () => {
  if (!descInput.value.trim()) {
    inputError.value = 'Description is required.'
    descRef.value?.focus()
    return false
  }
  if (!qtyInput.value || qtyInput.value < 1) {
    inputError.value = 'Quantity must be at least 1.'
    qtyRef.value?.focus()
    return false
  }
  inputError.value = ''
  return true
}

// ── Add row ───────────────────────────────────────────────────────────────────
const isSavingRow = ref(false)
const sessionItems = ref([])  // items added this session (shown in table as pending)

const addRow = async () => {
  if (!validateRow()) return
  isSavingRow.value = true
  const payload = {
    project: projectId.value,
    description: descInput.value.trim(),
    quantity_needed: qtyInput.value,
    status: needsPurchase.value
      ? 'needs_purchase'
      : selectedInventoryItem.value ? 'linked' : 'unlinked',
    inventory_item: needsPurchase.value ? null : (selectedInventoryItem.value?.id ?? null),
    notes: notesInput.value.trim(),
    sort_order: existingItems.value.length + sessionItems.value.length,
  }

  try {
    const response = await APIService.createBOMItem(payload)
    sessionItems.value.push(response.data)
    // Clear for next row
    descInput.value = ''
    qtyInput.value = 1
    needsPurchase.value = false
    notesInput.value = ''
    inventoryQuery.value = ''
    selectedInventoryItem.value = null
    searchResults.value = []
    showDropdown.value = false
    await nextTick()
    descRef.value?.focus()
  } catch (err) {
    inputError.value = err?.response?.data?.detail ?? 'Failed to save row. Please try again.'
  } finally {
    isSavingRow.value = false
  }
}

// ── Remove any item (existing or session) ────────────────────────────────────
const removeItem = async (item) => {
  const returnNote = item.inventory_item_title
    ? `\n\n${item.quantity_needed}× ${item.inventory_item_title} will be returned to Inventory.`
    : ''
  if (!confirm(`Remove "${item.description}" from this BOM?${returnNote}`)) return
  try {
    await APIService.deleteBOMItem(item.id)
    const exIdx = existingItems.value.findIndex(i => i.id === item.id)
    if (exIdx >= 0) {
      existingItems.value.splice(exIdx, 1)
    } else {
      const seIdx = sessionItems.value.findIndex(i => i.id === item.id)
      if (seIdx >= 0) sessionItems.value.splice(seIdx, 1)
    }
  } catch {
    errorBanner.value = 'Failed to remove item.'
  }
}

// ── Edit an item via modal ───────────────────────────────────────────────────
const showWizardEditModal = ref(false)
const wizardEditItem = ref(null)

const openWizardEdit = (item) => {
  wizardEditItem.value = item
  showWizardEditModal.value = true
}

const handleWizardItemUpdated = (updatedItem) => {
  // Update in-place in whichever array holds this item
  const exIdx = existingItems.value.findIndex(i => i.id === updatedItem.id)
  if (exIdx >= 0) {
    existingItems.value[exIdx] = updatedItem
  } else {
    const seIdx = sessionItems.value.findIndex(i => i.id === updatedItem.id)
    if (seIdx >= 0) sessionItems.value[seIdx] = updatedItem
  }
  showWizardEditModal.value = false
  wizardEditItem.value = null
}

// ── Quick Add to Inventory + Link ────────────────────────────────────────────
const quickAddBomItem = ref(null)
const showQuickAddModal = ref(false)

const openQuickAdd = (item) => {
  quickAddBomItem.value = item
  showQuickAddModal.value = true
}

// ── Done ─────────────────────────────────────────────────────────────────────
const goBack = () => {
  router.push({ name: 'project-detail', params: { id: projectId.value } })
}

// ── BOM status helpers ────────────────────────────────────────────────────────
const STATUS_LABELS = {
  covered: 'Covered',
  low: 'Running Low',
  overallocated: 'Overallocated',
  needs_purchase: 'Purchase',
  unlinked: 'Not Linked',
  linked: 'Linked',
}

const STATUS_CLASSES = {
  covered: 'badge-covered',
  low: 'badge-low',
  overallocated: 'badge-overallocated',
  needs_purchase: 'badge-purchase',
  unlinked: 'badge-unlinked',
  linked: 'badge-covered',
}

const getStatusLabel = (status) => STATUS_LABELS[status] ?? status
const getStatusClass = (status) => STATUS_CLASSES[status] ?? ''

// ── Table headers ─────────────────────────────────────────────────────────────
const tableHeaders = [
  { text: '#', value: '_rowNum', sortable: false },
  { text: 'Description', value: 'description' },
  { text: 'Qty', value: 'quantity_needed' },
  { text: 'Inventory Item', value: 'inventory_item_title' },
  { text: 'Status', value: 'status', sortable: false },
  { text: 'Actions', value: 'actions', sortable: false },
]

const allItems = computed(() =>
  [...existingItems.value, ...sessionItems.value].map((item, i) => ({ ...item, _rowNum: i + 1 }))
)

// ── Status filter ──────────────────────────────────────────────────────────────
const statusFilter = ref('all')

const STATUS_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'covered', label: 'Covered' },
  { value: 'low', label: 'Running Low' },
  { value: 'overallocated', label: 'Overallocated' },
  { value: 'needs_purchase', label: 'Needs Purchase' },
  { value: 'unlinked', label: 'Not Linked' },
]

const getItemStatus = (item) => item.allocation_status ?? item.status ?? 'unlinked'

const statusCounts = computed(() => {
  const counts = { all: allItems.value.length }
  for (const item of allItems.value) {
    const s = getItemStatus(item)
    counts[s] = (counts[s] || 0) + 1
  }
  return counts
})

const activeStatusFilters = computed(() =>
  STATUS_FILTERS.filter((f) => f.value === 'all' || statusCounts.value[f.value])
)

const filteredItems = computed(() => {
  if (statusFilter.value === 'all') return allItems.value
  return allItems.value.filter((item) => getItemStatus(item) === statusFilter.value)
})

onMounted(async () => {
  await loadProject()
  await nextTick()
  descRef.value?.focus()
})
</script>

<template>
  <div class="page-container">
    <div v-if="isLoading" class="loading-state"><p>Loading project…</p></div>

    <div v-else class="wizard-container">
      <!-- Header -->
      <div class="wizard-header">
        <div class="wizard-title-section">
          <button class="btn-back" @click="goBack">← Back to Project</button>
          <h1 class="wizard-title">
            BOM Wizard
            <span class="project-name" v-if="project">— {{ project.project_name }}</span>
          </h1>
          <p class="wizard-hint">
            Enter each part from your build's BOM one at a time.
            Press <kbd>Enter</kbd> to add a row and start the next item.
          </p>
        </div>
        <button class="btn btn-primary done-btn" @click="goBack">
          Done ({{ allItems.length }} item{{ allItems.length !== 1 ? 's' : '' }})
        </button>
      </div>

      <!-- Error banner -->
      <div v-if="errorBanner" class="error-banner">{{ errorBanner }}</div>

      <!-- Input row -->
      <div class="input-card">
        <div v-if="inputError" class="input-error">{{ inputError }}</div>
        <div class="input-row">
          <!-- Description -->
          <div class="field-group field-desc">
            <label class="field-label">Description</label>
            <input
              ref="descRef"
              v-model="descInput"
              type="text"
              class="form-control"
              placeholder="e.g. M3×8 SHCS"
              maxlength="255"
              @keydown.enter.prevent="addRow"
            />
          </div>

          <!-- Quantity -->
          <div class="field-group field-qty">
            <label class="field-label">Qty</label>
            <input
              ref="qtyRef"
              v-model.number="qtyInput"
              type="number"
              min="1"
              class="form-control"
              @keydown.enter.prevent="addRow"
            />
          </div>

          <!-- Inventory search -->
          <div class="field-group field-inv" :class="{ 'field-disabled': needsPurchase }">
            <label class="field-label">Inventory Item</label>
            <div class="inv-search-wrap">
              <input
                ref="invRef"
                v-model="inventoryQuery"
                type="text"
                class="form-control"
                placeholder="Search inventory…"
                autocomplete="off"
                :disabled="needsPurchase"
                @input="handleInvInput"
                @focus="handleInvFocus"
                @blur="closeDropdown"
                @keydown.enter.prevent="handleInvEnter"
              />
              <span v-if="isSearching" class="search-spinner">…</span>
              <ul v-if="showDropdown && !needsPurchase" class="inv-dropdown">
                <li
                  v-for="result in searchResults"
                  :key="result.id"
                  class="inv-dropdown-item"
                  @mousedown.prevent="selectInventoryItem(result)"
                >
                  <span class="result-title">{{ result.title }}</span>
                  <span class="result-qty" :class="result.quantity < 0 ? 'result-qty-overallocated' : ''">
                    {{ result.quantity < 0 ? '0 available (overallocated)' : result.quantity + ' available' }}
                  </span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Need to Purchase -->
          <div class="field-group field-purchase">
            <label class="field-label">Need to Purchase?</label>
            <label class="checkbox-label">
              <input
                v-model="needsPurchase"
                type="checkbox"
                @change="handleNeedsPurchaseChange"
              />
              <span>Yes</span>
            </label>
          </div>

          <!-- Notes -->
          <div class="field-group field-notes">
            <label class="field-label">Notes (optional)</label>
            <input
              v-model="notesInput"
              type="text"
              class="form-control"
              placeholder="Variant notes, etc."
              @keydown.enter.prevent="addRow"
            />
          </div>

          <!-- Add button -->
          <div class="field-group field-add">
            <label class="field-label">&nbsp;</label>
            <button
              class="btn-add"
              :disabled="isSavingRow"
              @click="addRow"
            >
              {{ isSavingRow ? '…' : 'Add' }}
            </button>
          </div>
        </div>
        <!-- Selected inventory item indicator (separate row, no layout shift) -->
        <p v-if="selectedInventoryItem && !needsPurchase" class="inv-selected-bar">
          ✓ Linked: {{ selectedInventoryItem.title }} ({{ selectedInventoryItem.quantity < 0 ? '0 available — overallocated' : selectedInventoryItem.quantity + ' available' }})
        </p>
      </div>

      <!-- BOM table -->
      <div class="bom-table-section">
        <div class="bom-table-header">
          <h3>
            Items Added ({{ allItems.length }})
            <span v-if="statusFilter !== 'all'" class="filter-count-hint">
              — showing {{ filteredItems.length }}
            </span>
          </h3>
        </div>

        <!-- Status filter chips -->
        <div v-if="allItems.length > 0" class="bom-filter-chips">
          <button
            v-for="f in activeStatusFilters"
            :key="f.value"
            :class="['bom-chip', { 'bom-chip-active': statusFilter === f.value }]"
            @click="statusFilter = f.value"
          >
            {{ f.label }}
            <span v-if="f.value !== 'all'" class="chip-count">{{ statusCounts[f.value] ?? 0 }}</span>
          </button>
        </div>

        <p v-if="allItems.length === 0" class="empty-hint">
          No items yet — start entering rows above.
        </p>

        <DataTable
          v-else
          :headers="tableHeaders"
          :items="filteredItems"
          :visible-columns="tableHeaders.map((h) => h.value)"
          empty-message="No items match the selected filter."
          class="bom-wizard-table"
        >
          <template #cell-_rowNum="{ item }">
            <span class="row-num">{{ item._rowNum }}</span>
          </template>
          <template #cell-description="{ item }">
            <div style="min-width:0">
              <span class="cell-truncate" :title="item.description">{{ item.description }}</span>
              <span v-if="item.notes" class="item-notes cell-truncate" :title="item.notes">{{ item.notes }}</span>
            </div>
          </template>
          <template #cell-inventory_item_title="{ item }">
            <span v-if="item.inventory_item_title" class="cell-truncate" :title="item.inventory_item_title">{{ item.inventory_item_title }}</span>
            <a
              v-else-if="item.status === 'needs_purchase'"
              class="bom-quick-add-link"
              @click.stop="openQuickAdd(item)"
            >Quick add inventory item</a>
            <span v-else class="text-muted">—</span>
          </template>
          <template #cell-status="{ item }">
            <span :class="['status-badge', getStatusClass(item.allocation_status ?? item.status)]">
              {{ getStatusLabel(item.allocation_status ?? item.status) }}
            </span>
          </template>
          <template #cell-actions="{ item }">
            <div style="display:flex;gap:0.4rem;align-items:center;flex-wrap:wrap;">
              <button
                class="btn-edit-row"
                @click.stop="openWizardEdit(item)"
              >
                Edit
              </button>
              <button
                class="btn-remove-datatable"
                @click.stop="removeItem(item)"
              >
                Remove
              </button>
            </div>
          </template>
        </DataTable>
      </div>

      <!-- Bottom Done button -->
      <div v-if="allItems.length > 0" class="wizard-footer">
        <button class="btn btn-primary" @click="goBack">
          Done — Back to Project
        </button>
      </div>
    </div>
  </div>

  <!-- Edit BOM item modal -->
  <AddBOMItemModal
    v-if="wizardEditItem"
    :show="showWizardEditModal"
    :project-id="projectId"
    :edit-item="wizardEditItem"
    @close="showWizardEditModal = false; wizardEditItem = null"
    @updated="handleWizardItemUpdated"
  />

  <!-- Quick Add to Inventory + Link modal -->
  <QuickAddInventoryModal
    :show="showQuickAddModal"
    :bom-item="quickAddBomItem"
    @close="showQuickAddModal = false; quickAddBomItem = null"
    @linked="(item) => { handleWizardItemUpdated(item); showQuickAddModal = false; quickAddBomItem = null }"
  />
</template>

<style scoped>
.page-container {
  padding: 2rem;
}

@media (max-width: 768px) {
  .page-container { padding: 1rem; }
}

.wizard-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

/* Header */
.wizard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .wizard-header { flex-direction: column; gap: 0.75rem; }
}

.wizard-title-section {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.btn-back {
  background: none;
  border: none;
  color: var(--color-heading);
  cursor: pointer;
  padding: 0;
  font-size: 0.9rem;
  text-align: left;
}

.btn-back:hover { text-decoration: underline; }

.wizard-title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0;
  color: var(--color-heading);
}

.project-name {
  font-weight: 400;
  color: var(--color-text-soft);
}

.wizard-hint {
  font-size: 0.875rem;
  color: var(--color-text-soft);
  margin: 0;
}

.wizard-hint kbd {
  background: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 3px;
  padding: 1px 5px;
  font-size: 0.8rem;
}

.done-btn {
  white-space: nowrap;
  flex-shrink: 0;
}

/* Error */
.error-banner {
  background: color-mix(in srgb, var(--color-red) 12%, transparent);
  color: var(--color-red);
  border-left: 3px solid var(--color-red);
  padding: 0.6rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
}

/* Input card */
.input-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.25rem;
}

.input-error {
  color: var(--color-red);
  font-size: 0.875rem;
  margin-bottom: 0.75rem;
}

.input-row {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  flex-wrap: wrap;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.field-desc { flex: 3; min-width: 180px; }
.field-qty { flex: 0.5; min-width: 70px; }
.field-inv { flex: 2.5; min-width: 180px; position: relative; }
.field-purchase { flex: 0 0 auto; min-width: 120px; }
.field-notes { flex: 2; min-width: 150px; }
.field-add { flex: 0 0 auto; }

.field-disabled input {
  opacity: 0.5;
  cursor: not-allowed;
}

.field-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-text-soft);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.form-control {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
  width: 100%;
  box-sizing: border-box;
}

.form-control:focus {
  outline: none;
  border-color: var(--color-blue);
  box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.15);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--color-text);
  padding: 0.5rem 0.75rem;
  border: 1px solid transparent;
  box-sizing: border-box;
}

.inv-search-wrap {
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

.inv-dropdown {
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
  z-index: 50;
}

.inv-dropdown-item {
  display: flex;
  justify-content: space-between;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  font-size: 0.875rem;
  border-bottom: 1px solid var(--color-border);
}

.inv-dropdown-item:last-child { border-bottom: none; }
.inv-dropdown-item:hover { background: var(--color-background-mute); }

.result-title { color: var(--color-heading); }
.result-qty { font-size: 0.8rem; color: var(--color-text-soft); }
.result-qty-overallocated { color: var(--color-red, #e53e3e); font-weight: 600; }

.inv-selected {
  font-size: 0.8rem;
  color: var(--color-green);
  margin: 0.2rem 0 0;
}

.btn-add {
  padding: 0.5rem 1.25rem;
  background: var(--color-blue);
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  height: 36px;
}

.btn-add:hover:not(:disabled) { opacity: 0.9; }
.btn-add:disabled { opacity: 0.5; cursor: not-allowed; }

/* Prevent long item names from causing horizontal scroll */
.bom-wizard-table :deep(table) {
  table-layout: fixed;
  width: 100%;
  border-collapse: collapse;
  border: none;
}

/* Match borderless row-only style of Project Detail page */
.bom-wizard-table :deep(th),
.bom-wizard-table :deep(td) {
  border: none;
  border-bottom: 1px solid var(--color-border);
  padding: 10px 15px;
  text-align: left;
}

.bom-wizard-table :deep(thead tr:first-child th) { border-top: none; }
.bom-wizard-table :deep(tbody tr:last-child td) { border-bottom: 1px solid var(--color-border); }

/* Column widths: keep small cols tight, give description the bulk */
.bom-wizard-table :deep(th:nth-child(1)),
.bom-wizard-table :deep(td:nth-child(1)) { width: 3%; }     /* # */
.bom-wizard-table :deep(th:nth-child(3)),
.bom-wizard-table :deep(td:nth-child(3)) { width: 8%; }     /* Qty */
.bom-wizard-table :deep(th:nth-child(4)),
.bom-wizard-table :deep(td:nth-child(4)) { width: 22%; }    /* Inventory Item */
.bom-wizard-table :deep(th:nth-child(5)),
.bom-wizard-table :deep(td:nth-child(5)) { width: 12%; }    /* Status */
.bom-wizard-table :deep(th:nth-child(6)),
.bom-wizard-table :deep(td:nth-child(6)) { width: 13%; }    /* Actions */
/* col 2 (Description) takes the remaining ~42% automatically */

.cell-truncate {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  white-space: normal;
}

/* Table section */
.bom-table-section {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.bom-table-header {
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-background-mute);
}

.bom-table-header h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--color-heading);
}

.filter-count-hint {
  font-weight: 400;
  color: var(--color-text-soft);
  font-size: 0.9rem;
}

.bom-filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  padding: 0.6rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-background-soft);
}

.bom-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.25rem 0.65rem;
  border-radius: 20px;
  border: 1px solid var(--color-border);
  background: var(--color-background);
  color: var(--color-text-soft);
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.bom-chip:hover {
  border-color: var(--color-blue);
  color: var(--color-blue);
}

.bom-chip-active {
  background: var(--color-blue);
  border-color: var(--color-blue);
  color: #fff;
}

.chip-count {
  background: rgba(255, 255, 255, 0.25);
  border-radius: 10px;
  padding: 0 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
}

.bom-chip:not(.bom-chip-active) .chip-count {
  background: var(--color-background-mute);
  color: var(--color-text-soft);
}

.empty-hint {
  padding: 1.5rem;
  color: var(--color-text-soft);
  font-size: 0.9rem;
  text-align: center;
  margin: 0;
}

.row-num {
  color: var(--color-text-soft);
  font-size: 0.85rem;
}

.item-notes {
  display: block;
  font-size: 0.78rem;
  color: var(--color-text-soft);
  font-style: italic;
  margin-top: 0.1rem;
}

.text-muted {
  color: var(--color-text-soft);
}

/* Status badges */
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
}

.badge-covered {
  background: color-mix(in srgb, var(--color-green) 15%, transparent);
  color: var(--color-green);
}

.badge-low {
  background: color-mix(in srgb, var(--color-alert-warning) 15%, transparent);
  color: var(--color-alert-warning);
}

.badge-overallocated {
  background: color-mix(in srgb, var(--color-red) 15%, transparent);
  color: var(--color-red);
}

.badge-purchase {
  background: color-mix(in srgb, var(--color-blue) 15%, transparent);
  color: var(--color-blue);
}

.badge-unlinked {
  background: color-mix(in srgb, var(--color-text-soft) 15%, transparent);
  color: var(--color-text-soft);
}

/* Row action buttons */
.btn-edit-row {
  background-color: var(--color-blue);
  color: white;
  padding: 5px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.btn-edit-row:hover { background-color: #0b5ed7; }

.bom-quick-add-link {
  color: var(--color-heading);
  cursor: pointer;
  text-decoration: none;
}
.bom-quick-add-link:hover {
  color: var(--color-heading);
  text-decoration: underline;
}

.btn-quick-add {
  background: var(--color-background-mute);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  padding: 5px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 500;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.btn-quick-add:hover {
  background: var(--color-background-soft);
  color: var(--color-text);
}

/* Selected inventory item row (below full input bar) */
.inv-selected-bar {
  margin: 0.5rem 0 0;
  font-size: 0.8rem;
  color: var(--color-green);
}

/* Footer */
.wizard-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.5rem;
}

.loading-state {
  padding: 2rem;
  color: var(--color-text-soft);
}
</style>
