<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import MainHeader from '../components/MainHeader.vue'
import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

const router = useRouter()
const route = useRoute()
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// Mode toggle: 'blueprint' or 'quickadd'
const createMode = ref('blueprint')
// Color mode toggle for Quick Add: 'single' or 'multi'
const quickAddColorMode = ref('single')

const spool = ref({
  filament_type: null,
  quantity: 1,
  is_opened: false,
  initial_weight: null,
  current_weight: null,
  price_paid: null,
  location: null,
  assigned_printer: null,
  project: null,
  notes: '',
  nfc_tag_id: null,
  // Quick Add fields
  standalone_name: '',
  standalone_brand: null,
  standalone_material_type: null,
  standalone_colors: ['#000000'], // Array of hex codes
  standalone_color_family: null,
  standalone_nozzle_temp_min: null,
  standalone_nozzle_temp_max: null,
  standalone_bed_temp_min: null,
  standalone_bed_temp_max: null,
  standalone_density: null,
})

const materialBlueprints = ref([])
const genericMaterials = ref([])
const brands = ref([])
const locations = ref([])
const printers = ref([])
const projects = ref([])

const colorFamilyOptions = [
  { value: 'red', label: 'Red' },
  { value: 'orange', label: 'Orange' },
  { value: 'yellow', label: 'Yellow' },
  { value: 'green', label: 'Green' },
  { value: 'blue', label: 'Blue' },
  { value: 'purple', label: 'Purple' },
  { value: 'pink', label: 'Pink' },
  { value: 'brown', label: 'Brown' },
  { value: 'black', label: 'Black' },
  { value: 'white', label: 'White' },
  { value: 'gray', label: 'Gray' },
  { value: 'clear', label: 'Clear/Natural' },
  { value: 'multi', label: 'Multi-Color' },
]

const loadOptions = async () => {
  try {
    const [materialsRes, genericsRes, brandsRes, locationsRes, printersRes, projectsRes] =
      await Promise.all([
        axios.get(`/api/materials/?type=blueprint`),
        axios.get(`/api/materials/?type=generic`),
        axios.get(`/api/brands/`),
        axios.get(`/api/locations/`),
        axios.get(`/api/printers/`),
        axios.get(`/api/projects/`),
      ])
    materialBlueprints.value = materialsRes.data.results || materialsRes.data
    genericMaterials.value = genericsRes.data.results || genericsRes.data
    brands.value = brandsRes.data.results || brandsRes.data
    locations.value = locationsRes.data.results || locationsRes.data
    printers.value = printersRes.data.results || printersRes.data
    projects.value = projectsRes.data.results || projectsRes.data

    // Pre-select material if coming from library
    if (route.query.materialId) {
      const materialId = parseInt(route.query.materialId)
      spool.value.filament_type = materialBlueprints.value.find((m) => m.id === materialId)
    }
  } catch (error) {
    console.error('Failed to load options:', error)
  }
}

// Custom label formatter for material blueprints in Multiselect
const formatMaterialLabel = (mat) => {
  if (!mat) return ''
  const brandName = mat.brand?.name || ''
  const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
  return `${brandName} ${mat.name}${diameter}`.trim()
}

