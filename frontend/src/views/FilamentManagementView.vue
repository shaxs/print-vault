<script setup>
import { ref, onMounted, watch, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import MainHeader from '../components/MainHeader.vue'
import FilamentTable from '../components/FilamentTable.vue'
import ColumnConfigModal from '../components/ColumnConfigModal.vue'
import MaterialLibraryView from './MaterialLibraryView.vue'
import GenericMaterialsView from './GenericMaterialsView.vue'

const route = useRoute()
const router = useRouter()

// Initialize activeTab from query param or default to 'spools'
const getInitialTab = () => {
  const tabParam = route.query.tab
  if (tabParam === 'blueprints' || tabParam === 'generics') {
    return tabParam
  }
  return 'spools'
}

const activeTab = ref(getInitialTab())

// Change tab and update URL so back button works correctly
const changeTab = (tab) => {
  activeTab.value = tab
  // Update URL with query param - use replace to avoid too many history entries
  if (tab === 'spools') {
    // Remove tab param for default view
    router.replace({ path: '/filaments', query: {} })
  } else {
    router.replace({ path: '/filaments', query: { tab } })
  }
}

const blueprintsRef = ref(null)
const genericsRef = ref(null)
const spools = ref([])
const searchText = ref('')
const isLoading = ref(false)
const isFilterModalVisible = ref(false)
const isColumnModalVisible = ref(false)
const showArchived = ref(false)

// Active filters that are applied
const activeFilters = reactive({
  status: '',
  brand: '',
  material: '',
  color_family: '',
  feature: '',
})

// Temporary filters (in modal before applying)
const temporaryFilters = reactive({
  status: '',
  brand: '',
  material: '',
  color_family: '',
  feature: '',
})

const statusOptions = [
  { value: '', label: '-- All --' },
  { value: 'new', label: 'New (Unopened)' },
  { value: 'opened', label: 'Opened' },
  { value: 'in_use', label: 'In Use' },
  { value: 'low', label: 'Low' },
  { value: 'empty', label: 'Empty' },
  { value: 'archived', label: 'Archived' },
]

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
const materials = ref([])
const features = ref([])

// Column visibility configuration
const availableColumns = [
  { value: 'photo', text: 'Photo' },
  { value: 'brand', text: 'Brand' },
  { value: 'colors', text: 'Colors' },
  { value: 'name', text: 'Name' },
  { value: 'material', text: 'Material' },
  { value: 'features', text: 'Features' },
  { value: 'quantity', text: 'Quantity' },
  { value: 'status', text: 'Status' },
  { value: 'location', text: 'Location/Printer' },
  { value: 'filamentUsed', text: 'Filament Used' },
]

const visibleColumns = ref([
  'photo',
  'brand',
  'colors',
  'name',
  'material',
  'features',
  'quantity',
  'status',
  'location',
  'filamentUsed',
])

const loadSpools = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (searchText.value) params.search = searchText.value
    if (activeFilters.status) params.status = activeFilters.status
    if (activeFilters.brand) params.brand = activeFilters.brand
    if (activeFilters.material) params.material = activeFilters.material
    if (activeFilters.color_family) params.color_family = activeFilters.color_family
    if (activeFilters.feature) params.feature = activeFilters.feature
    // Exclude archived by default unless showArchived is checked
    if (!showArchived.value) params.is_archived = false

    const response = await APIService.getFilamentSpools(params)
    spools.value = response.data.results || response.data
  } catch (error) {
    console.error('Failed to load filament spools:', error)
  } finally {
    isLoading.value = false
  }
}

const loadFilterOptions = async () => {
  try {
    // Load brands
    const brandsResponse = await APIService.getBrands()
    brands.value = brandsResponse.data.results || brandsResponse.data

    // Load base materials
    const materialsResponse = await APIService.getMaterials({ type: 'generic' })
    materials.value = materialsResponse.data.results || materialsResponse.data

    // Load features
    const featuresResponse = await APIService.getMaterialFeatures()
    features.value = featuresResponse.data.results || featuresResponse.data
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
  return (
    activeFilters.status ||
    activeFilters.brand ||
    activeFilters.material ||
    activeFilters.color_family ||
    activeFilters.feature
  )
})

const applyFilters = () => {
  // Copy temporary filters to active
  Object.assign(activeFilters, temporaryFilters)
  isFilterModalVisible.value = false
  loadSpools()
}

const clearFilters = () => {
  activeFilters.status = ''
  activeFilters.brand = ''
  activeFilters.material = ''
  activeFilters.color_family = ''
  activeFilters.feature = ''
  loadSpools()
}

