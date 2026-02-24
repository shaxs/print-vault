<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import APIService from '@/services/APIService.js'
import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

const props = defineProps({
  initialData: { type: Object, default: null },
})

const router = useRouter()
const printer = ref({})
const isEditMode = ref(false)
const photoFile = ref(null)
const photoPreview = ref(null)
const brands = ref([])
const materialBlueprints = ref([])

// Filament mode toggles
const primaryFilamentMode = ref('custom') // 'custom' or 'blueprint'
const accentFilamentMode = ref('custom') // 'custom' or 'blueprint'
const additionalFilaments = ref([]) // Array of { type: '', mode: 'custom'/'blueprint', custom: '', blueprint: null }

watch(
  () => props.initialData,
  (newData) => {
    if (newData) {
      printer.value = { ...newData }
      isEditMode.value = true
      
      // Initialize filament modes based on existing data
      if (newData.primary_filament_blueprint) {
        primaryFilamentMode.value = 'blueprint'
      } else if (newData.primary_filament_custom) {
        primaryFilamentMode.value = 'custom'
      }
      
      if (newData.accent_filament_blueprint) {
        accentFilamentMode.value = 'blueprint'
      } else if (newData.accent_filament_custom) {
        accentFilamentMode.value = 'custom'
      }
      
      // Load additional filaments if they exist
      if (newData.additional_filaments && newData.additional_filaments.length > 0) {
        additionalFilaments.value = newData.additional_filaments.map(f => ({
          type: f.type || '',
          mode: f.blueprint_id ? 'blueprint' : 'custom',
          custom: f.custom || '',
          blueprint: f.blueprint_id ? materialBlueprints.value.find(m => m.id === f.blueprint_id) : null
        }))
      }
    } else {
      printer.value = {
        title: '',
        manufacturer: null,
        serial_number: '',
        purchase_date: null,
        status: 'Active',
        notes: '',
        build_size_x: null,
        build_size_y: null,
        build_size_z: null,
        purchase_price: null,
        primary_filament_custom: '',
        primary_filament_blueprint: null,
        accent_filament_custom: '',
        accent_filament_blueprint: null,
      }
      isEditMode.value = false
      additionalFilaments.value = []
    }
  },
  { immediate: true },
)

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    photoFile.value = file
    photoPreview.value = URL.createObjectURL(file)
  }
}

const savePrinter = async () => {
  const formData = new FormData()
  const fieldsToAppend = [
    'title',
    'serial_number',
    'purchase_date',
    'status',
    'notes',
    'build_size_x',
    'build_size_y',
    'build_size_z',
    'purchase_price',
  ]
  fieldsToAppend.forEach((key) => {
    if (
      printer.value[key] !== null &&
      printer.value[key] !== undefined &&
      printer.value[key] !== ''
    ) {
      formData.append(key, printer.value[key])
    }
  })

  const brandValue = printer.value.manufacturer
  if (brandValue) {
    const brandName =
      typeof brandValue === 'object' && brandValue !== null ? brandValue.name : brandValue
    formData.append('manufacturer', JSON.stringify({ name: brandName }))
  } else if (isEditMode.value && brandValue === null) {
    formData.append('manufacturer', JSON.stringify(null))
  }
  
  // Handle filament fields
  if (primaryFilamentMode.value === 'custom' && printer.value.primary_filament_custom) {
    formData.append('primary_filament_custom', printer.value.primary_filament_custom)
    formData.append('primary_filament_blueprint_id', '')
  } else if (primaryFilamentMode.value === 'blueprint' && printer.value.primary_filament_blueprint) {
    formData.append('primary_filament_blueprint_id', printer.value.primary_filament_blueprint.id)
    formData.append('primary_filament_custom', '')
  } else {
    formData.append('primary_filament_custom', '')
    formData.append('primary_filament_blueprint_id', '')
  }
  
  if (accentFilamentMode.value === 'custom' && printer.value.accent_filament_custom) {
    formData.append('accent_filament_custom', printer.value.accent_filament_custom)
    formData.append('accent_filament_blueprint_id', '')
  } else if (accentFilamentMode.value === 'blueprint' && printer.value.accent_filament_blueprint) {
    formData.append('accent_filament_blueprint_id', printer.value.accent_filament_blueprint.id)
    formData.append('accent_filament_custom', '')
  } else {
    formData.append('accent_filament_custom', '')
    formData.append('accent_filament_blueprint_id', '')
  }
  
  // Handle additional filaments - convert to JSON format
  const additionalFilamentsData = additionalFilaments.value.map(f => ({
    type: f.type,
    custom: f.mode === 'custom' ? f.custom : '',
    blueprint_id: f.mode === 'blueprint' && f.blueprint ? f.blueprint.id : null
  }))
  formData.append('additional_filaments', JSON.stringify(additionalFilamentsData))

  if (photoFile.value) {
    formData.append('photo', photoFile.value)
  }

  try {
    let savedPrinter
    if (isEditMode.value) {
      savedPrinter = await APIService.updatePrinter(printer.value.id, formData)
    } else {
      savedPrinter = await APIService.createPrinter(formData)
    }
    router.push(`/printers/${savedPrinter.data.id}`)
  } catch (error) {
    console.error('Error saving printer:', error)
  }
}

