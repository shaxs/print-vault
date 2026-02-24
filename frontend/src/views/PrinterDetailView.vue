<script setup>
import { ref, onMounted, computed } from 'vue/dist/vue.esm-bundler.js'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import ErrorModal from '../components/ErrorModal.vue'
import InfoModal from '../components/InfoModal.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const route = useRoute()
const router = useRouter()
const printer = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')
const isErrorModalVisible = ref(false)

const isInfoModalVisible = ref(false)
const infoModalMessage = ref('')

const isPhotoModalVisible = ref(false)
const isDownloading = ref(new Set())

// Color swatch lightbox state
const isColorSwatchModalVisible = ref(false)
const selectedColorHex = ref(null)

const openColorSwatchModal = (colorHex) => {
  selectedColorHex.value = colorHex
  isColorSwatchModalVisible.value = true
}

const fetchPrinter = async () => {
  try {
    isLoading.value = true
    const response = await APIService.getPrinter(route.params.id)
    printer.value = response.data
  } catch (error) {
    console.error('Failed to fetch printer details:', error)
    errorMessage.value = 'Failed to load printer details. Please try again.'
    isErrorModalVisible.value = true
  } finally {
    isLoading.value = false
  }
}

const deleteMod = async (modId) => {
  if (confirm('Are you sure you want to delete this mod and all its files?')) {
    try {
      await APIService.deleteMod(modId)
      infoModalMessage.value = 'Mod deleted successfully.'
      isInfoModalVisible.value = true
      await fetchPrinter()
    } catch (error) {
      console.error('Failed to delete mod:', error)
      errorMessage.value = 'Failed to delete mod. Please try again.'
      isErrorModalVisible.value = true
    }
  }
}

const downloadAllModFiles = async (mod) => {
  isDownloading.value.add(mod.id)
  try {
    const response = await APIService.downloadModFiles(mod.id)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const filename = `${mod.name.replace(/ /g, '_')}_files.zip`
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Failed to download mod files:', error)
    errorMessage.value = 'Failed to download files. Please try again.'
    isErrorModalVisible.value = true
  } finally {
    isDownloading.value.delete(mod.id)
  }
}

const formatPurchasePrice = (price) => {
  if (price === null || price === undefined) {
    return 'N/A'
  }
  return `$${Number(price).toFixed(2)}`
}

const buildVolume = computed(() => {
  if (
    !printer.value ||
    printer.value.build_size_x == null ||
    printer.value.build_size_y == null ||
    printer.value.build_size_z == null
  ) {
    return 'N/A'
  }
  return `${printer.value.build_size_x}mm x ${printer.value.build_size_y}mm x ${printer.value.build_size_z}mm`
})

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  // Parse date as local time by adding 'T00:00:00' to force local timezone
  const date = new Date(dateString + 'T00:00:00')
  const options = { year: 'numeric', month: 'long', day: 'numeric' }
  return date.toLocaleDateString(undefined, options)
}

const deletePrinter = async () => {
  if (confirm('Are you sure you want to delete this printer? This action cannot be undone.')) {
    try {
      await APIService.deletePrinter(printer.value.id)
      router.push({ name: 'printer-list' })
    } catch (error) {
      console.error('Failed to delete printer:', error)
      errorMessage.value = 'Failed to delete printer. Please try again.'
      isErrorModalVisible.value = true
    }
  }
}

const getFileName = (filePath) => {
  if (!filePath) return ''
  return filePath.split('/').pop()
}

const formatMaterialName = (material) => {
  if (!material) return ''
  const brandName = material.brand?.name || ''
  const diameter = material.diameter ? ` (${material.diameter}mm)` : ''
  return `${brandName} ${material.name}${diameter}`.trim()
}

const getSpoolDisplayName = (spool) => {
  // Blueprint-based spool
  if (spool.filament_type) {
    return formatMaterialName(spool.filament_type)
  }
  // Quick Add spool
  if (spool.standalone_name) {
    const brand = spool.standalone_brand?.name || ''
    return brand ? `${brand} ${spool.standalone_name}` : spool.standalone_name
  }
  return `Spool #${spool.id}`
}

onMounted(fetchPrinter)
</script>

