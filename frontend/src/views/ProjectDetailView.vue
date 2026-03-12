<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import DataTable from '../components/DataTable.vue'
import ErrorModal from '../components/ErrorModal.vue'
import InfoModal from '../components/InfoModal.vue'
import AddInventoryToProjectModal from '../components/AddInventoryToProjectModal.vue'
import AddBOMItemModal from '../components/AddBOMItemModal.vue'
import InfoTooltip from '../components/InfoTooltip.vue'
import DeleteProjectModal from '../components/DeleteProjectModal.vue'
import QuickAddInventoryModal from '../components/QuickAddInventoryModal.vue'

const route = useRoute()
const router = useRouter()
const project = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')
const isErrorModalVisible = ref(false)
const isInfoModalVisible = ref(false)
const infoModalMessage = ref('')
const isPhotoModalVisible = ref(false)
const isDownloading = ref(false)
const isAddInventoryModalVisible = ref(false)

// Color swatch lightbox state
const isColorSwatchModalVisible = ref(false)
const selectedColorHex = ref(null)

const openColorSwatchModal = (colorHex) => {
  selectedColorHex.value = colorHex
  isColorSwatchModalVisible.value = true
}

const fetchProject = async () => {
  try {
    isLoading.value = true
    const response = await APIService.getProject(route.params.id)
    project.value = response.data
  } catch (error) {
    console.error('Failed to fetch project details:', error)
    errorMessage.value = 'Failed to load project details. Please try again.'
    isErrorModalVisible.value = true
  } finally {
    isLoading.value = false
  }
}

const getFileName = (filePath) => {
  if (!filePath) return ''
  return filePath.split('/').pop()
}

const deleteProject = () => {
  isDeleteProjectModalVisible.value = true
}

const handleDeleteProjectConfirm = async (restoreInventory) => {
  isDeleteProjectModalVisible.value = false
  try {
    await APIService.deleteProject(project.value.id, restoreInventory)
    router.push({ name: 'project-list' })
  } catch (error) {
    console.error('Failed to delete project:', error)
    errorMessage.value = 'Failed to delete project. Please try again.'
    isErrorModalVisible.value = true
  }
}

const removeInventoryItem = async (item) => {
  if (confirm(`Are you sure you want to remove "${item.title}" from this project?`)) {
    try {
      await APIService.removeInventoryFromProject(project.value.id, item.id)
      await fetchProject() // Refresh the data
    } catch (error) {
      console.error('Failed to remove inventory item:', error)
      errorMessage.value = 'Failed to remove inventory item. Please try again.'
      isErrorModalVisible.value = true
    }
  }
}

const viewItem = (item) => {
  router.push({ name: 'item-detail', params: { id: item.id } })
}

const downloadAllProjectFiles = async () => {
  if (!project.value || !project.value.files || project.value.files.length === 0) return
  isDownloading.value = true
  try {
    const response = await APIService.downloadProjectFiles(project.value.id)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const filename = `${project.value.project_name.replace(/ /g, '_')}_files.zip`
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to download files:', error)
    errorMessage.value = 'Failed to download files. Please try again.'
    isErrorModalVisible.value = true
  } finally {
    isDownloading.value = false
  }
}

const inventoryHeaders = computed(() => [
  { text: 'Title', value: 'title' },
  { text: 'Brand', value: 'brand' },
  { text: 'Part Type', value: 'part_type' },
  { text: 'Quantity', value: 'quantity' },
  { text: 'Cost', value: 'cost' },
  { text: 'Actions', value: 'actions', sortable: false },
])

// Get progress bar color based on percentage
const getProgressColor = (percentage) => {
  if (percentage === 0) return '#64748b' // gray
  if (percentage < 50) return '#ef4444' // red
  if (percentage < 100) return '#f59e0b' // orange
  return '#10b981' // green
}

// Get tracker progress style
const getTrackerProgressStyle = (tracker) => {
  const percentage = tracker?.progress_percentage || 0
  return {
    width: `${percentage}%`,
    height: '100%',
    backgroundColor: getProgressColor(percentage),
    transition: 'width 0.3s ease',
  }
}

// Format material name from blueprint
const formatMaterialName = (material) => {
  if (!material) return ''
  const brandName = material.brand?.name || ''
  const diameter = material.diameter ? ` (${material.diameter}mm)` : ''
  return `${brandName} ${material.name}${diameter}`.trim()
}

