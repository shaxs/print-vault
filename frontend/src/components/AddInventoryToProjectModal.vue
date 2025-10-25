<script setup>
import { ref, computed, watch } from 'vue'
import BaseModal from './BaseModal.vue'
import APIService from '../services/APIService'

const props = defineProps({
  show: {
    type: Boolean,
    required: true,
  },
  projectId: {
    type: Number,
    required: true,
  },
  existingInventoryIds: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'added'])

const allInventoryItems = ref([])
const selectedItems = ref([])
const searchQuery = ref('')
const brandFilter = ref('')
const partTypeFilter = ref('')
const locationFilter = ref('')
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const filterOptions = ref({ brands: [], partTypes: [], locations: [] })

// Filter available items (not already associated)
const availableItems = computed(() => {
  return allInventoryItems.value.filter((item) => !props.existingInventoryIds.includes(item.id))
})

// Filter items based on search query and filters
const filteredItems = computed(() => {
  let items = availableItems.value

  // Apply search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    items = items.filter((item) => {
      return (
        item.title.toLowerCase().includes(query) ||
        item.brand?.name.toLowerCase().includes(query) ||
        item.part_type?.name.toLowerCase().includes(query) ||
        item.location?.name.toLowerCase().includes(query)
      )
    })
  }

  // Apply brand filter
  if (brandFilter.value) {
    items = items.filter((item) => item.brand?.name === brandFilter.value)
  }

  // Apply part type filter
  if (partTypeFilter.value) {
    items = items.filter((item) => item.part_type?.name === partTypeFilter.value)
  }

  // Apply location filter
  if (locationFilter.value) {
    items = items.filter((item) => item.location?.name === locationFilter.value)
  }

  return items
})

// Check if item is selected
const isSelected = (itemId) => {
  return selectedItems.value.includes(itemId)
}

// Toggle item selection
const toggleItem = (itemId) => {
  const index = selectedItems.value.indexOf(itemId)
  if (index > -1) {
    selectedItems.value.splice(index, 1)
  } else {
    selectedItems.value.push(itemId)
  }
}

// Select all filtered items
const selectAll = () => {
  const allFilteredIds = filteredItems.value.map((item) => item.id)
  selectedItems.value = [...new Set([...selectedItems.value, ...allFilteredIds])]
}

// Deselect all items
const deselectAll = () => {
  selectedItems.value = []
}

// Fetch all inventory items
const fetchInventoryItems = async () => {
  try {
    isLoading.value = true
    errorMessage.value = ''
    const [itemsResponse, brandsResponse, partTypesResponse, locationsResponse] = await Promise.all(
      [
        APIService.getInventoryItems(),
        APIService.getBrands(),
        APIService.getPartTypes(),
        APIService.getLocations(),
      ],
    )
    allInventoryItems.value = itemsResponse.data.results || itemsResponse.data
    filterOptions.value.brands = brandsResponse.data
    filterOptions.value.partTypes = partTypesResponse.data
    filterOptions.value.locations = locationsResponse.data
  } catch (error) {
    console.error('Failed to fetch inventory items:', error)
    errorMessage.value = 'Failed to load inventory items. Please try again.'
  } finally {
    isLoading.value = false
  }
}

// Add selected items to project
const addSelectedItems = async () => {
  if (selectedItems.value.length === 0) {
    errorMessage.value = 'Please select at least one item to add.'
    return
  }

  try {
    isSaving.value = true
    errorMessage.value = ''

    // Add each selected item to the project
    await Promise.all(
      selectedItems.value.map((itemId) =>
        APIService.addInventoryToProject(props.projectId, itemId),
      ),
    )

    emit('added')
    handleClose()
  } catch (error) {
    console.error('Failed to add inventory items:', error)
    errorMessage.value = 'Failed to add some items. Please try again.'
  } finally {
    isSaving.value = false
  }
}

const handleClose = () => {
  selectedItems.value = []
  searchQuery.value = ''
  brandFilter.value = ''
  partTypeFilter.value = ''
  locationFilter.value = ''
  errorMessage.value = ''
  emit('close')
}

// Clear all filters
const clearFilters = () => {
  brandFilter.value = ''
  partTypeFilter.value = ''
  locationFilter.value = ''
}

// Check if any filters are active
const hasActiveFilters = computed(() => {
  return brandFilter.value || partTypeFilter.value || locationFilter.value
})

// Watch for modal open/close
watch(
  () => props.show,
  (newValue) => {
    if (newValue) {
      fetchInventoryItems()
    } else {
      // Reset state when closing
      selectedItems.value = []
      searchQuery.value = ''
      brandFilter.value = ''
      partTypeFilter.value = ''
      locationFilter.value = ''
      errorMessage.value = ''
    }
  },
)
</script>

