<script setup>
import { ref, onMounted } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import APIService from '@/services/APIService.js'

const locations = ref([])
const isEditModalVisible = ref(false)
const editingItem = ref(null)
const isDeleteModalVisible = ref(false)
const itemToDelete = ref(null)

const loadLocations = async () => {
  try {
    const response = await APIService.getLocations()
    locations.value = response.data
  } catch (error) {
    console.error('Failed to load locations:', error)
  }
}

const openEditModal = (item) => {
  editingItem.value = { ...item }
  isEditModalVisible.value = true
}

const openAddModal = () => {
  editingItem.value = { name: '' }
  isEditModalVisible.value = true
}

const saveItem = async () => {
  if (!editingItem.value || !editingItem.value.name) return
  const isEditing = !!editingItem.value.id
  const data = { name: editingItem.value.name }
  try {
    if (isEditing) {
      await APIService.updateLocation(editingItem.value.id, data)
    } else {
      await APIService.createLocation(data)
    }
    isEditModalVisible.value = false
    editingItem.value = null
    loadLocations()
  } catch (error) {
    console.error('Failed to save location:', error)
  }
}

const openDeleteItemModal = (item) => {
  itemToDelete.value = item
  isDeleteModalVisible.value = true
}

const handleDeleteConfirm = async () => {
  if (!itemToDelete.value) return
  try {
    await APIService.deleteLocation(itemToDelete.value.id)
    loadLocations()
  } catch (error) {
    console.error('Failed to delete location:', error)
  } finally {
    isDeleteModalVisible.value = false
    itemToDelete.value = null
  }
}

onMounted(() => {
  loadLocations()
})
</script>

<template>
  <div>
    <div class="content-header">
      <h3>Manage Locations</h3>
      <button @click="openAddModal" class="btn btn-primary">Add New</button>
    </div>
    <ul class="locations-list">
      <li v-for="location in locations" :key="location.id" class="location-item">
        <span>{{ location.name }}</span>
        <div class="actions-cell">
          <button @click="openEditModal(location)" class="btn btn-sm btn-primary">Edit</button>
          <button @click="openDeleteItemModal(location)" class="btn btn-sm btn-danger">
            Delete
          </button>
        </div>
      </li>
    </ul>

    <BaseModal
      :show="isEditModalVisible"
      :title="editingItem && editingItem.id ? 'Edit Location' : 'Add New Location'"
      @close="isEditModalVisible = false"
    >
      <form @submit.prevent="saveItem">
        <div class="form-group">
          <label for="name">Name</label>
          <input id="name" type="text" v-model="editingItem.name" required />
        </div>
      </form>
      <template #footer>
        <button @click="isEditModalVisible = false" type="button" class="btn btn-secondary">
          Cancel
        </button>
        <button @click="saveItem" class="btn btn-primary">Save</button>
      </template>
    </BaseModal>

    <BaseModal
      :show="isDeleteModalVisible"
      title="Confirm Deletion"
      @close="isDeleteModalVisible = false"
    >
      <p>Are you sure you want to delete '{{ itemToDelete?.name }}'?</p>
      <template #footer>
        <button @click="isDeleteModalVisible = false" type="button" class="btn btn-secondary">
          Cancel
        </button>
        <button @click="handleDeleteConfirm" class="btn btn-danger">Yes, Delete</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.content-header h3 {
  color: var(--color-heading);
}
.locations-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}
.location-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid var(--color-border);
}
.actions-cell {
  display: flex;
  gap: 10px;
}
/* Removed custom button styles; use global .btn classes */
.form-group {
  margin-bottom: 1rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: var(--color-heading);
}
.form-group input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}
</style>
