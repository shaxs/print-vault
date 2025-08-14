<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'
import BaseModal from '@/components/BaseModal.vue'

const route = useRoute()
const router = useRouter()
const item = ref(null)
const itemId = route.params.id
const isPhotoModalVisible = ref(false)
const isDeleteModalVisible = ref(false)

const handleDeleteConfirm = async () => {
  try {
    await APIService.deleteInventoryItem(itemId)
    isDeleteModalVisible.value = false
    router.push('/')
  } catch (error) {
    console.error('Error deleting item:', error)
    isDeleteModalVisible.value = false
  }
}

const filterList = (filterKey, filterValue) => {
  const query = {}
  query[filterKey] = filterValue
  router.push({ name: 'home', query })
}

onMounted(async () => {
  try {
    const response = await APIService.getInventoryItem(itemId)
    item.value = response.data
  } catch (error) {
    console.error('Error loading item details:', error)
  }
})

watch(isPhotoModalVisible, (newValue) => {
  const handleKeydown = (event) => {
    if (event.key === 'Escape') {
      isPhotoModalVisible.value = false
    }
  }
  if (newValue) {
    window.addEventListener('keydown', handleKeydown)
  } else {
    window.removeEventListener('keydown', handleKeydown)
  }
})
</script>

<template>
  <div class="detail-view">
    <MainHeader
      v-if="item"
      :title="item.title"
      :showSearch="false"
      :showAddButton="false"
      :showFilterButton="false"
      :showColumnButton="false"
    />

    <div class="actions-bar" v-if="item">
      <RouterLink
        :to="{ name: 'item-edit', params: { id: item.id } }"
        class="action-button edit-button"
        >Edit</RouterLink
      >
      <button @click="isDeleteModalVisible = true" class="action-button delete-button">
        Delete
      </button>
    </div>

    <div v-if="item" class="details-container">
      <div class="detail-item">
        <span class="label">Brand</span>
        <span
          v-if="item.brand"
          class="value clickable-link"
          @click="filterList('brand__name', item.brand.name)"
          >{{ item.brand.name }}</span
        >
        <span v-else class="value">N/A</span>
      </div>
      <div class="detail-item">
        <span class="label">Part Type</span>
        <span
          v-if="item.part_type"
          class="value clickable-link"
          @click="filterList('part_type__name', item.part_type.name)"
          >{{ item.part_type.name }}</span
        >
        <span v-else class="value">N/A</span>
      </div>
      <div class="detail-item">
        <span class="label">Location</span>
        <span
          v-if="item.location"
          class="value clickable-link"
          @click="filterList('location__name', item.location.name)"
          >{{ item.location.name }}</span
        >
        <span v-else class="value">N/A</span>
      </div>
      <div class="detail-item">
        <span class="label">Quantity</span><span class="value">{{ item.quantity }}</span>
      </div>
      <div class="detail-item">
        <span class="label">Cost</span><span class="value">${{ item.cost }}</span>
      </div>
      <div class="detail-item">
        <span class="label">Associated Projects</span>
        <div v-if="item.associated_projects && item.associated_projects.length">
          <RouterLink
            v-for="project in item.associated_projects"
            :key="project.id"
            :to="`/projects/${project.id}`"
            class="project-link"
            >{{ project.project_name }}</RouterLink
          >
        </div>
        <span v-else class="value">None</span>
      </div>
      <div class="detail-item full-width">
        <span class="label">Notes</span>
        <p class="value-notes">{{ item.notes || 'No notes.' }}</p>
      </div>
      <div class="detail-item full-width">
        <span class="label">Photo</span>
        <img
          v-if="item.photo"
          :src="item.photo"
          @click="isPhotoModalVisible = true"
          alt="Inventory item photo"
          class="detail-photo clickable"
        />
        <span v-else class="value">No photo.</span>
      </div>
    </div>
    <div v-else><p>Loading item details...</p></div>

    <BaseModal
      :show="isDeleteModalVisible"
      title="Confirm Deletion"
      @close="isDeleteModalVisible = false"
    >
      <p>
        Are you sure you want to delete the item '{{ item?.title }}'? This action cannot be undone.
      </p>
      <template #footer>
        <button @click="handleDeleteConfirm" class="delete-button action-button">
          Yes, Delete
        </button>
        <button
          @click="isDeleteModalVisible = false"
          type="button"
          class="cancel-button action-button"
        >
          Cancel
        </button>
      </template>
    </BaseModal>

    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button
        ><img :src="item.photo" alt="Full size item photo" class="modal-image" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-view {
  user-select: none;
}
.actions-bar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-bottom: 20px;
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
  user-select: none; /* Prevents text selection cursor */
}
.edit-button {
  background-color: var(--color-blue);
  color: white;
}
.delete-button {
  background-color: var(--color-red);
  color: white;
}
.details-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 20px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.detail-item {
  display: flex;
  flex-direction: column;
  flex-basis: calc(50% - 10px);
}
.detail-item.full-width {
  flex-basis: 100%;
}
.label {
  font-weight: bold;
  color: var(--color-text);
  font-size: 0.9rem;
  margin-bottom: 5px;
}
.value {
  font-size: 1.1rem;
  color: var(--color-heading);
}
.value-notes {
  font-size: 1rem;
  white-space: pre-wrap;
  margin: 0;
  color: var(--color-heading);
}
.detail-photo {
  max-width: 300px;
  max-height: 300px;
  border-radius: 8px;
  margin-top: 5px;
  cursor: pointer;
}
.project-link {
  color: var(--color-heading);
  text-decoration: none;
  display: block;
}
.project-link:hover {
  text-decoration: underline;
}
.clickable-link {
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: transparent;
  transition: text-decoration-color 0.3s;
}
.clickable-link:hover {
  text-decoration-color: var(--color-heading);
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
.modal-content {
  position: relative;
  max-width: 90vw;
  max-height: 90vh;
}
.modal-image {
  max-width: 100%;
  max-height: 100%;
  display: block;
}
.close-button {
  position: absolute;
  top: -15px;
  right: -15px;
  background: white;
  color: black;
  border: none;
  border-radius: 50%;
  width: 30px;
  height: 30px;
  font-size: 24px;
  line-height: 30px;
  text-align: center;
  cursor: pointer;
  font-weight: bold;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
}
@media (max-width: 768px) {
  .detail-item {
    flex-basis: 100%;
  }
}
</style>
