<script setup>
import { ref, computed, onMounted } from 'vue'
import APIService from '@/services/APIService.js'
import { parseFilename } from '@/utils/filenameParser'
import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

const props = defineProps({
  fileTree: { type: Array, required: true },
})

// Emit storage option changes to parent
const emit = defineEmits(['update:storageOption'])

// Force reactivity trigger
const forceUpdate = ref(0)

// Track which files are selected for bulk operations
const bulkSelectedFiles = ref(new Set())
const bulkQuantity = ref('')
const bulkColor = ref('')
const bulkMaterial = ref(null) // Single material OR array of materials (for multicolor)

// Check if multicolor is selected (enables multiple material selection)
const isMulticolorSelected = computed(() => {
  return bulkColor.value === 'Multicolor'
})

// File storage option - REQUIRED field, no default
const storageOption = ref('')

// Watch for storage option changes and emit to parent
import { watch } from 'vue'
watch(storageOption, (newValue) => {
  emit('update:storageOption', newValue)
})

// Material and color options
const colorOptions = ['Primary', 'Accent', 'Multicolor', 'Clear', 'Other']
const materialOptions = ref([])
const loadingMaterials = ref(false)

// Smart defaults material assignments
const smartDefaultPrimaryMaterial = ref(null)
const smartDefaultAccentMaterial = ref(null)

// Load materials from API (both blueprints and base materials)
const loadMaterials = async () => {
  loadingMaterials.value = true
  try {
    const response = await APIService.getMaterials()
    // Store full material objects for Multiselect
    materialOptions.value = response.data.results || response.data

    // If no materials loaded, use fallback
    if (materialOptions.value.length === 0) {
      // Create basic material objects for fallback
      materialOptions.value = [
        { id: 'abs', name: 'ABS', type: 'base' },
        { id: 'petg', name: 'PETG', type: 'base' },
        { id: 'pla', name: 'PLA', type: 'base' },
        { id: 'asa', name: 'ASA', type: 'base' },
        { id: 'tpu', name: 'TPU', type: 'base' },
        { id: 'nylon', name: 'Nylon', type: 'base' },
        { id: 'other', name: 'Other', type: 'base' }
      ]
    }
  } catch (error) {
    console.error('Failed to load materials:', error)
    // Fallback to default materials
    materialOptions.value = [
      { id: 'abs', name: 'ABS', type: 'base' },
      { id: 'petg', name: 'PETG', type: 'base' },
      { id: 'pla', name: 'PLA', type: 'base' },
      { id: 'asa', name: 'ASA', type: 'base' },
      { id: 'tpu', name: 'TPU', type: 'base' },
      { id: 'nylon', name: 'Nylon', type: 'base' },
      { id: 'other', name: 'Other', type: 'base' }
    ]
  } finally {
    loadingMaterials.value = false
    
    // Initialize smart defaults to first material (ABS typically)
    if (materialOptions.value.length > 0) {
      smartDefaultPrimaryMaterial.value = materialOptions.value[0]
      smartDefaultAccentMaterial.value = materialOptions.value[0]
    }
  }
}

// Format material label for Multiselect
const formatMaterialLabel = (mat) => {
  if (!mat) return ''
  const brandName = mat.brand?.name || ''
  const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
  return `${brandName} ${mat.name}${diameter}`.trim()
}

onMounted(() => {
  loadMaterials()
})

// Get all selected files (flat list)
const selectedFiles = computed(() => {
  // Add dependency on forceUpdate to trigger recomputation
  // This ensures the computed re-runs when forceUpdate changes
  if (forceUpdate.value < 0) return [] // Never true, but creates dependency

  const files = []

  function collectFiles(nodes) {
    nodes.forEach((node) => {
      if (node.children) {
        collectFiles(node.children)
      } else if (node.isSelected) {
        files.push(node)
      }
    })
  }

  collectFiles(props.fileTree)
  return files
})

// Count configured files
const configuredCount = computed(() => {
  // Dependency on selectedFiles will automatically re-trigger when forceUpdate changes
  return selectedFiles.value.filter((f) => f.color && f.material && f.quantity).length
})

// Calculate total file size
const totalSize = computed(() => {
  return selectedFiles.value.reduce((sum, file) => sum + (file.size || 0), 0)
})

