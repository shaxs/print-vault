<script setup>
import { ref, onMounted } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import APIService from '@/services/APIService.js'

const features = ref([])
const isEditModalVisible = ref(false)
const editingItem = ref(null)
const isDeleteModalVisible = ref(false)
const itemToDelete = ref(null)

const loadFeatures = async () => {
  try {
    const response = await APIService.getMaterialFeatures()
    features.value = response.data
  } catch (error) {
    console.error('Failed to load features:', error)
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
      await APIService.updateMaterialFeature(editingItem.value.id, data)
    } else {
      await APIService.createMaterialFeature(data)
    }
    isEditModalVisible.value = false
    editingItem.value = null
    loadFeatures()
  } catch (error) {
    console.error('Failed to save feature:', error)
  }
}

const openDeleteItemModal = (item) => {
  itemToDelete.value = item
  isDeleteModalVisible.value = true
}

const handleDeleteConfirm = async () => {
  if (!itemToDelete.value) return
  try {
    await APIService.deleteMaterialFeature(itemToDelete.value.id)
    loadFeatures()
  } catch (error) {
    console.error('Failed to delete feature:', error)
  } finally {
    isDeleteModalVisible.value = false
    itemToDelete.value = null
  }
}

onMounted(() => {
  loadFeatures()
})
</script>

<template>
  <div>
    <div class="content-header">
      <h3>Manage Material Features</h3>
      <button @click="openAddModal" class="btn btn-primary">Add New</button>
    </div>
    <p class="description">
      Material features are tags like "Matte", "High Speed", "Glitter", or "Carbon Filled" that you
      can apply to filament blueprints to help categorize and filter them.
    </p>
    <ul class="features-list">
      <li v-for="feature in features" :key="feature.id" class="feature-item">
        <span>{{ feature.name }}</span>
        <div class="actions-cell">
          <button @click="openEditModal(feature)" class="btn btn-sm btn-primary">Edit</button>
          <button @click="openDeleteItemModal(feature)" class="btn btn-sm btn-danger">
            Delete
          </button>
        </div>
      </li>
    </ul>

    <BaseModal
      :show="isEditModalVisible"
      :title="editingItem && editingItem.id ? 'Edit Feature' : 'Add New Feature'"
      @close="isEditModalVisible = false"
    >
      <form @submit.prevent="saveItem">
        <div class="form-group">
          <label for="name">Feature Name</label>
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
      <p>Are you sure you want to delete "{{ itemToDelete?.name }}"?</p>
      <p class="warning-text">This will remove the feature from all materials that use it.</p>
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
  margin-bottom: 10px;
}
.content-header h3 {
  color: var(--color-heading);
}
.description {
  color: var(--color-text-muted);
  font-size: 0.9rem;
  margin-bottom: 20px;
}
.features-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}
.feature-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  border-bottom: 1px solid var(--color-border);
}
.feature-item span {
  flex: 1;
  color: var(--color-text);
}
.actions-cell {
  display: flex;
  gap: 8px;
}
.warning-text {
  color: var(--color-danger, #dc3545);
  font-size: 0.875rem;
  margin-top: 0.5rem;
}
</style>