// Format spool display name
const getSpoolDisplayName = (spool) => {
  // Blueprint-based spool
  if (spool.filament_type) {
    return formatMaterialName(spool.filament_type)
  }
  // Quick Add spool
  if (spool.standalone_name) {
    const brand = spool.standalone_brand?.name || ''
    return brand ? `${brand} ${spool.standalone_name}` : spool.standalone_name
  }
  return `Spool #${spool.id}`
}

const existingInventoryIds = computed(() => {
  return project.value?.associated_inventory_items?.map((item) => item.id) || []
})

// BOM items with sequential row numbers (DataTable doesn't expose index in slots)
const bomItemsWithIndex = computed(() =>
  (project.value?.bom_items ?? []).map((item, i) => ({ ...item, _rowNum: i + 1 }))
)

// Status filter chips
const BOM_CHIP_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'covered', label: 'Covered' },
  { value: 'low', label: 'Running Low' },
  { value: 'overallocated', label: 'Overallocated' },
  { value: 'needs_purchase', label: 'Needs Purchase' },
  { value: 'unlinked', label: 'Not Linked' },
]

const bomStatusFilter = ref('all')

const getBomChipStatus = (item) => item.allocation_status ?? item.status ?? 'unlinked'

const bomStatusCounts = computed(() => {
  const items = project.value?.bom_items ?? []
  const counts = { all: items.length }
  for (const item of items) {
    const s = getBomChipStatus(item)
    counts[s] = (counts[s] || 0) + 1
  }
  return counts
})

const activeBomChipFilters = computed(() =>
  BOM_CHIP_FILTERS.filter((f) => f.value === 'all' || (bomStatusCounts.value[f.value] ?? 0) > 0)
)

const filteredBomItems = computed(() => {
  if (bomStatusFilter.value === 'all') return bomItemsWithIndex.value
  return bomItemsWithIndex.value.filter(
    (item) => getBomChipStatus(item) === bomStatusFilter.value,
  )
})

const handleInventoryAdded = async () => {
  isAddInventoryModalVisible.value = false
  infoModalMessage.value = 'Inventory items added successfully!'
  isInfoModalVisible.value = true
  await fetchProject() // Refresh the project data
}

// ── BOM ──────────────────────────────────────────────────────────────────────
const isAddBOMModalVisible = ref(false)
const isDeleteProjectModalVisible = ref(false)

const linkedBOMCount = computed(() => {
  if (!project.value?.bom_items) return 0
  return project.value.bom_items.filter(
    (item) => item.inventory_item && item.status !== 'needs_purchase',
  ).length
})
const movingToBOMItem = ref(null)
const editingBOMModalItem = ref(null)

// Quick Add + Link
const quickAddBomItem = ref(null)
const showQuickAddModal = ref(false)

const openQuickAdd = (item) => {
  quickAddBomItem.value = item
  showQuickAddModal.value = true
}

const bomHeaders = computed(() => [
  { text: '#', value: '_rowNum', sortable: false },
  { text: 'Description', value: 'description' },
  { text: 'Qty Required', value: 'quantity_needed' },
  { text: 'Inventory Item', value: 'inventory_item_title' },
  { text: 'Status', value: 'allocation_status', sortable: false },
  { text: 'Actions', value: 'actions', sortable: false },
])

const BOM_STATUS_LABELS = {
  covered: 'Covered',
  low: 'Running Low',
  overallocated: 'Overallocated',
  needs_purchase: 'Purchase',
  unlinked: 'Not Linked',
}

const BOM_STATUS_CLASSES = {
  covered: 'bom-status-covered',
  low: 'bom-status-low',
  overallocated: 'bom-status-overallocated',
  needs_purchase: 'bom-status-purchase',
  unlinked: 'bom-status-unlinked',
}

const getBOMStatusLabel = (status) => BOM_STATUS_LABELS[status] ?? status
const getBOMStatusClass = (status) => BOM_STATUS_CLASSES[status] ?? ''

const openBOMWizard = () => {
  router.push({ name: 'bom-wizard', params: { id: project.value.id } })
}

const moveToBOM = (inventoryItem) => {
  movingToBOMItem.value = inventoryItem
  isAddBOMModalVisible.value = true
}

const viewInventoryItem = (inventoryItemId) => {
  if (inventoryItemId) router.push({ name: 'item-detail', params: { id: inventoryItemId } })
}

const handleBOMItemAdded = async () => {
  if (movingToBOMItem.value) {
    // Item was moved from associated inventory → BOM; remove the association
    try {
      await APIService.removeInventoryFromProject(project.value.id, movingToBOMItem.value.id)
    } catch (e) {
      // Non-critical: item may not have been in associated inventory list
      console.warn('Could not remove inventory association during BOM move:', e)
    }
    movingToBOMItem.value = null
    isAddBOMModalVisible.value = false
  }
  fetchProject()
}