<template>
  <div class="page-container">
    <div v-if="isLoading" class="loading-state">
      <p>Loading printer details...</p>
    </div>

    <div v-if="!isLoading && printer" class="content-container">
      <div class="detail-header">
        <div class="header-content">
          <img
            :src="printer.photo"
            v-if="printer.photo"
            alt="Printer Photo"
            class="detail-photo clickable"
            @click="isPhotoModalVisible = true"
          />
          <div class="header-info">
            <h1>{{ printer.title }}</h1>
            <p class="manufacturer-serial">
              <span v-if="printer.manufacturer">{{ printer.manufacturer.name }}</span>
              <span v-else>N/A</span>
              | Serial: {{ printer.serial_number || 'N/A' }}
            </p>
          </div>
        </div>
        <div class="header-actions">
          <router-link
            :to="{ name: 'printer-edit', params: { id: printer.id } }"
            class="btn btn-primary"
            >Edit</router-link
          >
          <button @click="deletePrinter" class="btn btn-danger">Delete</button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="card">
          <div class="card-header">
            <h3>Printer Details</h3>
            <router-link
              :to="{ name: 'printer-edit', params: { id: printer.id } }"
              class="btn btn-sm btn-primary"
              >Edit</router-link
            >
          </div>
          <div class="card-body">
            <div class="card-section">
              <p>
                <strong>Status:</strong>
                <span
                  :class="[
                    'status-badge',
                    `status-${printer.status.toLowerCase().replace(/ /g, '-').replace(/\//g, '-')}`,
                  ]"
                  >{{ printer.status }}</span
                >
              </p>
              <p>
                <strong>Build Volume:&nbsp;</strong>
                <span>{{ buildVolume }}</span>
              </p>
              <p><strong>Purchase Date:</strong> {{ formatDate(printer.purchase_date) }}</p>
              <p>
                <strong>Purchase Price:</strong>
                {{ formatPurchasePrice(printer.purchase_price) }}
              </p>
            </div>
            <hr />
            <div class="card-section">
              <h4>Notes</h4>
              <p class="notes-content">{{ printer.notes || 'No notes available.' }}</p>
            </div>
            
            <!-- Filament Materials Section -->
            <div 
              v-if="printer.primary_filament_custom || printer.primary_filament_blueprint || 
                    printer.accent_filament_custom || printer.accent_filament_blueprint || 
                    (printer.additional_filaments_display && printer.additional_filaments_display.length > 0)"
              class="card-section"
            >
              <hr />
              <h4>Materials</h4>
              
              <div v-if="printer.primary_filament_custom || printer.primary_filament_blueprint" class="filament-item">
                <strong>Primary:</strong>
                <span 
                  v-if="printer.primary_filament_blueprint && printer.primary_filament_blueprint.colors && printer.primary_filament_blueprint.colors.length > 0"
                  class="color-swatch clickable"
                  :style="{ backgroundColor: printer.primary_filament_blueprint.colors[0] }"
                  :title="printer.primary_filament_blueprint.colors[0]"
                  @click.stop="openColorSwatchModal(printer.primary_filament_blueprint.colors[0])"
                ></span>
                <span v-if="printer.primary_filament_custom">{{ printer.primary_filament_custom }}</span>
                <router-link 
                  v-if="printer.primary_filament_blueprint" 
                  :to="`/filaments/materials/${printer.primary_filament_blueprint.id}`"
                  class="filament-link"
                >
                  {{ formatMaterialName(printer.primary_filament_blueprint) }}
                </router-link>
              </div>
              
              <div v-if="printer.accent_filament_custom || printer.accent_filament_blueprint" class="filament-item">
                <strong>Accent:</strong>
                <span 
                  v-if="printer.accent_filament_blueprint && printer.accent_filament_blueprint.colors && printer.accent_filament_blueprint.colors.length > 0"
                  class="color-swatch clickable"
                  :style="{ backgroundColor: printer.accent_filament_blueprint.colors[0] }"
                  :title="printer.accent_filament_blueprint.colors[0]"
                  @click.stop="openColorSwatchModal(printer.accent_filament_blueprint.colors[0])"
                ></span>
                <span v-if="printer.accent_filament_custom">{{ printer.accent_filament_custom }}</span>
                <router-link 
                  v-if="printer.accent_filament_blueprint" 
                  :to="`/filaments/materials/${printer.accent_filament_blueprint.id}`"
                  class="filament-link"
                >
                  {{ formatMaterialName(printer.accent_filament_blueprint) }}
                </router-link>
              </div>
              
              <div 
                v-for="(filament, index) in printer.additional_filaments_display" 
                :key="index"
                class="filament-item"
              >
                <strong>{{ filament.type }}:</strong>
                <span 
                  v-if="filament.blueprint && filament.blueprint.colors && filament.blueprint.colors.length > 0"
                  class="color-swatch clickable"
                  :style="{ backgroundColor: filament.blueprint.colors[0] }"
                  :title="filament.blueprint.colors[0]"
                  @click.stop="openColorSwatchModal(filament.blueprint.colors[0])"
                ></span>
                <span v-if="filament.custom">{{ filament.custom }}</span>
                <router-link 
                  v-if="filament.blueprint" 
                  :to="`/filaments/materials/${filament.blueprint.id}`"
                  class="filament-link"
                >
                  {{ formatMaterialName(filament.blueprint) }}
                </router-link>
              </div>
            </div>
            <hr v-if="printer.filamentspool_set && printer.filamentspool_set.length > 0" />
            <div v-if="printer.filamentspool_set && printer.filamentspool_set.length > 0" class="card-section">
              <h4>Assigned Spools</h4>
              <ul class="resource-list">
                <li v-for="spool in printer.filamentspool_set" :key="spool.id">
                  <div class="spool-name-wrapper">
                    <span 
                      v-if="spool.filament_type && spool.filament_type.colors && spool.filament_type.colors.length > 0"
                      class="color-swatch clickable"
                      :style="{ backgroundColor: spool.filament_type.colors[0] }"
                      :title="spool.filament_type.colors[0]"
                      @click.stop="openColorSwatchModal(spool.filament_type.colors[0])"
                    ></span>
                    <router-link :to="`/filaments/${spool.id}`">
                      {{ getSpoolDisplayName(spool) }}
                    </router-link>
                  </div>
                  <span class="spool-status" :class="`status-${spool.status}`">
                    {{ spool.status.replace('_', ' ').toUpperCase() }}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Maintenance</h3>
            <router-link
              :to="{ name: 'maintenance-edit', params: { id: printer.id } }"
              class="btn btn-sm btn-primary"
              >Edit</router-link
            >
          </div>
          <div class="card-body">
            <div class="card-section">
              <p>
                <strong>Last Maintained:</strong>
                {{ formatDate(printer.last_maintained_date) }}
              </p>
              <p>
                <strong>Maintenance Reminder:</strong>
                {{ formatDate(printer.maintenance_reminder_date) }}
              </p>
              <p>
                <strong>Last Carbon Filter Replacement:</strong>
                {{ formatDate(printer.last_carbon_replacement_date) }}
              </p>
              <p>
                <strong>Carbon Filter Reminder:</strong>
                {{ formatDate(printer.carbon_reminder_date) }}
              </p>
            </div>
            <hr />
            <div class="card-section">
              <h4>Maintenance Notes</h4>
              <p class="notes-content">
                {{ printer.maintenance_notes || 'No maintenance notes available.' }}
              </p>
            </div>
          </div>
        </div>

        <div class="card card-full-width">
          <div class="card-header">
            <h3>Mods</h3>
            <router-link
              :to="{ name: 'mod-create', params: { printerId: printer.id } }"
              class="btn btn-sm btn-secondary"
              >Add Mod</router-link
            >
          </div>
          <div class="card-body">
            <ul v-if="printer.mods && printer.mods.length > 0" class="mods-list">
              <li v-for="mod in printer.mods" :key="mod.id" class="mod-item">
                <div class="mod-info">
                  <a v-if="mod.link" :href="mod.link" target="_blank" class="mod-name-link">
                    <strong>{{ mod.name }}</strong>
                  </a>
                  <strong v-else>{{ mod.name }}</strong>
                  -
                  <span :class="['status-badge', `status-${mod.status.toLowerCase()}`]">{{
                    mod.status
                  }}</span>
                  <div v-if="mod.files && mod.files.length > 0" class="mod-files">
                    <ul>
                      <li v-for="file in mod.files" :key="file.id">
                        <a :href="file.file" target="_blank">{{ getFileName(file.file) }}</a>
                      </li>
                    </ul>
                  </div>
                </div>
                <div class="mod-actions">
                  <button
                    v-if="mod.files && mod.files.length > 0"
                    @click="downloadAllModFiles(mod)"
                    class="btn btn-sm btn-secondary download-btn"
                    :disabled="isDownloading.has(mod.id)"
                  >
                    <LoadingSpinner v-if="isDownloading.has(mod.id)" />
                    <span v-else>Download All</span>
                  </button>
                  <router-link
                    :to="{
                      name: 'mod-edit',
                      params: { printerId: printer.id, modId: mod.id },
                    }"
                    class="btn btn-sm btn-primary"
                    >Edit</router-link
                  >
                  <button @click="deleteMod(mod.id)" class="btn btn-sm btn-danger">Delete</button>
                </div>
              </li>
            </ul>
            <p v-else>No mods added yet.</p>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img :src="printer.photo" alt="Full size printer photo" class="modal-image" />
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

    <ErrorModal
      :show="isErrorModalVisible"
      :message="errorMessage"
      @close="isErrorModalVisible = false"
    />
    <InfoModal
      :show="isInfoModalVisible"
      :message="infoModalMessage"
      @close="isInfoModalVisible = false"
    />
  </div>
