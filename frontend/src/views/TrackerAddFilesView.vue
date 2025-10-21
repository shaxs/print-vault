<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import FileConfigurationStepSimple from '@/components/FileConfigurationStepSimple.vue'

const route = useRoute()
const router = useRouter()

// Data
const tracker = ref(null)
const loading = ref(true)
const error = ref(null)

// Tab state
const activeTab = ref('urls') // 'urls' or 'upload'

// Shared metadata state
const selectedCategory = ref('')
const categoryError = ref(false) // Track if user tried to submit without category

// URL Import state
const urlsText = ref('')
const importingURLs = ref(false)
const urlImportError = ref(null)
const showUrlPreview = ref(false)
const parsedUrlFiles = ref([])

// File Upload state
const selectedFiles = ref([])
const uploading = ref(false)
const uploadError = ref(null)
const dragOver = ref(false)
const showUploadConfig = ref(false)

// Materials data
const materials = ref([])

// Extract existing data from tracker
const existingCategories = computed(() => {
  if (!tracker.value || !tracker.value.files) return []
  const categories = new Set()
  tracker.value.files.forEach((file) => {
    if (file.directory_path) categories.add(file.directory_path)
  })
  return Array.from(categories).sort()
})

// Computed
const finalCategory = computed(() => {
  return selectedCategory.value
})

// Show error when ready to import but no category selected
const showCategoryError = computed(() => {
  return (showUrlPreview.value || showUploadConfig.value) && !selectedCategory.value
})

// Check if any files are unconfigured (using defaults)
const hasUnconfiguredFiles = computed(() => {
  const files = activeTab.value === 'urls' ? parsedUrlFiles.value : selectedFiles.value
  return files.some(
    (file) => !file.color || !file.material || !file.quantity || file.quantity === 1,
  )
})

// Load tracker data
async function loadTracker() {
  try {
    loading.value = true
    const response = await APIService.getTracker(route.params.id)
    tracker.value = response.data
  } catch (err) {
    console.error('Failed to load tracker:', err)
    error.value = 'Failed to load tracker. Please try again.'
  } finally {
    loading.value = false
  }
}

// Load materials data
async function loadMaterials() {
  try {
    const response = await APIService.getMaterials()
    materials.value = response.data
  } catch (err) {
    console.error('Failed to load materials:', err)
  }
}

onMounted(() => {
  loadTracker()
  loadMaterials()
})

// Handle category updates from FileConfigurationStepSimple
function handleCategoryUpdate(value) {
  selectedCategory.value = value
  categoryError.value = false
}

// Methods
function cancel() {
  router.push({ name: 'tracker-detail', params: { id: route.params.id } })
}

// URL Import methods - Two-step flow
async function previewURLs() {
  urlImportError.value = null

  // Validate input
  if (!urlsText.value.trim()) {
    urlImportError.value = 'Please enter at least one URL'
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
    // Fetch metadata for each URL and create file objects
    const filesWithMetadata = []
    for (const url of urls) {
      try {
        const response = await APIService.fetchURLMetadata(url)
        filesWithMetadata.push({
          name: response.data.filename,
          url: url,
          size: response.data.size,
          source: response.data.source,
          // Initialize with empty config
          color: '',
          material: '',
          quantity: 1,
        })
      } catch (error) {
        console.error(`Failed to fetch metadata for ${url}:`, error)
        filesWithMetadata.push({
          name: url.split('/').pop().split('?')[0],
          url: url,
          size: 0,
          source: 'URL',
          color: '',
          material: '',
          quantity: 1,
        })
      }
    }

    parsedUrlFiles.value = filesWithMetadata
    showUrlPreview.value = true
  } catch (error) {
    console.error('Preview error:', error)
    urlImportError.value = error.response?.data?.error || 'Failed to preview URLs'
  } finally {
    importingURLs.value = false
  }
}

function backToUrlEntry() {
  showUrlPreview.value = false
  parsedUrlFiles.value = []
}