const openBOMEditModal = (item) => {
  editingBOMModalItem.value = item
}

const deleteBOMItem = async (item) => {
  const returnNote = item.inventory_item_title
    ? `\n\n${item.quantity_needed}× ${item.inventory_item_title} will be returned to Inventory.`
    : ''
  if (confirm(`Remove "${item.description}" from this BOM?${returnNote}`)) {
    try {
      await APIService.deleteBOMItem(item.id)
      await fetchProject()
    } catch (error) {
      console.error('Failed to delete BOM item:', error)
      errorMessage.value = 'Failed to remove BOM item. Please try again.'
      isErrorModalVisible.value = true
    }
  }
}

onMounted(fetchProject)
</script>

<template>
  <div class="page-container">
    <div v-if="isLoading" class="loading-state">
      <p>Loading project details...</p>
    </div>

    <div v-if="!isLoading && project" class="content-container">
      <div class="detail-header">
        <div class="header-content">
          <img
            :src="project.photo"
            v-if="project.photo"
            alt="Project Photo"
            class="detail-photo clickable"
            @click="isPhotoModalVisible = true"
          />
          <div class="header-info">
            <h1>{{ project.project_name }}</h1>
          </div>
        </div>
        <div class="header-actions">
          <button @click="router.push({ name: 'project-list' })" class="btn btn-secondary">&larr; Back to Projects</button>
          <router-link
            :to="{ name: 'project-edit', params: { id: project.id } }"
            class="btn btn-primary"
            >Edit</router-link
          >
          <button @click="deleteProject" class="btn btn-danger">Delete</button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="card">
          <div class="card-header">
            <h3>Project Details</h3>
          </div>
          <div class="card-body">
            <div class="card-section">
              <p>
                <strong>Status:</strong>
                <span
                  :class="[
                    'status-badge',
                    `status-${project.status.toLowerCase().replace(/ /g, '-')}`,
                  ]"
                  >{{ project.status }}</span
                >
              </p>
            </div>
            <hr />
            <div class="card-section">
              <h4>Description</h4>
              <p class="notes-content">{{ project.description || 'No description available.' }}</p>
            </div>
            <hr />
            <div class="card-section">
              <h4>Notes</h4>
              <p class="notes-content">{{ project.notes || 'No notes available.' }}</p>
            </div>
            <hr />
            <div class="card-section">
              <h4>Associated Printers</h4>
              <ul
                v-if="project.associated_printers && project.associated_printers.length > 0"
                class="resource-list"
              >
                <li v-for="printer in project.associated_printers" :key="printer.id">
                  <router-link :to="{ name: 'printer-detail', params: { id: printer.id } }">
                    {{ printer.title }}
                  </router-link>
                </li>
              </ul>
              <p v-else>No printers associated with this project.</p>
            </div>
            <hr v-if="project.materials_display && project.materials_display.length > 0" />
            <div v-if="project.materials_display && project.materials_display.length > 0" class="card-section">
              <h4>Materials</h4>
              <div class="materials-list">
                <div v-for="(material, index) in project.materials_display" :key="index" class="material-item">
                  <strong v-if="material.label">{{ material.label }}:</strong>
                  <span 
                    v-if="material.blueprint && material.blueprint.colors && material.blueprint.colors.length > 0"
                    class="color-swatch clickable"
                    :style="{ backgroundColor: material.blueprint.colors[0] }"
                    :title="material.blueprint.colors[0]"
                    @click.stop="openColorSwatchModal(material.blueprint.colors[0])"
                  ></span>
                  <span v-if="material.custom_color">{{ material.custom_color }}</span>
                  <router-link 
                    v-if="material.blueprint"
                    :to="`/filaments/materials/${material.blueprint.id}`"
                    class="material-link"
                  >
                    {{ formatMaterialName(material.blueprint) }}
                  </router-link>
                </div>
              </div>
            </div>
            <hr v-if="project.filaments_used && project.filaments_used.length > 0" />
            <div v-if="project.filaments_used && project.filaments_used.length > 0" class="card-section">
              <h4>Assigned Spools</h4>
              <ul class="resource-list">
                <li v-for="spool in project.filaments_used" :key="spool.id">
                  <div class="spool-name-wrapper">
                    <span 
                      v-if="spool.filament_type && spool.filament_type.colors && spool.filament_type.colors.length > 0"
                      class="color-swatch clickable"
                      :style="{ backgroundColor: spool.filament_type.colors[0] }"
                      :title="spool.filament_type.colors[0]"
                      @click.stop="openColorSwatchModal(spool.filament_type.colors[0])"
                    ></span>
                    <router-link :to="`/filaments/${spool.id}`">
                      {{ getSpoolDisplayName(spool) }}
                    </router-link>
                  </div>
                  <span class="spool-status" :class="`status-${spool.status}`">
                    {{ spool.status.replace('_', ' ').toUpperCase() }}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Resources</h3>
          </div>
          <div class="card-body">
            <div class="card-section">
              <h4>Links</h4>
              <ul v-if="project.links && project.links.length > 0" class="resource-list">
                <li v-for="link in project.links" :key="link.id">
                  <a :href="link.url" target="_blank">{{ link.name }}</a>
                </li>
              </ul>
              <p v-else>No links added yet.</p>
              <div class="manage-links-button">
                <button
                  @click="router.push({ name: 'project-manage-links', params: { id: project.id } })"
                  type="button"
                  class="btn btn-sm btn-primary"
                >
                  Manage Links
                </button>
              </div>
            </div>
            <hr />
            <div class="card-section">
              <h4>Files</h4>
              <ul v-if="project.files && project.files.length > 0" class="resource-list">
                <li v-for="file in project.files" :key="file.id">
                  <a :href="file.file" target="_blank">{{ getFileName(file.file) }}</a>
                </li>
              </ul>
              <p v-else>No files added yet.</p>
              <div class="block-add-form">
                <div style="display: flex; gap: 0.5rem; justify-content: flex-end">
                  <button
                    type="button"
                    class="btn btn-sm btn-secondary"
                    @click="downloadAllProjectFiles"
                    :disabled="isDownloading"
                  >
                    <span v-if="isDownloading">Downloading...</span>
                    <span v-else>Download All</span>
                  </button>
                  <button
                    @click="
                      router.push({ name: 'project-manage-files', params: { id: project.id } })
                    "
                    class="btn btn-sm btn-primary"
                  >
                    Manage Files
                  </button>
                </div>
              </div>
            </div>
            <hr />
            <div class="card-section">
              <h4>Print Trackers</h4>
              <div v-if="project.trackers && project.trackers.length > 0" class="tracker-list">
                <div v-for="tracker in project.trackers" :key="tracker.id" class="tracker-item">
                  <div class="tracker-header-row">
                    <router-link
                      :to="{ name: 'tracker-detail', params: { id: tracker.id } }"
                      class="tracker-name"
                    >
                      {{ tracker.name }}
                    </router-link>
                    <span class="tracker-stats">
                      {{ tracker.printed_quantity_total || 0 }} /
                      {{ tracker.total_quantity || 0 }} parts printed
                    </span>
                  </div>
                  <div class="tracker-progress">
                    <div class="tracker-progress-bar">
                      <div
                        class="tracker-progress-fill"
                        :style="getTrackerProgressStyle(tracker)"
                      ></div>
                    </div>
                    <span class="tracker-percentage">{{ tracker.progress_percentage || 0 }}%</span>
                  </div>
                </div>
              </div>
              <p v-else>No print trackers associated with this project.</p>
              <div class="manage-trackers-button">
                <button
                  @click="router.push({ name: 'tracker-create', query: { project: project.id } })"
                  type="button"
                  class="btn btn-sm btn-primary"
                >
                  New Tracker
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Bill of Materials ─────────────────────────────────── -->
        <div v-if="project" class="bom-section">
          <div class="card">
            <div class="card-header bom-card-header">
              <h3>
                Bill of Materials
                <InfoTooltip>
                  <strong>Associated Inventory Items</strong> are items from your inventory linked
                  to this project for reference. No quantity is tracked — it's a soft relationship
                  that helps you remember which inventory relates to this project.<br /><br />
                  A <strong>Bill of Materials (BOM)</strong> is a structured requirements list.
                  Each BOM entry specifies a quantity needed and is compared against your on-hand
                  stock to show allocation status (Covered, Low, Needs Purchase, etc.).<br /><br />
                  An inventory item can only be linked to a project as one or the other —
                  <strong>not both</strong>.
                </InfoTooltip>
              </h3>
              <div class="bom-header-actions">
                <button
                  type="button"
                  class="btn btn-sm btn-secondary"
                  @click="openBOMWizard"
                >
                  BOM Wizard
                </button>
                <button
                  type="button"
                  class="btn btn-sm btn-primary"
                  @click="isAddBOMModalVisible = true"
                >
                  Add Item
                </button>
              </div>
            </div>
            <div class="card-body table-card-body">
              <p
                v-if="!project.bom_items || project.bom_items.length === 0"
                class="bom-empty-state"
              >
                No BOM items yet.
                <button class="btn-link" @click="openBOMWizard">Use the BOM Wizard</button>
                to quickly enter all parts, or click <strong>Add Item</strong> to add one at a time.
              </p>

              <template v-else>
                <!-- Status filter chips -->
                <div class="bom-filter-chips">
                  <button
                    v-for="f in activeBomChipFilters"
                    :key="f.value"
                    :class="['bom-chip', { 'bom-chip-active': bomStatusFilter === f.value }]"
                    @click="bomStatusFilter = f.value"
                  >
                    {{ f.label }}
                    <span v-if="f.value !== 'all'" class="chip-count">{{
                      bomStatusCounts[f.value] ?? 0
                    }}</span>
                  </button>
                </div>

                <DataTable
                  :headers="bomHeaders"
                  :items="filteredBomItems"
                  :visible-columns="bomHeaders.map((h) => h.value)"
                  :empty-message="bomStatusFilter !== 'all' ? 'No items match the selected filter.' : 'No BOM items yet.'"
                  class="borderless-table bom-detail-table"
                >
                <!-- Row number -->
                <template #cell-_rowNum="{ item }">
                  <span class="bom-row-num">{{ item._rowNum }}</span>
                </template>

                <!-- Description -->
                <template #cell-description="{ item }">
                  <div class="bom-desc-cell">
                    <span class="cell-truncate" :title="item.description">{{ item.description }}</span>
                    <span v-if="item.notes" class="bom-item-notes cell-truncate" :title="item.notes">{{ item.notes }}</span>
                  </div>
                </template>

                <!-- Qty Required -->
                <template #cell-quantity_needed="{ item }">
                  <span>{{ item.quantity_needed }}</span>
                </template>

                <!-- Inventory Item link -->
                <template #cell-inventory_item_title="{ item }">
                  <span
                    v-if="item.inventory_item_title"
                    class="table-link grey-link cell-truncate"
                    :title="item.inventory_item_title"
                    @click="viewInventoryItem(item.inventory_item)"
                  >{{ item.inventory_item_title }}</span>
                  <a
                    v-else-if="item.status === 'needs_purchase'"
                    class="table-link grey-link"
                    @click.stop="openQuickAdd(item)"
                  >Quick add inventory item</a>
                  <span v-else class="text-muted">—</span>
                </template>

                <!-- Allocation status badge -->
                <template #cell-allocation_status="{ item }">
                  <span :class="['bom-status-badge', getBOMStatusClass(item.allocation_status)]">
                    {{ getBOMStatusLabel(item.allocation_status) }}
                  </span>
                </template>

                <!-- Actions -->
                <template #cell-actions="{ item }">
                  <div class="bom-action-btns">
                    <button
                      class="btn btn-sm btn-primary bom-edit-btn"
                      @click.stop="openBOMEditModal(item)"
                    >Edit</button>
                    <button
                      class="btn-remove-datatable"
                      @click.stop="deleteBOMItem(item)"
                    >Remove</button>
                  </div>
                </template>
              </DataTable>
              </template>

            </div>
          </div>
        </div>

        <!-- ── Associated Inventory Items ──────────────────────── -->
        <div v-if="project" class="details-container inventory-full-width">
          <div class="card-header">
            <h3>
              Associated Inventory Items
              <InfoTooltip>
                <strong>Associated Inventory Items</strong> are items from your inventory linked
                to this project for reference. No quantity is tracked — it's a soft relationship
                that helps you remember which inventory relates to this project.<br /><br />
                A <strong>Bill of Materials (BOM)</strong> is a structured requirements list.
                Each BOM entry specifies a quantity needed and is compared against your on-hand
                stock to show allocation status (Covered, Low, Needs Purchase, etc.).<br /><br />
                An inventory item can only be linked to a project as one or the other —
                <strong>not both</strong>.
              </InfoTooltip>
            </h3>
            <button
              @click="isAddInventoryModalVisible = true"
              type="button"
              class="btn btn-sm btn-primary"
            >
              Add Inventory
            </button>
          </div>
          <DataTable
            :headers="inventoryHeaders"
            :items="project.associated_inventory_items"
            :visible-columns="inventoryHeaders.map((h) => h.value)"
            @row-click="viewItem"
            class="borderless-table"
          >
            <template #cell-title="{ item }">
              <span class="table-link grey-link">{{ item.title }}</span>
            </template>
            <template #cell-brand="{ item }">
              {{ item.brand ? item.brand.name : 'N/A' }}
            </template>
            <template #cell-part_type="{ item }">
              {{ item.part_type && item.part_type.name ? item.part_type.name : 'N/A' }}
            </template>
            <template #cell-quantity="{ item }">
              {{ item.quantity }}
            </template>
            <template #cell-cost="{ item }"> ${{ item.cost || '0.00' }} </template>
            <template #cell-actions="{ item }">
              <div class="action-group">
                <button @click.stop="moveToBOM(item)" class="btn btn-sm btn-secondary">
                  Move to BOM
                </button>
                <button @click.stop="removeInventoryItem(item)" class="btn-remove-datatable">
                  Remove
                </button>
              </div>
            </template>
          </DataTable>
        </div>
      </div>
    </div>

    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img :src="project.photo" alt="Full size project photo" class="modal-image" />
      </div>
    </div>

    <!-- Color Swatch Lightbox Modal -->
    <div
      v-if="isColorSwatchModalVisible"
      class="modal-overlay"
      @click="isColorSwatchModalVisible = false"
    >
      <div class="color-swatch-modal-content" @click.stop>
        <button @click="isColorSwatchModalVisible = false" class="close-button">&times;</button>
        <div
          class="color-swatch-large"
          :style="{ backgroundColor: selectedColorHex || '#cccccc' }"
        ></div>
        <p class="color-hex-label">{{ selectedColorHex }}</p>
      </div>
    </div>

    <ErrorModal
      :show="isErrorModalVisible"
      :message="errorMessage"
      @close="isErrorModalVisible = false"
    />
    <InfoModal
      :show="isInfoModalVisible"
      :message="infoModalMessage"
      @close="isInfoModalVisible = false"
    />

    <AddInventoryToProjectModal
      v-if="project"
      :show="isAddInventoryModalVisible"
      :project-id="project.id"
      :existing-inventory-ids="existingInventoryIds"
      @close="isAddInventoryModalVisible = false"
      @added="handleInventoryAdded"
    />

    <!-- Add / Move-to-BOM modal -->
    <AddBOMItemModal
      v-if="project"
      :show="isAddBOMModalVisible"
      :project-id="project.id"
      :pre-selected-inventory-item="movingToBOMItem"
      @close="isAddBOMModalVisible = false; movingToBOMItem = null"
      @added="handleBOMItemAdded"
    />
    <!-- Edit BOM item modal -->
    <AddBOMItemModal
      v-if="project && editingBOMModalItem"
      :show="editingBOMModalItem !== null"
      :project-id="project.id"
      :edit-item="editingBOMModalItem"
      @close="editingBOMModalItem = null"
      @updated="editingBOMModalItem = null; fetchProject()"
    />

    <!-- Delete project confirmation modal -->
    <DeleteProjectModal
      v-if="project"
      :show="isDeleteProjectModalVisible"
      :project-name="project.project_name"
      :project-status="project.status"
      :linked-b-o-m-count="linkedBOMCount"
      @close="isDeleteProjectModalVisible = false"
      @confirm="handleDeleteProjectConfirm"
    />

    <!-- Quick Add to Inventory + Link modal -->
    <QuickAddInventoryModal
      :show="showQuickAddModal"
      :bom-item="quickAddBomItem"
      @close="showQuickAddModal = false; quickAddBomItem = null"
      @linked="() => { showQuickAddModal = false; quickAddBomItem = null; fetchProject() }"
    />
  </div>
