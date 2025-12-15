<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import Multiselect from 'vue-multiselect'
import BaseModal from '@/components/BaseModal.vue'
import 'vue-multiselect/dist/vue-multiselect.css'

const router = useRouter()
const route = useRoute()
const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const spool = ref({
  filament_type: null,
  quantity: 0,
  is_opened: false,
  initial_weight: null,
  current_weight: null,
  price_paid: null,
  location: null,
  assigned_printer: null,
  project: null,
  notes: '',
  nfc_tag_id: '',
})

// Track original status to detect changes for split logic
const originalStatus = ref(null)
const originalQuantity = ref(0)

// Split spool modal
const showSplitModal = ref(false)
const splitSpools = ref([]) // Array of spools in the modal for user to configure

// Initialize split spools when modal opens
const initSplitSpools = () => {
  splitSpools.value = []
  for (let i = 0; i < originalQuantity.value; i++) {
    splitSpools.value.push({
      index: i + 1,
      status: 'new', // Default to unopened
      placement: '', // Combined location/printer as "location:id" or "printer:id"
    })
  }
}

// Handle placement dropdown change - parse the combined value
const handlePlacementChange = () => {
  // placement is already bound via v-model, no extra handling needed
  // The value is stored as "location:id" or "printer:id"
}

const materialBlueprints = ref([])
const locations = ref([])
const printers = ref([])
const projects = ref([])
const isLoading = ref(true)

const loadSpool = async () => {
  try {
    const response = await axios.get(`/api/filament-spools/${route.params.id}/`)
    spool.value = response.data
    // Store original values for split detection
    originalStatus.value = response.data.status
    originalQuantity.value = response.data.quantity
  } catch (error) {
    console.error('Failed to load spool:', error)
  } finally {
    isLoading.value = false
  }
}

const loadOptions = async () => {
  try {
    const [materialsRes, locationsRes, printersRes, projectsRes] = await Promise.all([
      axios.get(`/api/materials/?type=blueprint`),
      axios.get(`/api/locations/`),
      axios.get(`/api/printers/`),
      axios.get(`/api/projects/`),
    ])
    materialBlueprints.value = materialsRes.data.results || materialsRes.data
    locations.value = locationsRes.data.results || locationsRes.data
    printers.value = printersRes.data.results || printersRes.data
    projects.value = projectsRes.data.results || projectsRes.data
  } catch (error) {
    console.error('Failed to load options:', error)
  }
}

// Load additional options for Quick Add spools
const genericMaterials = ref([])
const brands = ref([])

const loadQuickAddOptions = async () => {
  try {
    const [genericsRes, brandsRes] = await Promise.all([
      axios.get(`/api/materials/?type=generic`),
      axios.get(`/api/brands/`),
    ])
    genericMaterials.value = genericsRes.data.results || genericsRes.data
    brands.value = brandsRes.data.results || brandsRes.data
  } catch (error) {
    console.error('Failed to load Quick Add options:', error)
  }
}

// Quick Add color mode
const quickAddColorMode = ref('single')

// Watch for Quick Add spool to set color mode
watch(
  () => spool.value.standalone_colors,
  (colors) => {
    if (colors && colors.length > 1) {
      quickAddColorMode.value = 'multi'
    } else {
      quickAddColorMode.value = 'single'
    }
  },
  { immediate: true },
)

// Multi-color functions for Quick Add
const addQuickAddColor = () => {
  if (!spool.value.standalone_colors) {
    spool.value.standalone_colors = ['#000000']
  }
  spool.value.standalone_colors.push('#000000')
}

const removeQuickAddColor = (index) => {
  if (spool.value.standalone_colors.length > 2 && index >= 2) {
    spool.value.standalone_colors.splice(index, 1)
  }
}

// Watch color mode to adjust colors array
watch(quickAddColorMode, (newMode) => {
  if (!spool.value.standalone_colors) {
    spool.value.standalone_colors = ['#000000']
  }
  if (newMode === 'single' && spool.value.standalone_colors.length > 1) {
    spool.value.standalone_colors = [spool.value.standalone_colors[0]]
  } else if (newMode === 'multi' && spool.value.standalone_colors.length === 1) {
    spool.value.standalone_colors.push('#000000')
  }
})

