<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'
import DataTable from '@/components/DataTable.vue'
import BaseModal from '@/components/BaseModal.vue'

const route = useRoute()
const router = useRouter()
const project = ref(null)
const projectId = route.params.id
const isModalVisible = ref(false)
const isDeleteModalVisible = ref(false)
const itemToDelete = ref(null)
const newLink = ref({ name: '', url: '' })
const newFiles = ref(null)
const newFileRef = ref(null)

const inventoryHeaders = [
  { text: 'Title', value: 'title' },
  { text: 'Brand', value: 'brand' },
  { text: 'Part Type', value: 'partType' },
  { text: 'Quantity', value: 'quantity' },
  { text: 'Cost', value: 'cost' },
  { text: 'Actions', value: 'actions' },
]
const printerHeaders = [
  { text: 'Title', value: 'title' },
  { text: 'Manufacturer', value: 'manufacturer' },
  { text: 'Status', value: 'status' },
  { text: 'Actions', value: 'actions' },
]

const loadProjectDetails = async () => {
  try {
    const response = await APIService.getProject(projectId)
    project.value = response.data
  } catch (error) {
    console.error('Error loading project details:', error)
  }
}
const openDeleteModal = (type, id, name) => {
  itemToDelete.value = { type, id, name }
  isDeleteModalVisible.value = true
}
const handleDeleteConfirm = async () => {
  if (!itemToDelete.value) return
  try {
    if (itemToDelete.value.type === 'project') {
      await APIService.deleteProject(itemToDelete.value.id)
      router.push('/projects')
    } else if (itemToDelete.value.type === 'link') {
      await APIService.deleteProjectLink(itemToDelete.value.id)
      loadProjectDetails()
    } else if (itemToDelete.value.type === 'file') {
      await APIService.deleteProjectFile(itemToDelete.value.id)
      loadProjectDetails()
    }
  } catch (error) {
    console.error(`Error deleting ${itemToDelete.value.type}:`, error)
  } finally {
    isDeleteModalVisible.value = false
    itemToDelete.value = null
  }
}
const handleFileUpload = (event) => {
  newFiles.value = event.target.files
}
const addLink = async () => {
  try {
    await APIService.createProjectLink({ ...newLink.value, project: projectId })
    newLink.value = { name: '', url: '' }
    loadProjectDetails()
  } catch (error) {
    console.error('Error adding link:', error)
  }
}
const addFiles = async () => {
  if (!newFiles.value || newFiles.value.length === 0) return
  const formData = new FormData()
  formData.append('project', projectId)
  for (const file of newFiles.value) {
    formData.append('file', file)
  }
  try {
    await APIService.createProjectFile(formData)
    if (newFileRef.value) newFileRef.value.value = null
    loadProjectDetails()
  } catch (error) {
    console.error('Error adding files:', error)
  }
}
const viewItem = (item) => router.push({ name: 'item-detail', params: { id: item.id } })
const viewPrinter = (printer) => router.push({ name: 'printer-detail', params: { id: printer.id } })

watch(isModalVisible, (newValue) => {
  const handleKeydown = (event) => {
    if (event.key === 'Escape') {
      isModalVisible.value = false
    }
  }
  if (newValue) {
    window.addEventListener('keydown', handleKeydown)
  } else {
    window.removeEventListener('keydown', handleKeydown)
  }
})

onMounted(() => {
  loadProjectDetails()
})
</script>