const totalSizeMB = computed(() => {
  return (totalSize.value / (1024 * 1024)).toFixed(2)
})

const totalSizeGB = computed(() => {
  return (totalSize.value / (1024 * 1024 * 1024)).toFixed(2)
})

// Check if total size is large (>1 GB)
const isLargeDownload = computed(() => {
  return totalSize.value > 1024 * 1024 * 1024 // > 1 GB
})

// Check if any uploaded files exist
const hasUploadedFiles = computed(() => {
  return selectedFiles.value.some((file) => file.source === 'Upload')
})

// Check if any URL files exist (not uploaded)
const hasUrlFiles = computed(() => {
  return selectedFiles.value.some((file) => file.source !== 'Upload')
})

// Check if storage option is required (only when URL files exist)
const isStorageOptionRequired = computed(() => {
  return hasUrlFiles.value
})

// Apply smart defaults to all unconfigured files
function applySmartDefaults() {
  const defaultMaterial = smartDefaultPrimaryMaterial.value?.name || materialOptions.value[0]?.name || 'ABS'
  const primaryMaterial = smartDefaultPrimaryMaterial.value?.name || 'ABS'
  const accentMaterial = smartDefaultAccentMaterial.value?.name || 'ABS'
  const primaryMaterialId = smartDefaultPrimaryMaterial.value?.id
  const accentMaterialId = smartDefaultAccentMaterial.value?.id

  // Directly modify the fileTree nodes to ensure reactivity
  function applyToNodes(nodes) {
    nodes.forEach((node) => {
      if (node.children) {
        applyToNodes(node.children)
      } else if (node.isSelected) {
        const defaults = parseFilename(node.name, defaultMaterial)
        if (!node.color) node.color = defaults.color
        
        // Get final color (either existing or detected)
        const finalColor = node.color || defaults.color
        
        // Apply material based on color - ALWAYS update for Primary/Accent to allow correction
        if (finalColor === 'Accent') {
          node.material = accentMaterial
          if (accentMaterialId) node.material_ids = [accentMaterialId]
        } else if (finalColor === 'Primary') {
          node.material = primaryMaterial
          if (primaryMaterialId) node.material_ids = [primaryMaterialId]
        } else if (!node.material) {
          // For other colors (Clear, Multicolor, Other), only set if empty
          node.material = defaults.material || primaryMaterial
          if (primaryMaterialId) node.material_ids = [primaryMaterialId]
        }
        
        // Always apply quantity from smart defaults (don't skip if quantity is 1)
        if (!node.quantity || node.quantity === 1) node.quantity = defaults.quantity
      }
    })
  }

  applyToNodes(props.fileTree)

  // Force Vue to detect the changes by incrementing forceUpdate
  forceUpdate.value++
}

// Apply bulk settings to selected files
function applyBulkSettings() {
  selectedFiles.value.forEach((file) => {
    if (bulkSelectedFiles.value.has(file.name)) {
      if (bulkQuantity.value) file.quantity = parseInt(bulkQuantity.value) || 1
      if (bulkColor.value) file.color = bulkColor.value
      
      // Handle material - single or multiple (for multicolor)
      if (bulkMaterial.value) {
        if (Array.isArray(bulkMaterial.value)) {
          // Multiple materials selected (multicolor)
          file.material = bulkMaterial.value.map(m => m.name).join(', ')
          file.material_ids = bulkMaterial.value.map(m => m.id)
        } else {
          // Single material
          file.material = bulkMaterial.value.name || bulkMaterial.value
          file.material_ids = [bulkMaterial.value.id]
        }
      }
    }
  })

  // Clear only the file selections (preserve quantity, color, material for next apply)
  bulkSelectedFiles.value.clear()

  // Force reactivity
  forceUpdate.value++
}

// Toggle bulk selection for a file
function toggleBulkSelection(filename) {
  if (bulkSelectedFiles.value.has(filename)) {
    bulkSelectedFiles.value.delete(filename)
  } else {
    bulkSelectedFiles.value.add(filename)
  }
}

