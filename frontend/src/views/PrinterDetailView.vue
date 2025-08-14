<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'
import DataTable from '@/components/DataTable.vue'
import BaseModal from '@/components/BaseModal.vue'

const route = useRoute()
const router = useRouter()
const printer = ref(null)
const printerId = route.params.id
const isPhotoModalVisible = ref(false)
const isAddModalVisible = ref(false)
const isEditModalVisible = ref(false)
const isDeleteModalVisible = ref(false)
const itemToDelete = ref(null)

const newMod = ref({ name: '', link: '', status: 'Planned' })
const newModFiles = ref(null)
const newModFileRef = ref(null)
const editingMod = ref(null)
const editModFileRef = ref(null)

const modHeaders = [
  { text: 'Name', value: 'name' },
  { text: 'Link', value: 'link' },
  { text: 'Files', value: 'files' },
  { text: 'Actions', value: 'actions' },
]
const plannedMods = computed(() => printer.value?.mods.filter((m) => m.status === 'Planned') || [])
const inProgressMods = computed(
  () => printer.value?.mods.filter((m) => m.status === 'In Progress') || [],
)
const completedMods = computed(
  () => printer.value?.mods.filter((m) => m.status === 'Completed') || [],
)
const closeAllModals = () => {
  isAddModalVisible.value = false
  isEditModalVisible.value = false
}
const loadPrinterDetails = async () => {
  try {
    const response = await APIService.getPrinter(printerId)
    printer.value = response.data
  } catch (error) {
    console.error('Error loading printer details:', error)
  }
}
const openDeleteModal = (type, id, name) => {
  itemToDelete.value = { type, id, name }
  isDeleteModalVisible.value = true
}
const handleDeleteConfirm = async () => {
  if (!itemToDelete.value) return
  try {
    if (itemToDelete.value.type === 'printer') {
      await APIService.deletePrinter(itemToDelete.value.id)
      router.push('/printers')
    } else if (itemToDelete.value.type === 'mod') {
      await APIService.deleteMod(itemToDelete.value.id)
      loadPrinterDetails()
    }
  } catch (error) {
    console.error(`Error deleting ${itemToDelete.value.type}:`, error)
  } finally {
    isDeleteModalVisible.value = false
    itemToDelete.value = null
  }
}
const handleNewModFileUpload = (event) => {
  newModFiles.value = event.target.files
}
const addMod = async () => {
  const modFormData = new FormData()
  modFormData.append('printer', printerId)
  modFormData.append('name', newMod.value.name)
  modFormData.append('status', newMod.value.status)
  if (newMod.value.link) modFormData.append('link', newMod.value.link)
  try {
    const modResponse = await APIService.createMod(modFormData)
    const newModId = modResponse.data.id
    if (newModFiles.value && newModFiles.value.length > 0) {
      const fileFormData = new FormData()
      fileFormData.append('mod', newModId)
      for (const file of newModFiles.value) {
        fileFormData.append('file', file)
      }
      await APIService.createModFile(fileFormData)
    }
    closeAllModals()
    newMod.value = { name: '', link: '', status: 'Planned' }
    if (newModFileRef.value) newModFileRef.value.value = null
    loadPrinterDetails()
  } catch (error) {
    console.error('Error adding mod:', error)
  }
}
const openEditModModal = (mod) => {
  editingMod.value = { ...mod }
  isEditModalVisible.value = true
}
const updateMod = async () => {
  if (!editingMod.value) return
  try {
    await APIService.updateMod(editingMod.value.id, {
      name: editingMod.value.name,
      link: editingMod.value.link,
      status: editingMod.value.status,
    })
    const files = editModFileRef.value?.files
    if (files && files.length > 0) {
      const fileFormData = new FormData()
      fileFormData.append('mod', editingMod.value.id)
      for (const file of files) {
        fileFormData.append('file', file)
      }
      await APIService.createModFile(fileFormData)
    }
    closeAllModals()
    editingMod.value = null
    loadPrinterDetails()
  } catch (error) {
    console.error('Error updating mod:', error)
  }
}
const deleteModFile = async (fileId) => {
  if (window.confirm('Are you sure you want to delete this file?')) {
    try {
      await APIService.deleteModFile(fileId)
      const modIndex = printer.value.mods.findIndex((m) => m.id === editingMod.value.id)
      if (modIndex !== -1) {
        const updatedModFiles = editingMod.value.files.filter((f) => f.id !== fileId)
        editingMod.value.files = updatedModFiles
        printer.value.mods[modIndex].files = updatedModFiles
      }
    } catch (error) {
      console.error('Error deleting mod file:', error)
    }
  }
}
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
onMounted(() => {
  loadPrinterDetails()
})
</script>

