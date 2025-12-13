<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const spool = ref(null)
const isLoading = ref(true)
const isPhotoModalVisible = ref(false)
const isColorSwatchModalVisible = ref(false)
const selectedColorHex = ref(null)
const selectedPhotoUrl = ref(null)
const selectedPhotoCaption = ref('')

const loadSpool = async () => {
  isLoading.value = true
  try {
    const response = await axios.get(`/api/filament-spools/${route.params.id}/`)
    spool.value = response.data
  } catch (error) {
    console.error('Failed to load spool:', error)
  } finally {
    isLoading.value = false
  }
}

// Computed properties that handle both Quick Add and Blueprint spools
const spoolName = computed(() => {
  if (!spool.value) return 'Spool'
  return spool.value.is_quick_add
    ? spool.value.standalone_name
    : spool.value.filament_type?.name || 'Unknown Material'
})

const spoolBrand = computed(() => {
  if (!spool.value) return null
  return spool.value.is_quick_add ? spool.value.standalone_brand : spool.value.filament_type?.brand
})

const spoolMaterialType = computed(() => {
  if (!spool.value) return null
  return spool.value.is_quick_add
    ? spool.value.standalone_material_type
    : spool.value.filament_type?.base_material
})

const spoolColors = computed(() => {
  if (!spool.value) return []
  return spool.value.is_quick_add
    ? spool.value.standalone_colors || []
    : spool.value.filament_type?.colors || []
})

const spoolPhoto = computed(() => {
  if (!spool.value) return null
  return spool.value.is_quick_add ? spool.value.standalone_photo : spool.value.filament_type?.photo
})

// Additional photos inherited from the blueprint (not available for Quick Add spools)
const spoolAdditionalPhotos = computed(() => {
  if (!spool.value) return []
  if (spool.value.is_quick_add) return []
  return spool.value.filament_type?.additional_photos || []
})

const spoolDiameter = computed(() => {
  if (!spool.value) return null
  return spool.value.is_quick_add ? null : spool.value.filament_type?.diameter
})

// Check if any print settings are available
const hasPrintSettings = computed(() => {
  if (!spool.value) return false

  if (spool.value.is_quick_add) {
    return (
      spool.value.standalone_nozzle_temp_min ||
      spool.value.standalone_nozzle_temp_max ||
      spool.value.standalone_bed_temp_min ||
      spool.value.standalone_bed_temp_max ||
      spool.value.standalone_density
    )
  } else {
    const ft = spool.value.filament_type
    if (!ft) return false
    return (
      ft.nozzle_temp_min ||
      ft.nozzle_temp_max ||
      ft.bed_temp_min ||
      ft.bed_temp_max ||
      ft.density ||
      ft.tds_value
    )
  }
})

// Get print settings for display (handles both modes)
const printSettings = computed(() => {
  if (!spool.value) return {}

  if (spool.value.is_quick_add) {
    return {
      nozzle_temp_min: spool.value.standalone_nozzle_temp_min,
      nozzle_temp_max: spool.value.standalone_nozzle_temp_max,
      bed_temp_min: spool.value.standalone_bed_temp_min,
      bed_temp_max: spool.value.standalone_bed_temp_max,
      density: spool.value.standalone_density,
      tds_value: null,
    }
  } else {
    const ft = spool.value.filament_type || {}
    return {
      nozzle_temp_min: ft.nozzle_temp_min,
      nozzle_temp_max: ft.nozzle_temp_max,
      bed_temp_min: ft.bed_temp_min,
      bed_temp_max: ft.bed_temp_max,
      density: ft.density,
      tds_value: ft.tds_value,
    }
  }
})

const getStatusClass = (status) => {
  const statusMap = {
    new: 'status-new',
    opened: 'status-opened',
    in_use: 'status-in-use',
    low: 'status-low',
    empty: 'status-empty',
    archived: 'status-archived',
  }
  return statusMap[status] || ''
}

const filamentUsedPercent = () => {
  if (!spool.value || !spool.value.weight_remaining_percent) return 0
  return 100 - spool.value.weight_remaining_percent
}

const getFilamentUsedColor = (usedPercent) => {
  if (usedPercent <= 50) return '#10b981' // Green - 0-50% used (plenty left)
  if (usedPercent <= 75) return '#eab308' // Yellow - 51-75% used (medium)
  if (usedPercent <= 90) return '#f59e0b' // Orange - 76-90% used (getting low)
  return '#ef4444' // Red - 91-100% used (almost empty)
}