const addBrand = (searchTerm) => {
  if (searchTerm) {
    const newBrand = { id: null, name: searchTerm }
    brands.value.push(newBrand)
    spool.value.standalone_brand = newBrand
  }
}

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

// Check if this is a split scenario (opening one spool from a batch)
const isBatchSpool = computed(() => {
  return originalStatus.value === 'new' && originalQuantity.value > 1
})

// Watch for status changes to trigger split modal
watch(
  () => spool.value.status,
  (newStatus) => {
    // Only trigger if:
    // 1. This is a batch (original status was 'new' and quantity > 1)
    // 2. User is changing to an "opened" status
    const openedStatuses = ['opened', 'in_use', 'low']
    if (isBatchSpool.value && openedStatuses.includes(newStatus) && !showSplitModal.value) {
      console.log('Status changed to opened on batch - showing split modal')
      initSplitSpools()
      showSplitModal.value = true
    }
  },
)

// Computed to count how many spools are being opened
const openedSpoolCount = computed(() => {
  return splitSpools.value.filter((s) => s.status !== 'new').length
})

// Computed to count remaining unopened
const remainingUnopenedCount = computed(() => {
  return splitSpools.value.filter((s) => s.status === 'new').length
})

const saveSpool = async () => {
  try {
    const isQuickAdd = spool.value.is_quick_add

    const payload = {
      quantity: spool.value.is_opened ? 0 : spool.value.quantity,
      is_opened: spool.value.is_opened,
      status: spool.value.status,
      notes: spool.value.notes || '',
    }

    if (isQuickAdd) {
      // Quick Add mode - update standalone fields
      payload.standalone_name = spool.value.standalone_name
      payload.standalone_colors = spool.value.standalone_colors
      payload.standalone_color_family = spool.value.standalone_color_family
      payload.standalone_material_type_id = spool.value.standalone_material_type?.id

      // Handle brand
      if (spool.value.standalone_brand) {
        const brandName =
          typeof spool.value.standalone_brand === 'object'
            ? spool.value.standalone_brand.name
            : spool.value.standalone_brand
        payload.standalone_brand = JSON.stringify({ name: brandName })
      }

      // Handle print settings
      payload.standalone_nozzle_temp_min = spool.value.standalone_nozzle_temp_min
      payload.standalone_nozzle_temp_max = spool.value.standalone_nozzle_temp_max
      payload.standalone_bed_temp_min = spool.value.standalone_bed_temp_min
      payload.standalone_bed_temp_max = spool.value.standalone_bed_temp_max
      payload.standalone_density = spool.value.standalone_density
    } else {
      // Blueprint mode
      payload.filament_type_id = spool.value.filament_type?.id
    }

    if (spool.value.is_opened) {
      payload.initial_weight = spool.value.initial_weight
      payload.current_weight = spool.value.current_weight
    }

    // Always send price_paid (even if null to clear it)
    payload.price_paid = spool.value.price_paid || null

    // Always send location_id (even if null to clear it)
    payload.location_id = spool.value.location?.id || null

    // Always send assigned_printer_id (even if null to clear it)
    payload.assigned_printer_id = spool.value.assigned_printer?.id || null

    // Always send project_id (even if null to clear it)
    payload.project_id = spool.value.project?.id || null

    if (spool.value.nfc_tag_id) {
      payload.nfc_tag_id = spool.value.nfc_tag_id
    }

    await axios.patch(`/api/filament-spools/${route.params.id}/`, payload)
    router.push(`/filaments/${route.params.id}`)
  } catch (error) {
    console.error('Failed to save spool:', error)
    if (error.response?.data) {
      alert(`Error: ${JSON.stringify(error.response.data)}`)
    }
  }
}

