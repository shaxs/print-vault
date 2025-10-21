<script setup>
import { ref, computed } from 'vue'
import BaseModal from './BaseModal.vue'
import APIService from '../services/APIService'

const props = defineProps({
  show: { type: Boolean, required: true },
  trackerId: { type: Number, required: true },
  existingCategories: { type: Array, default: () => [] },
  existingFiles: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'filesImported', 'filesUploaded'])

// Tab state
const activeTab = ref('urls') // 'urls' or 'upload'

// Shared metadata state
const selectedCategory = ref('')
const newCategoryName = ref('')
const showNewCategoryInput = ref(false)
const color = ref('')
const material = ref('')
const quantity = ref(1)

// URL Import state
const urlsText = ref('')
const importingURLs = ref(false)
const urlImportError = ref(null)

// File Upload state
const selectedFiles = ref([])
const uploading = ref(false)
const uploadError = ref(null)
const dragOver = ref(false)

// Extract existing colors and materials from existing files
const existingColors = computed(() => {
  const colors = new Set()
  props.existingFiles.forEach((file) => {
    if (file.color) colors.add(file.color)
  })
  return Array.from(colors).sort()
})

const existingMaterials = computed(() => {
  const materials = new Set()
  props.existingFiles.forEach((file) => {
    if (file.material) materials.add(file.material)
  })
  return Array.from(materials).sort()
})

// Computed
const hasFiles = computed(() => selectedFiles.value.length > 0)
const totalSize = computed(() => {
  return selectedFiles.value.reduce((sum, file) => sum + file.size, 0)
})

const finalCategory = computed(() => {
  return showNewCategoryInput.value ? newCategoryName.value.trim() : selectedCategory.value
})

// Methods
function close() {
  resetForm()
  emit('close')
}

function resetForm() {
  activeTab.value = 'urls'
  urlsText.value = ''
  selectedCategory.value = ''
  newCategoryName.value = ''
  showNewCategoryInput.value = false
  color.value = ''
  material.value = ''
  quantity.value = 1
  selectedFiles.value = []
  importingURLs.value = false
  uploading.value = false
  urlImportError.value = null
  uploadError.value = null
  dragOver.value = false
}

function toggleNewCategory() {
  showNewCategoryInput.value = !showNewCategoryInput.value
  if (showNewCategoryInput.value) {
    selectedCategory.value = ''
  } else {
    newCategoryName.value = ''
  }
}

// URL Import methods
async function importURLs() {
  urlImportError.value = null

  // Validate input
  if (!urlsText.value.trim()) {
    urlImportError.value = 'Please enter at least one URL'
    return
  }

  if (!finalCategory.value) {
    urlImportError.value = 'Please select or create a category'
    return
  }

  // Parse URLs (one per line)
  const urls = urlsText.value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

  if (urls.length === 0) {
    urlImportError.value = 'No valid URLs found'
    return
  }

  // Validate URLs
  const urlPattern = /^https?:\/\/.+/i
  const supportedExtensions = ['.3mf', '.stl', '.stp', '.step', '.obj', '.gcode']
  const invalidLines = []
  const invalidExtensions = []

  urls.forEach((line, index) => {
    if (!urlPattern.test(line)) {
      invalidLines.push(`Line ${index + 1}: "${line}"`)
    } else {
      const urlLower = line.toLowerCase()
      const hasValidExtension = supportedExtensions.some((ext) => urlLower.endsWith(ext))
      if (!hasValidExtension) {
        invalidExtensions.push(
          `Line ${index + 1}: "${line}" (must end with ${supportedExtensions.join(', ')})`,
        )
      }
    }
  })

  if (invalidLines.length > 0) {
    urlImportError.value = `Invalid URLs found:\n${invalidLines.join('\n')}\n\nPlease enter valid URLs starting with http:// or https://`
    return
  }

  if (invalidExtensions.length > 0) {
    urlImportError.value = `Unsupported file extensions:\n${invalidExtensions.join('\n')}`
    return
  }

  importingURLs.value = true

  try {
    // Fetch metadata for each URL
    const filesWithMetadata = []
    for (const url of urls) {
      try {
        const response = await APIService.fetchURLMetadata(url)
        filesWithMetadata.push({
          url: url,
          filename: response.data.filename,
          size: response.data.size,
          source: response.data.source,
          category: finalCategory.value,
          color: color.value || '',
          material: material.value || '',
          quantity: quantity.value || 1,
        })
      } catch (error) {
        console.error(`Failed to fetch metadata for ${url}:`, error)
        // Use URL as fallback
        filesWithMetadata.push({
          url: url,
          filename: url.split('/').pop().split('?')[0],
          size: 0,
          source: 'URL',
          category: finalCategory.value,
          color: color.value || '',
          material: material.value || '',
          quantity: quantity.value || 1,
        })
      }
    }

    // Emit files for configuration step
    emit('filesImported', filesWithMetadata)
    resetForm()
  } catch (error) {
    console.error('Import error:', error)
    urlImportError.value = error.response?.data?.error || 'Failed to import URLs'
  } finally {
    importingURLs.value = false
  }
}

