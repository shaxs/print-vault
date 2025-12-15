<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import APIService from '../services/APIService'
import axios from 'axios'
import MainHeader from '../components/MainHeader.vue'
import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'

const router = useRouter()

const material = ref({
  name: '',
  is_generic: false,
  brand: null,
  base_material: null,
  features: [], // Material features (Matte, High Speed, etc.)
  diameter: '1.75',
  spool_weight: 1000,
  empty_spool_weight: null,
  vendor: null,
  vendor_link: '',
  price_per_spool: null,
  low_stock_threshold: 2,
  tds_value: null,
  colors: ['#000000'], // Array of hex codes only
  color_family: null,
  nozzle_temp_min: null,
  nozzle_temp_max: null,
  bed_temp_min: null,
  bed_temp_max: null,
  density: null,
  notes: '',
})

const colorMode = ref('single') // 'single' or 'multi'
const lowStockEnabled = ref(false) // Enable/disable low stock alerts

const photoFile = ref(null)
const photoPreview = ref(null)
const isPhotoModalVisible = ref(false) // Lightbox for main photo

// Additional Photos (staged locally until save)
const additionalPhotos = ref([]) // Array of { file: File, preview: string, caption: string }
const additionalPhotoFile = ref(null)
const additionalPhotoInput = ref(null)
const newPhotoCaption = ref('')
const isAdditionalPhotoModalVisible = ref(false) // Lightbox for additional photos
const selectedAdditionalPhoto = ref(null) // Currently viewed additional photo

const brands = ref([])
const baseMaterials = ref([])
const vendors = ref([])
const features = ref([]) // All available features for dropdown

const diameterOptions = [
  { value: '1.75', label: '1.75mm' },
  { value: '2.85', label: '2.85mm' },
  { value: '3.00', label: '3.00mm' },
]

watch(
  () => material.value.is_generic,
  (isGeneric) => {
    if (isGeneric) {
      // Clear blueprint-specific fields
      material.value.brand = null
      material.value.base_material = null
      material.value.diameter = null
      material.value.spool_weight = null
      material.value.vendor = null
      material.value.vendor_link = ''
      material.value.price_per_spool = null
      material.value.low_stock_threshold = null
      material.value.tds_value = null
    } else {
      // Set defaults for blueprint
      material.value.diameter = '1.75'
      material.value.spool_weight = 1000
      material.value.low_stock_threshold = 2
    }
  },
)

const loadOptions = async () => {
  try {
    const [brandsRes, materialsRes, vendorsRes, featuresRes] = await Promise.all([
      axios.get('/api/brands/'),
      axios.get('/api/materials/?type=generic'),
      axios.get('/api/vendors/'),
      axios.get('/api/material-features/'),
    ])
    brands.value = brandsRes.data.results || brandsRes.data
    baseMaterials.value = materialsRes.data.results || materialsRes.data
    vendors.value = vendorsRes.data.results || vendorsRes.data
    features.value = featuresRes.data.results || featuresRes.data
  } catch (error) {
    console.error('Failed to load options:', error)
  }
}

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    photoFile.value = file
    photoPreview.value = URL.createObjectURL(file)
  }
}