const deleteSpool = async () => {
  const name = spool.value.is_quick_add
    ? spool.value.standalone_name
    : spool.value.filament_type?.name || 'this spool'

  if (
    !confirm(
      `Are you sure you want to delete this spool?\n\n"${name}"\n\nThis action cannot be undone.`,
    )
  ) {
    return
  }

  try {
    await axios.delete(`/api/filament-spools/${route.params.id}/`)
    router.push('/filaments')
  } catch (error) {
    console.error('Failed to delete spool:', error)
    alert('Failed to delete spool. Please try again.')
  }
}

// Handle split modal confirmation - process the split
const handleSplitConfirm = async () => {
  const spoolsToOpen = splitSpools.value.filter((s) => s.status !== 'new')

  // If no spools are being opened, just close the modal and reset status
  if (spoolsToOpen.length === 0) {
    console.log('No spools marked as opened - cancelling')
    handleSplitCancel()
    return
  }

  console.log('Processing split:', spoolsToOpen.length, 'spools to open')

  try {
    // Parse placement field into location_id or printer_id
    const parsePlacement = (placement) => {
      if (!placement) return { location_id: null, printer_id: null }
      const [type, id] = placement.split(':')
      if (type === 'location') return { location_id: parseInt(id), printer_id: null }
      if (type === 'printer') return { location_id: null, printer_id: parseInt(id) }
      return { location_id: null, printer_id: null }
    }

    // Call the split API with the list of spools to open
    const response = await axios.post(`/api/filament-spools/${route.params.id}/open-spool/`, {
      spools_to_open: spoolsToOpen.map((s) => ({
        status: s.status,
        ...parsePlacement(s.placement),
      })),
    })

    console.log('Split response:', response.data)
    showSplitModal.value = false

    // Navigate to spools list to see results
    router.push('/filaments?tab=spools')
  } catch (error) {
    console.error('Failed to split spool:', error)
    alert(`Error: ${error.response?.data?.error || 'Failed to split spools'}`)
  }
}

// Handle split modal cancel - user doesn't want to open any spools
const handleSplitCancel = () => {
  console.log('User cancelled - resetting status to new')
  showSplitModal.value = false
  // Reset status back to "new" (unopened)
  spool.value.status = 'new'
}

const addLocation = async (searchTerm) => {
  if (searchTerm) {
    try {
      // Create location on backend using APIService
      const response = await axios.post('/api/locations/', { name: searchTerm })
      const newLocation = response.data
      locations.value.push(newLocation)
      spool.value.location = newLocation
      console.log('Location created successfully:', newLocation)
    } catch (error) {
      console.error('Failed to create location:', error)
      alert('Failed to create new location. Please try again.')
    }
  }
}

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

// Computed for display name (handles both Quick Add and Blueprint)
const spoolName = computed(() => {
  if (!spool.value) return 'Spool'
  return spool.value.is_quick_add
    ? spool.value.standalone_name
    : spool.value.filament_type?.name || 'Unknown Material'
})

onMounted(async () => {
  await loadOptions()
  await loadQuickAddOptions()
  await loadSpool()
})
</script>

