<script setup>
import { ref } from 'vue'
import BaseModal from './BaseModal.vue'
import APIService from '../services/APIService'

defineProps({
  show: {
    type: Boolean,
    required: true,
  },
})

const emit = defineEmits(['close', 'imported'])

const fileInput = ref(null)
const selectedFile = ref(null)
const uploading = ref(false)
const uploadError = ref(null)
const result = ref(null)

function onFileChange(event) {
  uploadError.value = null
  result.value = null
  const file = event.target.files[0]
  if (file && !file.name.toLowerCase().endsWith('.csv')) {
    uploadError.value = 'Only CSV files are supported.'
    selectedFile.value = null
    return
  }
  selectedFile.value = file || null
}

function downloadTemplate() {
  const header = 'title,brand,part_type,location,vendor,vendor_link,model,quantity,cost,notes'
  const example =
    'M3 x 6mm Socket Head Screw,Generic,Fasteners,Fasteners,Amazon,https://example.com,M3x6SH,10,0.05,Black oxide'
  const blob = new Blob([header + '\n' + example + '\n'], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'inventory_import_template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

async function uploadFile() {
  if (!selectedFile.value) {
    uploadError.value = 'Please select a CSV file first.'
    return
  }

  uploading.value = true
  uploadError.value = null
  result.value = null

  try {
    const response = await APIService.importInventoryItems(selectedFile.value)
    result.value = response.data
    if (response.data.created > 0) {
      emit('imported')
    }
  } catch (err) {
    const msg = err.response?.data?.error || 'Upload failed. Please check the file and try again.'
    uploadError.value = msg
  } finally {
    uploading.value = false
  }
}

function close() {
  selectedFile.value = null
  uploadError.value = null
  result.value = null
  uploading.value = false
  if (fileInput.value) fileInput.value.value = ''
  emit('close')
}
</script>

<template>
  <BaseModal :show="show" title="Import Inventory Items" @close="close">
    <div class="import-body">
      <!-- Instructions -->
      <p class="import-instructions">
        Upload a CSV file to bulk-import inventory items. Only <strong>title</strong> is required —
        all other fields are optional. Existing items (matched by title) are skipped.
      </p>

      <button class="btn btn-secondary template-btn" @click="downloadTemplate" type="button">
        Download CSV Template
      </button>

      <!-- File picker -->
      <div class="file-picker">
        <label class="file-label" for="csv-file-input">Choose CSV file</label>
        <input
          id="csv-file-input"
          ref="fileInput"
          type="file"
          accept=".csv"
          class="file-input"
          @change="onFileChange"
        />
        <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
        <span v-else class="file-name file-name--empty">No file selected</span>
      </div>

      <!-- Error -->
      <div v-if="uploadError" class="import-error">{{ uploadError }}</div>

      <!-- Result summary -->
      <div v-if="result" class="import-result">
        <div class="result-counts">
          <span class="result-created">✓ {{ result.created }} created</span>
          <span v-if="result.skipped" class="result-skipped">~ {{ result.skipped }} skipped (already exist)</span>
        </div>
        <div v-if="result.errors && result.errors.length" class="result-errors">
          <p class="result-errors-title">Row errors ({{ result.errors.length }}):</p>
          <ul>
            <li v-for="e in result.errors" :key="e.row">
              Row {{ e.row }}<span v-if="e.title"> ({{ e.title }})</span>: {{ e.error }}
            </li>
          </ul>
        </div>
      </div>
    </div>

    <template #footer>
      <button class="btn btn-secondary" @click="close" type="button">
        {{ result ? 'Done' : 'Cancel' }}
      </button>
      <button
        v-if="!result"
        class="btn btn-primary"
        @click="uploadFile"
        :disabled="uploading || !selectedFile"
        type="button"
      >
        {{ uploading ? 'Importing…' : 'Import' }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.import-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.import-instructions {
  color: var(--color-text);
  margin: 0;
  line-height: 1.5;
}

.template-btn {
  align-self: flex-start;
}

.file-picker {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.file-label {
  display: inline-block;
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-mute);
  color: var(--color-text);
  cursor: pointer;
  font-size: 0.9rem;
  white-space: nowrap;
}

.file-label:hover {
  background-color: var(--color-background-soft);
}

.file-input {
  display: none;
}

.file-name {
  color: var(--color-text);
  font-size: 0.9rem;
  word-break: break-all;
}

.file-name--empty {
  color: var(--color-text-muted, var(--color-border));
  font-style: italic;
}

.import-error {
  padding: 0.6rem 0.8rem;
  background-color: var(--color-danger-bg, #fde8e8);
  border: 1px solid var(--color-danger, #e53e3e);
  border-radius: 4px;
  color: var(--color-danger, #c53030);
  font-size: 0.9rem;
}

.import-result {
  padding: 0.75rem 1rem;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 6px;
}

.result-counts {
  display: flex;
  gap: 1.25rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

.result-created {
  color: var(--color-success, #38a169);
  font-weight: 600;
}

.result-skipped {
  color: var(--color-text);
}

.result-errors-title {
  font-weight: 600;
  color: var(--color-heading);
  margin: 0.5rem 0 0.25rem;
}

.result-errors ul {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.85rem;
  color: var(--color-danger, #c53030);
}
</style>