// File Upload methods
function handleFileSelect(event) {
  const files = Array.from(event.target.files)
  addFiles(files)
}

function handleDrop(event) {
  event.preventDefault()
  dragOver.value = false

  const files = Array.from(event.dataTransfer.files)
  addFiles(files)
}

function handleDragOver(event) {
  event.preventDefault()
  dragOver.value = true
}

function handleDragLeave() {
  dragOver.value = false
}

function addFiles(files) {
  // Filter for 3D printing files
  const validExtensions = ['.stl', '.3mf', '.obj', '.gcode', '.step', '.stp']
  const validFiles = files.filter((file) => {
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    return validExtensions.includes(ext)
  })

  selectedFiles.value = [...selectedFiles.value, ...validFiles]
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

async function uploadFiles() {
  if (!hasFiles.value || uploading.value) return

  uploadError.value = null

  if (!finalCategory.value) {
    uploadError.value = 'Please select or create a category'
    return
  }

  uploading.value = true

  try {
    const formData = new FormData()
    selectedFiles.value.forEach((file) => {
      formData.append('files', file)
    })

    formData.append('category', finalCategory.value)
    if (color.value) formData.append('color', color.value)
    if (material.value) formData.append('material', material.value)
    formData.append('quantity', quantity.value.toString())

    const response = await APIService.uploadTrackerFiles(props.trackerId, formData)

    if (response.data.success) {
      emit('filesUploaded', response.data)
      resetForm()
    }
  } catch (error) {
    console.error('Upload error:', error)
    uploadError.value = error.response?.data?.error || 'Failed to upload files'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <BaseModal :show="show" title="Add Files" @close="close">
    <!-- Tabs -->
    <div class="tabs">
      <button
        :class="['tab', { active: activeTab === 'urls' }]"
        @click="activeTab = 'urls'"
        :disabled="importingURLs || uploading"
      >
        From URLs
      </button>
      <button
        :class="['tab', { active: activeTab === 'upload' }]"
        @click="activeTab = 'upload'"
        :disabled="importingURLs || uploading"
      >
        Upload Files
      </button>
    </div>

    <!-- Tab Content -->
    <div class="tab-content">
      <!-- URL Import Tab -->
      <div v-if="activeTab === 'urls'" class="url-import-section">
        <div class="form-group">
          <label>URLs (one per line)</label>
          <textarea
            v-model="urlsText"
            rows="6"
            placeholder="https://example.com/file1.stl&#10;https://example.com/file2.stl"
            :disabled="importingURLs"
          ></textarea>
          <p class="help-text">Supported: STL, 3MF, OBJ, GCODE, STEP</p>
        </div>

        <div v-if="urlImportError" class="alert alert-error">
          {{ urlImportError }}
        </div>
      </div>

      <!-- Upload Tab -->
      <div v-if="activeTab === 'upload'" class="upload-section">
        <div
          class="drop-zone"
          :class="{ 'drag-over': dragOver }"
          @drop="handleDrop"
          @dragover="handleDragOver"
          @dragleave="handleDragLeave"
        >
          <div class="drop-zone-content">
            <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p>Drag and drop files here or</p>
            <label class="file-input-label">
              <input
                type="file"
                multiple
                accept=".stl,.3mf,.obj,.gcode,.step,.stp"
                @change="handleFileSelect"
                :disabled="uploading"
                style="display: none"
              />
              <span class="btn btn-secondary">Browse Files</span>
            </label>
            <p class="help-text">Supported: STL, 3MF, OBJ, GCODE, STEP</p>
          </div>
        </div>

        <!-- Selected Files List -->
        <div v-if="hasFiles" class="selected-files">
          <h4>Selected Files ({{ selectedFiles.length }})</h4>
          <div class="file-list">
            <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
              <button @click="removeFile(index)" class="btn-remove" :disabled="uploading">×</button>
            </div>
          </div>
          <div class="total-size">Total: {{ formatFileSize(totalSize) }}</div>
        </div>

        <div v-if="uploadError" class="alert alert-error">
          {{ uploadError }}
        </div>
      </div>
    </div>

    <!-- Shared Metadata Form -->
    <div class="metadata-section">
      <h4>File Configuration</h4>

      <!-- Category -->
      <div class="form-group">
        <label>Category *</label>
        <div v-if="!showNewCategoryInput">
          <select v-model="selectedCategory" :disabled="importingURLs || uploading">
            <option value="">-- Select Category --</option>
            <option v-for="cat in existingCategories" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
          <button
            @click="toggleNewCategory"
            class="btn-link"
            :disabled="importingURLs || uploading"
          >
            + Add New Category
          </button>
        </div>
        <div v-else>
          <input
            v-model="newCategoryName"
            type="text"
            placeholder="Enter new category name"
            :disabled="importingURLs || uploading"
          />
          <button
            @click="toggleNewCategory"
            class="btn-link"
            :disabled="importingURLs || uploading"
          >
            Choose Existing
          </button>
        </div>
      </div>

      <!-- Color & Material -->
      <div class="form-row">
        <div class="form-group">
          <label>Color</label>
          <input
            v-model="color"
            type="text"
            list="color-suggestions"
            placeholder="e.g., Primary, Accent"
            :disabled="importingURLs || uploading"
          />
          <datalist id="color-suggestions">
            <option v-for="c in existingColors" :key="c" :value="c" />
          </datalist>
        </div>

        <div class="form-group">
          <label>Material</label>
          <input
            v-model="material"
            type="text"
            list="material-suggestions"
            placeholder="e.g., ABS, PLA, PETG"
            :disabled="importingURLs || uploading"
          />
          <datalist id="material-suggestions">
            <option v-for="m in existingMaterials" :key="m" :value="m" />
          </datalist>
        </div>
      </div>

      <!-- Quantity -->
      <div class="form-group">
        <label>Quantity</label>
        <input
          v-model.number="quantity"
          type="number"
          min="1"
          :disabled="importingURLs || uploading"
        />
      </div>
    </div>

    <!-- Footer -->
    <template #footer>
      <button @click="close" :disabled="importingURLs || uploading" class="btn btn-secondary">
        Cancel
      </button>
      <button
        v-if="activeTab === 'urls'"
        @click="importURLs"
        :disabled="importingURLs || !urlsText.trim()"
        class="btn btn-primary"
      >
        {{ importingURLs ? 'Importing...' : 'Import URLs' }}
      </button>
      <button
        v-else
        @click="uploadFiles"
        :disabled="uploading || !hasFiles"
        class="btn btn-primary"
      >
        {{
          uploading
            ? 'Uploading...'
            : `Upload ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`
        }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
/* Tabs */
.tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 20px;
}

.tab {
  flex: 1;
  padding: 12px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--color-text-muted);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: -2px;
}

.tab:hover:not(:disabled) {
  color: var(--color-text);
  background-color: var(--color-background-soft);
}

.tab.active {
  color: var(--vt-c-indigo);
  border-bottom-color: var(--vt-c-indigo);
}

.tab:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Tab Content */
.tab-content {
  min-height: 200px;
  margin-bottom: 20px;
}

/* URL Import Section */
.url-import-section textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-family: monospace;
  font-size: 0.9rem;
  resize: vertical;
}

.url-import-section textarea:focus {
  outline: none;
  border-color: var(--vt-c-indigo);
}

/* Upload Section */
.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  padding: 40px 20px;
  text-align: center;
  transition: all 0.3s ease;
  background-color: var(--color-background);
  margin-bottom: 20px;
}