<template>
  <div class="page-container">
    <div v-if="isLoading" class="loading">Loading...</div>

    <div v-else class="content-container">
      <div class="detail-header">
        <h1>Edit Spool</h1>
        <div class="actions">
          <button type="button" @click="deleteSpool" class="btn btn-danger">Delete</button>
        </div>
      </div>

      <form @submit.prevent="saveSpool" class="spool-form">
        <!-- Quick Add Spool Fields -->
        <template v-if="spool.is_quick_add">
          <div class="form-section">
            <h2>Spool Details</h2>
            <span class="quick-add-badge">Quick Add Spool</span>

            <div class="form-group">
              <label for="standalone-name">Spool Name *</label>
              <input
                type="text"
                id="standalone-name"
                v-model="spool.standalone_name"
                placeholder="e.g., Coral Weave, Sunset Silk"
                required
              />
              <p class="help-text">Descriptive name for this spool.</p>
            </div>

            <div class="form-group">
              <label for="standalone-brand">Brand</label>
              <Multiselect
                v-model="spool.standalone_brand"
                :options="brands"
                label="name"
                track-by="id"
                placeholder="Select or create brand"
                :taggable="true"
                @tag="addBrand"
                tag-placeholder="Press enter to create new brand"
              />
            </div>

            <div class="form-group">
              <label for="standalone-material">Material Type</label>
              <Multiselect
                v-model="spool.standalone_material_type"
                :options="genericMaterials"
                label="name"
                track-by="id"
                placeholder="Select material type (PLA, PETG, etc.)"
              />
            </div>
          </div>

          <div class="form-section">
            <h2>Color</h2>

            <div class="form-group">
              <label>Color Mode</label>
              <div class="color-mode-toggle">
                <button
                  type="button"
                  :class="['mode-btn', { active: quickAddColorMode === 'single' }]"
                  @click="quickAddColorMode = 'single'"
                >
                  Single Color
                </button>
                <button
                  type="button"
                  :class="['mode-btn', { active: quickAddColorMode === 'multi' }]"
                  @click="quickAddColorMode = 'multi'"
                >
                  Multi-Color
                </button>
              </div>
            </div>

            <div class="form-group" v-if="quickAddColorMode === 'single'">
              <label for="standalone-color">Color</label>
              <div class="color-picker-row">
                <input
                  type="color"
                  id="standalone-color"
                  :value="spool.standalone_colors?.[0] || '#000000'"
                  @input="spool.standalone_colors = [$event.target.value]"
                />
                <span class="color-hex">{{ spool.standalone_colors?.[0] || '#000000' }}</span>
              </div>
            </div>

            <div class="form-group" v-if="quickAddColorMode === 'multi'">
              <label>Colors</label>
              <div class="multi-color-container">
                <div
                  v-for="(color, idx) in spool.standalone_colors"
                  :key="idx"
                  class="color-picker-row"
                >
                  <input
                    type="color"
                    :value="color"
                    @input="spool.standalone_colors[idx] = $event.target.value"
                  />
                  <span class="color-hex">{{ color }}</span>
                  <button
                    v-if="idx >= 2"
                    type="button"
                    class="btn btn-danger btn-sm"
                    @click="removeQuickAddColor(idx)"
                  >
                    ×
                  </button>
                </div>
                <button type="button" class="btn btn-secondary btn-sm" @click="addQuickAddColor">
                  + Add Color
                </button>
              </div>
            </div>

            <div class="form-group">
              <label for="standalone-color-family">Color Family</label>
              <select id="standalone-color-family" v-model="spool.standalone_color_family">
                <option value="">-- Select Color Family --</option>
                <option v-for="opt in colorFamilyOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
              <p class="help-text">Used for filtering and organization.</p>
            </div>
          </div>
        </template>

        <!-- Blueprint Spool Fields -->
        <template v-else>
          <div class="form-section">
            <h2>Filament Type</h2>
            <div class="form-group">
              <label for="material">Material Blueprint</label>
              <Multiselect
                v-model="spool.filament_type"
                :options="materialBlueprints"
                label="name"
                track-by="id"
                placeholder="Select material blueprint"
                :custom-label="(opt) => `${opt.brand?.name || ''} ${opt.name} (${opt.diameter}mm)`"
              />
              <p class="help-text">Select the correct material blueprint for this spool.</p>
            </div>
          </div>

          <div class="form-section">
            <h2>Color</h2>
            <div v-if="spool.filament_type" class="info-box">
              <router-link
                :to="`/filaments/materials/${spool.filament_type.id}/edit`"
                class="color-display clickable-link"
              >
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
                <div class="color-info">
                  <strong>{{ spool.filament_type.name || 'Unknown' }}</strong>
                  <span
                    v-if="spool.filament_type.colors && spool.filament_type.colors.length > 1"
                    class="multi-color-badge"
                  >
                    ({{ spool.filament_type.colors.length }} colors)
                  </span>
                  <p class="note">Click to view or edit this material blueprint.</p>
                </div>
              </router-link>
            </div>
          </div>
        </template>

        <div class="form-section">
          <h2>Quantity & Status</h2>
          <div class="form-group">
            <label for="status">Status</label>
            <select id="status" v-model="spool.status" required>
              <option value="new">New (Unopened)</option>
              <option value="opened">Opened</option>
              <option value="in_use">In Use</option>
              <option value="low">Low</option>
              <option value="empty">Empty</option>
              <option value="archived">Archived</option>
            </select>
            <p class="help-text">Update status as needed to track filament lifecycle.</p>
          </div>

          <div v-if="!showWeightFields" class="form-group">
            <label for="quantity">Quantity (Unopened Spools)</label>
            <input type="number" id="quantity" v-model.number="spool.quantity" min="0" required />
          </div>

          <div v-if="showWeightFields">
            <div class="form-group">
              <label for="initial-weight">Initial Weight (grams)</label>
              <input
                type="number"
                id="initial-weight"
                v-model.number="spool.initial_weight"
                min="1"
                required
              />
              <p class="help-text">Update this if the initial weight was entered incorrectly.</p>
            </div>

            <div class="form-group">
              <label for="current-weight">Current Weight (grams) *</label>
              <input
                type="number"
                id="current-weight"
                v-model.number="spool.current_weight"
                required
              />
              <p class="help-text">
                Update this as you use the filament. Status will auto-update based on weight.
              </p>
            </div>
          </div>

          <div class="form-group" style="margin-top: 1.5rem">
            <label for="price-paid">Price Paid ($)</label>
            <input
              type="number"
              id="price-paid"
              v-model.number="spool.price_paid"
              min="0"
              step="0.01"
              placeholder="e.g., 19.99"
            />
            <p class="help-text">
              Actual price paid for this spool (optional). Used for inventory value calculations.
            </p>
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
            <input type="text" id="nfc-tag" v-model="spool.nfc_tag_id" />
          </div>

          <div class="form-group">
            <label for="notes">Notes</label>
            <textarea id="notes" v-model="spool.notes" rows="4"></textarea>
          </div>
        </div>

        <div class="form-actions">
          <button
            type="button"
            @click="router.push(`/filaments/${route.params.id}`)"
            class="btn btn-secondary"
          >
            Cancel
          </button>
          <button type="submit" class="btn btn-primary">Save Changes</button>
        </div>
      </form>
    </div>

    <!-- Split Spool Modal -->
    <BaseModal :show="showSplitModal" title="Manage Spools in Batch" @close="handleSplitCancel">
      <div class="split-modal-content">
        <p class="split-description">
          You have <strong>{{ originalQuantity }} spools</strong> in this batch. Set the status and
          location/printer for each spool you want to open.
        </p>

        <div class="split-summary" v-if="openedSpoolCount > 0">
          <span class="badge badge-info">
            {{ openedSpoolCount }} spool(s) will be opened • {{ remainingUnopenedCount }} will
            remain unopened
          </span>
        </div>

        <table class="split-table">
          <thead>
            <tr>
              <th>Spool</th>
              <th>Status</th>
              <th>Location / Printer</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="splitSpool in splitSpools" :key="splitSpool.index">
              <td class="spool-number">#{{ splitSpool.index }}</td>
              <td>
                <select v-model="splitSpool.status" class="split-select">
                  <option value="new">Unopened</option>
                  <option value="opened">Opened</option>
                  <option value="in_use">In Use</option>
                </select>
              </td>
              <td>
                <div v-if="splitSpool.status !== 'new'" class="location-printer-group">
                  <select
                    v-model="splitSpool.placement"
                    class="placement-select"
                    @change="handlePlacementChange(splitSpool)"
                  >
                    <option value="">-- Select --</option>
                    <optgroup label="Locations">
                      <option
                        v-for="loc in locations"
                        :key="'loc-' + loc.id"
                        :value="'location:' + loc.id"
                      >
                        {{ loc.name }}
                      </option>
                    </optgroup>
                    <optgroup label="Printers">
                      <option
                        v-for="printer in printers"
                        :key="'printer-' + printer.id"
                        :value="'printer:' + printer.id"
                      >
                        {{ printer.title }}
                      </option>
                    </optgroup>
                  </select>
                </div>
                <span v-else class="not-applicable">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <template #footer>
        <button type="button" class="btn btn-secondary" @click="handleSplitCancel">Cancel</button>
        <button
          type="button"
          class="btn btn-primary"
          @click="handleSplitConfirm"
          :disabled="openedSpoolCount === 0"
        >
          {{
            openedSpoolCount === 0 ? 'Select spools to open' : `Open ${openedSpoolCount} Spool(s)`
          }}
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
/* Page layout matching InventoryDetailView */
.page-container {
  padding: 2rem;
}

