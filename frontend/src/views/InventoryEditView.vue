<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'
import InventoryForm from '@/components/InventoryForm.vue'

const route = useRoute()
const itemToEdit = ref(null)
const isLoading = ref(false)

// Store view state in reactive ref that updates when route changes
// We'll also use sessionStorage as a backup since Vue Router's state can be unreliable
const viewState = ref({
  filteredItemIds: null,
  currentIndex: null,
})

// Update view state from history when component loads or route changes
const updateViewState = () => {
  const state = history.state || {}

  // Try to get from history.state first
  let filteredItemIds = state.filteredItemIds || null
  let currentIndex = state.currentIndex !== undefined ? state.currentIndex : null

  // If not in history.state, try sessionStorage as backup
  if (!filteredItemIds) {
    const stored = sessionStorage.getItem('inventoryNavState')
    if (stored) {
      const parsed = JSON.parse(stored)
      filteredItemIds = parsed.filteredItemIds
      currentIndex = parsed.currentIndex
      // Don't overwrite - sessionStorage may have been updated just before navigation
    }
  } else {
    // Don't write to sessionStorage - it may have already been updated by the handler
  }

  viewState.value = { filteredItemIds, currentIndex }
}

const loadItem = async () => {
  isLoading.value = true
  try {
    const itemId = route.params.id
    const response = await APIService.getInventoryItem(itemId)
    itemToEdit.value = response.data
  } catch (error) {
    console.error('Error loading item to edit:', error)
  } finally {
    isLoading.value = false
  }
}

// Watch for route param changes to reload data when navigating between items
watch(
  () => route.params.id,
  () => {
    updateViewState()
    loadItem()
  },
  { immediate: true },
)
</script>

<template>
  <div>
    <MainHeader title="Edit Item" :showSearch="false" :showAddButton="false" />
    <p v-if="isLoading">Loading item...</p>
    <InventoryForm
      v-else-if="itemToEdit"
      :key="`item-${route.params.id}-${viewState.currentIndex}`"
      :initial-data="itemToEdit"
      :filtered-item-ids="viewState.filteredItemIds"
      :current-index="viewState.currentIndex"
    />
    <p v-else>Loading item...</p>
  </div>
</template>