// Toggle select all files for bulk operation
function toggleSelectAllForBulk() {
  if (bulkSelectedFiles.value.size === selectedFiles.value.length) {
    // All selected, deselect all
    bulkSelectedFiles.value.clear()
  } else {
    // Not all selected, select all
    selectedFiles.value.forEach((file) => {
      bulkSelectedFiles.value.add(file.name)
    })
  }
}

// Check if all files are selected for bulk
function areAllFilesSelectedForBulk() {
  return (
    bulkSelectedFiles.value.size === selectedFiles.value.length && selectedFiles.value.length > 0
  )
}

// Select all files in a specific directory
function toggleDirectorySelection(files) {
  const allSelected = files.every((file) => bulkSelectedFiles.value.has(file.name))

  if (allSelected) {
    // Deselect all files in directory
    files.forEach((file) => {
      bulkSelectedFiles.value.delete(file.name)
    })
  } else {
    // Select all files in directory
    files.forEach((file) => {
      bulkSelectedFiles.value.add(file.name)
    })
  }
}

// Check if all files in directory are selected
function areAllFilesInDirectorySelected(files) {
  return files.every((file) => bulkSelectedFiles.value.has(file.name))
}

// Group files by directory
const groupedFiles = computed(() => {
  const groups = {}

  function traverse(nodes, path = []) {
    nodes.forEach((node) => {
      if (node.children) {
        traverse(node.children, [...path, node.name])
      } else if (node.isSelected) {
        const dirPath = path.join(' / ') || 'Root'
        if (!groups[dirPath]) {
          groups[dirPath] = []
        }
        groups[dirPath].push(node)
      }
    })
  }

  traverse(props.fileTree)
  return groups
})
</script>