<template>
  <div class="detail-view">
    <MainHeader
      v-if="printer"
      :title="printer.title"
      :showSearch="false"
      :showAddButton="false"
      :showFilterButton="false"
      :showColumnButton="false"
    />
    <div class="details-grid" v-if="printer">
      <div class="details-container">
        <div class="section-header">
          <h3>Details</h3>
          <div>
            <RouterLink
              :to="{ name: 'printer-edit', params: { id: printer.id } }"
              class="action-button edit-button"
              >Edit</RouterLink
            ><button
              @click="openDeleteModal('printer', printer.id, printer.title)"
              class="action-button delete-button"
            >
              Delete
            </button>
          </div>
        </div>
        <div class="detail-item">
          <span class="label">Manufacturer</span
          ><span class="value">{{ printer.manufacturer ? printer.manufacturer.name : 'N/A' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Status</span><span class="value">{{ printer.status }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Serial Number</span
          ><span class="value">{{ printer.serial_number || 'N/A' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Purchase Date</span
          ><span class="value">{{ printer.purchase_date || 'N/A' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Purchase Price</span
          ><span class="value">${{ printer.purchase_price || '0.00' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Build Volume (mm)</span
          ><span class="value"
            >{{ printer.build_size_x || 'N/A' }} x {{ printer.build_size_y || 'N/A' }} x
            {{ printer.build_size_z || 'N/A' }}</span
          >
        </div>
        <div class="detail-item full-width">
          <span class="label">Notes</span>
          <p class="value-notes">{{ printer.notes || 'No notes.' }}</p>
        </div>
        <div class="detail-item full-width">
          <span class="label">Photo</span
          ><img
            v-if="printer.photo"
            :src="printer.photo"
            @click="isPhotoModalVisible = true"
            alt="Printer photo"
            class="detail-photo clickable"
          />
        </div>
      </div>
      <div class="details-container">
        <div class="section-header">
          <h3>Maintenance</h3>
          <RouterLink
            :to="{ name: 'maintenance-edit', params: { id: printer.id } }"
            class="action-button edit-button"
            >Edit</RouterLink
          >
        </div>
        <div class="detail-item">
          <span class="label">Last Maintenance</span
          ><span class="value">{{ printer.last_maintained_date || 'N/A' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Maintenance Reminder</span
          ><span class="value">{{ printer.maintenance_reminder_date || 'None set' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Last Carbon Filter Change</span
          ><span class="value">{{ printer.last_carbon_replacement_date || 'N/A' }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Carbon Filter Reminder</span
          ><span class="value">{{ printer.carbon_reminder_date || 'None set' }}</span>
        </div>
        <div class="detail-item full-width">
          <span class="label">Maintenance Notes</span>
          <p class="value-notes">{{ printer.maintenance_notes || 'No notes.' }}</p>
        </div>
      </div>
      <div class="details-container mods-section">
        <div class="section-header">
          <h3>Mods</h3>
          <button @click="isAddModalVisible = true" class="action-button add-button">
            Add Mod
          </button>
        </div>
        <div v-if="completedMods.length > 0" class="mod-group">
          <h4>Completed</h4>
          <DataTable
            :headers="modHeaders"
            :items="completedMods"
            :visible-columns="modHeaders.map((h) => h.value)"
            @row-click.stop
            ><template #cell-name="{ item }">{{ item.name }}</template
            ><template #cell-link="{ item }"
              ><a :href="item.link" target="_blank" v-if="item.link" class="table-link"
                >View Link</a
              ></template
            ><template #cell-files="{ item }"
              ><div v-if="item.files.length > 0">
                <div v-for="file in item.files" :key="file.id" class="file-link">
                  <a :href="file.file" target="_blank" class="table-link">{{
                    file.file.split('/').pop()
                  }}</a>
                </div>
              </div>
              <span v-else>N/A</span></template
            ><template #cell-actions="{ item }"
              ><div class="actions-cell">
                <button @click="openEditModModal(item)" class="action-button edit-button">
                  Edit</button
                ><button
                  @click="openDeleteModal('mod', item.id, item.name)"
                  class="action-button delete-button"
                >
                  Delete
                </button>
              </div></template
            ></DataTable
          >
        </div>
        <div v-if="inProgressMods.length > 0" class="mod-group">
          <h4>In Progress</h4>
          <DataTable
            :headers="modHeaders"
            :items="inProgressMods"
            :visible-columns="modHeaders.map((h) => h.value)"
            @row-click.stop
            ><template #cell-name="{ item }">{{ item.name }}</template
            ><template #cell-link="{ item }"
              ><a :href="item.link" target="_blank" v-if="item.link" class="table-link"
                >View Link</a
              ></template
            ><template #cell-files="{ item }"
              ><div v-if="item.files.length > 0">
                <div v-for="file in item.files" :key="file.id" class="file-link">
                  <a :href="file.file" target="_blank" class="table-link">{{
                    file.file.split('/').pop()
                  }}</a>
                </div>
              </div>
              <span v-else>N/A</span></template
            ><template #cell-actions="{ item }"
              ><div class="actions-cell">
                <button @click="openEditModModal(item)" class="action-button edit-button">
                  Edit</button
                ><button
                  @click="openDeleteModal('mod', item.id, item.name)"
                  class="action-button delete-button"
                >
                  Delete
                </button>
              </div></template
            ></DataTable
          >
        </div>
        <div v-if="plannedMods.length > 0" class="mod-group">
          <h4>Planned</h4>
          <DataTable
            :headers="modHeaders"
            :items="plannedMods"
            :visible-columns="modHeaders.map((h) => h.value)"
            @row-click.stop
            ><template #cell-name="{ item }">{{ item.name }}</template
            ><template #cell-link="{ item }"
              ><a :href="item.link" target="_blank" v-if="item.link" class="table-link"
                >View Link</a
              ></template
            ><template #cell-files="{ item }"
              ><div v-if="item.files.length > 0">
                <div v-for="file in item.files" :key="file.id" class="file-link">
                  <a :href="file.file" target="_blank" class="table-link">{{
                    file.file.split('/').pop()
                  }}</a>
                </div>
              </div>
              <span v-else>N/A</span></template
            ><template #cell-actions="{ item }"
              ><div class="actions-cell">
                <button @click="openEditModModal(item)" class="action-button edit-button">
                  Edit</button
                ><button
                  @click="openDeleteModal('mod', item.id, item.name)"
                  class="action-button delete-button"
                >
                  Delete
                </button>
              </div></template
            ></DataTable
          >
        </div>
        <p v-if="!printer.mods.length">No mods added yet.</p>
      </div>
      <div class="details-container projects-section">
        <div class="section-header"><h3>Associated Projects</h3></div>
        <p v-if="!printer.associated_projects.length">
          This printer is not yet associated with any projects.
        </p>
      </div>
    </div>
    <p v-else>Loading printer details...</p>

    <BaseModal
      :show="isDeleteModalVisible"
      title="Confirm Deletion"
      @close="isDeleteModalVisible = false"
      ><p>
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
      ></BaseModal
    >
    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button
        ><img :src="printer.photo" alt="Full size printer photo" class="modal-image" />
      </div>
    </div>
    <div
      v-if="isAddModalVisible || isEditModalVisible"
      class="modal-overlay"
      @click="closeAllModals"
    >
      <form
        @submit.prevent="isEditModalVisible ? updateMod() : addMod()"
        class="modal-form"
        @click.stop
      >
        <h3>{{ isEditModalVisible ? 'Edit Mod' : 'Add New Mod' }}</h3>
        <div class="form-group">
          <label>Name</label
          ><input v-if="isEditModalVisible" type="text" v-model="editingMod.name" required /><input
            v-else
            type="text"
            v-model="newMod.name"
            required
          />
        </div>
        <div class="form-group">
          <label>Link</label
          ><input v-if="isEditModalVisible" type="url" v-model="editingMod.link" /><input
            v-else
            type="url"
            v-model="newMod.link"
          />
        </div>
        <div class="form-group">
          <label>Status</label
          ><select v-if="isEditModalVisible" v-model="editingMod.status">
            <option>Planned</option>
            <option>In Progress</option>
            <option>Completed</option></select
          ><select v-else v-model="newMod.status">
            <option>Planned</option>
            <option>In Progress</option>
            <option>Completed</option>
          </select>
        </div>
        <div class="form-group" v-if="isEditModalVisible">
          <label>Existing Files</label>
          <div v-if="!editingMod.files.length">No files uploaded.</div>
          <div v-for="file in editingMod.files" :key="file.id" class="file-list-item">
            <span>{{ file.file.split('/').pop() }}</span
            ><button @click.prevent="deleteModFile(file.id)" class="delete-mod-button">X</button>
          </div>
        </div>
        <div class="form-group">
          <label>Add Files</label
          ><input
            type="file"
            :ref="isEditModalVisible ? 'editModFileRef' : 'newModFileRef'"
            @change="!isEditModalVisible && handleNewModFileUpload($event)"
            multiple
          />
        </div>
        <div class="form-actions">
          <button type="submit" class="save-button">Save</button
          ><button @click="closeAllModals" type="button" class="cancel-button">Cancel</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.detail-view {
  user-select: none;
}
.details-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
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
.section-header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 10px;
}
.section-header div {
  display: flex;
  gap: 10px;
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
.value,
.file-link a {
  font-size: 1.1rem;
  color: var(--color-heading);
  text-decoration: none;
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
.mods-section,
.projects-section {
  grid-column: 1 / -1;
}
.mods-section :deep(.table-container) {
  width: 100%;
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
:deep(.table-link) {
  color: var(--color-text);
  text-decoration: none;
}
:deep(.table-link:hover) {
  text-decoration: underline;
}
:deep(.table-link:visited) {
  color: var(--color-text);
}
.mod-group {
  width: 100%;
}
.mod-group h4 {
  color: var(--color-heading);
  margin-top: 20px;
  margin-bottom: 10px;
}
.mod-group:first-of-type h4 {
  margin-top: 0;
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
.modal-form {
  background-color: var(--color-background-soft);
  padding: 20px;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
}
.modal-form .form-group input,
.modal-form .form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
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
.file-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}
.delete-mod-button {
  background-color: var(--color-red);
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
  padding: 4px 8px;
  font-size: 0.8rem;
}
.form-group {
  margin-bottom: 1rem;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
@media (max-width: 992px) {
  .details-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 768px) {
  .detail-item {
    flex-basis: 100%;
  }
}
</style>
