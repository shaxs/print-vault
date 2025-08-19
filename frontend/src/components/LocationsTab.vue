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
      <button @click="openAddModal" class="action-button add-button">Add New</button>
    </div>
    <ul class="locations-list">
      <li v-for="location in locations" :key="location.id" class="location-item">
        <span>{{ location.name }}</span>
        <div class="actions-cell">
          <button @click="openEditModal(location)" class="action-button edit-button">Edit</button>
          <button @click="openDeleteItemModal(location)" class="action-button delete-button">
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
        <button @click="saveItem" class="action-button save-button">Save</button>
        <button
          @click="isEditModalVisible = false"
          type="button"
          class="action-button cancel-button"
        >
          Cancel
        </button>
      </template>
    </BaseModal>

    <BaseModal
      :show="isDeleteModalVisible"
      title="Confirm Deletion"
      @close="isDeleteModalVisible = false"
    >
      <p>Are you sure you want to delete '{{ itemToDelete?.name }}'?</p>
      <template #footer>
        <button @click="handleDeleteConfirm" class="action-button delete-button">
          Yes, Delete
        </button>
        <button
          @click="isDeleteModalVisible = false"
          type="button"
          class="action-button cancel-button"
        >
          Cancel
        </button>
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
.action-button {
  padding: 8px 15px;
  text-decoration: none;
  border-radius: 5px;
  font-weight: bold;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  font-size: 0.9rem;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.edit-button,
.add-button,
.save-button {
  background-color: var(--color-blue);
  color: white;
}
.delete-button {
  background-color: var(--color-red);
  color: white;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
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