const saveSpool = async () => {
  try {
    const isQuickAdd = createMode.value === 'quickadd'

    const payload = {
      is_quick_add: isQuickAdd,
      quantity: spool.value.is_opened ? 1 : spool.value.quantity,
      is_opened: spool.value.is_opened,
      notes: spool.value.notes || '',
    }

    if (isQuickAdd) {
      // Quick Add mode - use standalone fields
      payload.standalone_name = spool.value.standalone_name

      // Handle brand - send as JSON for get_or_create on backend
      if (spool.value.standalone_brand) {
        const brandName =
          typeof spool.value.standalone_brand === 'object'
            ? spool.value.standalone_brand.name
            : spool.value.standalone_brand
        payload.standalone_brand = JSON.stringify({ name: brandName })
      }

      payload.standalone_material_type_id = spool.value.standalone_material_type?.id
      payload.standalone_colors = spool.value.standalone_colors
      payload.standalone_color_family = spool.value.standalone_color_family

      // Optional print settings
      if (spool.value.standalone_nozzle_temp_min) {
        payload.standalone_nozzle_temp_min = spool.value.standalone_nozzle_temp_min
      }
      if (spool.value.standalone_nozzle_temp_max) {
        payload.standalone_nozzle_temp_max = spool.value.standalone_nozzle_temp_max
      }
      if (spool.value.standalone_bed_temp_min) {
        payload.standalone_bed_temp_min = spool.value.standalone_bed_temp_min
      }
      if (spool.value.standalone_bed_temp_max) {
        payload.standalone_bed_temp_max = spool.value.standalone_bed_temp_max
      }
      if (spool.value.standalone_density) {
        payload.standalone_density = spool.value.standalone_density
      }

      // Weight for Quick Add
      if (spool.value.is_opened) {
        payload.initial_weight = spool.value.initial_weight || 1000
        payload.current_weight = spool.value.current_weight || spool.value.initial_weight || 1000
      } else {
        payload.initial_weight = spool.value.initial_weight || 1000
        payload.current_weight = spool.value.initial_weight || 1000
      }
    } else {
      // Blueprint mode
      payload.filament_type_id = spool.value.filament_type?.id

      if (spool.value.is_opened) {
        payload.initial_weight = spool.value.initial_weight
        payload.current_weight = spool.value.current_weight || spool.value.initial_weight
      } else {
        // For unopened spools, use the blueprint's spool_weight
        const blueprintWeight = spool.value.filament_type?.spool_weight || 1000
        payload.initial_weight = blueprintWeight
        payload.current_weight = blueprintWeight
      }
    }

    if (spool.value.location) {
      const locationName =
        typeof spool.value.location === 'object' ? spool.value.location.name : spool.value.location
      payload.location_name = locationName
    }

    if (spool.value.assigned_printer) {
      payload.assigned_printer_id = spool.value.assigned_printer.id
    }

    if (spool.value.project) {
      payload.project_id = spool.value.project.id
    }

    if (spool.value.nfc_tag_id && spool.value.nfc_tag_id.trim() !== '') {
      payload.nfc_tag_id = spool.value.nfc_tag_id.trim()
    }

    if (spool.value.price_paid) {
      payload.price_paid = spool.value.price_paid
    }

    await axios.post(`/api/filament-spools/`, payload)
    router.push('/filaments')
  } catch (error) {
    console.error('Failed to save spool:', error)
    if (error.response?.data) {
      alert(`Error: ${JSON.stringify(error.response.data)}`)
    }
  }
}

const addLocation = (searchTerm) => {
  if (searchTerm) {
    const newLocation = { id: null, name: searchTerm }
    locations.value.push(newLocation)
    spool.value.location = newLocation
  }
}

const addBrand = (searchTerm) => {
  if (searchTerm) {
    const newBrand = { id: null, name: searchTerm }
    brands.value.push(newBrand)
    spool.value.standalone_brand = newBrand
  }
}

// Quick Add multi-color functions
const addQuickAddColor = () => {
  spool.value.standalone_colors.push('#000000')
}

const removeQuickAddColor = (index) => {
  // Multi-color mode requires at least 2 colors (index 0 and 1)
  if (spool.value.standalone_colors.length > 2 && index >= 2) {
    spool.value.standalone_colors.splice(index, 1)
  }
}

// Watch color mode to adjust colors array
watch(quickAddColorMode, (newMode) => {
  if (newMode === 'single' && spool.value.standalone_colors.length > 1) {
    spool.value.standalone_colors = [spool.value.standalone_colors[0]]
  } else if (newMode === 'multi' && spool.value.standalone_colors.length === 1) {
    spool.value.standalone_colors.push('#000000')
  }
})

const showWeightFields = computed(() => spool.value.is_opened)

// Make location and printer mutually exclusive
watch(
  () => spool.value.location,
  (newLocation) => {
    if (newLocation && spool.value.assigned_printer) {
      spool.value.assigned_printer = null
    }
  },
)

watch(
  () => spool.value.assigned_printer,
  (newPrinter) => {
    if (newPrinter && spool.value.location) {
      spool.value.location = null
    }
  },
)

// Auto-populate initial weight from blueprint when filament type is selected and spool is opened
watch(
  () => spool.value.filament_type,
  (newMaterial) => {
    if (newMaterial && spool.value.is_opened && newMaterial.spool_weight) {
      spool.value.initial_weight = newMaterial.spool_weight
    }
  },
)

// Also watch is_opened to pre-populate weight when checkbox is checked
watch(
  () => spool.value.is_opened,
  (isOpened) => {
    if (isOpened && spool.value.filament_type?.spool_weight) {
      spool.value.initial_weight = spool.value.filament_type.spool_weight
    }
  },
)

onMounted(() => {
  loadOptions()
})
</script>