async function importURLs() {
  console.log('=== importURLs called ===')
  console.log('selectedCategory.value:', selectedCategory.value)
  console.log('finalCategory.value:', finalCategory.value)
  console.log('urlImportError before:', urlImportError.value)

  if (!finalCategory.value) {
    console.log('NO CATEGORY - Setting error!')
    categoryError.value = true
    urlImportError.value = 'Please select or create a category before importing'
    console.log('urlImportError after:', urlImportError.value)
    console.log('categoryError:', categoryError.value)
    return
  }

  categoryError.value = false
  urlImportError.value = null
  importingURLs.value = true

  try {
    // Build files array with configuration from FileConfigurationStepSimple
    const filesWithMetadata = parsedUrlFiles.value.map((file) => ({
      name: file.name, // Backend expects 'name', not 'filename'
      url: file.url,
      size: file.size,
      source: file.source,
      category: finalCategory.value,
      color: file.color || '',
      material: file.material || '',
      quantity: file.quantity || 1,
    }))

    console.log('Importing URLs with data:', filesWithMetadata)

    // Add files to tracker
    await APIService.addFilesToTracker(tracker.value.id, filesWithMetadata)

    // Navigate back to tracker detail
    router.push({ name: 'tracker-detail', params: { id: route.params.id } })
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

  // Add files with empty config (FileConfigurationStepSimple will handle initialization)
  const filesWithDefaults = validFiles.map((file) => ({
    name: file.name,
    size: file.size,
    file: file, // Keep reference to actual File object for upload
    color: '',
    material: '',
    quantity: 1,
  }))

  selectedFiles.value = [...selectedFiles.value, ...filesWithDefaults]

  // Show configuration step immediately
  if (selectedFiles.value.length > 0) {
    showUploadConfig.value = true
  }
}

function backToFileSelection() {
  showUploadConfig.value = false
  selectedFiles.value = []
}

async function uploadFiles() {
  if (!selectedFiles.value.length || uploading.value) return

  uploadError.value = null

  if (!finalCategory.value) {
    categoryError.value = true
    uploadError.value = 'Please select or create a category before uploading'
    return
  }

  categoryError.value = false
  uploading.value = true

  try {
    let totalUploaded = 0
    const errors = []

    // Upload files one at a time with their individual configurations
    for (const fileObj of selectedFiles.value) {
      const formData = new FormData()
      formData.append('files', fileObj.file) // Use actual File object
      formData.append('category', finalCategory.value)
      formData.append('color', fileObj.color || '')
      formData.append('material', fileObj.material || '')
      formData.append('quantity', fileObj.quantity.toString())

      try {
        await APIService.uploadTrackerFiles(tracker.value.id, formData)
        totalUploaded++
      } catch (err) {
        console.error(`Failed to upload ${fileObj.name}:`, err)
        errors.push(fileObj.name)
      }
    }

    if (totalUploaded > 0) {
      // Navigate back to tracker detail if any files succeeded
      router.push({ name: 'tracker-detail', params: { id: route.params.id } })
    } else {
      uploadError.value = `Failed to upload all files: ${errors.join(', ')}`
    }
  } catch (error) {
    console.error('Upload error:', error)
    const errorData = error.response?.data
    if (errorData?.skipped_files && errorData.skipped_files.length > 0) {
      const skippedList = errorData.skipped_files.map((f) => `${f.filename}: ${f.error}`).join('\n')
      uploadError.value = `Failed to upload files:\n${skippedList}`
    } else {
      uploadError.value = errorData?.error || 'Failed to upload files'
    }
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>Loading tracker...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <p>{{ error }}</p>
      <button @click="loadTracker" class="btn btn-primary">Retry</button>
    </div>

    <!-- Main Content -->
    <div v-else class="content">
      <!-- Page Header -->
      <div class="page-header">
        <h1>Add Files to {{ tracker.name }}</h1>
      </div>

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

      <!-- Tab Content Card -->
      <div class="card">
        <div class="card-body">
          <!-- URL Import Tab -->
          <div v-if="activeTab === 'urls'">
            <!-- Step 1: Paste URLs -->
            <div v-if="!showUrlPreview" class="url-import-section">
              <div class="form-group">
                <label>URLs (one per line)</label>
                <textarea
                  v-model="urlsText"
                  rows="8"
                  placeholder="https://example.com/file1.stl&#10;https://example.com/file2.stl"
                  :disabled="importingURLs"
                ></textarea>
                <p class="help-text">Supported: STL, 3MF, OBJ, GCODE, STEP</p>
              </div>

              <div v-if="urlImportError" class="alert alert-error">
                {{ urlImportError }}
              </div>
            </div>

            <!-- Step 2: Configure Files -->
            <div v-else>
              <FileConfigurationStepSimple
                :files="parsedUrlFiles"
                :existing-categories="existingCategories"
                :category-error="categoryError"
                @update:category="handleCategoryUpdate"
              />

              <div v-if="urlImportError" class="alert alert-error">
                {{ urlImportError }}
              </div>
            </div>
          </div>

          <!-- Upload Tab -->
          <div v-if="activeTab === 'upload'">
            <!-- If no files selected, show drop zone -->
            <div v-if="!showUploadConfig" class="upload-section">
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
            </div>

            <!-- If files selected, show configuration -->
            <div v-else>
              <FileConfigurationStepSimple
                :files="selectedFiles"
                :existing-categories="existingCategories"
                :category-error="categoryError"
                @update:category="handleCategoryUpdate"
              />

              <div v-if="uploadError" class="alert alert-error">
                {{ uploadError }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Error Messages -->
      <div v-if="showCategoryError" class="alert alert-error" style="margin-top: 1rem">
        ⚠️ Please select or create a category before importing
      </div>
      <div
        v-if="hasUnconfiguredFiles && !showCategoryError"
        class="alert alert-info"
        style="margin-top: 1rem"
      >
        💡 Tip: Unconfigured files will be saved without settings. Configure them now using bulk
        actions and smart defaults — it's much faster than editing one-by-one later!
      </div>
      <div v-if="urlImportError" class="alert alert-error" style="margin-top: 1rem">
        {{ urlImportError }}
      </div>
      <div v-if="uploadError" class="alert alert-error" style="margin-top: 1rem">
        {{ uploadError }}
      </div>

      <!-- Form Actions -->
      <div class="form-actions">
        <button
          v-if="
            (activeTab === 'urls' && showUrlPreview) || (activeTab === 'upload' && showUploadConfig)
          "
          @click="activeTab === 'urls' ? backToUrlEntry() : backToFileSelection()"
          :disabled="importingURLs || uploading"
          class="btn btn-secondary"
        >
          Back
        </button>
        <button
          v-else
          @click="cancel"
          :disabled="importingURLs || uploading"
          class="btn btn-secondary"
        >
          Cancel
        </button>

        <button
          v-if="activeTab === 'urls' && !showUrlPreview"
          @click="previewURLs"
          :disabled="importingURLs"
          class="btn btn-primary"
        >
          {{ importingURLs ? 'Loading...' : 'Preview & Configure' }}
        </button>
        <button
          v-else-if="activeTab === 'urls' && showUrlPreview"
          @click="importURLs"
          :disabled="importingURLs || !selectedCategory"
          class="btn btn-primary"
        >
          {{
            importingURLs
              ? 'Importing...'
              : `Import ${parsedUrlFiles.length} URL${parsedUrlFiles.length !== 1 ? 's' : ''}`
          }}
        </button>
        <button
          v-else-if="activeTab === 'upload' && showUploadConfig"
          @click="uploadFiles"
          :disabled="uploading || !selectedCategory"
          class="btn btn-primary"
        >
          {{
            uploading
              ? 'Uploading...'
              : `Upload ${selectedFiles.length} File${selectedFiles.length !== 1 ? 's' : ''}`
          }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Page Layout */
.page-container {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Loading & Error States */
.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 20px;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid var(--color-border);
  border-top-color: var(--vt-c-indigo);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Breadcrumb */
.breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.breadcrumb a {
  color: var(--vt-c-indigo);
  text-decoration: none;
}

.breadcrumb a:hover {
  text-decoration: underline;
}

.breadcrumb .separator {
  color: var(--color-text-muted);
}

.breadcrumb .current {
  color: var(--color-text);
}

/* Page Header */
.page-header {
  margin-bottom: 10px;
}

.page-header h1 {
  color: var(--color-heading);
  font-size: 2rem;
  margin-bottom: 8px;
}

.subtitle {
  color: var(--color-text-muted);
  font-size: 1rem;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0;
  background-color: var(--color-background-mute);
}

.tab {
  flex: 1;
  padding: 15px 20px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  color: var(--color-text);
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.tab:hover:not(:disabled) {
  color: var(--color-heading);
}

.tab.active {
  color: var(--color-heading);
  border-bottom-color: var(--color-blue);
}

.tab:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Cards */
.card {
  background-color: var(--color-background-soft);
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.card-header {
  padding: 20px;
  border-bottom: 1px solid var(--color-border);
}

.card-header h3 {
  color: var(--color-heading);
  font-size: 1.25rem;
  margin: 0;
}

.card-body {
  padding: 20px;
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
  padding: 30px 20px;
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
  gap: 8px;
}

.upload-icon {
  width: 40px;
  height: 40px;
  color: var(--color-text-muted);
  margin-bottom: 5px;
}

.drop-zone p {
  color: var(--color-text);
  margin: 5px 0;
  font-size: 1rem;
}

.file-input-label {
  cursor: pointer;
}

/* Selected Files */
.selected-files {
  margin-top: 20px;
}

.files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.files-header h4 {
  color: var(--color-heading);
  font-size: 1rem;
  margin: 0;
}

.file-list-config {
  border: 1px solid var(--color-border);
  border-radius: 6px;
  max-height: 400px;
  overflow-y: auto;
}

.file-config-item {
  padding: 12px;
  border-bottom: 1px solid var(--color-border);
  background-color: var(--color-background);
}

.file-config-item:last-child {
  border-bottom: none;
}

.file-info-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.file-name {
  flex: 1;
  color: var(--color-heading);
  font-size: 0.9rem;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  color: var(--color-text-muted);
  font-size: 0.85rem;
  white-space: nowrap;
}

.btn-remove-small {
  background: none;
  border: none;
  color: #dc2626;
  font-size: 1.3rem;
  cursor: pointer;
  padding: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  flex-shrink: 0;
}

.btn-remove-small:hover:not(:disabled) {
  color: #b91c1c;
}

.btn-remove-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.file-config-row {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 8px;
}

.config-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-field label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-field select,
.config-field input {
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 0.875rem;
}

.config-field select:focus,
.config-field input:focus {
  outline: none;
  border-color: var(--color-blue);
}

.config-field-small {
  max-width: 80px;
}

.config-field-small input {
  text-align: center;
}

.total-size {
  padding: 10px;
  text-align: right;
  font-weight: bold;
  color: var(--color-text);
  border-top: 1px solid var(--color-border);
  margin-top: 5px;
}

/* Form Elements */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--color-text);
  font-weight: 500;
  font-size: 0.95rem;
}

.category-input-group {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.category-input-group select,
.category-input-group input {
  flex: 1;
  max-width: 300px;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.95rem;
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
  gap: 20px;
}

.form-row .form-group {
  flex: 1;
}

.btn-link {
  background: none;
  border: none;
  color: var(--vt-c-indigo);
  cursor: pointer;
  font-size: 0.9rem;
  margin-top: 8px;
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

.alert-info {
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: var(--color-text);
  padding: 12px;
  border-radius: 6px;
  font-size: 0.9rem;
}

/* Form Actions */
.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding-top: 20px;
}

/* Button overrides - use global styles from main.css */
</style>