const saveMaterial = async (redirectToSpool = false) => {
  try {
    const formData = new FormData()
    formData.append('name', material.value.name)
    formData.append('is_generic', material.value.is_generic)

    if (!material.value.is_generic) {
      // Blueprint-specific fields
      if (material.value.brand) {
        const brandName =
          typeof material.value.brand === 'object'
            ? material.value.brand.name
            : material.value.brand
        formData.append('brand', JSON.stringify({ name: brandName }))
      }

      if (material.value.base_material) {
        formData.append('base_material_id', material.value.base_material.id)
      }

      // Send features as JSON array
      if (material.value.features && material.value.features.length > 0) {
        const featureData = material.value.features.map((f) =>
          typeof f === 'object' ? { name: f.name } : f,
        )
        formData.append('features', JSON.stringify(featureData))
      } else {
        formData.append('features', JSON.stringify([]))
      }

      if (material.value.diameter) formData.append('diameter', material.value.diameter)
      if (material.value.spool_weight) formData.append('spool_weight', material.value.spool_weight)

      if (material.value.vendor) {
        const vendorName =
          typeof material.value.vendor === 'object'
            ? material.value.vendor.name
            : material.value.vendor
        formData.append('vendor', JSON.stringify({ name: vendorName }))
      }

      if (material.value.vendor_link) formData.append('vendor_link', material.value.vendor_link)
      if (material.value.price_per_spool)
        formData.append('price_per_spool', material.value.price_per_spool)
      // Only send low_stock_threshold if enabled, otherwise send null to disable alerts
      if (lowStockEnabled.value && material.value.low_stock_threshold !== null) {
        formData.append('low_stock_threshold', material.value.low_stock_threshold)
      } else if (!lowStockEnabled.value) {
        formData.append('low_stock_threshold', '')
      }
      if (material.value.tds_value) formData.append('tds_value', material.value.tds_value)

      // Send colors as JSON array of hex codes
      const validColors = material.value.colors.filter((hex) => hex && hex !== '')
      if (validColors.length > 0) {
        formData.append('colors', JSON.stringify(validColors))
      }

      // Send color_family if selected
      if (material.value.color_family) {
        formData.append('color_family', material.value.color_family)
      }

      if (material.value.nozzle_temp_min)
        formData.append('nozzle_temp_min', material.value.nozzle_temp_min)
      if (material.value.nozzle_temp_max)
        formData.append('nozzle_temp_max', material.value.nozzle_temp_max)
      if (material.value.bed_temp_min) formData.append('bed_temp_min', material.value.bed_temp_min)
      if (material.value.bed_temp_max) formData.append('bed_temp_max', material.value.bed_temp_max)
      if (material.value.density) formData.append('density', material.value.density)
      if (material.value.notes) formData.append('notes', material.value.notes)

      if (photoFile.value) {
        formData.append('photo', photoFile.value)
      }
    }

    const response = await APIService.createMaterial(formData)
    const materialId = response.data?.id

    // Upload additional photos if any were staged
    if (materialId && additionalPhotos.value.length > 0) {
      for (const photo of additionalPhotos.value) {
        try {
          const photoFormData = new FormData()
          photoFormData.append('image', photo.file)
          if (photo.caption) {
            photoFormData.append('caption', photo.caption)
          }
          await axios.post(`/api/materials/${materialId}/photos/`, photoFormData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
        } catch (photoError) {
          console.error('Failed to upload additional photo:', photoError)
          // Continue with other photos even if one fails
        }
      }
    }

    if (redirectToSpool && materialId) {
      // Redirect to spool creation with the new material pre-selected
      router.push(`/filaments/create?materialId=${materialId}`)
    } else {
      router.push('/filaments?tab=blueprints')
    }
  } catch (error) {
    console.error('Failed to save material:', error)
    if (error.response?.data) {
      alert(`Error: ${JSON.stringify(error.response.data)}`)
    }
  }
}

const addBrand = (searchTerm) => {
  if (searchTerm) {
    const newBrand = { id: null, name: searchTerm }
    brands.value.push(newBrand)
    material.value.brand = newBrand
  }
}

const addBaseMaterial = async (searchTerm) => {
  if (searchTerm) {
    try {
      // Create the generic material on the backend
      const response = await APIService.createMaterial({
        name: searchTerm,
        is_generic: true,
      })
      const newMaterial = response.data
      baseMaterials.value.push(newMaterial)
      material.value.base_material = newMaterial
    } catch (error) {
      console.error('Failed to create base material:', error)
      // Still add locally as fallback
      const newMaterial = { id: null, name: searchTerm, is_generic: true }
      baseMaterials.value.push(newMaterial)
      material.value.base_material = newMaterial
    }
  }
}

const addVendor = (searchTerm) => {
  if (searchTerm) {
    const newVendor = { id: null, name: searchTerm }
    vendors.value.push(newVendor)
    material.value.vendor = newVendor
  }
}

const addFeature = async (searchTerm) => {
  if (searchTerm) {
    try {
      // Create the feature on the backend
      const response = await axios.post('/api/material-features/', { name: searchTerm })
      const newFeature = response.data
      features.value.push(newFeature)
      material.value.features.push(newFeature)
    } catch (error) {
      console.error('Failed to create feature:', error)
      // Still add locally as fallback
      const newFeature = { id: null, name: searchTerm }
      features.value.push(newFeature)
      material.value.features.push(newFeature)
    }
  }
}

const addColor = () => {
  material.value.colors.push('#000000')
}

const removeColor = (index) => {
  // Multi-color mode requires at least 2 colors (index 0 and 1)
  if (material.value.colors.length > 2 && index >= 2) {
    material.value.colors.splice(index, 1)
  }
}

// Additional Photo handling
const handleAdditionalPhotoUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    additionalPhotoFile.value = file
  }
}