<template>
  <div>
    <MainHeader
      title="Add New Filament Spool"
      :showSearch="false"
      :showAddButton="false"
      :showFilterButton="false"
      :showColumnButton="false"
    />

    <form @submit.prevent="saveSpool" class="spool-form">
      <!-- Mode Toggle -->
      <div class="form-section">
        <h2>Creation Mode</h2>
        <div class="mode-toggle">
          <label class="mode-option" :class="{ active: createMode === 'blueprint' }">
            <input type="radio" value="blueprint" v-model="createMode" />
            <span class="mode-label">From Blueprint</span>
            <span class="mode-desc">Select an existing material blueprint</span>
          </label>
          <label class="mode-option" :class="{ active: createMode === 'quickadd' }">
            <input type="radio" value="quickadd" v-model="createMode" />
            <span class="mode-label">Quick Add</span>
            <span class="mode-desc">One-off spool without a blueprint</span>
          </label>
        </div>
      </div>

      <!-- Blueprint Mode: Filament Type Selection -->
      <div v-if="createMode === 'blueprint'" class="form-section">
        <h2>Filament Type</h2>
        <div class="form-group">
          <label for="material">Material Blueprint *</label>
          <Multiselect
            id="material"
            v-model="spool.filament_type"
            :options="materialBlueprints"
            :custom-label="formatMaterialLabel"
            track-by="id"
            placeholder="Type to search materials..."
            :allow-empty="false"
            :searchable="true"
            :taggable="false"
          />
          <p class="help-text">
            Only brand-specific materials are shown.
            <RouterLink to="/filaments/materials/create">Create a blueprint</RouterLink> if needed.
          </p>
        </div>
      </div>

      <!-- Quick Add Mode: Direct Entry Fields -->
      <div v-if="createMode === 'quickadd'" class="form-section">
        <h2>Spool Information</h2>
        <div class="form-group">
          <label for="standalone-name">Name *</label>
          <input
            type="text"
            id="standalone-name"
            v-model="spool.standalone_name"
            required
            placeholder="e.g., Convention Metallic Blue"
          />
        </div>

        <div class="form-group">
          <label for="standalone-brand">Brand</label>
          <Multiselect
            v-model="spool.standalone_brand"
            :options="brands"
            label="name"
            track-by="id"
            placeholder="Select or type to add brand"
            :taggable="true"
            @tag="addBrand"
          />
        </div>

        <div class="form-group">
          <label for="standalone-material">Material Type *</label>
          <Multiselect
            v-model="spool.standalone_material_type"
            :options="genericMaterials"
            label="name"
            track-by="id"
            placeholder="Select material type (PLA, PETG, etc.)"
          />
        </div>

        <!-- Color Type Toggle -->
        <div class="form-group">
          <label>Color Type</label>
          <div class="color-mode-toggle">
            <label>
              <input type="radio" v-model="quickAddColorMode" value="single" />
              Single Color
            </label>
            <label>
              <input type="radio" v-model="quickAddColorMode" value="multi" />
              Multi-Color (Gradient/Blend)
            </label>
          </div>
        </div>

        <!-- Color entries (supports multiple colors) -->
        <div v-for="(colorHex, index) in spool.standalone_colors" :key="index" class="color-entry">
          <div class="color-entry-header">
            <h3>Color {{ index + 1 }}</h3>
            <button
              v-if="index >= 2"
              type="button"
              @click="removeQuickAddColor(index)"
              class="btn-remove-color"
            >
              Remove
            </button>
          </div>
          <div class="form-group">
            <div class="color-picker-group">
              <input
                type="color"
                :id="`standalone-color-${index}`"
                v-model="spool.standalone_colors[index]"
                class="color-picker"
              />
              <input
                type="text"
                v-model="spool.standalone_colors[index]"
                placeholder="#000000"
                class="color-input"
              />
            </div>
          </div>
        </div>

        <button
          v-if="quickAddColorMode === 'multi'"
          type="button"
          @click="addQuickAddColor"
          class="btn btn-secondary"
        >
          + Add Another Color
        </button>

        <div class="form-group">
          <label for="standalone-color-family">Color Family</label>
          <select id="standalone-color-family" v-model="spool.standalone_color_family">
            <option :value="null">-- Select --</option>
            <option v-for="opt in colorFamilyOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label for="standalone-weight">Spool Weight (grams)</label>
          <input
            type="number"
            id="standalone-weight"
            v-model.number="spool.initial_weight"
            placeholder="1000"
          />
          <p class="help-text">Default: 1000g (1kg spool)</p>
        </div>

        <div class="form-group">
          <label for="standalone-price-paid">Price Paid ($)</label>
          <input
            type="number"
            id="standalone-price-paid"
            v-model.number="spool.price_paid"
            min="0"
            step="0.01"
            placeholder="e.g., 19.99"
          />
          <p class="help-text">Actual price paid for this spool (optional).</p>
        </div>
      </div>

      <!-- Quick Add: Optional Print Settings -->
      <div v-if="createMode === 'quickadd'" class="form-section collapsible">
        <details>
          <summary><h2>Print Settings (Optional)</h2></summary>
          <div class="form-row">
            <div class="form-group">
              <label>Nozzle Temp Min (°C)</label>
              <input
                type="number"
                v-model.number="spool.standalone_nozzle_temp_min"
                placeholder="190"
              />
            </div>
            <div class="form-group">
              <label>Nozzle Temp Max (°C)</label>
              <input
                type="number"
                v-model.number="spool.standalone_nozzle_temp_max"
                placeholder="220"
              />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Bed Temp Min (°C)</label>
              <input
                type="number"
                v-model.number="spool.standalone_bed_temp_min"
                placeholder="50"
              />
            </div>
            <div class="form-group">
              <label>Bed Temp Max (°C)</label>
              <input
                type="number"
                v-model.number="spool.standalone_bed_temp_max"
                placeholder="60"
              />
            </div>
          </div>
          <div class="form-group">
            <label>Density (g/cm³)</label>
            <input
              type="number"
              step="0.01"
              v-model.number="spool.standalone_density"
              placeholder="1.24"
            />
          </div>
        </details>
      </div>

      <!-- Blueprint Info Box -->
      <div v-if="createMode === 'blueprint' && spool.filament_type" class="info-box">
        <div class="color-display">
          <div class="color-swatches">
            <div
              v-for="(colorHex, idx) in spool.filament_type.colors || []"
              :key="idx"
              class="color-swatch"
              :style="{ backgroundColor: colorHex || '#cccccc' }"
            ></div>
            <div
              v-if="!spool.filament_type.colors || spool.filament_type.colors.length === 0"
              class="color-swatch"
              style="background-color: #cccccc"
            ></div>
          </div>
          <div>
            <strong>{{ spool.filament_type.name || 'No material selected' }}</strong>
            <span
              v-if="spool.filament_type.colors && spool.filament_type.colors.length > 1"
              class="multi-color-badge"
            >
              ({{ spool.filament_type.colors.length }} colors)
            </span>
          </div>
        </div>
      </div>

      <div class="form-section">
        <h2>Quantity & Status</h2>
        <div class="form-group">
          <label>
            <input type="radio" :value="false" v-model="spool.is_opened" />
            Unopened Spool(s)
          </label>
          <label>
            <input type="radio" :value="true" v-model="spool.is_opened" />
            Opened Spool (Track by Weight)
          </label>
        </div>

        <div v-if="!showWeightFields" class="form-group">
          <label for="quantity">Quantity (Unopened Spools)</label>
          <input type="number" id="quantity" v-model.number="spool.quantity" min="1" required />
        </div>

        <div v-if="showWeightFields" class="form-group">
          <label for="initial-weight">Initial Weight (grams) *</label>
          <input
            type="number"
            id="initial-weight"
            v-model.number="spool.initial_weight"
            required
            placeholder="e.g., 1000"
          />
        </div>

        <div v-if="showWeightFields" class="form-group">
          <label for="current-weight">Current Weight (grams)</label>
          <input
            type="number"
            id="current-weight"
            v-model.number="spool.current_weight"
            placeholder="Leave blank to use initial weight"
          />
          <p class="help-text">If not specified, will be set to initial weight.</p>
        </div>

        <div class="form-group">
          <label for="price-paid">Price Paid ($)</label>
          <input
            type="number"
            id="price-paid"
            v-model.number="spool.price_paid"
            min="0"
            step="0.01"
            placeholder="e.g., 19.99"
          />
          <p class="help-text">Actual price paid for this spool (optional).</p>
        </div>
      </div>

      <div class="form-section">
        <h2>Location & Assignment</h2>
        <p class="help-text" style="margin-bottom: 1rem">
          Filament is either stored in a location OR assigned to a printer (not both).
        </p>

        <div class="form-group">
          <label for="location">Storage Location</label>
          <Multiselect
            v-model="spool.location"
            :options="locations"
            label="name"
            track-by="id"
            placeholder="Select or type to add new location"
            :taggable="true"
            @tag="addLocation"
          />
        </div>

        <div class="form-group">
          <label for="printer">Assigned Printer</label>
          <Multiselect
            v-model="spool.assigned_printer"
            :options="printers"
            label="title"
            track-by="id"
            placeholder="Select printer or leave empty"
            :allow-empty="true"
          />
        </div>

        <div class="form-group">
          <label for="project">Associated Project</label>
          <Multiselect
            v-model="spool.project"
            :options="projects"
            label="project_name"
            track-by="id"
            placeholder="Select project or leave empty"
            :allow-empty="true"
          />
        </div>
      </div>

      <div class="form-section">
        <h2>Additional Details</h2>
        <div class="form-group">
          <label for="nfc-tag">NFC Tag ID</label>
          <input
            type="text"
            id="nfc-tag"
            v-model="spool.nfc_tag_id"
            placeholder="Optional unique identifier"
          />
        </div>

        <div class="form-group">
          <label for="notes">Notes</label>
          <textarea
            id="notes"
            v-model="spool.notes"
            rows="4"
            placeholder="Any additional notes about this spool..."
          ></textarea>
        </div>
      </div>

      <div class="form-actions">
        <button type="button" @click="router.push('/filaments')" class="btn-cancel">Cancel</button>
        <button type="submit" class="btn-save">Save Spool</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.spool-form {
  max-width: 800px;
  margin: 0 auto;
}

