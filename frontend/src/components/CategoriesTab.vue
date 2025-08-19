<script setup>
import { ref, computed, watch } from 'vue'
import APIService from '@/services/APIService.js'
import DataTable from '@/components/DataTable.vue'
import BaseModal from '@/components/BaseModal.vue'

const props = defineProps({
  categoryType: {
    type: String,
    required: true,
    validator: (value) => ['brands', 'partTypes', 'locations'].includes(value),
  },
})

const items = ref([])
const isEditModalVisible = ref(false)
const editingItem = ref(null)
const isDeleteModalVisible = ref(false)
const itemToDelete = ref(null)

const headers = [
  { text: 'Name', value: 'name' },
  { text: 'Actions', value: 'actions' },
]

const title = computed(() => {
  if (props.categoryType === 'brands') return 'Manage Brands & Manufacturers'
  if (props.categoryType === 'partTypes') return 'Manage Part Types'
  if (props.categoryType === 'locations') return 'Manage Locations'
  return ''
})

const api = computed(() => {
  const map = {
    brands: {
      get: APIService.getBrands,
      create: APIService.createBrand,
      update: APIService.updateBrand,
      delete: APIService.deleteBrand,
    },
    partTypes: {
      get: APIService.getPartTypes,
      create: APIService.createPartType,
      update: APIService.updatePartType,
      delete: APIService.deletePartType,
    },
    locations: {
      get: APIService.getLocations,
      create: APIService.createLocation,
      update: APIService.updateLocation,
      delete: APIService.deleteLocation,
    },
  }
  return map[props.categoryType]
})

const loadData = async () => {
  try {
    const response = await api.value.get()
    items.value = response.data
  } catch (error) {
    console.error(`Failed to load ${props.categoryType}:`, error)
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
      await api.value.update(editingItem.value.id, data)
    } else {
      await api.value.create(data)
    }
    isEditModalVisible.value = false
    editingItem.value = null
    loadData()
  } catch (error) {
    console.error('Failed to save item:', error)
  }
}

const openDeleteItemModal = (item) => {
  itemToDelete.value = item
  isDeleteModalVisible.value = true
}

const handleDeleteConfirm = async () => {
  if (!itemToDelete.value) return
  try {
    await api.value.delete(itemToDelete.value.id)
    loadData()
  } catch (error) {
    console.error('Failed to delete item:', error)
  } finally {
    isDeleteModalVisible.value = false
    itemToDelete.value = null
  }
}

watch(() => props.categoryType, loadData, { immediate: true })
</script>

<template>
  <div>
    <div class="content-header">
      <h3>{{ title }}</h3>
      <button @click="openAddModal" class="action-button add-button">Add New</button>
    </div>
    <DataTable
      :headers="headers"
      :items="items"
      :visible-columns="headers.map((h) => h.value)"
      @row-click.stop
    >
      <template #cell-name="{ item }">{{ item.name }}</template>
      <template #cell-actions="{ item }">
        <div class="actions-cell">
          <button @click="openEditModal(item)" class="action-button edit-button">Edit</button>
          <button @click="openDeleteItemModal(item)" class="action-button delete-button">
            Delete
          </button>
        </div>
      </template>
    </DataTable>

    <BaseModal
      :show="isEditModalVisible"
      :title="editingItem && editingItem.id ? 'Edit Name' : 'Add New Name'"
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
/* Scoped styles copied from SettingsView.vue */
.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.content-header h3 {
  color: var(--color-heading);
}
.actions-cell {
  display: flex;
  gap: 10px;
  align-items: center;
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
