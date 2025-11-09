<script setup>
import { ref } from 'vue'
import BaseModal from './BaseModal.vue'
import APIService from '../services/APIService'

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

const urlsText = ref('')
const selectedCategory = ref('')
const newCategoryName = ref('')
const showNewCategoryInput = ref(false)
const importing = ref(false)
const importError = ref(null)

function close() {
  urlsText.value = ''
  selectedCategory.value = ''
  newCategoryName.value = ''
  showNewCategoryInput.value = false
  importError.value = null
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

async function importURLs() {
  importError.value = null

  // Validate input
  if (!urlsText.value.trim()) {
    importError.value = 'Please enter at least one URL'
    return
  }

  const category = showNewCategoryInput.value
    ? newCategoryName.value.trim()
    : selectedCategory.value

  if (!category) {
    importError.value = 'Please select or create a category'
    return
  }

  // Parse URLs (one per line)
  const urls = urlsText.value
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

  if (urls.length === 0) {
    importError.value = 'No valid URLs found'
    return
  }

  // Validate all lines are URLs
  const urlPattern = /^https?:\/\/.+/i
  const supportedExtensions = ['.3mf', '.stl', '.oltp', '.stp', '.step', '.svg', '.amf', '.obj']
  const invalidLines = []
  const invalidExtensions = []

  urls.forEach((line, index) => {
    if (!urlPattern.test(line)) {
      invalidLines.push(`Line ${index + 1}: "${line}"`)
    } else {
      // Check if URL ends with a supported file extension
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
    importError.value = `Invalid URLs found:\n${invalidLines.join('\n')}\n\nPlease enter valid URLs starting with http:// or https://`
    return
  }

  if (invalidExtensions.length > 0) {
    importError.value = `URLs must point to 3D print files:\n${invalidExtensions.join('\n')}`
    return
  }

  // Check for duplicates in the input
  const urlSet = new Set()
  const duplicateLines = []
  urls.forEach((url, index) => {
    if (urlSet.has(url)) {
      duplicateLines.push(`Line ${index + 1}: "${url}" (duplicate)`)
    }
    urlSet.add(url)
  })

  if (duplicateLines.length > 0) {
    importError.value = `Duplicate URLs found:\n${duplicateLines.join('\n')}\n\nPlease remove duplicates before importing.`
    return
  }

  // Check for URLs that already exist in the tracker
  const existingUrls = new Set(props.existingFiles.map((f) => f.url))
  const alreadyAdded = []
  urls.forEach((url, index) => {
    if (existingUrls.has(url)) {
      alreadyAdded.push(`Line ${index + 1}: "${url}" (already added)`)
    }
  })

  if (alreadyAdded.length > 0) {
    importError.value = `URLs already in tracker:\n${alreadyAdded.join('\n')}\n\nPlease remove URLs that have already been added.`
    return
  }

  importing.value = true

  try {
    // Fetch metadata for each URL
    const filePromises = urls.map(async (url) => {
      try {
        const response = await APIService.fetchURLMetadata(url)
        return {
          name: response.data.filename,
          url: url,
          source: response.data.source,
          category: category,
          size: response.data.size || 0,
        }
      } catch (error) {
        console.error(`Failed to fetch metadata for ${url}:`, error)
        // Return basic file info even if metadata fetch fails
        return {
          name: url.split('/').pop() || 'unknown_file',
          url: url,
          source: 'Unknown',
          category: category,
          size: 0,
        }
      }
    })

    const files = await Promise.all(filePromises)

    // Emit imported files
    emit('filesImported', files)

    // Close modal
    close()
  } catch (error) {
    console.error('Import error:', error)
    importError.value = 'Failed to import URLs. Please try again.'
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <BaseModal :show="show" title="Import Files from URLs" @close="close">
    <div class="modal-content">
      <div v-if="importError" class="alert alert-danger">
        <strong>Error:</strong> {{ importError }}
      </div>

      <div class="form-group">
        <label for="urlsInput">Paste URLs (one per line)</label>
        <textarea
          id="urlsInput"
          v-model="urlsText"
          class="form-control"
          rows="8"
          placeholder="https://github.com/user/repo/file.stl
https://printables.com/.../part.stl
https://thingiverse.com/.../thing.stl"
          :disabled="importing"
        ></textarea>
        <small class="form-text">
          Supports GitHub, Printables, Thingiverse, and direct file URLs
        </small>
      </div>

      <div class="form-group">
        <label for="categorySelect">Add to Category *</label>
        <div class="category-input-group">
          <select
            v-if="!showNewCategoryInput"
            id="categorySelect"
            v-model="selectedCategory"
            class="form-control"
            :disabled="importing"
          >
            <option value="">-- Select Category --</option>
            <option v-for="cat in props.existingCategories" :key="cat" :value="cat">
              {{ cat }}
            </option>
          </select>

          <input
            v-else
            type="text"
            v-model="newCategoryName"
            class="form-control"
            placeholder="Enter new category name"
            :disabled="importing"
          />

          <button
            type="button"
            class="btn btn-secondary"
            @click="toggleNewCategory"
            :disabled="importing"
          >
            {{ showNewCategoryInput ? 'Select Existing' : 'Create New' }}
          </button>
        </div>
      </div>
    </div>

    <template #footer>
      <button class="btn btn-secondary" @click="close" :disabled="importing">Cancel</button>
      <button class="btn btn-primary" @click="importURLs" :disabled="importing">
        {{ importing ? 'Importing...' : 'Import URLs' }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.modal-content {
  padding: 0;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

label {
  display: block;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

.form-control {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.9rem;
  font-family: inherit;
  transition: border-color 0.2s;
}

.form-control:focus {
  outline: none;
  background-color: var(--color-background);
  border-color: var(--color-heading);
}

.form-control:disabled {
  background-color: #f3f4f6;
  cursor: not-allowed;
}

textarea.form-control {
  resize: vertical;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  white-space: nowrap;
  overflow-x: auto;
  overflow-y: auto;
}

.form-text {
  display: block;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: #6b7280;
}

.category-input-group {
  display: flex;
  gap: 0.75rem;
}

.category-input-group .form-control {
  flex: 1;
}

.category-input-group .btn {
  white-space: nowrap;
}

.alert {
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  word-wrap: break-word;
  word-break: break-all;
  white-space: pre-wrap;
  overflow-wrap: break-word;
  max-width: 100%;
}

.alert-danger {
  background-color: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}
</style>