const progressBarStyle = () => {
  const percentage = filamentUsedPercent()
  return {
    width: `${percentage}%`,
    height: '100%',
    backgroundColor: getFilamentUsedColor(percentage),
    transition: 'width 0.3s ease, background-color 0.3s ease',
  }
}

const deleteSpool = async () => {
  if (
    !confirm(
      `Are you sure you want to delete this spool?\n\n"${spoolName.value}"\n\nThis action cannot be undone.`,
    )
  ) {
    return
  }

  try {
    await axios.delete(`/api/filament-spools/${spool.value.id}/`)
    router.push('/filaments')
  } catch (error) {
    console.error('Failed to delete spool:', error)
    alert('Failed to delete spool. Please try again.')
  }
}

const openColorSwatchModal = (colorHex) => {
  selectedColorHex.value = colorHex
  isColorSwatchModalVisible.value = true
}

const openPhotoInModal = (photoUrl, caption = '') => {
  selectedPhotoUrl.value = photoUrl
  selectedPhotoCaption.value = caption
  isPhotoModalVisible.value = true
}

onMounted(() => {
  loadSpool()
})
</script>

<template>
  <div class="page-container">
    <div v-if="isLoading" class="loading-state">
      <p>Loading...</p>
    </div>

    <div v-else-if="!spool" class="error">
      <p>Spool not found.</p>
      <button @click="router.push('/filaments')" class="btn btn-primary">Back to Spools</button>
    </div>

    <div v-else class="content-container">
      <!-- Page Header with Edit/Delete buttons -->
      <div class="detail-header">
        <h1>{{ spoolName }}</h1>
        <div class="actions">
          <button @click="router.push('/filaments?tab=spools')" class="btn btn-secondary">
            ← Back to Spools
          </button>
          <button @click="router.push(`/filaments/${spool.id}/edit`)" class="btn btn-primary">
            Edit
          </button>
          <button @click="deleteSpool" class="btn btn-danger">Delete</button>
        </div>
      </div>

      <div class="detail-grid">
        <!-- Left Column: Photo Card -->
        <div class="photo-column">
          <div class="card photo-card">
            <div class="card-header">
              <h3>Spool Photos</h3>
            </div>
            <div class="card-body photo-card-body photo-gallery-body">
              <!-- Main Photo -->
              <div class="main-photo-container">
                <img
                  v-if="spoolPhoto"
                  :src="spoolPhoto"
                  :alt="spoolName"
                  class="detail-photo clickable"
                  @click="openPhotoInModal(spoolPhoto, 'Main Photo')"
                />
                <div v-else class="no-photo">
                  <div class="color-swatches-preview">
                    <div
                      v-for="(colorHex, idx) in spoolColors"
                      :key="idx"
                      class="color-swatch-preview"
                      :style="{ backgroundColor: colorHex || '#cccccc' }"
                      @click="openColorSwatchModal(colorHex)"
                      title="Click to view larger swatch"
                    ></div>
                    <div
                      v-if="spoolColors.length === 0"
                      class="color-swatch-preview"
                      style="background-color: #cccccc"
                    ></div>
                  </div>
                  <p>No Photo Available</p>
                </div>
              </div>
              <!-- Additional Photos Gallery (inherited from blueprint, only show if there are additional photos) -->
              <div v-if="spoolAdditionalPhotos.length > 0" class="additional-photos-gallery">
                <!-- Additional Photos from Blueprint only (main photo is already shown above) -->
                <div
                  v-for="photo in spoolAdditionalPhotos"
                  :key="photo.id"
                  class="additional-photo-item clickable"
                  @click="openPhotoInModal(photo.image, photo.caption || 'No caption')"
                >
                  <img
                    :src="photo.image"
                    :alt="`${spoolName} - ${photo.caption || 'Additional Photo'}`"
                  />
                  <span class="photo-caption">{{ photo.caption || 'No caption' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Details Cards -->
        <div class="details-column">
          <!-- Spool Details Card -->
          <div class="card">
            <div class="card-header">
              <h3>Spool Details</h3>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">Brand:</span>
                  <span class="value">{{ spoolBrand?.name || 'N/A' }}</span>
                </div>
                <div class="info-item">
                  <span class="label">Material:</span>
                  <span class="value">{{ spoolMaterialType?.name || 'N/A' }}</span>
                </div>
                <div
                  v-if="
                    !spool.is_quick_add &&
                    spool.filament_type?.features &&
                    spool.filament_type.features.length > 0
                  "
                  class="info-item features-item"
                >
                  <span class="label">Features:</span>
                  <span class="value">
                    <span
                      v-for="feature in spool.filament_type.features"
                      :key="feature.id"
                      class="feature-badge"
                    >
                      {{ feature.name }}
                    </span>
                  </span>
                </div>
                <div v-if="spoolDiameter" class="info-item">
                  <span class="label">Diameter:</span>
                  <span class="value">{{ spoolDiameter }}mm</span>
                </div>
                <div class="info-item">
                  <span class="label">Status:</span>
                  <span class="value">
                    <span :class="['status-badge', getStatusClass(spool.status)]">
                      {{ spool.status.replace('_', ' ').toUpperCase() }}
                    </span>
                    <span v-if="spool.is_quick_add" class="quick-add-badge">Quick Add</span>
                  </span>
                </div>
                <div class="info-item color-item">
                  <span class="label">Color:</span>
                  <span class="value color-value">
                    <div class="color-swatches-inline">
                      <div
                        v-for="(colorHex, idx) in spoolColors"
                        :key="idx"
                        class="color-swatch-inline clickable"
                        :style="{ backgroundColor: colorHex || '#cccccc' }"
                        @click="openColorSwatchModal(colorHex)"
                        title="Click to view larger swatch"
                      ></div>
                      <div
                        v-if="spoolColors.length === 0"
                        class="color-swatch-inline"
                        style="background-color: #cccccc"
                      ></div>
                    </div>
                    <span v-if="spoolColors.length > 1" class="multi-color-label"
                      >({{ spoolColors.length }} colors)</span
                    >
                  </span>
                </div>
                <div class="info-item">
                  <span class="label">Added:</span>
                  <span class="value">{{ new Date(spool.date_added).toLocaleDateString() }}</span>
                </div>
                <div v-if="!spool.is_quick_add && spool.filament_type" class="info-item">
                  <span class="label">Blueprint:</span>
                  <span class="value">
                    <router-link
                      :to="`/filaments/materials/${spool.filament_type.id}`"
                      class="blueprint-link"
                    >
                      {{ spool.filament_type.name }}
                    </router-link>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Weight & Quantity Card -->
          <div class="card">
            <div class="card-header">
              <h3>Weight & Quantity</h3>
            </div>
            <div class="card-body">
              <div v-if="spool.is_opened" class="info-grid">
                <div class="info-item">
                  <span class="label">Current Weight:</span>
                  <span class="value">{{ spool.current_weight }}g</span>
                </div>
                <div class="info-item">
                  <span class="label">Initial Weight:</span>
                  <span class="value">{{ spool.initial_weight }}g</span>
                </div>
                <div class="info-item">
                  <span class="label">Remaining:</span>
                  <span class="value">{{ spool.weight_remaining_percent?.toFixed(1) }}%</span>
                </div>
                <div v-if="spool.date_opened" class="info-item">
                  <span class="label">Date Opened:</span>
                  <span class="value">{{ new Date(spool.date_opened).toLocaleDateString() }}</span>
                </div>
                <div v-if="spool.date_emptied" class="info-item">
                  <span class="label">Date Emptied:</span>
                  <span class="value">{{ new Date(spool.date_emptied).toLocaleDateString() }}</span>
                </div>
              </div>
              <div v-else class="info-grid">
                <div class="info-item">
                  <span class="label">Unopened Spools:</span>
                  <span class="value">{{ spool.quantity }}</span>
                </div>
              </div>

              <!-- Filament Usage Progress Bar (for opened spools) -->
              <div v-if="spool.is_opened" class="progress-section-card">
                <div class="progress-header">
                  <span class="progress-label">Filament Used</span>
                  <span
                    class="progress-percentage"
                    :style="{ color: getFilamentUsedColor(filamentUsedPercent()) }"
                    >{{ filamentUsedPercent().toFixed(1) }}%</span
                  >
                </div>
                <div class="progress-bar-bg">
                  <div class="progress-bar-fg" :style="progressBarStyle()"></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Location & Assignment Card (now in right column) -->
          <div class="card" v-if="spool.location || spool.assigned_printer || spool.project">
            <div class="card-header">
              <h3>Location & Assignment</h3>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div v-if="spool.location" class="info-item">
                  <span class="label">Location:</span>
                  <span class="value">{{ spool.location.name }}</span>
                </div>
                <div v-else-if="spool.assigned_printer" class="info-item">
                  <span class="label">Assigned Printer:</span>
                  <span class="value">{{ spool.assigned_printer.title }}</span>
                </div>
                <div v-if="spool.project" class="info-item">
                  <span class="label">Associated Project:</span>
                  <span class="value">{{ spool.project.project_name }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Print Settings Card (in right column) -->
          <div class="card" v-if="hasPrintSettings">
            <div class="card-header">
              <h3>Print Settings</h3>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div
                  v-if="printSettings.nozzle_temp_min || printSettings.nozzle_temp_max"
                  class="info-item"
                >
                  <span class="label">Nozzle Temp:</span>
                  <span class="value">
                    <template v-if="printSettings.nozzle_temp_min && printSettings.nozzle_temp_max">
                      {{ printSettings.nozzle_temp_min }}°C - {{ printSettings.nozzle_temp_max }}°C
                    </template>
                    <template v-else-if="printSettings.nozzle_temp_min">
                      {{ printSettings.nozzle_temp_min }}°C (min)
                    </template>
                    <template v-else>{{ printSettings.nozzle_temp_max }}°C (max)</template>
                  </span>
                </div>
                <div
                  v-if="printSettings.bed_temp_min || printSettings.bed_temp_max"
                  class="info-item"
                >
                  <span class="label">Bed Temp:</span>
                  <span class="value">
                    <template v-if="printSettings.bed_temp_min && printSettings.bed_temp_max">
                      {{ printSettings.bed_temp_min }}°C - {{ printSettings.bed_temp_max }}°C
                    </template>
                    <template v-else-if="printSettings.bed_temp_min">
                      {{ printSettings.bed_temp_min }}°C (min)
                    </template>
                    <template v-else>{{ printSettings.bed_temp_max }}°C (max)</template>
                  </span>
                </div>
                <div v-if="printSettings.density" class="info-item">
                  <span class="label">Density:</span>
                  <span class="value">{{ printSettings.density }} g/cm³</span>
                </div>
                <div v-if="printSettings.tds_value" class="info-item">
                  <span class="label">TDS Value:</span>
                  <span class="value">{{ printSettings.tds_value }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Additional Details Card (in right column) -->
          <div class="card" v-if="spool.notes || spool.nfc_tag_id">
            <div class="card-header">
              <h3>Additional Details</h3>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div v-if="spool.nfc_tag_id" class="info-item">
                  <span class="label">NFC Tag:</span>
                  <span class="value">{{ spool.nfc_tag_id }}</span>
                </div>
                <div v-if="spool.notes" class="info-item notes-item">
                  <span class="label">Notes:</span>
                  <span class="value">{{ spool.notes }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Photo Lightbox Modal -->
    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img
          :src="selectedPhotoUrl || spoolPhoto"
          :alt="selectedPhotoCaption || spoolName"
          class="modal-image"
        />
        <p v-if="selectedPhotoCaption" class="modal-caption">{{ selectedPhotoCaption }}</p>
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
  </div>
</template>

<style scoped>
/* Page Layout - Matching InventoryDetailView */
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

.loading-state,
.error {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-muted);
}

/* Detail Header - Matching InventoryDetailView */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
  }
}

.detail-header h1 {
  font-size: 2.5rem;
  font-weight: 600;
  word-wrap: break-word;
  overflow-wrap: break-word;
  margin: 0;
}

@media (max-width: 768px) {
  .detail-header h1 {
    font-size: 1.75rem;
  }
}

.actions {
  display: flex;
  gap: 1rem;
}

@media (max-width: 768px) {
  .actions {
    width: 100%;
    justify-content: stretch;
  }

  .actions .btn {
    flex: 1;
  }
}

/* Detail Grid - Two Column Layout */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 768px) {
  .detail-grid {
    grid-template-columns: 1fr 2fr;
    gap: 2rem;
  }
}

/* Card Styles - Matching InventoryDetailView */
.card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 1.5rem;
}

