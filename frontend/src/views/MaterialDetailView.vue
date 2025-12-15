<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const material = ref(null)
const isLoading = ref(true)
const isPhotoModalVisible = ref(false)
const isColorSwatchModalVisible = ref(false)
const selectedColorHex = ref(null)
const selectedPhotoUrl = ref(null)
const selectedPhotoCaption = ref('')

const loadMaterial = async () => {
  isLoading.value = true
  try {
    const response = await axios.get(`/api/materials/${route.params.id}/`)
    material.value = response.data
  } catch (error) {
    console.error('Failed to load material:', error)
  } finally {
    isLoading.value = false
  }
}

// Computed for display
const materialName = computed(() => {
  if (!material.value) return 'Material'
  if (material.value.brand) {
    return `${material.value.brand.name} ${material.value.name}`
  }
  return material.value.name
})

const hasPrintSettings = computed(() => {
  if (!material.value) return false
  return (
    material.value.nozzle_temp_min ||
    material.value.nozzle_temp_max ||
    material.value.bed_temp_min ||
    material.value.bed_temp_max ||
    material.value.density
  )
})

const deleteMaterial = async () => {
  if (
    !confirm(
      `Are you sure you want to delete this material blueprint?\n\n"${materialName.value}"\n\nThis will NOT delete any spools using this blueprint, but they will need to be re-assigned.\n\nThis action cannot be undone.`,
    )
  ) {
    return
  }

  try {
    await axios.delete(`/api/materials/${material.value.id}/`)
    router.push('/filaments/materials')
  } catch (error) {
    console.error('Failed to delete material:', error)
    alert('Failed to delete material. Please try again.')
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

// Clone material - stores data in sessionStorage and navigates to create page
const cloneMaterial = () => {
  if (!material.value) return

  // Prepare cloned data - EXCLUDE: photo, name, colors, color_family, vendor, vendor_link, tds_value
  // Same fields as edit page's saveAndClone function
  // Note: brand and base_material are passed as full objects (not just IDs) to match edit page behavior
  const clonedData = {
    is_generic: material.value.is_generic,
    brand: material.value.brand || null,
    base_material: material.value.base_material || null,
    diameter: material.value.diameter,
    spool_weight: material.value.spool_weight,
    empty_spool_weight: material.value.empty_spool_weight,
    price_per_spool: material.value.price_per_spool,
    low_stock_threshold: material.value.low_stock_threshold,
    nozzle_temp_min: material.value.nozzle_temp_min,
    nozzle_temp_max: material.value.nozzle_temp_max,
    bed_temp_min: material.value.bed_temp_min,
    bed_temp_max: material.value.bed_temp_max,
    density: material.value.density,
    notes: material.value.notes,
    lowStockEnabled: material.value.low_stock_threshold > 0,
  }

  // Store in sessionStorage and navigate (same as edit page)
  sessionStorage.setItem('materialCloneData', JSON.stringify(clonedData))
  router.push('/filaments/materials/create')
}

onMounted(() => {
  loadMaterial()
})
</script>

<template>
  <div class="page-container">
    <div v-if="isLoading" class="loading-state">
      <p>Loading...</p>
    </div>

    <div v-else-if="!material" class="error">
      <p>Material blueprint not found.</p>
      <button @click="router.push('/filaments/materials')" class="btn btn-primary">
        Back to Materials
      </button>
    </div>

    <div v-else class="content-container">
      <!-- Page Header with Edit/Delete buttons -->
      <div class="detail-header">
        <h1>{{ materialName }}</h1>
        <div class="actions">
          <button @click="router.push('/filaments?tab=blueprints')" class="btn btn-secondary">
            ← Back to Blueprints
          </button>
          <button
            @click="router.push(`/filaments/create?materialId=${material.id}`)"
            class="btn btn-create-spool"
          >
            Create Spool
          </button>
          <button @click="cloneMaterial" class="btn btn-clone">Clone</button>
          <button
            @click="router.push(`/filaments/materials/${material.id}/edit`)"
            class="btn btn-primary"
          >
            Edit
          </button>
          <button @click="deleteMaterial" class="btn btn-danger">Delete</button>
        </div>
      </div>

      <div class="detail-grid">
        <!-- Left Column: Photo Card -->
        <div class="photo-column">
          <div class="card photo-card">
            <div class="card-header">
              <h3>Material Photos</h3>
            </div>
            <div class="card-body photo-card-body photo-gallery-body">
              <!-- Main Photo -->
              <div class="main-photo-container">
                <img
                  v-if="material.photo"
                  :src="material.photo"
                  :alt="materialName"
                  class="detail-photo clickable"
                  @click="openPhotoInModal(material.photo, 'Main Photo')"
                />
                <div v-else class="no-photo">
                  <div class="color-swatches-preview">
                    <div
                      v-for="(colorHex, idx) in material.colors || []"
                      :key="idx"
                      class="color-swatch-preview clickable"
                      :style="{ backgroundColor: colorHex || '#cccccc' }"
                      @click="openColorSwatchModal(colorHex)"
                      title="Click to view larger swatch"
                    ></div>
                    <div
                      v-if="!material.colors || material.colors.length === 0"
                      class="color-swatch-preview"
                      style="background-color: #cccccc"
                    ></div>
                  </div>
                  <p>No Photo Available</p>
                </div>
              </div>
              <!-- Additional Photos Gallery (only show if there are additional photos) -->
              <div
                v-if="material.additional_photos && material.additional_photos.length > 0"
                class="additional-photos-gallery"
              >
                <!-- Additional Photos from API only (main photo is already shown above) -->
                <div
                  v-for="photo in material.additional_photos"
                  :key="photo.id"
                  class="additional-photo-item clickable"
                  @click="openPhotoInModal(photo.image, photo.caption || 'No caption')"
                >
                  <img
                    :src="photo.image"
                    :alt="`${materialName} - ${photo.caption || 'Additional Photo'}`"
                  />
                  <span class="photo-caption">{{ photo.caption || 'No caption' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Details Cards -->
        <div class="details-column">
          <!-- Material Details Card -->
          <div class="card">
            <div class="card-header">
              <h3>Material Details</h3>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div v-if="material.brand" class="info-item">
                  <span class="label">Brand:</span>
                  <span class="value">{{ material.brand.name }}</span>
                </div>
                <div v-if="material.base_material" class="info-item">
                  <span class="label">Material Type:</span>
                  <span class="value">{{ material.base_material.name }}</span>
                </div>
                <div
                  v-if="material.features && material.features.length > 0"
                  class="info-item features-item"
                >
                  <span class="label">Features:</span>
                  <span class="value">
                    <span
                      v-for="feature in material.features"
                      :key="feature.id"
                      class="feature-badge"
                    >
                      {{ feature.name }}
                    </span>
                  </span>
                </div>
                <div class="info-item">
                  <span class="label">Diameter:</span>
                  <span class="value">{{ material.diameter }}mm</span>
                </div>
                <div v-if="material.spool_weight" class="info-item">
                  <span class="label">Spool Weight:</span>
                  <span class="value">{{ material.spool_weight }}g</span>
                </div>
                <div v-if="material.empty_spool_weight" class="info-item">
                  <span class="label">Empty Spool Weight:</span>
                  <span class="value">{{ material.empty_spool_weight }}g</span>
                </div>
                <div class="info-item color-item">
                  <span class="label">Color:</span>
                  <span class="value color-value">
                    <div class="color-swatches-inline">
                      <div
                        v-for="(colorHex, idx) in material.colors || []"
                        :key="idx"
                        class="color-swatch-inline clickable"
                        :style="{ backgroundColor: colorHex || '#cccccc' }"
                        @click="openColorSwatchModal(colorHex)"
                        title="Click to view larger swatch"
                      ></div>
                      <div
                        v-if="!material.colors || material.colors.length === 0"
                        class="color-swatch-inline"
                        style="background-color: #cccccc"
                      ></div>
                    </div>
                    <span
                      v-if="material.colors && material.colors.length > 1"
                      class="multi-color-label"
                    >
                      ({{ material.colors.length }} colors)
                    </span>
                  </span>
                </div>
                <div v-if="material.color_family" class="info-item">
                  <span class="label">Color Family:</span>
                  <span class="value">{{ material.color_family }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Purchase Info Card -->
          <div class="card" v-if="material.vendor || material.price_per_spool">
            <div class="card-header">
              <h3>Purchase Info</h3>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div v-if="material.vendor" class="info-item">
                  <span class="label">Vendor:</span>
                  <span class="value">
                    <a
                      v-if="material.vendor_link"
                      :href="material.vendor_link"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="vendor-link"
                    >
                      {{ material.vendor.name }}
                    </a>
                    <span v-else>{{ material.vendor.name }}</span>
                  </span>
                </div>
                <div v-if="material.price_per_spool" class="info-item">
                  <span class="label">Price per Spool:</span>
                  <span class="value">${{ material.price_per_spool }}</span>
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
                <div v-if="material.nozzle_temp_min || material.nozzle_temp_max" class="info-item">
                  <span class="label">Nozzle Temp:</span>
                  <span class="value">
                    <template v-if="material.nozzle_temp_min && material.nozzle_temp_max">
                      {{ material.nozzle_temp_min }}°C - {{ material.nozzle_temp_max }}°C
                    </template>
                    <template v-else-if="material.nozzle_temp_min">
                      {{ material.nozzle_temp_min }}°C (min)
                    </template>
                    <template v-else>{{ material.nozzle_temp_max }}°C (max)</template>
                  </span>
                </div>
                <div v-if="material.bed_temp_min || material.bed_temp_max" class="info-item">
                  <span class="label">Bed Temp:</span>
                  <span class="value">
                    <template v-if="material.bed_temp_min && material.bed_temp_max">
                      {{ material.bed_temp_min }}°C - {{ material.bed_temp_max }}°C
                    </template>
                    <template v-else-if="material.bed_temp_min">
                      {{ material.bed_temp_min }}°C (min)
                    </template>
                    <template v-else>{{ material.bed_temp_max }}°C (max)</template>
                  </span>
                </div>
                <div v-if="material.density" class="info-item">
                  <span class="label">Density:</span>
                  <span class="value">{{ material.density }} g/cm³</span>
                </div>
                <div v-if="material.tds_value" class="info-item">
                  <span class="label">TDS Value:</span>
                  <span class="value">{{ material.tds_value }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Stock Settings Card -->
          <div class="card" v-if="material.low_stock_threshold">
            <div class="card-header">
              <h3>Stock Settings</h3>
            </div>
            <div class="card-body">
              <div class="info-grid">
                <div class="info-item">
                  <span class="label">Low Stock Alert:</span>
                  <span class="value">{{ material.low_stock_threshold }} spools</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Notes Card -->
          <div class="card" v-if="material.notes">
            <div class="card-header">
              <h3>Notes</h3>
            </div>
            <div class="card-body">
              <div class="notes-section">
                <p class="notes-content">{{ material.notes }}</p>
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
          :src="selectedPhotoUrl || material.photo"
          :alt="selectedPhotoCaption || materialName"
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

/* Create Spool button - Green (matches Save and Add Spool on edit page) */
.btn-create-spool {
  background-color: var(--color-green, #198754);
  color: white;
  border: 1px solid var(--color-green, #198754);
}

.btn-create-spool:hover {
  background-color: #157347;
}

/* Clone button - Purple (matches Save and Clone on edit page) */
.btn-clone {
  background-color: var(--color-purple, #6f42c1);
  color: white;
  border: 1px solid var(--color-purple, #6f42c1);
}

.btn-clone:hover {
  background-color: #5a32a3;
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

/* Photo Gallery Layout */
.card-body.photo-gallery-body {
  flex-direction: column;
  gap: 1rem;
}

.main-photo-container {
  display: flex;
  justify-content: center;
  width: 100%;
}

.additional-photos-gallery {
  display: flex;
  gap: 0.75rem;
  justify-content: center;
  flex-wrap: wrap;
  width: 100%;
  padding-top: 0.5rem;
  border-top: 1px solid var(--color-border);
}

.additional-photo-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.additional-photo-item img {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  transition:
    transform 0.2s,
    border-color 0.2s;
}

.additional-photo-item:hover img {
  transform: scale(1.05);
  border-color: var(--color-primary);
}

.photo-caption {
  font-size: 0.7rem;
  color: var(--color-text-soft);
  text-align: center;
}

@media (max-width: 768px) {
  .card-body.photo-card-body {
    padding: 1rem;
  }
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

/* Vendor Link */
.vendor-link {
  color: var(--color-text);
  text-decoration: none;
}

.vendor-link:hover {
  text-decoration: underline;
  color: var(--color-primary, #3b82f6);
}

/* Notes Section */
.notes-section {
  padding: 1.5rem;
}

.notes-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  color: var(--color-text);
  margin: 0;
}

@media (max-width: 768px) {
  .notes-section {
    padding: 1rem;
  }
  .notes-content {
    font-size: 0.9rem;
  }
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

/* Clickable swatch styles */
.color-swatch-preview.clickable,
.color-swatch-inline.clickable {
  cursor: pointer;
  transition:
    transform 0.15s ease,
    box-shadow 0.15s ease;
}

.color-swatch-preview.clickable:hover,
.color-swatch-inline.clickable:hover {
  transform: scale(1.15);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
</style>
