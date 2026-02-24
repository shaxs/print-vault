<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import DataTable from '../components/DataTable.vue'
import BaseModal from '../components/BaseModal.vue'
import InfoTooltip from '../components/InfoTooltip.vue'

const route = useRoute()
const router = useRouter()
const item = ref(null)
const isLoading = ref(true)
const isDeleteModalVisible = ref(false)
const isPhotoModalVisible = ref(false)

// Preserve view state from list navigation
const viewState = computed(() => history.state || {})

const fetchInventoryItem = async () => {
  try {
    const response = await APIService.getInventoryItem(route.params.id)
    item.value = response.data
  } catch (error) {
    console.error('Failed to fetch inventory item:', error)
  } finally {
    isLoading.value = false
  }
}

const deleteItem = async () => {
  if (confirm(`Are you sure you want to delete "${item.value.title}"? This cannot be undone.`)) {
    try {
      await APIService.deleteInventoryItem(item.value.id)
      router.push({ name: 'home' })
    } catch (error) {
      console.error('Failed to delete item:', error)
    }
  }
}

const removeProjectAssociation = async (project) => {
  if (
    confirm(`Are you sure you want to remove the project "${project.project_name}" from this item?`)
  ) {
    try {
      await APIService.removeProjectFromInventory(item.value.id, project.id)
      await fetchInventoryItem() // Refresh the data
    } catch (error) {
      console.error('Failed to remove project association:', error)
    }
  }
}

const projectHeaders = computed(() => [
  { text: 'Project Name', value: 'project_name' },
  { text: 'Action', value: 'actions', sortable: false },
])

const viewProject = (project) => {
  router.push({ name: 'project-detail', params: { id: project.id } })
}

const editItem = () => {
  router.push({
    name: 'item-edit',
    params: { id: item.value.id },
    state: viewState.value,
  })
}

// ── BOM Allocation ────────────────────────────────────────────────────────────
const allocation = ref(null)
const showClosedBOMProjects = ref(false)

const fetchAllocation = async (id) => {
  try {
    const response = await APIService.getInventoryAllocation(id)
    allocation.value = response.data
  } catch {
    allocation.value = null
  }
}

const bomProjectHeaders = [
  { text: 'Project Name', value: 'project_name' },
  { text: 'Qty Allocated', value: 'qty_allocated' },
  { text: 'Project Status', value: 'project_status' },
]

const closedBOMProjectHeaders = [
  { text: 'Name', value: 'project_name' },
  { text: 'Qty Allocated', value: 'qty_allocated' },
  { text: 'Status', value: 'project_status' },
]

const allocationStatusLabel = computed(() => {
  if (!allocation.value) return null
  const { qty_on_hand, qty_needed, is_overallocated } = allocation.value
  if (qty_needed === 0) return null
  if (is_overallocated) return 'Overallocated'
  if (item.value?.is_consumable && item.value?.low_stock_threshold) {
    if ((qty_on_hand - qty_needed) <= item.value.low_stock_threshold) return 'Running Low'
  }
  return 'Covered'
})

const allocationStatusClass = computed(() => {
  const s = allocationStatusLabel.value
  if (s === 'Overallocated') return 'alloc-overallocated'
  if (s === 'Running Low') return 'alloc-low'
  if (s === 'Covered') return 'alloc-covered'
  return ''
})

const availableClass = computed(() => {
  if (!allocation.value) return ''
  const avail = allocation.value.qty_available
  if (avail < 0) return 'avail-negative'
  if (avail === 0) return 'avail-zero'
  if (item.value?.is_consumable && item.value?.low_stock_threshold && avail <= item.value.low_stock_threshold) return 'avail-low'
  return 'avail-ok'
})

const formatProjectStatus = (status) =>
  status ? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : '—'

const viewBOMProject = (proj) => {
  router.push({ name: 'project-detail', params: { id: proj.id } })
}

const removeBOMItem = async (proj) => {
  const msg = `Remove ${item.value.title} from the BOM of project "${proj.project_name}"? This will release ${proj.qty_allocated} unit(s) back to available stock.`
  if (confirm(msg)) {
    try {
      await APIService.deleteBOMItem(proj.bom_item_id)
      await fetchAllocation(item.value.id)
    } catch (error) {
      console.error('Failed to remove BOM item:', error)
    }
  }
}

onMounted(async () => {
  await fetchInventoryItem()
  if (item.value) fetchAllocation(item.value.id)
})
</script>

