<script setup>
import { ref, onMounted, watch, reactive, computed, defineExpose } from 'vue'
import APIService from '../services/APIService'
import MaterialTable from '../components/MaterialTable.vue'
import ColumnConfigModal from '../components/ColumnConfigModal.vue'

const materials = ref([])
const searchText = ref('')
const isLoading = ref(false)
const isFilterModalVisible = ref(false)
const isColumnModalVisible = ref(false)

// Active filters that are applied
const activeFilters = reactive({
  brand: '',
  material: '',
  color_family: '',
})

// Temporary filters (in modal before applying)
const temporaryFilters = reactive({
  brand: '',
  material: '',
  color_family: '',
})

const colorFamilyOptions = [
  { value: '', label: '-- All --' },
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
  { value: 'clear', label: 'Clear' },
  { value: 'multi', label: 'Multi-Color' },
]

const brands = ref([])
const baseMaterials = ref([])

// Column visibility configuration
const availableColumns = [
  { value: 'photo', text: 'Photo' },
  { value: 'brand', text: 'Brand' },
  { value: 'name', text: 'Name' },
  { value: 'colors', text: 'Colors' },
  { value: 'material', text: 'Material' },
  { value: 'colorFamily', text: 'Color Family' },
  { value: 'diameter', text: 'Diameter' },
]

const visibleColumns = ref([
  'photo',
  'brand',
  'name',
  'colors',
  'material',
  'colorFamily',
  'diameter',
])

const loadMaterials = async () => {
  isLoading.value = true
  try {
    const params = { type: 'blueprint' } // Only load blueprints
    if (searchText.value) params.search = searchText.value
    if (activeFilters.brand) params.brand = activeFilters.brand
    if (activeFilters.material) params.base_material = activeFilters.material
    if (activeFilters.color_family) params.color_family = activeFilters.color_family

    const response = await APIService.getMaterials(params)
    materials.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to load blueprint materials:', error)
  } finally {
    isLoading.value = false
  }
}

const loadFilterOptions = async () => {
  try {
    // Load brands
    const brandsResponse = await APIService.getBrands()
    brands.value = brandsResponse.data.results || brandsResponse.data

    // Load base materials (generic only)
    const materialsResponse = await APIService.getMaterials({ type: 'generic' })
    baseMaterials.value = materialsResponse.data.results || materialsResponse.data
  } catch (error) {
    console.error('Failed to load filter options:', error)
  }
}

const openFilterModal = () => {
  // Copy active filters to temporary
  Object.assign(temporaryFilters, activeFilters)
  isFilterModalVisible.value = true
}

const isFilterActive = computed(() => {
  return activeFilters.brand || activeFilters.material || activeFilters.color_family
})

const applyFilters = () => {
  // Copy temporary filters to active
  Object.assign(activeFilters, temporaryFilters)
  isFilterModalVisible.value = false
  loadMaterials()
}

const clearFilters = () => {
  activeFilters.brand = ''
  activeFilters.material = ''
  activeFilters.color_family = ''
  loadMaterials()
}

const clearFiltersAndClose = () => {
  temporaryFilters.brand = ''
  temporaryFilters.material = ''
  temporaryFilters.color_family = ''
  clearFilters()
  isFilterModalVisible.value = false
}

const openColumnModal = () => {
  isColumnModalVisible.value = true
}

const closeColumnModal = () => {
  isColumnModalVisible.value = false
}

const handleColumnUpdate = (updatedColumns) => {
  visibleColumns.value = updatedColumns
}

// Expose methods for parent component to call
defineExpose({
  openFilterModal,
  openColumnModal,
})

watch(searchText, () => {
  loadMaterials()
})

onMounted(() => {
  loadMaterials()
  loadFilterOptions()
})
</script>

<template>
  <div>
    <div class="filter-indicator" v-if="isFilterActive">
      <span>Filters are active.</span>
      <button @click="clearFilters">Clear Filters</button>
    </div>

    <div v-if="isLoading" class="loading">Loading...</div>
    <MaterialTable v-else :items="materials" :visible-columns="visibleColumns" />

    <Teleport to="body">
      <div v-if="isFilterModalVisible" class="modal-overlay" @click="isFilterModalVisible = false">
        <div class="modal-form" @click.stop>
          <h3>Filter Blueprints</h3>
          <form @submit.prevent="applyFilters">
            <div class="form-group">
              <label>Brand</label>
              <select v-model="temporaryFilters.brand">
                <option value="">-- All --</option>
                <option v-for="brand in brands" :key="brand.id" :value="brand.id">
                  {{ brand.name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>Base Material</label>
              <select v-model="temporaryFilters.material">
                <option value="">-- All --</option>
                <option v-for="material in baseMaterials" :key="material.id" :value="material.id">
                  {{ material.name }}
                </option>
              </select>
            </div>

            <div class="form-group">
              <label>Color Family</label>
              <select v-model="temporaryFilters.color_family">
                <option v-for="opt in colorFamilyOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>

            <div class="form-actions">
              <button
                v-if="isFilterActive"
                @click="clearFiltersAndClose"
                type="button"
                class="btn btn-danger"
              >
                Remove Filters
              </button>
              <div class="form-actions-right">
                <button type="submit" class="btn btn-primary">Apply Filters</button>
                <button
                  @click="isFilterModalVisible = false"
                  type="button"
                  class="btn btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      <ColumnConfigModal
        v-if="isColumnModalVisible"
        :all-columns="availableColumns"
        :visible-columns="visibleColumns"
        @close="closeColumnModal"
        @save="handleColumnUpdate"
      />
    </Teleport>
  </div>
</template>

<style scoped>
.loading {
  text-align: center;
  padding: 40px;
  color: var(--color-text);
  font-size: 1.1rem;
}

.filter-indicator {
  padding: 10px;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-indicator button {
  background: none;
  border: none;
  color: var(--color-text);
  cursor: pointer;
  text-decoration: underline;
  font-size: 0.9rem;
}

.filter-indicator button:hover {
  color: var(--color-heading);
}

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

.modal-form {
  background-color: var(--color-background-soft);
  padding: 20px;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
}

.modal-form h3 {
  color: var(--color-heading);
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: var(--color-heading);
}

.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}

.form-actions-right {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
</style>