const addBrand = (newBrand) => {
  const brand = { name: newBrand }
  brands.value.push(brand)
  printer.value.manufacturer = brand
}

const addAdditionalFilament = () => {
  additionalFilaments.value.push({
    type: '',
    mode: 'custom',
    custom: '',
    blueprint: null
  })
}

const removeAdditionalFilament = (index) => {
  additionalFilaments.value.splice(index, 1)
}

const formatMaterialLabel = (mat) => {
  if (!mat) return ''
  const brandName = mat.brand?.name || ''
  const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
  return `${brandName} ${mat.name}${diameter}`.trim()
}

onMounted(async () => {
  try {
    const [brandsRes, materialsRes] = await Promise.all([
      APIService.getBrands(),
      APIService.getMaterials({ type: 'blueprint' })
    ])
    brands.value = brandsRes.data
    materialBlueprints.value = materialsRes.data.results || materialsRes.data
  } catch (error) {
    console.error('Error loading options:', error)
  }
})
</script>

<template>
  <form @submit.prevent="savePrinter" class="item-form">
    <div class="form-group">
      <label for="title">Title</label>
      <input id="title" v-model="printer.title" type="text" required />
    </div>

    <div class="form-group">
      <label for="manufacturer">Manufacturer (Brand)</label>
      <multiselect
        id="manufacturer"
        v-model="printer.manufacturer"
        :options="brands"
        label="name"
        track-by="name"
        placeholder="Select or type to add brand"
        :taggable="true"
        @tag="addBrand"
      ></multiselect>
    </div>

    <div class="form-group">
      <label for="serial_number">Serial Number</label>
      <input id="serial_number" v-model="printer.serial_number" type="text" />
    </div>

    <div class="form-group">
      <label for="purchase_price">Purchase Price</label>
      <input
        id="purchase_price"
        v-model.number="printer.purchase_price"
        type="number"
        step="0.01"
      />
    </div>

    <div class="form-group">
      <label for="purchase_date">Purchase Date</label>
      <input id="purchase_date" v-model="printer.purchase_date" type="date" />
    </div>

    <div class="form-group">
      <label for="status">Status</label>
      <select id="status" v-model="printer.status">
        <option>Active</option>
        <option>Under Repair</option>
        <option>Sold</option>
        <option>Archived</option>
        <option>Planned</option>
      </select>
    </div>

    <div class="form-group">
      <label>Build Volume (X, Y, Z in mm)</label>
      <div class="multi-input">
        <input v-model.number="printer.build_size_x" type="number" placeholder="X" />
        <input v-model.number="printer.build_size_y" type="number" placeholder="Y" />
        <input v-model.number="printer.build_size_z" type="number" placeholder="Z" />
      </div>
    </div>

    <div class="form-group">
      <label for="photo">Photo</label>
      <input id="photo" type="file" @change="handleFileUpload" accept="image/*" />
      <div v-if="photoPreview || (isEditMode && printer.photo)" class="photo-preview">
        <img :src="photoPreview || printer.photo" alt="Printer preview" />
      </div>
    </div>

    <!-- Primary Filament -->
      <div class="form-group">
        <label>Primary Color/Material</label>
        <div class="radio-group">
          <label class="radio-label">
            <input type="radio" v-model="primaryFilamentMode" value="custom" />
            Custom Entry
          </label>
          <label class="radio-label">
            <input type="radio" v-model="primaryFilamentMode" value="blueprint" />
            Select from Library
          </label>
        </div>
        
        <input 
          v-if="primaryFilamentMode === 'custom'"
          v-model="printer.primary_filament_custom"
          type="text"
          placeholder="e.g., Red PLA, Black PETG"
          class="filament-input"
        />
        
        <multiselect
          v-if="primaryFilamentMode === 'blueprint'"
          v-model="printer.primary_filament_blueprint"
          :options="materialBlueprints"
          :custom-label="formatMaterialLabel"
          track-by="id"
          placeholder="Select material blueprint"
          :show-no-results="false"
        ></multiselect>
      </div>

      <!-- Accent Filament -->
      <div class="form-group">
        <label>Accent Color/Material</label>
        <div class="radio-group">
          <label class="radio-label">
            <input type="radio" v-model="accentFilamentMode" value="custom" />
            Custom Entry
          </label>
          <label class="radio-label">
            <input type="radio" v-model="accentFilamentMode" value="blueprint" />
            Select from Library
          </label>
        </div>
        
        <input 
          v-if="accentFilamentMode === 'custom'"
          v-model="printer.accent_filament_custom"
          type="text"
          placeholder="e.g., White PLA, Clear PETG"
          class="filament-input"
        />
        
        <multiselect
          v-if="accentFilamentMode === 'blueprint'"
          v-model="printer.accent_filament_blueprint"
          :options="materialBlueprints"
          :custom-label="formatMaterialLabel"
          track-by="id"
          placeholder="Select material blueprint"
          :show-no-results="false"
        ></multiselect>
      </div>

      <!-- Additional Filaments -->
      <div v-if="additionalFilaments.length > 0" class="additional-filaments-section">
        <label>Additional Materials</label>
        <div 
          v-for="(filament, index) in additionalFilaments" 
          :key="index"
          class="additional-filament-card"
        >
          <div class="card-content">
            <div class="form-group">
              <label>Type</label>
              <input 
                v-model="filament.type"
                type="text"
                placeholder="e.g., Canopy, Extruder, X-Mount"
              />
            </div>

            <div class="form-group">
              <label>Color/Material</label>
              <div class="radio-group">
                <label class="radio-label">
                  <input type="radio" v-model="filament.mode" value="custom" />
                  Custom Entry
                </label>
                <label class="radio-label">
                  <input type="radio" v-model="filament.mode" value="blueprint" />
                  Select from Library
                </label>
              </div>
              
              <input 
                v-if="filament.mode === 'custom'"
                v-model="filament.custom"
                type="text"
                placeholder="e.g., Orange PLA"
                class="filament-input"
              />
              
              <multiselect
                v-if="filament.mode === 'blueprint'"
                v-model="filament.blueprint"
                :options="materialBlueprints"
                :custom-label="formatMaterialLabel"
                track-by="id"
                placeholder="Select material blueprint"
                :show-no-results="false"
              ></multiselect>
            </div>

            <button 
              type="button" 
              class="btn btn-sm btn-danger remove-btn"
              @click="removeAdditionalFilament(index)"
            >
              Remove
            </button>
          </div>
        </div>
      </div>

      <button 
        type="button" 
        class="btn btn-secondary add-material-btn"
        @click="addAdditionalFilament"
      >
        + Add Another Material
      </button>

    <div class="form-group">
      <label for="notes">Notes</label>
      <textarea id="notes" v-model="printer.notes" rows="6"></textarea>
    </div>

    <div class="form-actions">
      <button type="submit" class="btn btn-primary">Save Printer Details</button>
      <RouterLink
        :to="isEditMode ? `/printers/${printer.id}` : '/printers'"
        class="btn btn-secondary"
      >
        Cancel
      </RouterLink>
    </div>
  </form>