<template>
  <div class="page-container">
    <div v-if="isLoading" class="loading-state">
      <p>Loading...</p>
    </div>

    <div v-if="!isLoading && item" class="content-container">
      <div class="detail-header">
        <h1>{{ item.title }}</h1>
        <div class="actions">
          <button @click="router.push({ name: 'home' })" class="btn btn-secondary">&larr; Back to Inventory</button>
          <button @click="editItem" class="btn btn-primary">Edit</button>
          <button @click="deleteItem" class="btn btn-danger">Delete</button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="photo-column">
          <div class="card photo-card">
            <div class="card-header">
              <h3>Item Photo</h3>
            </div>
            <div class="card-body photo-card-body">
              <img
                v-if="item.photo"
                :src="item.photo"
                :alt="item.title"
                class="detail-photo clickable"
                @click="isPhotoModalVisible = true"
              />
              <div v-else class="no-photo">No Photo Available</div>
            </div>
          </div>
        </div>

        <div class="details-column">
          <div class="card">
            <div class="card-header">
              <h3>Item Details</h3>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">Brand: </span>
                  <span class="value">{{ item.brand?.name || 'N/A' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Part Type: </span>
                  <span class="value">{{ item.part_type?.name || 'N/A' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Location: </span>
                  <span class="value">{{ item.location?.name || 'N/A' }}</span>
                </div>
                <div class="info-item" v-if="item.vendor || item.vendor_link">
                  <span class="label">Vendor: </span>
                  <span class="value">
                    <a
                      v-if="item.vendor_link"
                      :href="item.vendor_link"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="vendor-link"
                    >
                      {{ item.vendor?.name || 'External Link' }}
                    </a>
                    <span v-else>{{ item.vendor?.name || 'N/A' }}</span>
                  </span>
                </div>
                <div class="info-item" v-if="item.model">
                  <span class="label">Model: </span>
                  <span class="value">{{ item.model }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Quantity: </span>
                  <span class="value">{{ item.quantity }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Cost: </span>
                  <span class="value">{{ item.cost ? `$${item.cost}` : 'N/A' }}</span>
                </div>
                <div v-if="item.is_consumable" class="info-item">
                  <span class="label">Low Stock Alert: </span>
                  <span class="value">Enabled</span>
                </div>
                <div v-if="item.is_consumable" class="info-item">
                  <span class="label">Warning Threshold: </span>
                  <span class="value">{{ item.low_stock_threshold ?? 'Not Set' }}</span>
                </div>
              </div>
              <hr v-if="item.notes" />
              <div v-if="item.notes" class="notes-section">
                <h4>Notes</h4>
                <p class="notes-content">{{ item.notes }}</p>
              </div>
            </div>
          </div>

          <div class="card">
            <div class="card-header">
              <h3>
                Associated Projects
                <InfoTooltip>
                  This item is <strong>soft-linked</strong> to these projects — it's been marked
                  as relevant or purchased for use. No quantity is tracked against the project.<br /><br />
                  An inventory item can be either <strong>Associated</strong> (soft link) or part of
                  a project's <strong>Bill of Materials</strong> (structured, quantity-tracked), but
                  not both for the same project.
                </InfoTooltip>
              </h3>
            </div>
            <div class="card-body table-card-body">
              <DataTable
                :headers="projectHeaders"
                :items="item.associated_projects"
                :visible-columns="projectHeaders.map((h) => h.value)"
                @row-click="viewProject"
                empty-message="No Projects Associated."
              >
                <template #cell-project_name="{ item }">
                  <span class="table-link grey-link">{{ item.project_name }}</span>
                </template>
                <template #cell-actions="{ item }">
                  <button @click.stop="removeProjectAssociation(item)" class="btn-remove-datatable">
                    Remove
                  </button>
                </template>
              </DataTable>
            </div>
          </div>

          <!-- ── BOM Allocation ────────────────────────── -->
          <div v-if="allocation && allocation.qty_needed > 0" class="card">
            <div class="card-header">
              <h3>
                BOM Allocation
                <InfoTooltip>
                  This item appears in the <strong>Bill of Materials</strong> of one or more
                  projects. Each BOM entry specifies a quantity needed and is compared against
                  your on-hand stock to show whether you're covered, low, or need to purchase
                  more.<br /><br />
                  BOM is a <strong>structured association</strong> — once an item is in a
                  project's BOM it is no longer a soft association and quantity is actively
                  tracked.
                </InfoTooltip>
              </h3>
            </div>
            <div class="card-body">
              <!-- Summary info-grid row -->
              <div class="alloc-summary-grid">
                <div class="alloc-cell">
                  <span class="alloc-label">Qty on Hand</span>
                  <span class="alloc-value">{{ allocation.qty_on_hand }}</span>
                </div>
                <div class="alloc-cell">
                  <span class="alloc-label">Qty Needed</span>
                  <span :class="['alloc-value', allocationStatusClass]">{{ allocation.qty_needed }}</span>
                </div>
                <div class="alloc-cell">
                  <span class="alloc-label">Available</span>
                  <span :class="['alloc-value', availableClass]">{{ allocation.qty_available }}</span>
                </div>
                <div class="alloc-cell">
                  <span class="alloc-label">Status</span>
                  <span v-if="allocationStatusLabel" :class="['alloc-badge', allocationStatusClass]">
                    {{ allocationStatusLabel }}
                  </span>
                  <span v-else class="alloc-value text-muted">—</span>
                </div>
              </div>

              <!-- Active projects table -->
              <div v-if="allocation.active_projects.length > 0" class="alloc-section">
                <DataTable
                  :headers="bomProjectHeaders"
                  :items="allocation.active_projects"
                  :visible-columns="bomProjectHeaders.map((h) => h.value)"
                  empty-message=""
                  @row-click="viewBOMProject"
                >
                  <template #cell-project_name="{ item: proj }">
                    <span class="table-link grey-link">{{ proj.project_name }}</span>
                  </template>
                  <template #cell-project_status="{ item: proj }">
                    <span class="project-status-text">{{ formatProjectStatus(proj.project_status) }}</span>
                  </template>
                  <template #cell-actions="{ item: proj }">
                    <button @click.stop="removeBOMItem(proj)" class="btn-remove-datatable">
                      Remove
                    </button>
                  </template>
                </DataTable>
              </div>

              <!-- Closed projects (collapsed) -->
              <div v-if="allocation.closed_projects.length > 0" class="alloc-section closed-section">
                <button
                  type="button"
                  class="btn btn-sm btn-secondary"
                  @click="showClosedBOMProjects = !showClosedBOMProjects"
                >
                  {{ showClosedBOMProjects ? 'Hide' : 'Show' }} Closed Projects ({{ allocation.closed_projects.length }})
                </button>
                <template v-if="showClosedBOMProjects">
                  <DataTable
                    :headers="closedBOMProjectHeaders"
                    :items="allocation.closed_projects"
                    :visible-columns="closedBOMProjectHeaders.map((h) => h.value)"
                    empty-message=""
                  >
                    <template #cell-project_name="{ item: proj }">
                      <span class="table-link grey-link text-muted">{{ proj.project_name }}</span>
                    </template>
                    <template #cell-project_status="{ item: proj }">
                      <span class="text-muted">{{ formatProjectStatus(proj.project_status) }}</span>
                    </template>
                  </DataTable>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img :src="item.photo" :alt="item.title" class="modal-image" />
      </div>
    </div>

    <BaseModal
      :show="isDeleteModalVisible"
      title="Confirm Deletion"
      @close="isDeleteModalVisible = false"
    >
      <p>Are you sure you want to permanently delete "{{ item.title }}"?</p>
      <template #footer>
        <button
          @click="isDeleteModalVisible = false"
          type="button"
          class="btn btn-secondary btn-sm"
        >
          Cancel
        </button>
        <button @click="confirmDelete" class="btn btn-danger btn-sm">Yes, Delete</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.page-container {
  padding: 2rem;
}

@media (max-width: 768px) {
  .page-container {
    padding: 1rem;
  }
}

.content-container {
  max-width: 1200px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
  }
}

.detail-header h1 {
  font-size: 2.5rem;
  font-weight: 600;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

@media (max-width: 768px) {
  .detail-header h1 {
    font-size: 1.75rem;
  }
}

.actions {
  display: flex;
  gap: 1rem;
}

@media (max-width: 768px) {
  .actions {
    width: 100%;
    justify-content: stretch;
  }

  .actions .btn {
    flex: 1;
  }
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr 2fr;
    gap: 2rem;
  }
}

.card-body.photo-card-body {
  padding: 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
}

@media (max-width: 768px) {
  .card-body.photo-card-body {
    padding: 1rem;
  }
}

.detail-photo {
  width: 100%;
  max-width: 400px;
  height: auto;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .detail-photo {
    max-width: 100%;
  }
}
.clickable {
  cursor: pointer;
}
.no-photo {
  width: 100%;
  aspect-ratio: 1/1;
  max-width: 400px;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--color-text-soft);
  font-weight: 500;
}
.card-body {
  padding: 0;
  word-wrap: break-word;
}

.card-body.table-card-body {
  overflow: visible;
}

.info-grid {
  padding: 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

@media (max-width: 768px) {
  .info-grid {
    padding: 1rem;
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
}

.info-item {
  display: flex;
  align-items: baseline;
  word-wrap: break-word;
  overflow-wrap: break-word;
  gap: 0.25rem;
}

.info-item .label {
  font-weight: bold;
  color: var(--color-heading);
  flex-shrink: 0;
}

.info-item .value {
  font-size: 1rem;
  word-break: break-word;
  overflow-wrap: break-word;
  min-width: 0;
  flex: 1;
}

@media (max-width: 768px) {
  .info-item .value {
    font-size: 0.9rem;
  }
}

hr {
  border: 0;
  border-top: 1px solid var(--color-border);
  margin: 0 1.5rem;
}

.notes-section {
  padding: 1.5rem;
}

@media (max-width: 768px) {
  .notes-section {
    padding: 1rem;
  }
}

.notes-section h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}

.notes-content {
  white-space: pre-wrap;
  word-wrap: break-word;
}

@media (max-width: 768px) {
  .notes-content {
    font-size: 0.9rem;
  }
}
.table-link.grey-link {
  color: var(--color-heading);
  text-decoration: none;
  cursor: pointer;
}
.table-link.grey-link:hover,
.table-link.grey-link:active,
.table-link.grey-link:visited {
  color: var(--color-heading);
  text-decoration: underline;
}
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}
.modal-image {
  max-width: 100%;
  max-height: 100%;
  display: block;
  border-radius: 8px;
}
.card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 2rem;
}

@media (max-width: 768px) {
  .card {
    margin-bottom: 1rem;
  }
}

.card:last-child {
  margin-bottom: 0;
}

.card-header {
  padding: 1rem 1.5rem;
  background: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .card-header {
    padding: 0.75rem 1rem;
  }
}

.card-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: var(--color-heading);
}

@media (max-width: 768px) {
  .card-header h3 {
    font-size: 1rem;
  }
}

.borderless-table {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.borderless-table :deep(table) {
  border-collapse: collapse;
  border: none;
  width: 100%;
  margin-top: 0;
  min-width: 600px;
}

@media (max-width: 768px) {
  .borderless-table :deep(table) {
    font-size: 0.875rem;
  }
}

.borderless-table :deep(th),
.borderless-table :deep(td) {
  border: none;
  border-bottom: 1px solid var(--color-border);
  padding: 10px 15px;
  text-align: left;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .borderless-table :deep(th),
  .borderless-table :deep(td) {
    padding: 8px 10px;
  }
}

.borderless-table :deep(thead tr:first-child th) {
  border-top: none;
}
.borderless-table :deep(tbody tr:last-child td) {
  border-bottom: none;
}
.action-button {
  padding: 8px 15px;
  border: none;
  border-radius: 5px;
  text-decoration: none;
  font-weight: bold;
  cursor: pointer;
}
.delete-button {
  background-color: var(--color-red);
  color: white;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
}
.vendor-link {
  color: var(--color-text);
  text-decoration: none;
  word-break: break-word;
}
.vendor-link:hover {
  text-decoration: underline;
}

/* ── BOM Allocation ─────────────────────────────────────────────────────── */
.alloc-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0;
  border-bottom: 1px solid var(--color-border);
}

@media (max-width: 600px) {
  .alloc-summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.alloc-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem;
  border-right: 1px solid var(--color-border);
  gap: 0.25rem;
}

.alloc-cell:last-child {
  border-right: none;
}

.alloc-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-text-soft);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.alloc-value {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-heading);
}

.alloc-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 0.82rem;
  font-weight: 600;
}

.alloc-covered, .avail-ok {
  color: var(--color-green);
}

.avail-zero {
  color: var(--color-text-muted);
}

.alloc-covered.alloc-badge {
  background: color-mix(in srgb, var(--color-green) 15%, transparent);
}

.alloc-low, .avail-low {
  color: var(--color-alert-warning);
}

.alloc-low.alloc-badge {
  background: color-mix(in srgb, var(--color-alert-warning) 15%, transparent);
}

.alloc-overallocated, .avail-negative {
  color: var(--color-red);
}

.alloc-overallocated.alloc-badge {
  background: color-mix(in srgb, var(--color-red) 15%, transparent);
}

.alloc-section {
  padding: 0.75rem 0 0;
}

.alloc-section-title {
  padding: 0.25rem 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-soft);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0;
}

.closed-section {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-border);
}

.project-status-text {
  font-size: 0.875rem;
  color: var(--color-text);
}

.text-muted {
  color: var(--color-text-soft);
}
</style>