</template>

<style scoped>
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

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  gap: 1rem;
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
  }
}

.header-content {
  display: flex;
  align-items: center;
  min-width: 0;
  flex: 1;
}

@media (max-width: 768px) {
  .header-content {
    width: 100%;
  }
}

.detail-photo {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 8px;
  margin-right: 1.5rem;
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .detail-photo {
    width: 80px;
    height: 80px;
    margin-right: 1rem;
  }
}

.detail-photo.clickable {
  cursor: pointer;
}

.header-info {
  min-width: 0;
  flex: 1;
}

.header-info h1 {
  font-size: 2.5rem;
  font-weight: 600;
  margin: 0;
  color: var(--color-heading);
  word-wrap: break-word;
  overflow-wrap: break-word;
}

@media (max-width: 768px) {
  .header-info h1 {
    font-size: 1.75rem;
  }
}

.manufacturer-serial {
  font-size: 1.1rem;
  color: var(--color-text);
  margin: 0.25rem 0 0.5rem;
  word-wrap: break-word;
}

@media (max-width: 768px) {
  .manufacturer-serial {
    font-size: 1rem;
  }
}

.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: white; /* Default text color */
  margin-left: 0.5rem;
}

/* Status Colors */
.status-active,
.status-operational,
.status-completed {
  background-color: var(--color-green);
}

