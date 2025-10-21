<script setup>
import { ref, computed, onMounted } from 'vue'
import APIService from '@/services/APIService.js'
import { parseFilename } from '@/utils/filenameParser'

const props = defineProps({
  files: { type: Array, required: true }, // Simple array of file objects
  existingCategories: { type: Array, default: () => [] },
  categoryError: { type: Boolean, default: false }, // Show error state for category
})

const emit = defineEmits(['update:category'])

// Force reactivity trigger
const forceUpdate = ref(0)

// Track which files are selected for bulk operations
const bulkSelectedFiles = ref(new Set())
const bulkColor = ref('')
const bulkMaterial = ref('')

// Category state
const selectedCategory = ref('')
const newCategoryName = ref('')
const showNewCategoryInput = ref(false)

// Material and color options
const colorOptions = ['Primary', 'Accent', 'Multicolor', 'Clear', 'Other']
const materialOptions = ref([])
const loadingMaterials = ref(false)

// Emit category changes
import { watch } from 'vue'
watch(selectedCategory, (newValue) => {
  emit('update:category', newValue)
})

watch(newCategoryName, (newValue) => {
  if (showNewCategoryInput.value) {
    emit('update:category', newValue)
  }
})

// Load materials from API
const loadMaterials = async () => {
  loadingMaterials.value = true
  try {
    const response = await APIService.getMaterials()
    materialOptions.value = response.data.map((m) => m.name)

    // If no materials loaded, use fallback
    if (materialOptions.value.length === 0) {
      materialOptions.value = ['ABS', 'PETG', 'PLA', 'ASA', 'TPU', 'Nylon', 'Other']
    }
  } catch (error) {
    console.error('Failed to load materials:', error)
    // Fallback to default materials
    materialOptions.value = ['ABS', 'PETG', 'PLA', 'ASA', 'TPU', 'Nylon', 'Other']
  } finally {
    loadingMaterials.value = false
  }
}

onMounted(() => {
  loadMaterials()
})

// Count configured files
const configuredCount = computed(() => {
  return props.files.filter((f) => f.color && f.material && f.quantity).length
})

// Calculate total file size
const totalSize = computed(() => {
  return props.files.reduce((sum, file) => sum + (file.size || 0), 0)
})

const totalSizeMB = computed(() => {
  return (totalSize.value / (1024 * 1024)).toFixed(2)
})

// Check if all files are configured
const allFilesConfigured = computed(() => {
  return props.files.length > 0 && configuredCount.value === props.files.length
})

// Apply smart defaults to all unconfigured files
function applySmartDefaults() {
  const defaultMaterial = materialOptions.value[0] || 'ABS'

  props.files.forEach((file) => {
    const defaults = parseFilename(file.name, defaultMaterial)
    if (!file.color) file.color = defaults.color
    if (!file.material) file.material = defaults.material
    // Always apply quantity from smart defaults (don't skip if quantity is 1)
    if (!file.quantity || file.quantity === 1) file.quantity = defaults.quantity
  })

  // Force reactivity
  forceUpdate.value++
}

// Apply bulk settings to selected files
function applyBulkSettings() {
  props.files.forEach((file) => {
    if (bulkSelectedFiles.value.has(file.name)) {
      if (bulkColor.value) file.color = bulkColor.value
      if (bulkMaterial.value) file.material = bulkMaterial.value
    }
  })

  // Clear bulk selections and inputs
  bulkSelectedFiles.value.clear()
  bulkColor.value = ''
  bulkMaterial.value = ''

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
  if (bulkSelectedFiles.value.size === props.files.length) {
    bulkSelectedFiles.value.clear()
  } else {
    props.files.forEach((file) => {
      bulkSelectedFiles.value.add(file.name)
    })
  }
}

// Check if all files are selected for bulk
function areAllFilesSelectedForBulk() {
  return bulkSelectedFiles.value.size === props.files.length && props.files.length > 0
}

// Toggle category input
function toggleNewCategory() {
  showNewCategoryInput.value = !showNewCategoryInput.value
  if (showNewCategoryInput.value) {
    selectedCategory.value = ''
  } else {
    newCategoryName.value = ''
  }
}