</template>

<style scoped>
/* Cleaned up CSS for ProjectDetailView.vue */

/* Inline action button groups in DataTable cells */
.action-group {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  justify-content: flex-end;
}
.action-group .btn.btn-sm {
  padding: 5px 10px;
  font-size: 0.8rem;
  border-radius: 4px;
  border: none;
  line-height: normal;
}

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
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  gap: 1rem;
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
  }
}

.header-content {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
}

@media (max-width: 768px) {
  .header-content {
    width: 100%;
  }
}

.detail-photo {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 8px;
  margin-right: 1.5rem;
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .detail-photo {
    width: 80px;
    height: 80px;
    margin-right: 1rem;
  }
}

.detail-photo.clickable {
  cursor: pointer;
}

.header-info {
  min-width: 0;
  flex: 1;
}

.header-info h1 {
  font-size: 2.5rem;
  font-weight: 600;
  margin: 0;
  color: var(--color-heading);
  word-wrap: break-word;
  overflow-wrap: break-word;
}

@media (max-width: 768px) {
  .header-info h1 {
    font-size: 1.75rem;
  }
}

.header-actions {
  display: flex;
  gap: 1rem;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .header-actions {
    width: 100%;
    justify-content: stretch;
  }

  .header-actions .btn {
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
    grid-template-columns: repeat(2, 1fr);
  }
}
.card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