<template>
  <div class="config-step-container">
    <div class="config-header">
      <h2>Configure Print Settings</h2>
      <p class="subtitle">
        Set quantity, color, and material for each file. Use bulk operations to configure multiple
        files at once.
      </p>
      <div class="progress-info">
        <span class="progress-label">Configuration Progress:</span>
        <span class="progress-count"
          >{{ configuredCount }} of {{ selectedFiles.length }} files configured</span
        >
        <div class="progress-bar-bg">
          <div
            class="progress-bar-fg"
            :style="{ width: (configuredCount / selectedFiles.length) * 100 + '%' }"
          ></div>
        </div>
      </div>
    </div>

    <div class="config-layout">
      <!-- Left Pane: Selected Files List -->
      <div class="files-pane">
        <div class="pane-header">
          <h3>Selected Files ({{ selectedFiles.length }})</h3>
          <div class="bulk-select-actions">
            <span class="bulk-count" v-if="bulkSelectedFiles.size > 0">
              ({{ bulkSelectedFiles.size }} selected)
            </span>
            <button
              class="btn btn-sm"
              :class="areAllFilesSelectedForBulk() ? 'btn-secondary' : 'btn-primary'"
              @click="toggleSelectAllForBulk"
            >
              {{ areAllFilesSelectedForBulk() ? 'Unselect All' : 'Select All' }}
            </button>
          </div>
        </div>

        <div class="files-list">
          <div v-for="(files, directory) in groupedFiles" :key="directory" class="directory-group">
            <div class="directory-header">
              <input
                type="checkbox"
                :checked="areAllFilesInDirectorySelected(files)"
                @change="toggleDirectorySelection(files)"
                class="directory-checkbox"
              />
              <span class="directory-name">{{ directory }}</span>
              <span class="file-count">({{ files.length }} files)</span>
            </div>

            <div
              v-for="file in files"
              :key="file.name"
              class="file-item"
              :class="{
                'bulk-selected': bulkSelectedFiles.has(file.name),
                configured: file.color && file.material && file.quantity,
              }"
            >
              <input
                type="checkbox"
                :checked="bulkSelectedFiles.has(file.name)"
                @change="toggleBulkSelection(file.name)"
                class="bulk-checkbox"
              />
              <div class="file-info">
                <div class="file-name-row">
                  <span class="file-name">{{ file.name }}</span>
                  <span v-if="file.sizeMB" class="file-size-text">{{ file.sizeMB }} MB</span>
                </div>
                <div class="file-config" v-if="file.color || file.material || file.quantity">
                  <span class="config-badge" v-if="file.quantity">Qty: {{ file.quantity }}</span>
                  <span class="config-badge color-badge" v-if="file.color">{{ file.color }}</span>
                  <span class="config-badge material-badge" v-if="file.material">{{
                    file.material
                  }}</span>
                </div>
                <div class="file-config unconfigured" v-else>
                  <span class="warning-text">Not configured</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Pane: Configuration Controls -->
      <div class="config-pane">
        <div class="config-section">
          <h3>Bulk Configuration</h3>
          <p class="section-description">
            Select files from the list and apply settings to multiple files at once.
          </p>

          <div class="form-group">
            <label>Quantity</label>
            <input
              v-model.number="bulkQuantity"
              type="number"
              min="1"
              class="form-control"
              placeholder="Enter quantity..."
            />
          </div>

          <div class="form-group">
            <label>Color</label>
            <select v-model="bulkColor" class="form-control">
              <option value="">Select color...</option>
              <option v-for="color in colorOptions" :key="color" :value="color">
                {{ color }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>Material{{ isMulticolorSelected ? 's' : '' }}</label>
            <Multiselect
              v-model="bulkMaterial"
              :options="materialOptions"
              :custom-label="formatMaterialLabel"
              track-by="id"
              :placeholder="isMulticolorSelected ? 'Type to search and select multiple materials...' : 'Type to search materials...'"
              :loading="loadingMaterials"
              :searchable="true"
              :multiple="isMulticolorSelected"
              :close-on-select="!isMulticolorSelected"
              :show-labels="false"
            />
            <p v-if="isMulticolorSelected" class="help-text">
              Select multiple materials for MMU/multicolor printing
            </p>
          </div>

          <button
            class="btn btn-primary full-width"
            @click="applyBulkSettings"
            :disabled="bulkSelectedFiles.size === 0"
          >
            Apply to {{ bulkSelectedFiles.size }} Selected File{{
              bulkSelectedFiles.size !== 1 ? 's' : ''
            }}
          </button>
        </div>

        <div class="config-section quick-actions">
          <h3>Quick Actions</h3>

          <div class="form-group">
            <label>Primary Material</label>
            <Multiselect
              v-model="smartDefaultPrimaryMaterial"
              :options="materialOptions"
              :custom-label="formatMaterialLabel"
              track-by="id"
              placeholder="Primary color material..."
              :loading="loadingMaterials"
              :searchable="true"
              :close-on-select="true"
              :show-labels="false"
            />
          </div>

          <div class="form-group">
            <label>Accent Material</label>
            <Multiselect
              v-model="smartDefaultAccentMaterial"
              :options="materialOptions"
              :custom-label="formatMaterialLabel"
              track-by="id"
              placeholder="Accent color material..."
              :loading="loadingMaterials"
              :searchable="true"
              :close-on-select="true"
              :show-labels="false"
            />
          </div>

          <button class="btn btn-secondary full-width" @click="applySmartDefaults">
            Apply Smart Defaults
          </button>
          <p class="action-description">
            Automatically detects quantity from filenames (_x2, _x4) and color from brackets ([a] =
            Accent). Uses selected materials above.
          </p>
        </div>

        <div v-if="hasUrlFiles" class="config-section storage-option-section">
          <h3>File Storage Option <span class="required-badge">Required</span></h3>
          <p class="section-description">
            Choose how you want to store the STL files for this tracker.
            <span v-if="hasUploadedFiles" class="upload-note"
              >Any uploaded files will be stored locally.</span
            >
          </p>

          <!-- File size summary -->
          <div class="file-size-summary">
            <div class="size-info">
              <span class="size-label">Total Size:</span>
              <span class="size-value">
                {{ totalSizeMB }} MB
                <span v-if="parseFloat(totalSizeGB) > 0.1" class="size-secondary"
                  >({{ totalSizeGB }} GB)</span
                >
              </span>
            </div>
            <div class="size-info">
              <span class="size-label">Files:</span>
              <span class="size-value">{{ selectedFiles.length }} files</span>
            </div>
          </div>

          <div class="radio-group">
            <label class="radio-option" :class="{ selected: storageOption === 'link' }">
              <input type="radio" v-model="storageOption" value="link" name="storageOption" />
              <div class="radio-content">
                <span class="radio-title">Store File Links</span>
                <span class="radio-description"
                  >Files remain at their source. Only links will be stored in the tracker. No
                  storage space required.</span
                >
              </div>
            </label>

            <label class="radio-option" :class="{ selected: storageOption === 'local' }">
              <input type="radio" v-model="storageOption" value="local" name="storageOption" />
              <div class="radio-content">
                <span class="radio-title">Download and Store Locally</span>
                <span class="radio-description"
                  >Files will be downloaded and stored on your server. Requires {{ totalSizeMB }} MB
                  of storage.</span
                >
              </div>
            </label>
          </div>

          <div class="storage-warning" v-if="storageOption === 'local' && isLargeDownload">
            <strong>⚠️ Large Download Warning:</strong> You are about to download
            {{ totalSizeGB }} GB ({{ selectedFiles.length }} files). This may take several minutes
            depending on your connection speed. Please ensure you have sufficient storage space
            available.
          </div>

          <div class="storage-note" v-else-if="storageOption === 'local'">
            <strong>Note:</strong> Files will be downloaded to your local server when you create the
            tracker.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.config-step-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.config-header {
  text-align: center;
  margin-bottom: 1rem;
}

.config-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-heading);
  margin-bottom: 0.5rem;
}