// Format file size
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// Expose method to check if ready to import
defineExpose({
  allFilesConfigured,
})
</script>

<template>
  <div class="config-step-container">
    <div class="config-header">
      <h2>Configure Files</h2>
      <p class="subtitle">
        Set quantity, color, and material for each file. All files must be configured before
        importing.
      </p>
      <div class="progress-info">
        <span class="progress-label">Configuration Progress:</span>
        <span class="progress-count"
          >{{ configuredCount }} of {{ files.length }} files configured</span
        >
        <div class="progress-bar-bg">
          <div
            class="progress-bar-fg"
            :style="{ width: files.length > 0 ? (configuredCount / files.length) * 100 + '%' : 0 }"
          ></div>
        </div>
      </div>
    </div>

    <div class="config-layout">
      <!-- Left Pane: Files List with Category -->
      <div class="files-pane">
        <div class="pane-header">
          <div class="header-top">
            <h3>Selected Files ({{ files.length }})</h3>
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

          <!-- Category Selection -->
          <div class="category-section">
            <label>Category *</label>
            <div class="category-input-group">
              <select
                v-if="!showNewCategoryInput"
                v-model="selectedCategory"
                class="category-select"
                :class="{ error: categoryError && !selectedCategory }"
              >
                <option value="">-- Select Category --</option>
                <option v-for="cat in existingCategories" :key="cat" :value="cat">
                  {{ cat }}
                </option>
              </select>
              <input
                v-else
                v-model="newCategoryName"
                type="text"
                placeholder="Enter new category name"
                class="category-input"
                :class="{ error: categoryError && !newCategoryName }"
              />
              <button @click="toggleNewCategory" class="btn btn-sm btn-secondary">
                {{ showNewCategoryInput ? 'Choose Existing' : 'Add New Category' }}
              </button>
            </div>
            <p v-if="categoryError" class="error-message">
              ⚠️ Please select or create a category before importing
            </p>
          </div>
        </div>

        <div class="files-list">
          <div
            v-for="(file, index) in files"
            :key="index"
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
                <span v-if="file.size" class="file-size-text">{{ formatFileSize(file.size) }}</span>
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

        <div class="files-footer">
          <span class="total-size">Total: {{ totalSizeMB }} MB</span>
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
            <label>Color</label>
            <select v-model="bulkColor" class="form-control">
              <option value="">Select color...</option>
              <option v-for="color in colorOptions" :key="color" :value="color">
                {{ color }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>Material</label>
            <select v-model="bulkMaterial" class="form-control">
              <option value="">Select material...</option>
              <option v-for="material in materialOptions" :key="material" :value="material">
                {{ material }}
              </option>
            </select>
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

          <button class="btn btn-secondary full-width" @click="applySmartDefaults">
            Apply Smart Defaults
          </button>
          <p class="action-description">
            Automatically detects quantity from filenames (_x2, _x4) and color from brackets ([a] =
            Accent, [d] = Multicolor).
          </p>
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
  background-color: var(--color-background);
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

/* Category Section */
.category-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.category-section label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-heading);
}

.category-input-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.category-select,
.category-input {
  flex: 1;
  max-width: 300px;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 0.9rem;
}

.category-select:focus,
.category-input:focus {
  outline: none;
  border-color: var(--color-blue);
}

.files-list {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.25rem;
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

.files-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--color-border);
  background-color: var(--color-background);
}

.total-size {
  font-weight: 600;
  color: var(--color-heading);
  font-size: 0.9rem;
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

.action-description {
  font-size: 0.8rem;
  color: var(--color-text-soft);
  margin-top: 0.5rem;
  line-height: 1.4;
}

/* Error States */
.category-select.error,
.category-input.error {
  border-color: var(--color-red);
  border-width: 2px;
}

.error-message {
  color: var(--color-red);
  font-size: 0.875rem;
  margin-top: 0.5rem;
  font-weight: 500;
}

/* Responsive */
@media (max-width: 1024px) {
  .config-layout {
    grid-template-columns: 1fr;
  }

  .config-pane {
    order: -1;
  }
}
</style>