@media (max-width: 768px) {
  .card {
    margin-bottom: 1rem;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px 8px 20px;
  background: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  border-top: none;
  gap: 0.5rem;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .card-header {
    padding: 12px 15px 8px 15px;
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

.card-body {
  padding: 20px;
  flex-grow: 1;
}

@media (max-width: 768px) {
  .card-body {
    padding: 15px;
  }
}
.card-section h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}
.card-body p {
  margin: 0 0 0.75rem 0;
  line-height: 1.6;
}
.card-body p:last-child {
  margin-bottom: 0;
}
.notes-content {
  white-space: pre-wrap;
}
.card-body hr {
  border: 0;
  border-top: 1px solid var(--color-border);
  margin: 1.5rem 0;
}
.resource-list {
  list-style-type: none;
  padding: 0;
  margin: 0 0 1rem 0;
}
.resource-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border-mute);
  word-break: break-word;
}

@media (max-width: 768px) {
  .resource-list li {
    font-size: 0.875rem;
  }
}

.resource-list li:last-child {
  border-bottom: none;
}
.resource-list a,
.card-body :deep(a) {
  color: var(--color-text);
  text-decoration: none;
  word-break: break-word;
}
.resource-list a:hover,
.card-body :deep(a:hover) {
  text-decoration: underline;
}