.subtitle {
  color: var(--color-text-soft);
  font-size: 0.95rem;
  margin-bottom: 1rem;
}

.progress-info {
  max-width: 600px;
  margin: 0 auto;
}

.progress-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-heading);
  margin-right: 0.5rem;
}

.progress-count {
  font-size: 0.9rem;
  color: var(--color-heading);
  font-weight: 500;
}

.progress-bar-bg {
  width: 100%;
  background-color: var(--color-background);
  border-radius: 9999px;
  height: 0.5rem;
  margin-top: 0.5rem;
}

.progress-bar-fg {
  background-color: var(--color-blue);
  height: 0.5rem;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.config-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 1.5rem;
  min-height: 500px;
}

/* Left Pane - Files List */
.files-pane {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pane-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--color-border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: var(--color-background);
}

.pane-header h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0;
}

.bulk-select-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.bulk-count {
  color: var(--color-text-soft);
  font-weight: 500;
  margin-right: 0.25rem;
}

.files-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
}

.directory-group {
  margin-bottom: 1.5rem;
}

.directory-group:last-child {
  margin-bottom: 0;
}

.directory-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--color-border);
}

.directory-checkbox {
  cursor: pointer;
  margin: 0;
  flex-shrink: 0;
}

.directory-name {
  font-weight: 600;
  color: var(--color-heading);
  font-size: 0.95rem;
}

.file-count {
  color: var(--color-text-soft);
  font-size: 0.85rem;
}

.file-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.6rem;
  border-radius: 6px;
  margin-bottom: 0.4rem;
  transition: background-color 0.15s;
  cursor: pointer;
}

.file-item:hover {
  background-color: var(--color-background-mute);
}

.file-item.bulk-selected {
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid var(--color-blue);
}

.file-item.configured {
  border-left: 3px solid var(--color-green);
}

.bulk-checkbox {
  margin-top: 0.2rem;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.file-name {
  font-size: 0.9rem;
  color: var(--color-text);
  word-break: break-word;
  flex: 1;
}

.file-size-text {
  font-size: 0.75rem;
  color: var(--color-text-soft);
  white-space: nowrap;
  font-weight: 500;
}

.file-config {
  display: flex;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.file-config.unconfigured {
  margin-top: 0.25rem;
}

.config-badge {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 12px;
  background-color: var(--color-background);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  font-weight: 500;
}

.color-badge {
  background-color: rgba(59, 130, 246, 0.1);
  border-color: var(--color-blue);
  color: var(--color-blue);
}

.material-badge {
  background-color: rgba(168, 85, 247, 0.1);
  border-color: #a855f7;
  color: #a855f7;
}

.warning-text {
  font-size: 0.8rem;
  color: #f5a623;
  font-style: italic;
}

/* Right Pane - Configuration */
.config-pane {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  position: sticky;
  top: 1rem;
  align-self: flex-start;
  max-height: calc(100vh - 2rem);
  overflow-y: auto;
}

.config-section {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.25rem;
}

.config-section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0 0 0.5rem 0;
}

.section-description {
  font-size: 0.85rem;
  color: var(--color-text-soft);
  margin-bottom: 1rem;
}

.upload-note {
  display: block;
  margin-top: 0.5rem;
  color: var(--color-text-soft);
  font-weight: 500;
  font-size: 0.9rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-heading);
  margin-bottom: 0.4rem;
}