const clearFiltersAndClose = () => {
  temporaryFilters.status = ''
  temporaryFilters.brand = ''
  temporaryFilters.material = ''
  temporaryFilters.color_family = ''
  temporaryFilters.feature = ''
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

// Handler for filter/column buttons - route to appropriate tab
const handleOpenFilter = () => {
  if (activeTab.value === 'spools') {
    openFilterModal()
  } else if (activeTab.value === 'blueprints' && blueprintsRef.value) {
    blueprintsRef.value.openFilterModal()
  } else if (activeTab.value === 'generics' && genericsRef.value) {
    genericsRef.value.openFilterModal()
  }
}

const handleOpenColumns = () => {
  if (activeTab.value === 'spools') {
    openColumnModal()
  } else if (activeTab.value === 'blueprints' && blueprintsRef.value) {
    blueprintsRef.value.openColumnModal()
  } else if (activeTab.value === 'generics' && genericsRef.value) {
    genericsRef.value.openColumnModal()
  }
}

watch(searchText, () => {
  if (activeTab.value === 'spools') {
    loadSpools()
  }
})

onMounted(() => {
  loadSpools()
  loadFilterOptions()
})
</script>

<template>
  <main>
    <MainHeader
      :title="
        activeTab === 'spools'
          ? 'Filament Spools'
          : activeTab === 'blueprints'
            ? 'Material Blueprints'
            : 'Generic Materials'
      "
      :createUrl="activeTab === 'spools' ? '/filaments/create' : '/filaments/materials/create'"
      v-model="searchText"
      :showFilterButton="true"
      :showColumnButton="true"
      @open-filter="handleOpenFilter"
      @open-columns="handleOpenColumns"
    />

    <div class="tabs">
      <button @click="changeTab('spools')" :class="{ active: activeTab === 'spools' }">
        Spools
      </button>
      <button @click="changeTab('blueprints')" :class="{ active: activeTab === 'blueprints' }">
        Blueprints
      </button>
      <button @click="changeTab('generics')" :class="{ active: activeTab === 'generics' }">
        Generic Materials
      </button>
    </div>

    <!-- Spools Tab -->
    <template v-if="activeTab === 'spools'">
      <div class="filter-indicator" v-if="isFilterActive">
        <span>Filters are active.</span>
        <button @click="clearFilters">Clear Filters</button>
      </div>

      <div class="table-controls">
        <label class="archive-toggle">
          <input type="checkbox" v-model="showArchived" @change="loadSpools" />
          Show archived spools
        </label>
      </div>

      <div v-if="isLoading" class="loading">Loading...</div>
      <FilamentTable v-else :items="spools" :visible-columns="visibleColumns" />

      <Teleport to="body">
        <div
          v-if="isFilterModalVisible"
          class="modal-overlay"
          @click="isFilterModalVisible = false"
        >
          <div class="modal-form" @click.stop>
            <h3>Filter Filaments</h3>
            <form @submit.prevent="applyFilters">
              <div class="form-group">
                <label>Status</label>
                <select v-model="temporaryFilters.status">
                  <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>

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
                  <option v-for="material in materials" :key="material.id" :value="material.id">
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

              <div class="form-group">
                <label>Feature</label>
                <select v-model="temporaryFilters.feature">
                  <option value="">-- All --</option>
                  <option v-for="feature in features" :key="feature.id" :value="feature.id">
                    {{ feature.name }}
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
    </template>

    <!-- Materials Tab -->
    <!-- Blueprints Tab -->
    <MaterialLibraryView
      v-else-if="activeTab === 'blueprints'"
      ref="blueprintsRef"
      :embedded="true"
    />

    <!-- Generic Materials Tab -->
    <GenericMaterialsView v-else-if="activeTab === 'generics'" ref="genericsRef" />
  </main>
</template>

<style scoped>
.tabs {
  display: flex;
  background-color: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
  margin: 20px 0;
}

.tabs button {
  padding: 12px 24px;
  cursor: pointer;
  background-color: transparent;
  border: none;
  color: var(--color-text);
  font-size: 1rem;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}

.tabs button:hover {
  background-color: var(--color-background-soft);
}

.tabs button.active {
  color: var(--color-heading);
  border-bottom-color: var(--color-blue);
}

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

.table-controls {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 15px;
}

.archive-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: var(--color-text);
  font-size: 0.9rem;
}

.archive-toggle input[type='checkbox'] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--color-primary);
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