.status-under-repair,
.status-under-maintenance {
  background-color: var(--color-red);
}

.status-inprogress,
.status-on-hold {
  background-color: #ffc107; /* Yellow */
  color: #333;
}

.status-decommissioned,
.status-planned,
.status-sold,
.status-archived {
  background-color: #6c757d; /* Grey */
}

.header-actions {
  display: flex;
  gap: 1rem;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .header-actions {
    width: 100%;
    justify-content: stretch;
  }

  .header-actions .btn {
    flex: 1;
  }
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr; /* Default to a single column for mobile-first */
  gap: 1.5rem;
}

/* On screens wider than 768px, switch to a two-column layout */
@media (min-width: 768px) {
  .detail-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  display: flex; /* Added for flexbox layout */
  flex-direction: column; /* Stack header and body vertically */
}

@media (max-width: 768px) {
  .card {
    margin-bottom: 1rem;
  }
}

.card.card-full-width {
  grid-column: 1 / -1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
  gap: 0.5rem;
  flex-wrap: wrap;
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
  padding: 1.5rem;
  flex-grow: 1; /* Allow body to grow and fill available space */
}

@media (max-width: 768px) {
  .card-body {
    padding: 1rem;
  }
}

.card-section h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}

.card-body p {
  margin: 0 0 0.75rem 0;
  line-height: 1.6;
  word-wrap: break-word;
}

