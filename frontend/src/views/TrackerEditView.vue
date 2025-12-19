<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'

const route = useRoute()
const router = useRouter()

const tracker = ref(null)
const originalStorageType = ref(null) // Track original value
const projects = ref([])
const loading = ref(true)
const saving = ref(false)
const error = ref(null)
const downloading = ref(false)
const downloadMessage = ref('')

// Material selection state
const materials = ref([])
const loadingMaterials = ref(false)
const primaryMaterialMode = ref('color') // 'color' or 'blueprint'
const accentMaterialMode = ref('color') // 'color' or 'blueprint'
const selectedPrimaryMaterial = ref(null)
const selectedAccentMaterial = ref(null)



// Check if download button should be shown
const shouldShowDownloadButton = computed(() => {
  if (!tracker.value) return false

  // Only show if:
  // 1. Current selection is "local"
  // 2. Original was "link" (storage type changed)
  // 3. There are files with github_url but no local_file
  const storageTypeChanged =
    originalStorageType.value === 'link' && tracker.value.storage_type === 'local'

  if (!storageTypeChanged) return false

  // Check if there are files that need downloading
  const hasFilesToDownload = tracker.value.files?.some(
    (file) => file.github_url && !file.local_file,
  )

  return hasFilesToDownload
})

const loadTracker = async () => {
  try {
    const response = await APIService.getTracker(route.params.id)
    tracker.value = response.data
    // Store original storage type
    originalStorageType.value = response.data.storage_type
    
    // Initialize material modes based on current data
    if (tracker.value.primary_material) {
      primaryMaterialMode.value = 'blueprint'
      selectedPrimaryMaterial.value = tracker.value.primary_material
      // Populate color from material display if available
      if (tracker.value.primary_material_display?.colors?.length > 0) {
        tracker.value.primary_color = tracker.value.primary_material_display.colors[0]
      }
    } else {
      primaryMaterialMode.value = 'color'
      selectedPrimaryMaterial.value = null // Explicitly set to null
    }
    
    if (tracker.value.accent_material) {
      accentMaterialMode.value = 'blueprint'
      selectedAccentMaterial.value = tracker.value.accent_material
      // Populate color from material display if available
      if (tracker.value.accent_material_display?.colors?.length > 0) {
        tracker.value.accent_color = tracker.value.accent_material_display.colors[0]
      }
    } else {
      accentMaterialMode.value = 'color'
      selectedAccentMaterial.value = null // Explicitly set to null
      // Clear accent color if it's the default (user never set it)
      if (tracker.value.accent_color === '#DC2626') {
        tracker.value.accent_color = ''
      }
    }
  } catch (err) {
    console.error('Failed to load tracker:', err)
    error.value = 'Failed to load tracker'
  }
}

const loadMaterials = async () => {
  loadingMaterials.value = true
  try {
    const response = await APIService.getMaterials()
    materials.value = response.data.results || response.data
  } catch (err) {
    console.error('Failed to load materials:', err)
  } finally {
    loadingMaterials.value = false
  }
}

const formatMaterialLabel = (mat) => {
  if (!mat) return ''
  const brandName = mat.brand?.name || ''
  const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
  return `${brandName} ${mat.name}${diameter}`.trim()
}

const loadProjects = async () => {
  try {
    const response = await APIService.getProjects()
    projects.value = response.data
  } catch (err) {
    console.error('Failed to load projects:', err)
  }
}

const saveTracker = async () => {
  saving.value = true
  error.value = null

  try {
    // Apply material cascade if either primary or accent use blueprint mode
    const usingBlueprintMode = 
      (primaryMaterialMode.value === 'blueprint' && selectedPrimaryMaterial.value) ||
      (accentMaterialMode.value === 'blueprint' && selectedAccentMaterial.value)
    
    if (usingBlueprintMode) {
      await APIService.updateTrackerMaterials(route.params.id, {
        primary_material_id: primaryMaterialMode.value === 'blueprint' ? selectedPrimaryMaterial.value : null,
        accent_material_id: accentMaterialMode.value === 'blueprint' ? selectedAccentMaterial.value : null,
        force_override_all: false,
        dry_run: false
      })
    }
    
    // Save other tracker fields
    await APIService.updateTracker(route.params.id, {
      name: tracker.value.name,
      project: tracker.value.project,
      github_url: tracker.value.github_url,
      storage_type: tracker.value.storage_type,
      show_on_dashboard: tracker.value.show_on_dashboard || false,
      primary_color: tracker.value.primary_color,
      accent_color: tracker.value.accent_color,
      primary_material: primaryMaterialMode.value === 'blueprint' ? selectedPrimaryMaterial.value : null,
      accent_material: accentMaterialMode.value === 'blueprint' ? selectedAccentMaterial.value : null,
      notes: tracker.value.notes || '',
    })
    
    router.push(`/trackers/${route.params.id}`)
  } catch (err) {
    console.error('Failed to save tracker:', err)
    error.value = 'Failed to save tracker. Please try again.'
  } finally {
    saving.value = false
  }
}