.spool-name-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.block-add-form {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 1rem;
}

@media (max-width: 768px) {
  .block-add-form > div {
    flex-direction: column;
  }

  .block-add-form button {
    width: 100%;
  }
}

.block-add-form .form-group {
  margin: 0;
}
.block-add-form button {
  align-self: flex-end;
}
.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: white;
  margin-left: 0.5rem;
}
.status-planning,
.status-planned,
.status-on-hold {
  background-color: #6c757d;
}
.status-in-progress {
  background-color: #ffc107;
  color: #333;
}
.status-completed {
  background-color: #28a745;
}
.status-archived {
  background-color: #343a40;
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
}
.inventory-full-width {
  grid-column: 1 / span 2;
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 20px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0;
  padding-bottom: 30px;
}

@media (max-width: 768px) {
  .inventory-full-width {
    grid-column: 1;
    overflow-x: auto;
  }
}

/* Tracker Cards Styling */
.tracker-list {
  margin-bottom: 1rem;
}

.tracker-item {
  margin-bottom: 1rem;
}

.tracker-item:last-child {
  margin-bottom: 0;
}

.tracker-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  gap: 0.5rem;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .tracker-header-row {
    flex-direction: column;
    align-items: flex-start;
  }
}

.tracker-name {
  color: var(--color-heading);
  text-decoration: none;
  font-weight: 500;
}

