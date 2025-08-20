<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import APIService from '@/services/APIService.js'
import BaseModal from '@/components/BaseModal.vue'

const route = useRoute()
const router = useRouter()
const item = ref(null)
const isDeleteModalVisible = ref(false)
const isPhotoModalVisible = ref(false)

const fetchInventoryItem = async () => {
  try {
    const response = await APIService.getInventoryItem(route.params.id)
    item.value = response.data
  } catch (error) {
    console.error('Failed to fetch inventory item:', error)
  }
}

const openDeleteModal = () => {
  isDeleteModalVisible.value = true
}

const confirmDelete = async () => {
  try {
    await APIService.deleteInventoryItem(item.value.id)
    router.push('/')
  } catch (error) {
    console.error('Failed to delete item:', error)
  } finally {
    isDeleteModalVisible.value = false
  }
}

onMounted(fetchInventoryItem)
</script>

<template>
  <div v-if="item" class="detail-view-container">
    <div class="main-content">
      <div class="item-header">
        <h1>{{ item.title }}</h1>
        <div class="actions">
          <RouterLink :to="`/item/${item.id}/edit`" class="action-button edit-button"
            >Edit</RouterLink
          >
          <button @click="openDeleteModal" class="action-button delete-button">Delete</button>
        </div>
      </div>

      <div class="details-grid">
        <div class="photo-container">
          <img
            v-if="item.photo"
            :src="item.photo"
            :alt="item.title"
            class="detail-photo clickable"
            @click="isPhotoModalVisible = true"
          />
          <div v-else class="no-photo">No Photo</div>
        </div>
        <div class="info-container">
          <div class="info-grid">
            <div class="info-item">
              <span class="label">Brand</span>
              <span class="value">{{ item.brand?.name || 'N/A' }}</span>
            </div>
            <div class="info-item">
              <span class="label">Part Type</span>
              <span class="value">{{ item.part_type?.name || 'N/A' }}</span>
            </div>
            <div class="info-item">
              <span class="label">Location</span>
              <span class="value">{{ item.location?.name || 'N/A' }}</span>
            </div>
            <div class="info-item">
              <span class="label">Quantity</span>
              <span class="value">{{ item.quantity }}</span>
            </div>
            <div class="info-item">
              <span class="label">Cost</span>
              <span class="value">{{ item.cost ? `$${item.cost}` : 'N/A' }}</span>
            </div>
            <div v-if="item.is_consumable" class="info-item">
              <span class="label">Status</span>
              <span class="value consumable-tag">Low Stock Alert Enabled</span>
            </div>
            <div v-if="item.is_consumable" class="info-item">
              <span class="label">Warning Threshold</span>
              <span class="value">{{ item.low_stock_threshold ?? 'Not Set' }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="notes-section" v-if="item.notes">
        <h2>Notes</h2>
        <p>{{ item.notes }}</p>
      </div>

      <!-- Associated Projects as a subsection inside main-content -->
      <div class="associated-projects-section">
        <h3>Associated Projects</h3>
        <ul v-if="item.associated_projects && item.associated_projects.length">
          <li v-for="project in item.associated_projects" :key="project.id">
            <RouterLink :to="`/project/${project.id}`">{{ project.project_name }}</RouterLink>
          </li>
        </ul>
        <p v-else>No projects associated with this item.</p>
      </div>
    </div>

    <BaseModal
      :show="isDeleteModalVisible"
      title="Confirm Deletion"
      @close="isDeleteModalVisible = false"
    >
      <p>Are you sure you want to permanently delete "{{ item.title }}"?</p>
      <template #footer>
        <button @click="confirmDelete" class="action-button delete-button">Yes, Delete</button>
        <button
          @click="isDeleteModalVisible = false"
          type="button"
          class="action-button cancel-button"
        >
          Cancel
        </button>
      </template>
    </BaseModal>

    <!-- Photo Lightbox Modal -->
    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img :src="item.photo" :alt="item.title" class="modal-image" />
      </div>
    </div>
  </div>
  <div v-else>Loading...</div>
</template>

<style scoped>
.detail-view-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
}
.main-content {
  background-color: var(--color-background-soft);
  padding: 20px;
  border-radius: 8px;
  width: 100%;
}
.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 15px;
  margin-bottom: 20px;
}
.item-header h1 {
  color: var(--color-heading);
}
.actions {
  display: flex;
  gap: 10px;
}
.action-button {
  padding: 8px 15px;
  border: none;
  border-radius: 5px;
  text-decoration: none;
  font-weight: bold;
  cursor: pointer;
}
.edit-button {
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

.details-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
}
.photo-container {
  width: 100%;
  margin-bottom: 20px;
}
.detail-photo {
  max-width: 300px;
  max-height: 300px;
  border-radius: 8px;
  margin-top: 5px;
  cursor: pointer;
}
.clickable {
  cursor: pointer;
}
.no-photo {
  width: 100%;
  aspect-ratio: 1/1;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--color-text-soft);
}
.info-container {
  margin-bottom: 20px;
}
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.info-item {
  display: flex;
  flex-direction: column;
}
.label {
  font-weight: bold;
  color: var(--color-heading);
  margin-bottom: 5px;
  font-size: 0.9rem;
}
.value {
  color: var(--color-text);
}
.consumable-tag {
  background-color: var(--color-orange-soft);
  color: var(--color-orange-dark);
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: bold;
  display: inline-block;
  font-size: 0.85rem;
}

.notes-section {
  margin-top: 30px;
}
.notes-section h2 {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 10px;
  margin-bottom: 15px;
}
.notes-section p {
  white-space: pre-wrap;
}

.associated-projects-section {
  background-color: var(--color-background-soft);
  padding: 20px;
  border-radius: 8px;
  margin-top: 30px;
}
.associated-projects-section h3 {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 10px;
  margin-bottom: 15px;
}
.associated-projects-section ul {
  list-style: none;
  padding: 0;
}
.associated-projects-section li a {
  text-decoration: none;
  color: var(--color-blue);
}

/* Modal styles for photo lightbox */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
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

@media (max-width: 992px) {
  .detail-view-container {
    padding: 10px;
  }
  .info-grid {
    grid-template-columns: 1fr;
  }
  .details-grid {
    grid-template-columns: 1fr;
  }
}
</style>