<template>
  <BaseModal :show="show" title="Add Inventory Items" @close="handleClose" size="large">
    <div class="modal-body">
      <div v-if="errorMessage" class="error-banner">
        {{ errorMessage }}
      </div>

      <div class="search-section">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by title, brand, part type, or location..."
          class="search-input"
        />
      </div>

      <div class="filter-section">
        <div class="filter-row">
          <div class="filter-group">
            <label>Brand</label>
            <select v-model="brandFilter" class="filter-select">
              <option value="">All Brands</option>
              <option v-for="brand in filterOptions.brands" :key="brand.id" :value="brand.name">
                {{ brand.name }}
              </option>
            </select>
          </div>

          <div class="filter-group">
            <label>Part Type</label>
            <select v-model="partTypeFilter" class="filter-select">
              <option value="">All Part Types</option>
              <option
                v-for="partType in filterOptions.partTypes"
                :key="partType.id"
                :value="partType.name"
              >
                {{ partType.name }}
              </option>
            </select>
          </div>

          <div class="filter-group">
            <label>Location</label>
            <select v-model="locationFilter" class="filter-select">
              <option value="">All Locations</option>
              <option
                v-for="location in filterOptions.locations"
                :key="location.id"
                :value="location.name"
              >
                {{ location.name }}
              </option>
            </select>
          </div>
        </div>

        <div v-if="hasActiveFilters" class="filter-actions">
          <span class="filter-active-text">Filters active</span>
          <button @click="clearFilters" type="button" class="clear-filters-btn">
            Clear Filters
          </button>
        </div>
      </div>

      <div class="selection-actions">
        <button
          @click="selectAll"
          type="button"
          class="btn btn-sm btn-secondary"
          :disabled="filteredItems.length === 0"
        >
          Select All
        </button>
        <button
          @click="deselectAll"
          type="button"
          class="btn btn-sm btn-secondary"
          :disabled="selectedItems.length === 0"
        >
          Deselect All
        </button>
        <span class="selection-count"
          >{{ selectedItems.length }} item{{ selectedItems.length !== 1 ? 's' : '' }} selected</span
        >
      </div>

      <div v-if="isLoading" class="loading-state">
        <p>Loading inventory items...</p>
      </div>

      <div v-else-if="availableItems.length === 0" class="empty-state">
        <p>All inventory items are already associated with this project.</p>
      </div>

      <div v-else-if="filteredItems.length === 0" class="empty-state">
        <p>No items match your search.</p>
      </div>

      <div v-else class="items-list">
        <div
          v-for="item in filteredItems"
          :key="item.id"
          class="item-card"
          :class="{ selected: isSelected(item.id) }"
          @click="toggleItem(item.id)"
        >
          <div class="item-checkbox">
            <input
              type="checkbox"
              :checked="isSelected(item.id)"
              @click.stop="toggleItem(item.id)"
            />
          </div>
          <div class="item-photo">
            <img v-if="item.photo" :src="item.photo" :alt="item.title" />
            <div v-else class="no-photo">No Photo</div>
          </div>
          <div class="item-details">
            <div class="item-title">{{ item.title }}</div>
            <div class="item-meta">
              <span v-if="item.brand">{{ item.brand.name }}</span>
              <span v-if="item.part_type">• {{ item.part_type.name }}</span>
              <span v-if="item.location">• {{ item.location.name }}</span>
            </div>
            <div class="item-quantity">Qty: {{ item.quantity }}</div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <button
        @click="addSelectedItems"
        type="button"
        class="btn btn-primary"
        :disabled="selectedItems.length === 0 || isSaving"
      >
        <span v-if="isSaving">Adding...</span>
        <span v-else
          >Add {{ selectedItems.length }} Item{{ selectedItems.length !== 1 ? 's' : '' }}</span
        >
      </button>
      <button @click="handleClose" type="button" class="btn btn-secondary" :disabled="isSaving">
        Cancel
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.modal-body {
  max-height: 600px;
  overflow-y: auto;
}

.error-banner {
  background-color: var(--color-red);
  color: white;
  padding: 0.75rem 1rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.search-section {
  margin-bottom: 1rem;
}

.search-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 1rem;
  background-color: var(--color-background);
  color: var(--color-text);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-brand);
}

.filter-section {
  margin-bottom: 1rem;
}

.filter-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.filter-group {
  display: flex;
  flex-direction: column;
}

.filter-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--color-heading);
  margin-bottom: 0.25rem;
}

.filter-select {
  padding: 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.875rem;
  background-color: var(--color-background);
  color: var(--color-text);
  cursor: pointer;
}

.filter-select:focus {
  outline: none;
  border-color: var(--color-brand);
}

.filter-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background-color: var(--color-background-mute);
  border-radius: 4px;
}

.filter-active-text {
  font-size: 0.875rem;
  color: var(--color-text);
}

.clear-filters-btn {
  background: none;
  border: none;
  color: var(--color-brand);
  cursor: pointer;
  font-size: 0.875rem;
  text-decoration: underline;
  padding: 0;
}

.clear-filters-btn:hover {
  color: var(--color-heading);
}

.selection-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}

.selection-count {
  margin-left: auto;
  font-size: 0.875rem;
  color: var(--color-text);
  font-weight: 500;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--color-text);
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.item-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border: 2px solid var(--color-border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  background-color: var(--color-background-soft);
}

.item-card:hover {
  border-color: var(--color-brand);
  background-color: var(--color-background-mute);
}

.item-card.selected {
  border-color: var(--color-brand);
  background-color: var(--color-background-mute);
}

.item-checkbox {
  flex-shrink: 0;
}

.item-checkbox input[type='checkbox'] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.item-photo {
  flex-shrink: 0;
  width: 60px;
  height: 60px;
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.item-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.no-photo {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-background-mute);
  font-size: 0.75rem;
  color: var(--color-text-soft);
}

.item-details {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-weight: 600;
  font-size: 1rem;
  color: var(--color-heading);
  margin-bottom: 0.25rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  font-size: 0.875rem;
  color: var(--color-text);
  margin-bottom: 0.25rem;
}

.item-quantity {
  font-size: 0.875rem;
  color: var(--color-text);
}
</style>