.tracker-name:hover {
  color: var(--color-heading);
  text-decoration: underline;
}

.tracker-stats {
  font-size: 0.875rem;
  color: var(--color-text);
}

@media (max-width: 768px) {
  .tracker-stats {
    font-size: 0.8rem;
  }
}

.tracker-progress {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tracker-progress-bar {
  flex: 1;
  height: 0.5rem;
  background-color: var(--color-background-mute);
  border-radius: 9999px;
  overflow: hidden;
}

.tracker-progress-fill {
  height: 100%;
  background-color: var(--color-brand);
  transition: width 0.3s ease;
  border-radius: 9999px;
}

.tracker-percentage {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-brand);
  min-width: 45px;
  text-align: right;
}

.manage-trackers-button {
  margin-top: 0.75rem;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .inventory-full-width {
    grid-column: 1 / span 1;
    padding: 0;
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
/* DataTable borderless style for inventory section */
.borderless-table {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.borderless-table :deep(table) {
  border-collapse: collapse;
  border: none;
  width: 100%;
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
  border-bottom: 1px solid var(--color-border);
}
.add-files-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.5rem;
}
.manage-links-button {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.5rem;
}

@media (max-width: 768px) {
  .manage-links-button button {
    width: 100%;
  }

  .manage-trackers-button button {
    width: 100%;
  }
}

/* Materials List Styling */
.materials-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.material-item {
  padding: 0.5rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.material-item strong {
  color: var(--color-heading);
}

.color-swatch {
  display: inline-block;
  width: 20px;
  height: 20px;
  border-radius: 3px;
  border: 1.5px solid var(--color-border);
  flex-shrink: 0;
}

.color-swatch.clickable {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.color-swatch.clickable:hover {
  transform: scale(1.1);
}

.material-link {
  margin-left: 0.5rem;
  color: var(--color-text);
  text-decoration: underline;
}

.material-link:hover {
  opacity: 0.8;
}

/* Spool Status Styling - matches FilamentSpoolDetailView */
.spool-status {
  display: inline-block;
  padding: 0.25rem 0.6rem;
  margin-left: 0.5rem;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}

.spool-status.status-new {
  background-color: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.spool-status.status-opened {
  background-color: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.spool-status.status-in_use {
  background-color: rgba(168, 85, 247, 0.1);
  color: #a855f7;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.spool-status.status-low {
  background-color: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.spool-status.status-empty {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

.spool-status.status-archived {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
  text-decoration: line-through;
}

/* Color Swatch Modal Styles */
.color-swatch-modal-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.close-button {
  position: absolute;
  top: -40px;
  right: 0;
  background: none;
  border: none;
  color: white;
  font-size: 2rem;
  cursor: pointer;
  padding: 0.5rem;
}

.close-button:hover {
  color: var(--color-text-muted);
}

.color-swatch-large {
  width: 250px;
  height: 250px;
  border-radius: 16px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.color-hex-label {
  color: white;
  font-size: 1.25rem;
  font-family: monospace;
  background: rgba(0, 0, 0, 0.5);
  padding: 0.5rem 1rem;
  border-radius: 8px;
}

/* ── Bill of Materials ──────────────────────────────────────────────────── */
.bom-section {
  grid-column: 1 / -1;
  margin-top: 0;
}

.bom-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bom-card-header h3 {
  margin: 0;
}

.bom-header-actions {
  display: flex;
  gap: 0.5rem;
}

.bom-empty-state {
  padding: 1.5rem;
  color: var(--color-text-soft);
  font-size: 0.95rem;
}

.btn-link {
  background: none;
  border: none;
  color: var(--color-heading);
  cursor: pointer;
  padding: 0;
  font-size: inherit;
  text-decoration: underline;
}

.bom-row-num {
  color: var(--color-text-soft);
  font-size: 0.85rem;
}

.bom-needed-nonzero {
  color: var(--color-red, #e53e3e);
  font-weight: 600;
}

.bom-needed-zero {
  color: var(--color-text-soft);
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

.bom-desc-cell {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

/* Prevent long BOM names from forcing horizontal scroll */
.bom-detail-table :deep(table) {
  table-layout: fixed;
  width: 100%;
}

.cell-truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bom-item-notes {
  font-size: 0.8rem;
  color: var(--color-text-soft);
  font-style: italic;
}

.bom-inline-edit {
  display: flex;
  gap: 0.25rem;
}

.bom-edit-input {
  padding: 4px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 0.875rem;
  width: 100%;
  box-sizing: border-box;
}

.bom-edit-qty {
  max-width: 70px;
}

.bom-action-btns {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  flex-wrap: wrap;
}

.bom-edit-btn {
  padding: 5px 10px;
  font-size: 0.8rem;
  line-height: normal;
  border: none;
}

.bom-quick-add-link {
  color: var(--color-heading);
  cursor: pointer;
  text-decoration: none;
}
.bom-quick-add-link:hover {
  color: var(--color-heading);
  text-decoration: underline;
}

.bom-save-btn {
  padding: 5px 10px;
  font-size: 0.8rem;
  line-height: normal;
  border: none;
}

/* Status badges */
.bom-status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
}

.bom-status-covered {
  background: color-mix(in srgb, var(--color-green) 15%, transparent);
  color: var(--color-green);
}

.bom-status-low {
  background: color-mix(in srgb, var(--color-alert-warning) 15%, transparent);
  color: var(--color-alert-warning);
}

.bom-status-overallocated {
  background: color-mix(in srgb, var(--color-red) 15%, transparent);
  color: var(--color-red);
}

.bom-status-purchase {
  background: color-mix(in srgb, var(--color-blue) 15%, transparent);
  color: var(--color-blue);
}

.bom-status-unlinked {
  background: color-mix(in srgb, var(--color-text-soft) 15%, transparent);
  color: var(--color-text-soft);
}

.bom-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-start;
}

.text-muted {
  color: var(--color-text-soft);
}
</style>