@media (max-width: 768px) {
  .card {
    margin-bottom: 1rem;
  }
}

.card:last-child {
  margin-bottom: 0;
}

.card-header {
  padding: 1rem 1.5rem;
  background: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .card-header {
    padding: 0.75rem 1rem;
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
  padding: 0;
}

.card-body.photo-card-body {
  padding: 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
}

.card-body.photo-gallery-body {
  flex-direction: column;
  gap: 1rem;
}

@media (max-width: 768px) {
  .card-body.photo-card-body {
    padding: 1rem;
  }
}

/* Main Photo Container */
.main-photo-container {
  width: 100%;
  display: flex;
  justify-content: center;
}

/* Photo Card */
.detail-photo {
  width: 100%;
  max-width: 400px;
  height: auto;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .detail-photo {
    max-width: 100%;
  }
}

.clickable {
  cursor: pointer;
}

.no-photo {
  width: 100%;
  aspect-ratio: 1/1;
  max-width: 400px;
  background-color: var(--color-background-mute);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--color-text-soft);
  font-weight: 500;
  gap: 1rem;
}

.color-swatches-preview {
  display: flex;
  gap: 0.5rem;
}

.color-swatch-preview {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: 3px solid var(--color-border);
}

/* Info Grid */
.info-grid {
  padding: 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

@media (max-width: 768px) {
  .info-grid {
    padding: 1rem;
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }
}

.info-item {
  display: flex;
  align-items: baseline;
  word-wrap: break-word;
  overflow-wrap: break-word;
  gap: 0.5rem;
}

.info-item .label {
  font-weight: bold;
  color: var(--color-heading);
  flex-shrink: 0;
}

.info-item .value {
  font-size: 1rem;
  word-break: break-word;
  overflow-wrap: break-word;
  min-width: 0;
  flex: 1;
}

@media (max-width: 768px) {
  .info-item .value {
    font-size: 0.9rem;
  }
}

/* Color Display in Info Grid */
.info-item.color-item {
  align-items: center;
}

.color-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.color-swatches-inline {
  display: flex;
  gap: 0.25rem;
}

.color-swatch-inline {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid var(--color-border);
}

.color-swatch-inline.clickable {
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.color-swatch-inline.clickable:hover {
  transform: scale(1.15);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.multi-color-label {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

/* Feature Badges */
.features-item {
  align-items: center;
}

.features-item .value {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.feature-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.625rem;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--color-text);
}

/* Blueprint Link */
.blueprint-link {
  color: var(--color-text);
  text-decoration: none;
}

.blueprint-link:hover {
  text-decoration: underline;
  color: var(--color-primary, #3b82f6);
}

/* Status Badge */
.status-badge {
  display: inline-block;
  padding: 0.25rem 0.6rem;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}

.status-new {
  background-color: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.status-opened {
  background-color: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.status-in-use {
  background-color: rgba(168, 85, 247, 0.1);
  color: #a855f7;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.status-low {
  background-color: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.status-empty {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

.status-archived {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
  text-decoration: line-through;
}

.quick-add-badge {
  display: inline-block;
  background-color: var(--color-background-mute);
  color: var(--color-text-muted);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  border: 1px solid var(--color-border);
  margin-left: 0.5rem;
}

/* Notes Section */
.notes-section {
  padding: 0 1.5rem 1.5rem 1.5rem;
  border-top: 1px solid var(--color-border);
  margin-top: 0;
}

.notes-section h4 {
  margin: 1rem 0 0.5rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}

.notes-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--color-text-muted);
  margin: 0;
}

@media (max-width: 768px) {
  .notes-section {
    padding: 0 1rem 1rem 1rem;
  }
  .notes-content {
    font-size: 0.9rem;
  }
}

/* Progress Bar (inside card) */
.progress-section-card {
  padding: 1rem 1.5rem 1.5rem 1.5rem;
  border-top: 1px solid var(--color-border);
}

@media (max-width: 768px) {
  .progress-section-card {
    padding: 1rem;
  }
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.progress-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-text);
}

.progress-percentage {
  font-size: 0.875rem;
  font-weight: 600;
}

.progress-bar-bg {
  width: 100%;
  background-color: var(--color-background);
  border-radius: 9999px;
  height: 0.75rem;
  overflow: hidden;
}

.progress-bar-fg {
  height: 0.75rem;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

/* Photo Lightbox Modal */
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
  max-height: 90vh;
  display: block;
  border-radius: 8px;
}

.modal-caption {
  color: white;
  text-align: center;
  margin-top: 1rem;
  font-size: 1rem;
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

/* Color Swatch Lightbox Modal */
.color-swatch-modal-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
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

/* Notes item styling - allow text to wrap */
.notes-item .value {
  white-space: normal;
  word-break: break-word;
}

/* Additional Photos Gallery */
.additional-photos-gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  width: 100%;
  justify-content: center;
}

.additional-photo-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
}

.additional-photo-item img {
  width: 100px;
  height: 75px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.additional-photo-item:hover img {
  opacity: 0.9;
  transform: scale(1.02);
}

.photo-caption {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-top: 0.25rem;
  text-align: center;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