const addAdditionalPhoto = () => {
  if (!additionalPhotoFile.value) return

  const preview = URL.createObjectURL(additionalPhotoFile.value)
  additionalPhotos.value.push({
    file: additionalPhotoFile.value,
    preview: preview,
    caption: newPhotoCaption.value || '',
  })

  // Reset inputs
  additionalPhotoFile.value = null
  newPhotoCaption.value = ''
  if (additionalPhotoInput.value) {
    additionalPhotoInput.value.value = ''
  }
}

const removeAdditionalPhoto = (index) => {
  // Revoke the object URL to free memory
  URL.revokeObjectURL(additionalPhotos.value[index].preview)
  additionalPhotos.value.splice(index, 1)
}

const openAdditionalPhotoModal = (photo) => {
  selectedAdditionalPhoto.value = photo
  isAdditionalPhotoModalVisible.value = true
}

watch(colorMode, (newMode) => {
  if (newMode === 'single' && material.value.colors.length > 1) {
    material.value.colors = [material.value.colors[0]]
  } else if (newMode === 'multi' && material.value.colors.length === 1) {
    material.value.colors.push('#000000')
  }
})

// Save & Clone - saves material then navigates to create with cloned data
const saveAndClone = async () => {
  try {
    const formData = new FormData()
    formData.append('name', material.value.name)
    formData.append('is_generic', material.value.is_generic)

    if (!material.value.is_generic) {
      // Blueprint-specific fields
      if (material.value.brand) {
        const brandName =
          typeof material.value.brand === 'object'
            ? material.value.brand.name
            : material.value.brand
        formData.append('brand', JSON.stringify({ name: brandName }))
      }

      if (material.value.base_material) {
        formData.append('base_material_id', material.value.base_material.id)
      }

      // Send features as JSON array
      if (material.value.features && material.value.features.length > 0) {
        const featureData = material.value.features.map((f) =>
          typeof f === 'object' ? { name: f.name } : f,
        )
        formData.append('features', JSON.stringify(featureData))
      } else {
        formData.append('features', JSON.stringify([]))
      }

      if (material.value.diameter) formData.append('diameter', material.value.diameter)
      if (material.value.spool_weight) formData.append('spool_weight', material.value.spool_weight)

      if (material.value.vendor) {
        const vendorName =
          typeof material.value.vendor === 'object'
            ? material.value.vendor.name
            : material.value.vendor
        formData.append('vendor', JSON.stringify({ name: vendorName }))
      }

      if (material.value.vendor_link) formData.append('vendor_link', material.value.vendor_link)
      if (material.value.price_per_spool)
        formData.append('price_per_spool', material.value.price_per_spool)
      if (lowStockEnabled.value && material.value.low_stock_threshold !== null) {
        formData.append('low_stock_threshold', material.value.low_stock_threshold)
      } else if (!lowStockEnabled.value) {
        formData.append('low_stock_threshold', '')
      }
      if (material.value.tds_value) formData.append('tds_value', material.value.tds_value)

      const validColors = material.value.colors.filter((hex) => hex && hex !== '')
      if (validColors.length > 0) {
        formData.append('colors', JSON.stringify(validColors))
      }

      if (material.value.color_family) {
        formData.append('color_family', material.value.color_family)
      }

      if (material.value.nozzle_temp_min)
        formData.append('nozzle_temp_min', material.value.nozzle_temp_min)
      if (material.value.nozzle_temp_max)
        formData.append('nozzle_temp_max', material.value.nozzle_temp_max)
      if (material.value.bed_temp_min) formData.append('bed_temp_min', material.value.bed_temp_min)
      if (material.value.bed_temp_max) formData.append('bed_temp_max', material.value.bed_temp_max)
      if (material.value.density) formData.append('density', material.value.density)
      if (material.value.notes) formData.append('notes', material.value.notes)

      if (photoFile.value) {
        formData.append('photo', photoFile.value)
      }
    }

    const response = await APIService.createMaterial(formData)
    const materialId = response.data?.id

    // Upload additional photos if any were staged
    if (materialId && additionalPhotos.value.length > 0) {
      for (const photo of additionalPhotos.value) {
        try {
          const photoFormData = new FormData()
          photoFormData.append('image', photo.file)
          if (photo.caption) {
            photoFormData.append('caption', photo.caption)
          }
          await axios.post(`/api/materials/${materialId}/photos/`, photoFormData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
        } catch (photoError) {
          console.error('Failed to upload additional photo:', photoError)
        }
      }
    }

    // Prepare cloned data - EXCLUDE: photo, name, colors, color_family, vendor, vendor_link, tds_value
    const clonedData = {
      is_generic: material.value.is_generic,
      brand: material.value.brand,
      base_material: material.value.base_material,
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
      lowStockEnabled: lowStockEnabled.value,
    }

    // Store in sessionStorage
    sessionStorage.setItem('materialCloneData', JSON.stringify(clonedData))

    // Since we're already on /filaments/materials/create, Vue Router won't remount.
    // Instead, manually load cloned data to reset the form with cloned values.
    loadClonedData()

    // Clear the photo and additional photos since they shouldn't be cloned
    photoFile.value = null
    photoPreview.value = null
    additionalPhotos.value = []

    // Scroll to top so user sees fresh form
    setTimeout(() => {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }, 50)

    // Log success for debugging
    console.log('Material saved successfully, form reset for clone')
  } catch (error) {
    console.error('Failed to save and clone material:', error)
    if (error.response?.data) {
      alert(`Error: ${JSON.stringify(error.response.data)}`)
    }
  }
}

// Load cloned data from sessionStorage if present
const loadClonedData = () => {
  const clonedDataStr = sessionStorage.getItem('materialCloneData')
  if (clonedDataStr) {
    try {
      const clonedData = JSON.parse(clonedDataStr)

      // Apply cloned values
      material.value.is_generic = clonedData.is_generic || false
      material.value.brand = clonedData.brand || null
      material.value.base_material = clonedData.base_material || null
      material.value.diameter = clonedData.diameter || '1.75'
      material.value.spool_weight = clonedData.spool_weight || 1000
      material.value.empty_spool_weight = clonedData.empty_spool_weight || null
      material.value.price_per_spool = clonedData.price_per_spool || null
      material.value.low_stock_threshold = clonedData.low_stock_threshold || 2
      material.value.nozzle_temp_min = clonedData.nozzle_temp_min || null
      material.value.nozzle_temp_max = clonedData.nozzle_temp_max || null
      material.value.bed_temp_min = clonedData.bed_temp_min || null
      material.value.bed_temp_max = clonedData.bed_temp_max || null
      material.value.density = clonedData.density || null
      material.value.notes = clonedData.notes || ''
      lowStockEnabled.value = clonedData.lowStockEnabled || false

      // Reset excluded fields to defaults
      material.value.name = ''
      material.value.colors = ['#000000']
      material.value.color_family = null
      material.value.vendor = null
      material.value.vendor_link = ''
      material.value.tds_value = null

      // Clear the cloned data from session storage after using
      sessionStorage.removeItem('materialCloneData')

      // Scroll to top of page so user can start filling out the form
      // Use setTimeout to ensure scroll happens after route transition completes
      setTimeout(() => {
        window.scrollTo(0, 0)
        document.documentElement.scrollTop = 0
        document.body.scrollTop = 0
        // Also try scrolling main content area if it exists
        const mainContent =
          document.querySelector('.material-form') || document.querySelector('main')
        if (mainContent) {
          mainContent.scrollIntoView({ behavior: 'instant', block: 'start' })
        }
      }, 100)
    } catch (e) {
      console.error('Failed to parse cloned data:', e)
      sessionStorage.removeItem('materialCloneData')
    }
  }
}

onMounted(async () => {
  await loadOptions()
  // Check sessionStorage for cloned data (from edit page's Save & Clone or detail page's Clone)
  loadClonedData()
})
</script>

<template>
  <div>
    <MainHeader
      title="Add New Material"
      :showSearch="false"
      :showAddButton="false"
      :showFilterButton="false"
      :showColumnButton="false"
    />

    <form @submit.prevent="saveMaterial(false)" class="material-form">
      <div class="form-section">
        <h2>Material Type</h2>
        <div class="form-group">
          <label>
            <input type="radio" :value="false" v-model="material.is_generic" />
            Blueprint (Brand-Specific Filament)
          </label>
          <label>
            <input type="radio" :value="true" v-model="material.is_generic" />
            Generic Material (Base Type)
          </label>
        </div>
      </div>

      <div class="form-section">
        <h2>Basic Information</h2>
        <div class="form-group">
          <label for="name">Name *</label>
          <input
            type="text"
            id="name"
            v-model="material.name"
            required
            placeholder="e.g., PolyTerra PLA or PLA"
          />
        </div>

        <div v-if="!material.is_generic" class="form-group">
          <label for="brand">Brand *</label>
          <Multiselect
            v-model="material.brand"
            :options="brands"
            label="name"
            track-by="id"
            placeholder="Select or type to add new brand"
            :taggable="true"
            @tag="addBrand"
          />
        </div>

        <div v-if="!material.is_generic" class="form-group">
          <label for="base-material">Base Material Type *</label>
          <Multiselect
            v-model="material.base_material"
            :options="baseMaterials"
            label="name"
            track-by="id"
            placeholder="Select or type to add new base material"
            :taggable="true"
            @tag="addBaseMaterial"
          />
        </div>

        <div v-if="!material.is_generic" class="form-group">
          <label for="features">Features</label>
          <Multiselect
            v-model="material.features"
            :options="features"
            :multiple="true"
            label="name"
            track-by="id"
            placeholder="Select or type to add features (e.g., Matte, High Speed)"
            :taggable="true"
            @tag="addFeature"
          />
        </div>

        <div v-if="!material.is_generic" class="form-group">
          <label for="photo">Main Photo</label>
          <input type="file" id="photo" @change="handleFileUpload" accept="image/*" />
          <img
            v-if="photoPreview"
            :src="photoPreview"
            alt="Preview"
            class="photo-preview clickable"
            @click="isPhotoModalVisible = true"
          />
        </div>

        <!-- Additional Photos Section -->
        <div v-if="!material.is_generic" class="form-group additional-photos-section">
          <label>Additional Photos</label>

          <!-- Staged Additional Photos -->
          <div v-if="additionalPhotos.length > 0" class="additional-photos-grid">
            <div
              v-for="(photo, index) in additionalPhotos"
              :key="index"
              class="additional-photo-item"
            >
              <img
                :src="photo.preview"
                :alt="photo.caption || 'Additional photo'"
                class="additional-photo-thumb clickable"
                @click="openAdditionalPhotoModal(photo)"
              />
              <div class="photo-overlay">
                <span class="photo-caption-display">{{ photo.caption || 'No caption' }}</span>
                <button
                  type="button"
                  class="delete-photo-btn"
                  @click="removeAdditionalPhoto(index)"
                  title="Remove photo"
                >
                  ×
                </button>
              </div>
            </div>
          </div>

          <!-- Add New Photo -->
          <div class="add-photo-inline">
            <input
              type="file"
              id="additional-photo"
              @change="handleAdditionalPhotoUpload"
              accept="image/*"
              ref="additionalPhotoInput"
            />
            <input
              type="text"
              v-model="newPhotoCaption"
              placeholder="Optional caption"
              class="caption-input"
            />
            <button
              type="button"
              class="btn btn-secondary btn-sm"
              @click="addAdditionalPhoto"
              :disabled="!additionalPhotoFile"
            >
              Add Photo
            </button>
          </div>
          <p class="help-text">Add multiple photos to show different angles or details</p>
        </div>
      </div>

      <div v-if="!material.is_generic" class="form-section">
        <h2>Specifications</h2>
        <div class="form-group">
          <label for="diameter">Diameter</label>
          <select id="diameter" v-model="material.diameter">
            <option v-for="opt in diameterOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="form-group">
          <label for="spool-weight">Standard Spool Weight (grams)</label>
          <input
            type="number"
            id="spool-weight"
            v-model.number="material.spool_weight"
            placeholder="e.g., 1000"
          />
        </div>

        <div class="form-group">
          <label for="empty-spool-weight">Empty Spool Weight (grams)</label>
          <input
            type="number"
            id="empty-spool-weight"
            v-model.number="material.empty_spool_weight"
            placeholder="e.g., 200"
          />
          <p class="help-text">
            Weight of the empty spool (used for accurate remaining filament calculations)
          </p>
        </div>
      </div>

      <div v-if="!material.is_generic" class="form-section">
        <h2>Color Information</h2>

        <div class="form-group">
          <label>Color Type</label>
          <div class="color-mode-toggle">
            <label>
              <input type="radio" v-model="colorMode" value="single" />
              Single Color
            </label>
            <label>
              <input type="radio" v-model="colorMode" value="multi" />
              Multi-Color (Gradient/Blend)
            </label>
          </div>
        </div>

        <div v-for="(colorHex, index) in material.colors" :key="index" class="color-entry">
          <div class="color-entry-header">
            <h3>Color Code {{ index + 1 }}</h3>
            <button
              v-if="index >= 2"
              type="button"
              @click="removeColor(index)"
              class="btn-remove-color"
            >
              Remove
            </button>
          </div>

          <div class="form-group">
            <div style="display: flex; gap: 1rem; align-items: center">
              <input type="color" :id="`color-hex-${index}`" v-model="material.colors[index]" />
              <input
                type="text"
                v-model="material.colors[index]"
                placeholder="#000000"
                style="flex: 1"
              />
            </div>
          </div>
        </div>

        <button
          v-if="colorMode === 'multi'"
          type="button"
          @click="addColor"
          class="btn btn-secondary"
        >
          + Add Another Color
        </button>

        <div class="form-group">
          <label for="color-family"
            >Primary Color Family
            <span class="help-text">(Helps with searching and filtering)</span></label
          >
          <select id="color-family" v-model="material.color_family">
            <option value="">-- Select a color family (optional) --</option>
            <option value="red">Red</option>
            <option value="orange">Orange</option>
            <option value="yellow">Yellow</option>
            <option value="green">Green</option>
            <option value="blue">Blue</option>
            <option value="purple">Purple</option>
            <option value="pink">Pink</option>
            <option value="brown">Brown</option>
            <option value="black">Black</option>
            <option value="white">White</option>
            <option value="gray">Gray</option>
            <option value="clear">Clear/Natural</option>
            <option value="multi">Multi-Color</option>
          </select>
        </div>
      </div>

      <div v-if="!material.is_generic" class="form-section">
        <h2>Print Settings (Optional)</h2>
        <div class="form-row">
          <div class="form-group">
            <label for="nozzle-temp-min">Nozzle Temp Min (°C)</label>
            <input
              type="number"
              id="nozzle-temp-min"
              v-model.number="material.nozzle_temp_min"
              placeholder="e.g., 200"
            />
          </div>

          <div class="form-group">
            <label for="nozzle-temp-max">Nozzle Temp Max (°C)</label>
            <input
              type="number"
              id="nozzle-temp-max"
              v-model.number="material.nozzle_temp_max"
              placeholder="e.g., 220"
            />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="bed-temp-min">Bed Temp Min (°C)</label>
            <input
              type="number"
              id="bed-temp-min"
              v-model.number="material.bed_temp_min"
              placeholder="e.g., 50"
            />
          </div>

          <div class="form-group">
            <label for="bed-temp-max">Bed Temp Max (°C)</label>
            <input
              type="number"
              id="bed-temp-max"
              v-model.number="material.bed_temp_max"
              placeholder="e.g., 70"
            />
          </div>
        </div>

        <div class="form-group">
          <label for="density">Material Density (g/cm³)</label>
          <input
            type="number"
            id="density"
            v-model.number="material.density"
            step="0.01"
            placeholder="e.g., 1.24"
          />
          <small style="color: var(--color-text-muted)"
            >Used for calculating filament length and volume</small
          >
        </div>
      </div>

      <div v-if="!material.is_generic" class="form-section">
        <h2>Vendor & Pricing</h2>
        <div class="form-group">
          <label for="vendor">Vendor</label>
          <Multiselect
            v-model="material.vendor"
            :options="vendors"
            label="name"
            track-by="id"
            placeholder="Select or type to add new vendor"
            :taggable="true"
            @tag="addVendor"
          />
        </div>

        <div class="form-group">
          <label for="vendor-link">Vendor Link</label>
          <input
            type="url"
            id="vendor-link"
            v-model="material.vendor_link"
            placeholder="https://..."
          />
        </div>

        <div class="form-group">
          <label for="price">Price Per Spool</label>
          <input
            type="number"
            id="price"
            v-model.number="material.price_per_spool"
            step="0.01"
            placeholder="e.g., 19.99"
          />
        </div>
      </div>

      <div v-if="!material.is_generic" class="form-section">
        <h2>Advanced</h2>
        <div class="form-group">
          <label>
            <input type="checkbox" v-model="lowStockEnabled" />
            Enable Low Stock Alerts
          </label>
        </div>

        <div v-if="lowStockEnabled" class="form-group">
          <label for="low-stock">Low Stock Threshold (spool count)</label>
          <input
            type="number"
            id="low-stock"
            v-model.number="material.low_stock_threshold"
            placeholder="e.g., 2"
          />
        </div>

        <div class="form-group">
          <label for="tds">TDS Value (HueForge)</label>
          <input
            type="number"
            id="tds"
            v-model.number="material.tds_value"
            placeholder="e.g., 54"
          />
          <p class="help-text">Translucency value for HueForge lithophanes (optional)</p>
        </div>
      </div>

      <div class="form-section">
        <h2>Notes & Comments</h2>
        <div class="form-group">
          <label for="notes">Notes</label>
          <textarea
            id="notes"
            v-model="material.notes"
            rows="4"
            placeholder="Add any notes, printing tips, quirks, or comments about this material..."
          ></textarea>
        </div>
      </div>

      <div class="form-actions">
        <button type="button" @click="router.push('/filaments?tab=blueprints')" class="btn-cancel">
          Cancel
        </button>
        <button
          v-if="!material.is_generic"
          type="button"
          @click="saveMaterial(true)"
          class="btn-save-add"
        >
          Save & Add Spool
        </button>
        <button
          v-if="!material.is_generic"
          type="button"
          @click="saveAndClone"
          class="btn-save-clone"
        >
          Save & Clone
        </button>
        <button type="submit" class="btn-save">Save Material</button>
      </div>
    </form>

    <!-- Photo Lightbox Modal -->
    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img :src="photoPreview" :alt="material.name || 'Material'" class="modal-image" />
      </div>
    </div>

    <!-- Additional Photo Lightbox Modal -->
    <div
      v-if="isAdditionalPhotoModalVisible"
      class="modal-overlay"
      @click="isAdditionalPhotoModalVisible = false"
    >
      <div class="modal-content" @click.stop>
        <button @click="isAdditionalPhotoModalVisible = false" class="close-button">&times;</button>
        <img
          v-if="selectedAdditionalPhoto"
          :src="selectedAdditionalPhoto.preview"
          :alt="selectedAdditionalPhoto.caption || 'Additional photo'"
          class="modal-image"
        />
        <p v-if="selectedAdditionalPhoto && selectedAdditionalPhoto.caption" class="modal-caption">
          {{ selectedAdditionalPhoto.caption }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.material-form {
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: var(--color-text);
}

.form-group input[type='text'],
.form-group input[type='number'],
.form-group input[type='url'],
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

.form-group input[type='radio'] {
  margin-right: 0.5rem;
}

.form-group textarea {
  resize: vertical;
  min-height: 100px;
  font-family: inherit;
}

.photo-preview {
  margin-top: 1rem;
  max-width: 200px;
  max-height: 200px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 2rem;
}

.btn-cancel,
.btn-save,
.btn-save-add,
.btn-save-clone {
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

.btn-save-add {
  background-color: var(--color-green, #198754);
  color: white;
  border: 1px solid var(--color-green, #198754);
}

.btn-save-add:hover {
  background-color: #157347;
}

.btn-save-clone {
  background-color: var(--color-purple, #6f42c1);
  color: white;
  border: 1px solid var(--color-purple, #6f42c1);
}

.btn-save-clone:hover {
  background-color: #5a32a3;
}

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

.color-preview {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  border: 2px solid var(--color-border);
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

/* Additional Photos Section */
.additional-photos-section {
  margin-top: 1rem;
}

.additional-photos-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
}

.additional-photo-item {
  position: relative;
  width: 120px;
}

.additional-photo-thumb {
  width: 120px;
  height: 90px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.photo-overlay {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 0.25rem;
}

.photo-caption-display {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.delete-photo-btn {
  background: var(--color-danger, #dc3545);
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-left: 0.5rem;
}

.delete-photo-btn:hover {
  background: #c82333;
}

.add-photo-inline {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.add-photo-inline input[type='file'] {
  flex: 1;
  min-width: 150px;
}

.caption-input {
  flex: 1;
  min-width: 150px;
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

/* Clickable images */
.clickable {
  cursor: pointer;
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.clickable:hover {
  opacity: 0.9;
  transform: scale(1.02);
}

/* Lightbox Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  position: relative;
  max-width: 90%;
  max-height: 90%;
  background-color: var(--color-background);
  border-radius: 8px;
  padding: 1rem;
}

.modal-image {
  max-width: 100%;
  max-height: 80vh;
  display: block;
  border-radius: 4px;
}

.modal-caption {
  text-align: center;
  margin-top: 1rem;
  color: var(--color-text);
  font-size: 0.875rem;
}

.close-button {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  background: var(--color-background-mute);
  border: none;
  color: var(--color-text);
  font-size: 1.5rem;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.close-button:hover {
  background: var(--color-background-soft);
}
</style>