const cancel = () => {
  router.push(`/trackers/${route.params.id}`)
}

// Update color when primary material blueprint is selected
// Get primary material color from the loaded materials list
const getPrimaryMaterialColor = () => {
  if (!selectedPrimaryMaterial.value) return '#cccccc'
  const material = materials.value.find(m => m.id === selectedPrimaryMaterial.value)
  return material?.colors?.[0] || tracker.value.primary_color || '#cccccc'
}

// Get accent material color from the loaded materials list
const getAccentMaterialColor = () => {
  if (!selectedAccentMaterial.value) return '#cccccc'
  const material = materials.value.find(m => m.id === selectedAccentMaterial.value)
  return material?.colors?.[0] || tracker.value.accent_color || '#cccccc'
}

const onPrimaryMaterialChange = (material) => {
  if (material && material.colors && material.colors.length > 0) {
    tracker.value.primary_color = material.colors[0]
  }
}

// Update color when accent material blueprint is selected
const onAccentMaterialChange = (material) => {
  if (material && material.colors && material.colors.length > 0) {
    tracker.value.accent_color = material.colors[0]
  }
}

const downloadAllFiles = async () => {
  if (
    !confirm(
      'Download all files from GitHub URLs? This will convert the tracker to use local storage.',
    )
  ) {
    return
  }

  downloading.value = true
  downloadMessage.value = ''
  error.value = null

  try {
    const response = await APIService.downloadAllTrackerFiles(route.params.id)

    if (response.data.count === 0) {
      downloadMessage.value =
        'No files need to be downloaded (all files already downloaded or no URLs found)'
    } else {
      downloadMessage.value = `Downloaded ${response.data.downloaded_count} of ${response.data.total_files} files`

      if (response.data.failed_count > 0) {
        downloadMessage.value += ` (${response.data.failed_count} failed)`
      }

      // Reload tracker to show updated storage_type and files
      await loadTracker()
    }
  } catch (err) {
    console.error('Failed to download files:', err)
    error.value = err.response?.data?.error || 'Failed to download files. Please try again.'
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadTracker(), loadProjects(), loadMaterials()])
  loading.value = false
})
</script>

