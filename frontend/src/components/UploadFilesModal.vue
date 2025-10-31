<script setup>
import { ref, computed } from 'vue'
import BaseModal from './BaseModal.vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  trackerId: { type: Number, required: true },
})

const emit = defineEmits(['close', 'filesUploaded'])

// Component state
const selectedFiles = ref([])
const category = ref('')
const color = ref('')
const material = ref('')
const quantity = ref(1)
const uploading = ref(false)
const dragOver = ref(false)

// Computed
const hasFiles = computed(() => selectedFiles.value.length > 0)
const totalSize = computed(() => {
  return selectedFiles.value.reduce((sum, file) => sum + file.size, 0)
})

// Methods
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

  uploading.value = true

  try {
    // Use APIService to upload
    const { default: APIService } = await import('../services/APIService')

    const formData = new FormData()
    selectedFiles.value.forEach((file) => {
      formData.append('files', file)
    })

    if (category.value) formData.append('category', category.value)
    if (color.value) formData.append('color', color.value)
    if (material.value) formData.append('material', material.value)
    formData.append('quantity', quantity.value.toString())

    const response = await APIService.uploadTrackerFiles(props.trackerId, formData)

    if (response.data.success) {
      emit('filesUploaded', response.data)
      resetForm()
      emit('close')
    }
  } catch (error) {
    console.error('Upload error:', error)
    alert('Failed to upload files: ' + (error.response?.data?.error || error.message))
  } finally {
    uploading.value = false
  }
}

function resetForm() {
  selectedFiles.value = []
  category.value = ''
  color.value = ''
  material.value = ''
  quantity.value = 1
}

function handleClose() {
  if (!uploading.value) {
    resetForm()
    emit('close')
  }
}
</script>

<template>
  <BaseModal :show="show" title="Upload Files" @close="handleClose">
    <!-- File Drop Zone -->
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
        <p>Drag & drop files here or</p>
        <label class="file-input-label">
          <input
            type="file"
            multiple
            accept=".stl,.3mf,.obj,.gcode,.step,.stp"
            @change="handleFileSelect"
            style="display: none"
          />
          <span class="btn-secondary">Browse Files</span>
        </label>
        <p class="file-types-hint">Supported: STL, 3MF, OBJ, GCODE, STEP</p>
      </div>
    </div>

    <!-- Selected Files List -->
    <div v-if="hasFiles" class="selected-files">
      <h4>Selected Files ({{ selectedFiles.length }})</h4>
      <div class="file-list">
        <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatFileSize(file.size) }}</span>
          <button @click="removeFile(index)" class="btn-icon-delete" :disabled="uploading">
            ×
          </button>
        </div>
      </div>
      <div class="total-size">Total: {{ formatFileSize(totalSize) }}</div>
    </div>

    <!-- Metadata Form -->
    <div v-if="hasFiles" class="metadata-form">
      <div class="form-row">
        <div class="form-group">
          <label>Category/Directory</label>
          <input
            v-model="category"
            type="text"
            placeholder="e.g., Brackets, Frame Parts"
            :disabled="uploading"
          />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Color</label>
          <input
            v-model="color"
            type="text"
            placeholder="e.g., Primary, Accent"
            :disabled="uploading"
          />
        </div>

        <div class="form-group">
          <label>Material</label>
          <input
            v-model="material"
            type="text"
            placeholder="e.g., ABS, PLA, PETG"
            :disabled="uploading"
          />
        </div>
      </div>

      <div class="form-row">
        <div class="form-group">
          <label>Quantity</label>
          <input v-model.number="quantity" type="number" min="1" :disabled="uploading" />
        </div>
      </div>
    </div>

    <!-- Footer Buttons -->
    <template #footer>
      <button @click="handleClose" :disabled="uploading" class="btn btn-secondary">Cancel</button>
      <button @click="uploadFiles" :disabled="!hasFiles || uploading" class="btn btn-primary">
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
/* Drop Zone */
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
  border-color: var(--color-primary);
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

.file-types-hint {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.file-input-label {
  cursor: pointer;
}

/* Selected Files */
.selected-files {
  margin-bottom: 20px;
}

.selected-files h4 {
  color: var(--color-heading);
  margin-bottom: 10px;
  font-size: 1rem;
}

.file-list {
  border: 1px solid var(--color-border);
  border-radius: 4px;
  max-height: 200px;
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

.total-size {
  padding: 10px;
  text-align: right;
  font-weight: bold;
  color: var(--color-text);
  border-top: 1px solid var(--color-border);
  margin-top: 5px;
}

/* Metadata Form */
.metadata-form {
  border-top: 1px solid var(--color-border);
  padding-top: 20px;
}

.form-row {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.form-group {
  flex: 1;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: var(--color-text);
  font-weight: 500;
  font-size: 0.9rem;
}

.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-group input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