.drop-zone.drag-over {
  border-color: var(--vt-c-indigo);
  background-color: var(--color-background-soft);
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.upload-icon {
  width: 48px;
  height: 48px;
  color: var(--color-text-muted);
  margin-bottom: 10px;
}

.drop-zone p {
  color: var(--color-text);
  margin: 5px 0;
}

.file-input-label {
  cursor: pointer;
}

/* Selected Files */
.selected-files h4 {
  color: var(--color-heading);
  margin-bottom: 10px;
  font-size: 1rem;
}

.file-list {
  border: 1px solid var(--color-border);
  border-radius: 4px;
  max-height: 150px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-bottom: 1px solid var(--color-border);
}

.file-item:last-child {
  border-bottom: none;
}

.file-name {
  flex: 1;
  color: var(--color-text);
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  white-space: nowrap;
}

.btn-remove {
  background: none;
  border: none;
  color: #dc2626;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.btn-remove:hover:not(:disabled) {
  color: #b91c1c;
}

.btn-remove:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.total-size {
  padding: 10px;
  text-align: right;
  font-weight: bold;
  color: var(--color-text);
  border-top: 1px solid var(--color-border);
  margin-top: 5px;
}

/* Metadata Section */
.metadata-section {
  border-top: 1px solid var(--color-border);
  padding-top: 20px;
  margin-top: 20px;
}

.metadata-section h4 {
  color: var(--color-heading);
  margin-bottom: 15px;
  font-size: 1rem;
}

/* Form Elements */
.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: var(--color-text);
  font-weight: 500;
  font-size: 0.9rem;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--vt-c-indigo);
}

.form-group input:disabled,
.form-group select:disabled,
.form-group textarea:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-row {
  display: flex;
  gap: 15px;
}

.form-row .form-group {
  flex: 1;
}

.btn-link {
  background: none;
  border: none;
  color: var(--vt-c-indigo);
  cursor: pointer;
  font-size: 0.85rem;
  margin-top: 5px;
  padding: 0;
}

.btn-link:hover:not(:disabled) {
  text-decoration: underline;
}

.btn-link:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.help-text {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-top: 5px;
}

/* Alerts */
.alert {
  padding: 12px;
  border-radius: 4px;
  margin-top: 15px;
}

.alert-error {
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: var(--color-text);
  white-space: pre-wrap;
}

/* Buttons */
.btn {
  padding: 10px 20px;
  border-radius: 4px;
  border: none;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary {
  background-color: var(--vt-c-indigo);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: var(--vt-c-indigo-dark);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.btn-secondary:hover:not(:disabled) {
  background-color: var(--color-background-soft);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
