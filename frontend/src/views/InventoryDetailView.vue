<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import DataTable from '../components/DataTable.vue'
import BaseModal from '../components/BaseModal.vue'

const route = useRoute()
const router = useRouter()
const item = ref(null)
const isLoading = ref(true)
const isDeleteModalVisible = ref(false)
const isPhotoModalVisible = ref(false)

const fetchInventoryItem = async () => {
  try {
    const response = await APIService.getInventoryItem(route.params.id)
    item.value = response.data
  } catch (error) {
    console.error('Failed to fetch inventory item:', error)
  } finally {
    isLoading.value = false
  }
}

const deleteItem = async () => {
  if (confirm(`Are you sure you want to delete "${item.value.title}"? This cannot be undone.`)) {
    try {
      await APIService.deleteInventoryItem(item.value.id)
      router.push({ name: 'home' })
    } catch (error) {
      console.error('Failed to delete item:', error)
    }
  }
}

const removeProjectAssociation = async (project) => {
  if (
    confirm(`Are you sure you want to remove the project "${project.project_name}" from this item?`)
  ) {
    try {
      await APIService.removeProjectFromInventory(item.value.id, project.id)
      await fetchInventoryItem() // Refresh the data
    } catch (error) {
      console.error('Failed to remove project association:', error)
    }
  }
}

const projectHeaders = computed(() => [
  { text: 'Project Name', value: 'project_name' },
  { text: 'Action', value: 'actions', sortable: false },
])

const viewProject = (project) => {
  router.push({ name: 'project-detail', params: { id: project.id } })
}

onMounted(fetchInventoryItem)
</script>

<template>
  <div v-if="isLoading" class="loading-state">
    <p>Loading...</p>
  </div>
  <div v-else-if="item" class="page-container">
    <div class="detail-header">
      <h1>{{ item.title }}</h1>
      <div class="actions">
        <router-link :to="`/item/${item.id}/edit`" class="btn btn-primary">Edit Item</router-link>
        <button @click="deleteItem" class="btn btn-danger">Delete</button>
      </div>
    </div>

    <div class="detail-grid">
      <div class="photo-column">
        <div class="card photo-card">
          <div class="card-header">
            <h3>Item Photo</h3>
          </div>
          <div class="card-body photo-card-body">
            <img
              v-if="item.photo"
              :src="item.photo"
              :alt="item.title"
              class="detail-photo clickable"
              @click="isPhotoModalVisible = true"
            />
            <div v-else class="no-photo">No Photo Available</div>
          </div>
        </div>
      </div>

      <div class="details-column">
        <div class="card">
          <div class="card-header">
            <h3>Item Details</h3>
          </div>
          <div class="card-body">
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Brand:</span>
                <span class="value">{{ item.brand?.name || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Part Type:</span>
                <span class="value">{{ item.part_type?.name || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Location:</span>
                <span class="value">{{ item.location?.name || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Quantity:</span>
                <span class="value">{{ item.quantity }}</span>
              </div>
              <div class="info-item">
                <span class="label">Cost:</span>
                <span class="value">{{ item.cost ? `$${item.cost}` : 'N/A' }}</span>
              </div>
              <div v-if="item.is_consumable" class="info-item">
                <span class="label">Low Stock Alert:</span>
                <span class="value">Enabled</span>
              </div>
              <div v-if="item.is_consumable" class="info-item">
                <span class="label">Warning Threshold:</span>
                <span class="value">{{ item.low_stock_threshold ?? 'Not Set' }}</span>
              </div>
            </div>
            <hr v-if="item.notes" />
            <div v-if="item.notes" class="notes-section">
              <h4>Notes</h4>
              <p class="notes-content">{{ item.notes }}</p>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Associated Projects</h3>
          </div>
          <div class="card-body table-card-body">
            <DataTable
              :headers="projectHeaders"
              :items="item.associated_projects"
              :visible-columns="projectHeaders.map((h) => h.value)"
              @row-click="viewProject"
              empty-message="No Projects Associated."
              class="borderless-table"
            >
              <template #cell-project_name="{ item }">
                <span class="table-link grey-link">{{ item.project_name }}</span>
              </template>
              <template #cell-actions="{ item }">
                <button @click.stop="removeProjectAssociation(item)" class="btn-remove-inventory">
                  Remove
                </button>
              </template>
            </DataTable>
          </div>
        </div>
      </div>
    </div>

    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img :src="item.photo" :alt="item.title" class="modal-image" />
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
  </div>
</template>

<style scoped>
.page-container {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
}
.detail-header h1 {
  font-size: 2.5rem;
  font-weight: 600;
}
.actions {
  display: flex;
  gap: 1rem;
}
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 2rem;
}
.card-body.photo-card-body {
  padding: 1.5rem;
  display: flex;
  justify-content: center;
  align-items: center;
}
.detail-photo {
  width: 100%;
  max-width: 400px;
  height: auto;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}
.clickable {
  cursor: pointer;
}
.no-photo {
  width: 100%;
  aspect-ratio: 1/1;
  max-width: 400px;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--color-text-soft);
  font-weight: 500;
}
.card-body {
  padding: 0;
}
.info-grid {
  padding: 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}
.info-item {
  display: flex;
  align-items: baseline;
}
.info-item .label {
  font-weight: bold;
  color: var(--color-heading);
  margin-right: 0.5rem;
}
.info-item .value {
  font-size: 1rem;
}
hr {
  border: 0;
  border-top: 1px solid var(--color-border);
  margin: 0 1.5rem;
}
.notes-section {
  padding: 1.5rem;
}
.notes-section h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
}
.notes-content {
  white-space: pre-wrap;
}
.table-link.grey-link {
  color: var(--color-heading);
  text-decoration: none;
  cursor: pointer;
}
.table-link.grey-link:hover,
.table-link.grey-link:active,
.table-link.grey-link:visited {
  color: var(--color-heading);
  text-decoration: underline;
}
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
  border-radius: 8px;
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
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
.card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 2rem;
}
.card:last-child {
  margin-bottom: 0;
}
.card-header {
  padding: 1rem 1.5rem;
  background: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
}
.card-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: var(--color-heading);
}
.borderless-table :deep(table) {
  border-collapse: collapse;
  border: none;
  width: 100%;
  margin-top: 0;
}
.borderless-table :deep(th),
.borderless-table :deep(td) {
  border: none;
  border-bottom: 1px solid var(--color-border);
  padding: 10px 15px;
  text-align: left;
}
.borderless-table :deep(thead tr:first-child th) {
  border-top: none;
}
.borderless-table :deep(tbody tr:last-child td) {
  border-bottom: none;
}
.action-button {
  padding: 8px 15px;
  border: none;
  border-radius: 5px;
  text-decoration: none;
  font-weight: bold;
  cursor: pointer;
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
.btn-remove-inventory {
  background-color: var(--color-red);
  color: white;
  padding: 5px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}
</style>