.form-section {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.form-section h2 {
  margin: 0 0 1rem 0;
  font-size: 1.25rem;
  color: var(--color-heading);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5rem;
}

.form-group {
  margin-bottom: 1.25rem;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--color-text);
}

.form-group input[type='text'],
.form-group input[type='number'],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.form-group input[type='radio'] {
  margin-right: 0.5rem;
}

.info-box {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.color-display {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.color-swatches {
  display: flex;
  gap: 0.25rem;
}

.color-swatch {
  width: 50px;
  height: 50px;
  border: 2px solid var(--color-border);
  border-radius: 8px;
}

.multi-color-badge {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-style: italic;
  margin-left: 0.5rem;
}

.color-picker-group {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.color-picker {
  width: 60px;
  height: 45px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  cursor: pointer;
}

.color-input {
  flex: 1;
}

.help-text {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.help-text a {
  color: var(--color-blue);
  text-decoration: underline;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.btn-cancel,
.btn-save {
  padding: 0.75rem 1.5rem;
  border-radius: 5px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-cancel {
  background: none;
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.btn-cancel:hover {
  border-color: var(--color-border-hover);
  background-color: var(--color-background-mute);
}

.btn-save {
  background-color: var(--color-blue);
  color: white;
  border: 1px solid var(--color-blue);
}

.btn-save:hover {
  background-color: #0b5ed7;
}

/* Mode Toggle Styles */
.mode-toggle {
  display: flex;
  gap: 1rem;
}

.mode-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1rem;
  border: 2px solid var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: var(--color-background);
}

.mode-option:hover {
  border-color: var(--color-border-hover);
}

.mode-option.active {
  border-color: var(--color-blue);
  background-color: var(--color-background-soft);
}

.mode-option input[type='radio'] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.mode-label {
  font-weight: 600;
  color: var(--color-heading);
  margin-bottom: 0.25rem;
}

.mode-desc {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

/* Form Row for side-by-side fields */
.form-row {
  display: flex;
  gap: 1rem;
}

.form-row .form-group {
  flex: 1;
}

/* Collapsible section */
.form-section.collapsible {
  padding: 0;
}

.form-section.collapsible details {
  padding: 1.5rem;
}

.form-section.collapsible summary {
  cursor: pointer;
  list-style: none;
}

.form-section.collapsible summary::-webkit-details-marker {
  display: none;
}

.form-section.collapsible summary h2 {
  display: inline;
  margin: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.form-section.collapsible summary h2::before {
  content: '▸ ';
}

.form-section.collapsible details[open] summary h2::before {
  content: '▾ ';
}

.muted {
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

/* Multi-color support */
.color-mode-toggle {
  display: flex;
  gap: 1.5rem;
}

.color-mode-toggle label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.color-entry {
  background-color: var(--color-background-mute);
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  border: 1px solid var(--color-border);
}

.color-entry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.color-entry-header h3 {
  margin: 0;
  font-size: 1rem;
  color: var(--color-heading);
}

.btn-remove-color {
  padding: 0.25rem 0.75rem;
  background-color: var(--color-red);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-remove-color:hover {
  background-color: #c82333;
}

.btn-secondary {
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.btn-secondary:hover {
  background-color: var(--color-background-soft);
  border-color: var(--color-border-hover);
}

/* Responsive */
@media (max-width: 600px) {
  .mode-toggle {
    flex-direction: column;
  }

  .form-row {
    flex-direction: column;
  }
}
</style>