</template>

<style>
/* Reusing styles from InventoryForm, so no need to be scoped */
.item-form {
  max-width: 500px;
  margin: 20px auto;
  padding: 20px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.form-group {
  margin-bottom: 1.5rem;
}
label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: var(--color-heading);
}
input[type='text'],
input[type='number'],
input[type='url'],
input[type='email'],
input[type='password'],
input[type='date'],
input[type='file'],
textarea,
select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}
.multi-input {
  display: flex;
  gap: 10px;
}
.photo-preview {
  margin-top: 15px;
}
.photo-preview img {
  max-width: 200px;
  max-height: 200px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
/* Removed custom button styles; use global .btn classes */
/* Multiselect dark theme override */
.multiselect__tags,
.multiselect__input {
  background: var(--color-background);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.multiselect__single {
  background: var(--color-background);
  color: var(--color-text);
}
.multiselect__content-wrapper {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
}
.multiselect__option {
  color: var(--color-text);
}
.multiselect__option--highlight {
  background: var(--color-blue);
}
.multiselect__option--selected {
  background: var(--color-background-mute);
}
.multiselect__tag {
  background: var(--color-blue);
}

/* Filament tracking styles */
.radio-group {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 0.75rem;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: normal;
  cursor: pointer;
  color: var(--color-text);
}

.radio-label input[type="radio"] {
  width: auto;
  margin: 0;
  cursor: pointer;
}

.filament-input {
  margin-top: 0.5rem;
}

.additional-filaments-section {
  margin-top: 1.5rem;
}

.additional-filament-card {
  margin-bottom: 1rem;
  padding: 0;
  background-color: transparent;
  border: none;
}

.additional-filament-card .card-content {
  position: relative;
}

.additional-filament-card .form-group {
  margin-bottom: 1rem;
}

.additional-filament-card .form-group:last-of-type {
  margin-bottom: 0.5rem;
}

.remove-btn {
  margin-top: 0.5rem;
}

.add-material-btn {
  width: 100%;
  margin-top: 1rem;
  margin-bottom: 2rem;
}
</style>