@media (max-width: 768px) {
  .card-body p {
    font-size: 0.9rem;
  }
}

.card-body p:last-child {
  margin-bottom: 0;
}

.card-body p.notes-content {
  /* Reset flex properties for notes content if they were set globally */
  display: block;
  white-space: pre-wrap; /* Preserve whitespace and newlines */
}

.card-body hr {
  border: 0;
  border-top: 1px solid var(--color-border);
  margin: 1.5rem 0;
}

/* Mods List Styles */
.mods-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.mod-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 0;
  border-bottom: 1px solid var(--color-border);
  gap: 1rem;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .mod-item {
    flex-direction: column;
    padding: 0.75rem 0;
  }
}

.mod-item:last-child {
  border-bottom: none;
}

.mod-info {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  flex-grow: 1;
  min-width: 0;
}

@media (max-width: 768px) {
  .mod-info {
    width: 100%;
  }
}

.mod-name-link {
  color: var(--color-text);
  text-decoration: none;
}

.mod-name-link:hover {
  text-decoration: underline;
}

.mod-files {
  margin-top: 0.75rem;
  font-size: 0.9rem;
  width: 100%;
}

@media (max-width: 768px) {
  .mod-files {
    font-size: 0.85rem;
  }
}

.mod-files ul {
  list-style: none;
  padding-left: 1rem;
  margin: 0;
  margin-bottom: 0.5rem;
}

.mod-files li a {
  color: var(--color-text);
  text-decoration: none;
  word-break: break-word;
}
.mod-files li a:hover {
  text-decoration: underline;
}

.mod-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
  margin-left: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .mod-actions {
    width: 100%;
    margin-left: 0;
    justify-content: stretch;
  }

  .mod-actions .btn {
    flex: 1;
  }

  .mod-actions .download-btn {
    flex: 1;
  }
}

.download-btn {
  min-width: 110px;
  min-height: 31px; /* Corresponds to the height of a .btn-sm */
  display: inline-flex;
  justify-content: center;
  align-items: center;
}

.file-input {
  display: none;
}

/* Modal styles for photo lightbox */
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
  max-height: 100%;
  display: block;
}

/* Filament Materials Styles */
.filament-item {
  margin-bottom: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filament-item strong {
  color: var(--color-heading);
  min-width: 80px;
}

.color-swatch {
  display: inline-block;
  width: 20px;
  height: 20px;
  border-radius: 3px;
  border: 1.5px solid var(--color-border);
  flex-shrink: 0;
}

.color-swatch.clickable {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.color-swatch.clickable:hover {
  transform: scale(1.1);
}

.filament-item span {
  color: var(--color-text);
}

.filament-link {
  color: var(--color-text);
  text-decoration: none;
}

.filament-link:hover {
  text-decoration: underline;
}

/* Spool Status Styling - matches FilamentSpoolDetailView */
.spool-status {
  display: inline-block;
  padding: 0.25rem 0.6rem;
  margin-left: 0.5rem;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
}

.spool-status.status-new {
  background-color: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.spool-status.status-opened {
  background-color: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.spool-status.status-in_use {
  background-color: rgba(168, 85, 247, 0.1);
  color: #a855f7;
  border: 1px solid rgba(168, 85, 247, 0.3);
}

.spool-status.status-low {
  background-color: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.spool-status.status-empty {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
}

.spool-status.status-archived {
  background-color: rgba(107, 114, 128, 0.1);
  color: #6b7280;
  border: 1px solid rgba(107, 114, 128, 0.3);
  text-decoration: line-through;
}

/* Resource List Styling */
.resource-list {
  list-style-type: none;
  padding: 0;
  margin: 0 0 1rem 0;
}

.resource-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border-mute);
  word-break: break-word;
}

@media (max-width: 768px) {
  .resource-list li {
    font-size: 0.875rem;
  }
}

.resource-list li:last-child {
  border-bottom: none;
}

.resource-list a {
  color: var(--color-text);
  text-decoration: none;
  word-break: break-word;
}

.resource-list a:hover {
  text-decoration: underline;
}

.spool-name-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Color Swatch Modal Styles */
.color-swatch-modal-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
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
</style>