<template>
  <div>
    <MainHeader
      title="Edit Tracker"
      :showSearch="false"
      :showAddButton="false"
      :showFilterButton="false"
      :showColumnButton="false"
    />

    <div v-if="loading" class="loading-container">
      <p>Loading tracker...</p>
    </div>

    <div v-else-if="tracker" class="form-container">
      <div v-if="error" class="error-message">{{ error }}</div>

      <form @submit.prevent="saveTracker" class="edit-form">
        <div class="form-group">
          <label for="name">Tracker Name *</label>
          <input id="name" v-model="tracker.name" type="text" class="form-input" required />
        </div>

        <div class="form-group">
          <label for="project">Associated Project</label>
          <select id="project" v-model="tracker.project" class="form-input">
            <option :value="null">No Project</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.project_name }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label for="github_url">GitHub URL</label>
          <input
            id="github_url"
            v-model="tracker.github_url"
            type="url"
            class="form-input"
            placeholder="https://github.com/..."
          />
        </div>

        <div class="form-group">
          <label for="notes">Notes</label>
          <textarea id="notes" v-model="tracker.notes" rows="4" class="form-input"></textarea>
        </div>

        <div class="form-group">
          <label for="storage_type">Storage Type</label>
          <select
            id="storage_type"
            v-model="tracker.storage_type"
            class="form-input"
            :disabled="downloading"
          >
            <option value="link">GitHub Links Only</option>
            <option value="local">Local Files</option>
          </select>
          <p class="help-text">
            Change from "Links" to "Local" to download files to your server.
            <button
              v-if="shouldShowDownloadButton"
              @click="downloadAllFiles"
              :disabled="downloading"
              class="btn btn-sm btn-secondary"
              style="margin-left: 8px"
              type="button"
            >
              {{ downloading ? 'Downloading...' : 'Download All Files Now' }}
            </button>
          </p>
          <div v-if="downloading" class="download-in-progress">
            <div class="spinner-small"></div>
            <span>Downloading files... Please wait before saving changes.</span>
          </div>
          <p v-if="downloadMessage" class="success-message">{{ downloadMessage }}</p>
        </div>

        <div class="form-group checkbox-group">
          <input id="show_on_dashboard" v-model="tracker.show_on_dashboard" type="checkbox" />
          <label for="show_on_dashboard">Featured on Dashboard</label>
        </div>
        <p class="help-text" style="margin-top: -0.5rem; margin-left: 0; margin-bottom: 2rem">
          Display this tracker in the dashboard's featured section
        </p>

        <!-- Primary Material/Color -->
        <div class="form-group">
          <label>Primary Material/Color</label>
          <div class="material-mode-toggle">
            <label class="radio-label">
              <input
                type="radio"
                v-model="primaryMaterialMode"
                value="color"
              />
              Manual Color
            </label>
            <label class="radio-label">
              <input
                type="radio"
                v-model="primaryMaterialMode"
                value="blueprint"
              />
              Material Blueprint
            </label>
          </div>
          
          <!-- Manual Color Mode -->
          <div v-if="primaryMaterialMode === 'color'" class="color-input-group">
            <input
              v-model="tracker.primary_color"
              type="color"
              class="color-picker"
            />
            <input
              v-model="tracker.primary_color"
              type="text"
              class="form-input"
              placeholder="#1E40AF"
            />
          </div>
          
          <!-- Blueprint Mode -->
          <div v-else>
            <select
              v-model="selectedPrimaryMaterial"
              @change="onPrimaryMaterialChange(materials.find(m => m.id === selectedPrimaryMaterial))"
              class="form-input"
            >
              <option :value="null">-- Select Material Blueprint --</option>
              <option v-for="mat in materials" :key="mat.id" :value="mat.id">
                {{ formatMaterialLabel(mat) }}
              </option>
            </select>
            <div v-if="selectedPrimaryMaterial" class="color-preview">
              <div
                class="color-swatch"
                :style="{ background: getPrimaryMaterialColor() }"
              ></div>
              <span class="color-code">{{ getPrimaryMaterialColor() }}</span>
            </div>
          </div>
        </div>

        <!-- Accent Material/Color -->
        <div class="form-group">
          <label>Accent Material/Color</label>
          <div class="material-mode-toggle">
            <label class="radio-label">
              <input
                type="radio"
                v-model="accentMaterialMode"
                value="color"
              />
              Manual Color
            </label>
            <label class="radio-label">
              <input
                type="radio"
                v-model="accentMaterialMode"
                value="blueprint"
              />
              Material Blueprint
            </label>
          </div>
          
          <!-- Manual Color Mode -->
          <div v-if="accentMaterialMode === 'color'" class="color-input-group">
            <input
              v-model="tracker.accent_color"
              type="color"
              class="color-picker"
            />
            <input
              v-model="tracker.accent_color"
              type="text"
              class="form-input"
              placeholder="#DC2626"
            />
          </div>
          
          <!-- Blueprint Mode -->
          <div v-else>
            <select
              v-model="selectedAccentMaterial"
              @change="onAccentMaterialChange(materials.find(m => m.id === selectedAccentMaterial))"
              class="form-input"
            >
              <option :value="null">-- Select Material Blueprint --</option>
              <option v-for="mat in materials" :key="mat.id" :value="mat.id">
                {{ formatMaterialLabel(mat) }}
              </option>
            </select>
            <div v-if="selectedAccentMaterial !== null && selectedAccentMaterial !== undefined" class="color-preview">
              <div
                class="color-swatch"
                :style="{ background: getAccentMaterialColor() }"
              ></div>
              <span class="color-code">{{ getAccentMaterialColor() }}</span>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button type="button" @click="cancel" class="btn btn-secondary" :disabled="downloading">
            Cancel
          </button>
          <button
            type="submit"
            class="btn btn-primary"
            :disabled="saving || downloading"
            :title="downloading ? 'Please wait for file download to complete' : ''"
          >
            <span v-if="downloading">Downloading files...</span>
            <span v-else-if="saving">Saving...</span>
            <span v-else>Save Changes</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.loading-container {
  padding: 40px;
  text-align: center;
}

.form-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.error-message {
  padding: 12px 16px;
  margin-bottom: 20px;
  background-color: #fee;
  color: #c00;
  border: 1px solid #fcc;
  border-radius: 4px;
}

.edit-form {
  background: var(--color-background-soft);
  padding: 24px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 500;
  color: var(--color-heading);
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-brand);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.checkbox-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}

.checkbox-group input {
  width: auto;
}

.checkbox-group label {
  margin-bottom: 0;
  font-weight: normal;
  user-select: none;
  cursor: pointer;
}

.color-input-group {
  display: flex;
  gap: 10px;
  align-items: center;
}

.color-picker {
  width: 50px;
  height: 42px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
  background: var(--color-background);
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border);
}

.help-text {
  font-size: 0.875rem;
  color: var(--color-text-soft);
  margin-top: 6px;
}

.success-message {
  font-size: 0.875rem;
  color: var(--color-green);
  margin-top: 6px;
  font-weight: 500;
}

.download-in-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  margin-top: 10px;
  background-color: var(--color-blue-soft);
  border: 1px solid var(--color-blue);
  border-radius: 4px;
  color: var(--color-blue-dark);
  font-weight: 500;
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 3px solid var(--color-blue-light);
  border-top-color: var(--color-blue);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Material Mode Toggle */
.material-mode-toggle {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 1rem;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--color-text);
}

.radio-label input[type="radio"] {
  cursor: pointer;
}

/* Color Input Group */
.color-input-group {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.color-picker {
  width: 60px;
  height: 40px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
}

/* Color Preview */
.color-preview {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.75rem;
  padding: 0.75rem;
  background: var(--color-background-soft);
  border-radius: 4px;
}

.color-swatch {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
}

.color-code {
  font-family: monospace;
  font-size: 0.875rem;
  color: var(--color-text);
  font-weight: 500;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
