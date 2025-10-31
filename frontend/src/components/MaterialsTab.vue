<script setup>
import { ref, onMounted } from 'vue'
import BaseModal from '@/components/BaseModal.vue'
import APIService from '@/services/APIService.js'

const materials = ref([])
const isEditModalVisible = ref(false)
const editingItem = ref(null)
const isDeleteModalVisible = ref(false)
const itemToDelete = ref(null)

const loadMaterials = async () => {
  try {
    const response = await APIService.getMaterials()
    materials.value = response.data
  } catch (error) {
    console.error('Failed to load materials:', error)
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
      await APIService.updateMaterial(editingItem.value.id, data)
    } else {
      await APIService.createMaterial(data)
    }
    isEditModalVisible.value = false
    editingItem.value = null
    loadMaterials()
  } catch (error) {
    console.error('Failed to save material:', error)
  }
}

const openDeleteItemModal = (item) => {
  itemToDelete.value = item
  isDeleteModalVisible.value = true
}

const handleDeleteConfirm = async () => {
  if (!itemToDelete.value) return
  try {
    await APIService.deleteMaterial(itemToDelete.value.id)
    loadMaterials()
  } catch (error) {
    console.error('Failed to delete material:', error)
  } finally {
    isDeleteModalVisible.value = false
    itemToDelete.value = null
  }
}

onMounted(() => {
  loadMaterials()
})
</script>

<template>
  <div>
    <div class="content-header">
      <h3>Manage 3D Printing Materials</h3>
      <button @click="openAddModal" class="btn btn-primary">Add New</button>
    </div>
    <ul class="materials-list">
      <li v-for="material in materials" :key="material.id" class="material-item">
        <span>{{ material.name }}</span>
        <div class="actions-cell">
          <button @click="openEditModal(material)" class="btn btn-sm btn-primary">Edit</button>
          <button @click="openDeleteItemModal(material)" class="btn btn-sm btn-danger">
            Delete
          </button>
        </div>
      </li>
    </ul>

    <BaseModal
      :show="isEditModalVisible"
      :title="editingItem && editingItem.id ? 'Edit Material' : 'Add New Material'"
      @close="isEditModalVisible = false"
    >
      <form @submit.prevent="saveItem">
        <div class="form-group">
          <label for="name">Name</label>
          <input id="name" type="text" v-model="editingItem.name" required />
        </div>
      </form>
      <template #footer>
        <button @click="saveItem" class="btn btn-primary">Save</button>
        <button @click="isEditModalVisible = false" type="button" class="btn btn-secondary">
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
        <button @click="handleDeleteConfirm" class="btn btn-danger">Yes, Delete</button>
        <button @click="isDeleteModalVisible = false" type="button" class="btn btn-secondary">
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
.materials-list {
  list-style-type: none;
  padding: 0;
  margin: 0;
}
.material-item {
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
