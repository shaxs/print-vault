<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import DataTable from '../components/DataTable.vue'
import ErrorModal from '../components/ErrorModal.vue'
import InfoModal from '../components/InfoModal.vue'
import AddInventoryToProjectModal from '../components/AddInventoryToProjectModal.vue'

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

const deleteProject = async () => {
  if (confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
    try {
      await APIService.deleteProject(project.value.id)
      router.push({ name: 'project-list' })
    } catch (error) {
      console.error('Failed to delete project:', error)
      errorMessage.value = 'Failed to delete project. Please try again.'
      isErrorModalVisible.value = true
    }
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

const handleInventoryAdded = async () => {
  isAddInventoryModalVisible.value = false
  infoModalMessage.value = 'Inventory items added successfully!'
  isInfoModalVisible.value = true
  await fetchProject() // Refresh the project data
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
                  + New Tracker
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="project" class="details-container inventory-full-width">
          <div class="card-header">
            <h3>Associated Inventory Items</h3>
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
              <button @click.stop="removeInventoryItem(item)" class="btn-remove-datatable">
                Remove
              </button>
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
  </div>
</template>

<style scoped>
/* Cleaned up CSS for ProjectDetailView.vue */

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
</style>
