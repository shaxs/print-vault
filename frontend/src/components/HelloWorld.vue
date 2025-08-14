<script setup>
import { ref, onMounted, watch, reactive, computed } from 'vue'
import APIService from '@/services/APIService.js'
import MainHeader from '../components/MainHeader.vue'
import InventoryList from '../components/InventoryList.vue'

const inventoryItems = ref([])
const searchText = ref('')
const isFilterModalVisible = ref(false)
const activeFilters = ref({})
const filterOptions = ref({ brands: [], partTypes: [], locations: [] })
const temporaryFilters = reactive({ brand__name: '', part_type__name: '', location__name: '' })

const isFilterActive = computed(() => {
  return Object.values(activeFilters.value).some((val) => val)
})

const loadInventory = async () => {
  try {
    const params = { ...activeFilters.value }
    if (searchText.value) {
      params.search = searchText.value
    }
    const response = await APIService.getInventoryItems(params)
    inventoryItems.value = response.data
  } catch (error) {
    console.error('Failed to load inventory:', error)
  }
}

watch(searchText, () => {
  loadInventory()
})

const openFilterModal = async () => {
  try {
    temporaryFilters.brand__name = activeFilters.value.brand__name || ''
    temporaryFilters.part_type__name = activeFilters.value.part_type__name || ''
    temporaryFilters.location__name = activeFilters.value.location__name || ''

    const [brandsRes, partTypesRes, locationsRes] = await Promise.all([
      APIService.getBrands(),
      APIService.getPartTypes(),
      APIService.getLocations(),
    ])
    filterOptions.value.brands = brandsRes.data
    filterOptions.value.partTypes = partTypesRes.data
    filterOptions.value.locations = locationsRes.data
    isFilterModalVisible.value = true
  } catch (error) {
    console.error('Failed to load filter options:', error)
  }
}

const applyFilters = () => {
  activeFilters.value = { ...temporaryFilters }
  isFilterModalVisible.value = false
  loadInventory()
}

const clearFilters = () => {
  activeFilters.value = {}
  temporaryFilters.brand__name = ''
  temporaryFilters.part_type__name = ''
  temporaryFilters.location__name = ''
  loadInventory()
}

onMounted(() => {
  loadInventory()
})
</script>

<template>
  <main>
    <MainHeader
      title="Parts List"
      createUrl="/create"
      v-model="searchText"
      @open-filter="openFilterModal"
    />
    <div class="filter-indicator" v-if="isFilterActive">
      <span>Filters are active.</span>
      <button @click="clearFilters">Clear Filters</button>
    </div>
    <InventoryList :items="inventoryItems" />

    <div v-if="isFilterModalVisible" class="modal-overlay" @click="isFilterModalVisible = false">
      <div class="modal-form" @click.stop>
        <h3>Filter Inventory</h3>
        <form @submit.prevent="applyFilters">
          <div class="form-group">
            <label>Brand</label>
            <select v-model="temporaryFilters.brand__name">
              <option value="">-- All --</option>
              <option v-for="brand in filterOptions.brands" :key="brand.id" :value="brand.name">
                {{ brand.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>Part Type</label>
            <select v-model="temporaryFilters.part_type__name">
              <option value="">-- All --</option>
              <option v-for="pt in filterOptions.partTypes" :key="pt.id" :value="pt.name">
                {{ pt.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>Location</label>
            <select v-model="temporaryFilters.location__name">
              <option value="">-- All --</option>
              <option v-for="loc in filterOptions.locations" :key="loc.id" :value="loc.name">
                {{ loc.name }}
              </option>
            </select>
          </div>
          <div class="form-actions">
            <button type="submit" class="save-button">Apply Filters</button>
            <button @click="isFilterModalVisible = false" type="button" class="cancel-button">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
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
  color: var(--color-blue);
  cursor: pointer;
  text-decoration: underline;
  font-size: 0.9rem;
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
  max-width: 400px;
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
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.save-button,
.cancel-button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  text-decoration: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
}
.save-button {
  background-color: var(--color-blue);
  color: white;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
}
</style>
