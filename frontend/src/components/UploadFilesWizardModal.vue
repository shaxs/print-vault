<script setup>
import { ref, computed } from 'vue'
import BaseModal from './BaseModal.vue'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  existingCategories: {
    type: Array,
    default: () => [],
  },
  existingFiles: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'filesImported'])

// Component state
const selectedFiles = ref([])
const selectedCategory = ref('')
const newCategoryName = ref('')
const showNewCategoryInput = ref(false)
const dragOver = ref(false)
const uploadError = ref(null)

// Computed
const hasFiles = computed(() => selectedFiles.value.length > 0)
const totalSize = computed(() => {
  return selectedFiles.value.reduce((sum, file) => sum + file.size, 0)
})

// Methods
function close() {
  selectedFiles.value = []
  selectedCategory.value = ''
  newCategoryName.value = ''
  showNewCategoryInput.value = false
  uploadError.value = null
  emit('close')
}

function toggleNewCategory() {
  showNewCategoryInput.value = !showNewCategoryInput.value
  if (showNewCategoryInput.value) {
    selectedCategory.value = ''
  } else {
    newCategoryName.value = ''
  }
}

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
  const validExtensions = ['.stl', '.3mf', '.obj', '.gcode', '.step', '.stp', '.svg', '.amf']
  const validFiles = files.filter((file) => {
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    return validExtensions.includes(ext)
  })

  // Check for duplicate filenames in current selection
  const existingNames = new Set(selectedFiles.value.map((f) => f.name))
  const duplicates = []
  const newFiles = []

  validFiles.forEach((file) => {
    if (existingNames.has(file.name)) {
      duplicates.push(file.name)
    } else {
      newFiles.push(file)
      existingNames.add(file.name)
    }
  })

  if (duplicates.length > 0) {
    uploadError.value = `Duplicate files skipped: ${duplicates.join(', ')}`
    setTimeout(() => {
      uploadError.value = null
    }, 5000)
  }

  selectedFiles.value = [...selectedFiles.value, ...newFiles]
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

function addFilesToWizard() {
  uploadError.value = null

  // Validate
  if (!hasFiles.value) {
    uploadError.value = 'Please select at least one file'
    return
  }

  const category = showNewCategoryInput.value
    ? newCategoryName.value.trim()
    : selectedCategory.value

  if (!category) {
    uploadError.value = 'Please select or create a category'
    return
  }

  // Check for duplicate filenames in existing files
  const existingNames = new Set(props.existingFiles.map((f) => f.name))
  const alreadyAdded = []

  selectedFiles.value.forEach((file) => {
    if (existingNames.has(file.name)) {
      alreadyAdded.push(file.name)
    }
  })

  if (alreadyAdded.length > 0) {
    uploadError.value = `Files already in tracker: ${alreadyAdded.join(', ')}\n\nPlease remove duplicate files.`
    return
  }

  // Convert File objects to the expected structure for the wizard
  const files = selectedFiles.value.map((file) => ({
    name: file.name,
    url: null, // Local files don't have URLs
    githubUrl: '', // Empty string for uploaded files (avoids NULL constraint)
    source: 'Upload',
    category: category,
    size: file.size,
    file: file, // Keep the File object for later upload
  }))

  // Emit files
  emit('filesImported', files)

  // Close modal
  close()
}
</script>

<template>
  <BaseModal :show="show" @close="close" title="Upload Files" width="600px">
    <div class="modal-content">
      <!-- Category selection -->
      <div class="form-group">
        <label>Category</label>
        <div class="category-controls">
          <select v-if="!showNewCategoryInput" v-model="selectedCategory" class="form-control">
            <option value="" disabled>Select a category</option>
            <option v-for="cat in existingCategories" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>
          <input
            v-else
            v-model="newCategoryName"
            type="text"
            class="form-control"
            placeholder="Enter new category name"
          />
          <button class="btn btn-secondary" @click="toggleNewCategory">
            {{ showNewCategoryInput ? 'Select Existing' : 'Create New' }}
          </button>
        </div>
      </div>

      <!-- File drop zone -->
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
          <p class="drop-zone-text">Drag and drop files here, or</p>
          <label for="file-upload" class="btn btn-primary upload-btn">Choose Files</label>
          <input
            id="file-upload"
            type="file"
            multiple
            accept=".stl,.3mf,.obj,.gcode,.step,.stp,.svg,.amf"
            @change="handleFileSelect"
            style="display: none"
          />
          <p class="file-types">Supported: STL, 3MF, OBJ, GCODE, STEP, STP, SVG, AMF</p>
        </div>
      </div>

      <!-- Selected files list -->
      <div v-if="hasFiles" class="selected-files">
        <div class="selected-files-header">
          <h4>Selected Files ({{ selectedFiles.length }})</h4>
          <span class="total-size">Total: {{ formatFileSize(totalSize) }}</span>
        </div>
        <div class="file-list">
          <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
            <div class="file-info">
              <span class="file-name">{{ file.name }}</span>
              <span class="file-size">{{ formatFileSize(file.size) }}</span>
            </div>
            <button class="btn-remove" @click="removeFile(index)" title="Remove file">×</button>
          </div>
        </div>
      </div>

      <!-- Error message -->
      <div v-if="uploadError" class="error-message">
        <span class="error-icon">⚠️</span>
        <span>{{ uploadError }}</span>
      </div>
    </div>

    <template #footer>
      <button class="btn btn-secondary" @click="close">Cancel</button>
      <button class="btn btn-primary" @click="addFilesToWizard" :disabled="!hasFiles">
        Add Files
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.modal-content {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  color: var(--color-heading);
  font-size: 0.95rem;
}

.category-controls {
  display: flex;
  gap: 0.5rem;
}

.form-control {
  flex: 1;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.95rem;
}

.form-control:focus {
  outline: none;
  background-color: var(--color-background);
  border-color: var(--color-heading);
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  transition: all 0.2s;
  background-color: var(--color-background-mute);
}

.drop-zone:hover {
  border-color: var(--color-border-hover);
  background-color: var(--color-background);
}

.drop-zone.drag-over {
  border-color: #2563eb;
  background-color: #eff6ff;
}

.drop-zone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.upload-icon {
  width: 48px;
  height: 48px;
  color: var(--color-text-soft);
}

.drop-zone-text {
  margin: 0;
  color: var(--color-text);
  font-size: 0.95rem;
}

.upload-btn {
  margin: 0;
}

.file-types {
  margin: 0;
  font-size: 0.8rem;
  color: var(--color-text-soft);
}

.selected-files {
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
}

.selected-files-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid var(--color-border);
}

.selected-files-header h4 {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-heading);
}

.total-size {
  font-size: 0.85rem;
  color: var(--color-text-soft);
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 6px;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 0.9rem;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  font-size: 0.8rem;
  color: var(--color-text-soft);
}

.btn-remove {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  font-size: 1.5rem;
  color: #dc2626;
  transition: color 0.2s;
  line-height: 1;
}

.btn-remove:hover {
  color: #b91c1c;
}

.error-message {
  padding: 0.75rem;
  background-color: #fef2f2;
  color: #991b1b;
  border-radius: 6px;
  border-left: 4px solid #dc2626;
  font-size: 0.9rem;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.error-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}
</style>