.content-container {
  max-width: 1200px;
  margin: 0 auto;
}

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

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--color-text-muted);
}

.spool-form {
  max-width: 800px;
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

.info-box {
  padding: 1rem;
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 5px;
  margin-bottom: 1rem;
}

.info-box p {
  margin: 0 0 0.5rem 0;
  color: var(--color-text);
}

.info-box p:last-child {
  margin-bottom: 0;
}

.info-box .note {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.color-display {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.clickable-link {
  text-decoration: none;
  color: inherit;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem;
  margin: -0.5rem;
  border-radius: 5px;
  transition: background-color 0.2s ease;
}

.clickable-link:hover {
  background-color: var(--color-background-soft);
}

.clickable-link .note {
  color: var(--color-text-soft);
}

.color-swatches {
  display: flex;
  gap: 0.25rem;
}

.color-swatch {
  width: 50px;
  height: 50px;
  border-radius: 5px;
  border: 1px solid var(--color-border);
  flex-shrink: 0;
}

.multi-color-badge {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-style: italic;
  margin-left: 0.5rem;
}

.color-info {
  flex: 1;
}

.color-info strong {
  display: block;
  margin-bottom: 0.25rem;
  color: var(--color-text);
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

.form-group input[readonly] {
  background-color: var(--color-background-mute);
  cursor: not-allowed;
}

.form-group select[disabled] {
  background-color: var(--color-background-mute);
  cursor: not-allowed;
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
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

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

/* Quick Add styles */
.quick-add-badge {
  display: inline-block;
  background-color: var(--color-primary, #3b82f6);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 500;
  margin-bottom: 1rem;
}

.color-mode-toggle {
  display: flex;
  gap: 0.5rem;
}

.mode-btn {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  background-color: var(--color-background);
  color: var(--color-text);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn:hover {
  background-color: var(--color-background-soft);
}

.mode-btn.active {
  background-color: var(--color-primary, #3b82f6);
  color: white;
  border-color: var(--color-primary, #3b82f6);
}

.color-picker-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.color-picker-row input[type='color'] {
  width: 50px;
  height: 40px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  cursor: pointer;
  padding: 2px;
}

.color-hex {
  font-family: monospace;
  font-size: 0.9rem;
  color: var(--color-text-muted);
  min-width: 70px;
}

.multi-color-container {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;
}

/* Split Modal Styles */
.split-modal-content {
  padding: 0.5rem 0;
}

.split-description {
  margin-bottom: 1rem;
  color: var(--color-text);
  line-height: 1.5;
}

.split-summary {
  margin-bottom: 1rem;
}

.badge {
  display: inline-block;
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 500;
}

.badge-info {
  background-color: rgba(59, 130, 246, 0.15);
  color: var(--color-primary, #3b82f6);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.split-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}

.split-table th,
.split-table td {
  padding: 0.75rem 0.5rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.split-table th {
  font-weight: 600;
  color: var(--color-heading);
  background-color: var(--color-background-soft);
  white-space: nowrap;
}

.split-table th:first-child {
  width: 60px;
}

.split-table th:nth-child(2) {
  width: 120px;
}

.split-table tbody tr:hover {
  background-color: var(--color-background-soft);
}

.spool-number {
  font-weight: 600;
  color: var(--color-text-muted);
}

.split-select {
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
  width: 110px;
}

.location-printer-group {
  display: flex;
  align-items: center;
}

.placement-select {
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.9rem;
  min-width: 200px;
  max-width: 100%;
}

.placement-select optgroup {
  font-weight: 600;
  color: var(--color-heading);
}

.not-applicable {
  color: var(--color-text-muted);
}

/* Make modal wider for the table */
:deep(.modal-content) {
  max-width: 700px;
  width: 90vw;
}
</style>