.form-control {
  width: 100%;
  padding: 0.6rem 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
}

.form-control:focus {
  outline: none;
  border-color: var(--color-blue);
}

.full-width {
  width: 100%;
  margin-top: 0.5rem;
}

.quick-actions .btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.icon {
  font-size: 1.1rem;
}

.action-description {
  font-size: 0.8rem;
  color: var(--color-text-soft);
  margin-top: 0.5rem;
  line-height: 1.4;
}

.help-section {
  background-color: var(--color-background);
}

.help-section h4 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0 0 0.75rem 0;
}

.help-list {
  list-style: none;
  padding: 0;
  margin: 0;
  font-size: 0.85rem;
}

.help-list li {
  padding: 0.4rem 0;
  color: var(--color-text-soft);
}

.help-list code {
  background-color: var(--color-background-soft);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  color: var(--color-text);
  font-size: 0.85rem;
}

/* Storage Option Section */
.storage-option-section {
  background-color: var(--color-background-mute);
  border: 2px solid var(--color-border);
}

.storage-option-section h3 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 0.5rem 0;
}

.required-badge {
  background-color: var(--color-red);
  color: white;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-description {
  font-size: 0.9rem;
  color: var(--color-text-soft);
  margin-bottom: 1rem;
}

.radio-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.radio-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border: 2px solid var(--color-border);
  border-radius: 8px;
  background-color: var(--color-background);
  cursor: pointer;
  transition: all 0.2s;
}

.radio-option:hover {
  border-color: var(--color-blue);
  background-color: var(--color-background-soft);
}

.radio-option.selected {
  border-color: var(--color-blue);
  background-color: rgba(59, 130, 246, 0.05);
}

.radio-option input[type='radio'] {
  margin-top: 0.2rem;
  cursor: pointer;
  flex-shrink: 0;
}

.radio-content {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}

.radio-title {
  font-weight: 600;
  color: var(--color-heading);
  font-size: 0.95rem;
}

.radio-description {
  font-size: 0.85rem;
  color: var(--color-text-soft);
  line-height: 1.4;
}

.storage-note {
  padding: 0.75rem;
  background-color: rgba(59, 130, 246, 0.1);
  border-left: 3px solid var(--color-blue);
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--color-text);
  margin-bottom: 1rem;
}

.storage-warning {
  padding: 0.75rem;
  background-color: rgba(234, 179, 8, 0.1);
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  font-size: 0.85rem;
  color: #92400e;
  margin-bottom: 1rem;
}

.file-size-summary {
  display: flex;
  gap: 2rem;
  padding: 1rem;
  background-color: var(--color-background-soft);
  border-radius: 6px;
  margin-bottom: 1rem;
  border: 1px solid var(--color-border);
}

.size-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.size-label {
  font-size: 0.75rem;
  color: var(--color-text-soft);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 600;
}

.size-value {
  font-size: 1.1rem;
  color: var(--color-heading);
  font-weight: 600;
}

.size-secondary {
  font-size: 0.9rem;
  color: var(--color-text-soft);
  font-weight: normal;
}

.implementation-note {
  padding: 0.75rem;
  background-color: rgba(234, 179, 8, 0.1);
  border-left: 3px solid #eab308;
  border-radius: 4px;
  font-size: 0.8rem;
  color: var(--color-text-soft);
}

.implementation-note strong {
  color: var(--color-heading);
  display: block;
  margin-bottom: 0.5rem;
}

.implementation-note ul {
  margin: 0;
  padding-left: 1.5rem;
  list-style-type: disc;
}

.implementation-note li {
  margin-bottom: 0.25rem;
  line-height: 1.4;
}

/* Responsive */
@media (max-width: 1024px) {
  .config-layout {
    grid-template-columns: 1fr;
  }

  .config-pane {
    order: -1;
    position: relative;
    top: auto;
    max-height: none;
  }
}
</style>