<template>
  <div class="detail-view">
    <MainHeader
      v-if="project"
      :title="project.project_name"
      :showSearch="false"
      :showAddButton="false"
      :showFilterButton="false"
      :showColumnButton="false"
    />
    <div class="actions-bar" v-if="project">
      <RouterLink
        :to="{ name: 'project-edit', params: { id: project.id } }"
        class="action-button edit-button"
        >Edit</RouterLink
      >
      <button
        @click="openDeleteModal('project', project.id, project.project_name)"
        class="action-button delete-button"
      >
        Delete
      </button>
    </div>
    <div v-if="project" class="details-grid">
      <div class="details-container">
        <div class="section-header"><h3>Details</h3></div>
        <div class="detail-item">
          <span class="label">Status</span><span class="value">{{ project.status }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Total Estimated Cost</span
          ><span class="value">${{ project.total_cost.toFixed(2) }}</span>
        </div>
        <div class="detail-item full-width">
          <span class="label">Description</span>
          <p class="value-notes">{{ project.description || 'N/A' }}</p>
        </div>
        <div class="detail-item full-width">
          <span class="label">Notes</span>
          <p class="value-notes">{{ project.notes || 'No notes.' }}</p>
        </div>
        <div class="detail-item full-width">
          <span class="label">Photo</span
          ><img
            v-if="project.photo"
            :src="project.photo"
            @click="isModalVisible = true"
            alt="Project photo"
            class="detail-photo clickable"
          />
        </div>
      </div>
    </div>
    <div v-if="project" class="details-container full-width-container">
      <div class="section-header"><h3>Links</h3></div>
      <table class="data-table">
        <tbody>
          <tr v-for="link in project.links" :key="link.id">
            <td>
              <a :href="link.url" target="_blank" class="table-link">{{ link.name }}</a>
            </td>
            <td class="table-actions">
              <button
                @click="openDeleteModal('link', link.id, link.name)"
                class="delete-button-small"
              >
                Delete
              </button>
            </td>
          </tr>
          <tr v-if="!project.links.length">
            <td colspan="2">No links added yet.</td>
          </tr>
        </tbody>
      </table>
      <form @submit.prevent="addLink" class="inline-add-form">
        <input type="text" v-model="newLink.name" placeholder="Link Name" required /><input
          type="url"
          v-model="newLink.url"
          placeholder="https://..."
          required
        /><button type="submit" class="action-button add-button">Add Link</button>
      </form>
    </div>
    <div v-if="project" class="details-container full-width-container">
      <div class="section-header"><h3>Files</h3></div>
      <table class="data-table">
        <tbody>
          <tr v-for="file in project.files" :key="file.id">
            <td>
              <a :href="file.file" target="_blank" class="table-link">{{
                file.file.split('/').pop()
              }}</a>
            </td>
            <td class="table-actions">
              <button
                @click="openDeleteModal('file', file.id, file.file.split('/').pop())"
                class="delete-button-small"
              >
                Delete
              </button>
            </td>
          </tr>
          <tr v-if="!project.files.length">
            <td colspan="2">No files added yet.</td>
          </tr>
        </tbody>
      </table>
      <form @submit.prevent="addFiles" class="inline-add-form">
        <input type="file" @change="handleFileUpload" ref="newFileRef" multiple /><button
          type="submit"
          class="action-button add-button"
        >
          Add Files
        </button>
      </form>
    </div>
    <div v-if="project" class="details-container full-width-container">
      <div class="section-header"><h3>Associated Inventory Items</h3></div>
      <DataTable
        :headers="inventoryHeaders"
        :items="project.associated_inventory_items"
        :visible-columns="inventoryHeaders.map((h) => h.value)"
        @row-click="viewItem"
        ><template #cell-title="{ item }">{{ item.title }}</template
        ><template #cell-brand="{ item }">{{ item.brand ? item.brand.name : 'N/A' }}</template
        ><template #cell-partType="{ item }">{{
          item.part_type ? item.part_type.name : 'N/A'
        }}</template
        ><template #cell-quantity="{ item }">{{ item.quantity }}</template
        ><template #cell-cost="{ item }">${{ item.cost }}</template
        ><template #cell-actions="{ item }"
          ><button @click.stop="removeItem(item.id)" class="delete-button-small">
            Remove
          </button></template
        ></DataTable
      >
    </div>
    <div v-if="project" class="details-container full-width-container">
      <div class="section-header"><h3>Associated Printers</h3></div>
      <DataTable
        :headers="printerHeaders"
        :items="project.associated_printers"
        :visible-columns="printerHeaders.map((h) => h.value)"
        @row-click="viewPrinter"
        ><template #cell-title="{ item }">{{ item.title }}</template
        ><template #cell-manufacturer="{ item }">{{
          item.manufacturer ? item.manufacturer.name : 'N/A'
        }}</template
        ><template #cell-status="{ item }">{{ item.status }}</template
        ><template #cell-actions="{ item }"
          ><button @click.stop="removePrinter(item.id)" class="delete-button-small">
            Remove
          </button></template
        ></DataTable
      >
    </div>
    <p v-else>Loading project details...</p>

    <BaseModal
      :show="isDeleteModalVisible"
      title="Confirm Deletion"
      @close="isDeleteModalVisible = false"
    >
      <p>
        Are you sure you want to delete the {{ itemToDelete?.type }} '{{ itemToDelete?.name }}'?
      </p>
      <template #footer
        ><button @click="handleDeleteConfirm" class="action-button delete-button">
          Yes, Delete</button
        ><button
          @click="isDeleteModalVisible = false"
          type="button"
          class="action-button cancel-button"
        >
          Cancel
        </button></template
      >
    </BaseModal>
    <div v-if="isModalVisible" class="modal-overlay" @click="isModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isModalVisible = false" class="close-button">&times;</button
        ><img :src="project.photo" alt="Full size project photo" class="modal-image" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.detail-view {
  user-select: none;
}
.details-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
}
.details-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 20px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  align-content: flex-start;
  margin-bottom: 20px;
}
.full-width-container {
  display: block;
}
.section-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 10px;
}
.details-container h3 {
  margin: 0;
  color: var(--color-heading);
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
  user-select: none;
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
.inline-add-form {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  flex-wrap: wrap;
}
.inline-add-form input {
  padding: 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  flex-grow: 1;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table td {
  padding: 8px;
  border-bottom: 1px solid var(--color-border);
}
.table-link {
  color: var(--color-text);
  text-decoration: none;
}
.table-link:hover {
  text-decoration: underline;
}
.table-actions {
  text-align: right;
}
.delete-button-small {
  background-color: var(--color-red);
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  padding: 4px 8px;
  font-size: 0.8rem;
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
@media (max-width: 768px) {
  .details-grid {
    grid-template-columns: 1fr;
  }
  .detail-item {
    flex-basis: 100%;
  }
}
</style>
