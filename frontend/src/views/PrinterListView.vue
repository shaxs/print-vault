<script setup>
import { ref, onMounted, watch, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '../components/MainHeader.vue'
import PrinterList from '../components/PrinterList.vue'
import ColumnConfigModal from '../components/ColumnConfigModal.vue'

const route = useRoute()
const router = useRouter()
const allPrinterColumns = ref([
  { text: 'Title', value: 'title', defaultVisible: true },
  { text: 'Photo', value: 'photo', defaultVisible: false },
  { text: 'Manufacturer', value: 'manufacturer', defaultVisible: true },
  { text: 'Status', value: 'status', defaultVisible: true },
  { text: 'Serial Number', value: 'serial_number', defaultVisible: false },
  { text: 'Purchase Date', value: 'purchase_date', defaultVisible: false },
])
const visibleColumns = ref([])
const storageKey = 'printer-columns'

const loadColumns = () => {
  const saved = localStorage.getItem(storageKey)
  if (saved) {
    visibleColumns.value = JSON.parse(saved)
  } else {
    visibleColumns.value = allPrinterColumns.value
      .filter((c) => c.defaultVisible)
      .map((c) => c.value)
  }
}
const saveColumns = (newColumns) => {
  visibleColumns.value = newColumns
  localStorage.setItem(storageKey, JSON.stringify(newColumns))
}

const printers = ref([])
const searchText = ref('')
const isFilterModalVisible = ref(false)
const isColumnModalVisible = ref(false)
const activeFilters = ref({})
const filterOptions = ref({
  brands: [],
  statuses: ['Active', 'Under Repair', 'Sold', 'Archived', 'Planned'],
})
const temporaryFilters = reactive({ manufacturer__name: '', status: '' })
const filterStorageKey = 'printer-filters'

const isFilterActive = computed(() => {
  return searchText.value || Object.values(activeFilters.value).some((val) => val && val.length > 0)
})

const loadPrinters = async () => {
  try {
    const params = { ...activeFilters.value }
    if (searchText.value) {
      params.search = searchText.value
    }
    const response = await APIService.getPrinters(params)
    printers.value = response.data
  } catch (error) {
    console.error('Failed to load printers:', error)
  }
}

watch(searchText, (newSearchText) => {
  const query = { ...route.query }
  if (newSearchText) {
    query.search = newSearchText
  } else {
    delete query.search
  }
  router.replace({ query })
})

watch(
  () => route.query,
  (newQuery) => {
    activeFilters.value = { ...newQuery }
    searchText.value = newQuery.search || ''
    loadPrinters()
  },
  { immediate: true },
)

const openFilterModal = async () => {
  try {
    temporaryFilters.manufacturer__name = activeFilters.value.manufacturer__name || ''
    temporaryFilters.status = activeFilters.value.status || ''
    if (filterOptions.value.brands.length === 0) {
      const brandsRes = await APIService.getBrands()
      filterOptions.value.brands = brandsRes.data
    }
    isFilterModalVisible.value = true
  } catch (error) {
    console.error('Failed to load filter options:', error)
  }
}

const applyFilters = () => {
  const newFilters = { ...route.query } // Start with existing query

  // Update or remove each filter based on temporary values
  for (const key in temporaryFilters) {
    if (temporaryFilters[key]) {
      newFilters[key] = temporaryFilters[key]
    } else {
      delete newFilters[key] // Remove filter if set to "All" (empty)
    }
  }

  localStorage.setItem(filterStorageKey, JSON.stringify(newFilters))
  isFilterModalVisible.value = false
  router.push({ query: newFilters })
}

const clearFilters = () => {
  temporaryFilters.manufacturer__name = ''
  temporaryFilters.status = ''
  localStorage.removeItem(filterStorageKey)
  router.push({ query: { search: searchText.value || undefined } })
}

const clearFiltersAndClose = () => {
  clearFilters()
  isFilterModalVisible.value = false
}

onMounted(() => {
  loadColumns()

  // Restore filters from localStorage if they exist and not already in URL
  const storedFilters = localStorage.getItem(filterStorageKey)
  if (storedFilters && Object.keys(route.query).length === 0) {
    try {
      const filters = JSON.parse(storedFilters)
      router.replace({ query: filters })
    } catch (error) {
      console.error('Failed to restore filters:', error)
    }
  }
})
</script>

<template>
  <main>
    <MainHeader
      title="Printers"
      createUrl="/printers/create"
      v-model="searchText"
      @open-filter="openFilterModal"
      @open-columns="isColumnModalVisible = true"
    />
    <div class="filter-indicator" v-if="isFilterActive">
      <span>Filters are active.</span>
      <button @click="clearFilters">Clear Filters</button>
    </div>
    <PrinterList :items="printers" :visible-columns="visibleColumns" />

    <Teleport to="body">
      <ColumnConfigModal
        v-if="isColumnModalVisible"
        :all-columns="allPrinterColumns"
        :visible-columns="visibleColumns"
        @close="isColumnModalVisible = false"
        @save="saveColumns"
      />

      <div v-if="isFilterModalVisible" class="modal-overlay" @click="isFilterModalVisible = false">
        <div class="modal-form" @click.stop>
          <h3>Filter Printers</h3>
          <form @submit.prevent="applyFilters">
            <div class="form-group">
              <label>Manufacturer</label>
              <select v-model="temporaryFilters.manufacturer__name">
                <option value="">-- All --</option>
                <option v-for="brand in filterOptions.brands" :key="brand.id" :value="brand.name">
                  {{ brand.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>Status</label>
              <select v-model="temporaryFilters.status">
                <option value="">-- All --</option>
                <option v-for="status in filterOptions.statuses" :key="status" :value="status">
                  {{ status }}
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
    </Teleport>
  </main>
</template>

<style scoped>
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
