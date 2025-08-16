<script setup>
import { ref, onMounted, computed } from 'vue'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'
import DataTable from '@/components/DataTable.vue'
import BaseModal from '@/components/BaseModal.vue'
import InfoModal from '@/components/InfoModal.vue'

const activeTab = ref('brands')
const brands = ref([])
const partTypes = ref([])
const locations = ref([])
const isEditModalVisible = ref(false)
const editingItem = ref(null)
const isDeleteModalVisible = ref(false)
const itemToDelete = ref(null)

const isInitialDeleteModalVisible = ref(false)
const isFinalDeleteModalVisible = ref(false)
const deleteConfirmationText = ref('')
const deleteCheckbox = ref(false)

const restoreFile = ref(null)
const isInitialRestoreModalVisible = ref(false)
const isFinalRestoreModalVisible = ref(false)
const restoreConfirmationText = ref('')
const restoreCheckbox = ref(false)
const isRestoring = ref(false) // New state to track the restore process

const isInfoModalVisible = ref(false)
const infoModalTitle = ref('')
const infoModalMessage = ref('')
const infoModalIsError = ref(false)

const headers = [
  { text: 'Name', value: 'name' },
  { text: 'Actions', value: 'actions' },
]
const activeData = computed(() => {
  if (activeTab.value === 'brands') return brands.value
  if (activeTab.value === 'partTypes') return partTypes.value
  if (activeTab.value === 'locations') return locations.value
  return []
})
const isFinalDeleteDisabled = computed(() => {
  return deleteConfirmationText.value !== 'DELETE ALL' || !deleteCheckbox.value
})
const isFinalRestoreDisabled = computed(() => {
  return restoreConfirmationText.value !== 'RESTORE' || !restoreCheckbox.value
})

const showInfoModal = (title, message, isError = false) => {
  infoModalTitle.value = title
  infoModalMessage.value = message
  infoModalIsError.value = isError
  isInfoModalVisible.value = true
}

const handleInfoModalClose = () => {
  isInfoModalVisible.value = false
  if (!infoModalIsError.value) {
    window.location.reload()
  }
}

const exportData = async () => {
  try {
    const response = await APIService.exportData()
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const filename =
      response.headers['content-disposition']?.split('filename=')[1]?.replace(/"/g, '') ||
      'print_vault_backup.zip'
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
  } catch (error) {
    console.error('Failed to export data:', error)
    showInfoModal('Error', 'An error occurred while exporting data.', true)
  }
}
const handleInitialDelete = () => {
  isInitialDeleteModalVisible.value = true
}
const proceedToFinalDelete = () => {
  isInitialDeleteModalVisible.value = false
  isFinalDeleteModalVisible.value = true
}
const cancelFinalDelete = () => {
  isFinalDeleteModalVisible.value = false
  deleteConfirmationText.value = ''
  deleteCheckbox.value = false
}
const handleFinalDelete = async () => {
  if (isFinalDeleteDisabled.value) return
  try {
    await APIService.deleteAllData()
    isFinalDeleteModalVisible.value = false
    showInfoModal('Success', 'All data and files have been successfully deleted.')
  } catch (error) {
    console.error('Failed to delete all data:', error)
    showInfoModal('Error', 'An error occurred while deleting data.', true)
  }
}

const handleRestoreUpload = (event) => {
  restoreFile.value = event.target.files[0]
}
const initiateRestore = () => {
  if (!restoreFile.value) {
    showInfoModal('Missing File', 'A backup ZIP file is required to restore data.', true)
    return
  }
  isInitialRestoreModalVisible.value = true
}
const proceedToFinalRestore = () => {
  isInitialRestoreModalVisible.value = false
  isFinalRestoreModalVisible.value = true
}
const cancelFinalRestore = () => {
  isFinalRestoreModalVisible.value = false
  restoreConfirmationText.value = ''
  restoreCheckbox.value = false
}
const confirmRestore = async () => {
  if (isFinalRestoreDisabled.value) return
  isRestoring.value = true // Start loading state
  try {
    const formData = new FormData()
    formData.append('backup_file', restoreFile.value)
    await APIService.restoreData(formData)
    cancelFinalRestore()
    showInfoModal('Success', 'Data has been successfully restored.')
  } catch (error) {
    const errorMessage =
      error.response?.data?.error || 'An error occurred during the restore process.'
    console.error('Failed to restore data:', error)
    cancelFinalRestore()
    showInfoModal('Restore Failed', errorMessage, true)
  } finally {
    isRestoring.value = false // Stop loading state
  }
}

const loadAllData = async () => {
  try {
    const [brandsRes, partTypesRes, locationsRes] = await Promise.all([
      APIService.getBrands(),
      APIService.getPartTypes(),
      APIService.getLocations(),
    ])
    brands.value = brandsRes.data
    partTypes.value = partTypesRes.data
    locations.value = locationsRes.data
  } catch (error) {
    console.error('Failed to load settings data:', error)
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
    if (activeTab.value === 'brands') {
      isEditing
        ? await APIService.updateBrand(editingItem.value.id, data)
        : await APIService.createBrand(data)
    } else if (activeTab.value === 'partTypes') {
      isEditing
        ? await APIService.updatePartType(editingItem.value.id, data)
        : await APIService.createPartType(data)
    } else if (activeTab.value === 'locations') {
      isEditing
        ? await APIService.updateLocation(editingItem.value.id, data)
        : await APIService.createLocation(data)
    }
    isEditModalVisible.value = false
    editingItem.value = null
    loadAllData()
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
    if (activeTab.value === 'brands') await APIService.deleteBrand(itemToDelete.value.id)
    else if (activeTab.value === 'partTypes') await APIService.deletePartType(itemToDelete.value.id)
    else if (activeTab.value === 'locations') await APIService.deleteLocation(itemToDelete.value.id)
    loadAllData()
  } catch (error) {
    console.error('Failed to delete item:', error)
  } finally {
    isDeleteModalVisible.value = false
    itemToDelete.value = null
  }
}

onMounted(() => {
  loadAllData()
})
</script>

<template>
  <div>
    <MainHeader title="Settings" :showSearch="false" :showAddButton="false" />
    <div class="settings-container">
      <div class="tabs">
        <button @click="activeTab = 'brands'" :class="{ active: activeTab === 'brands' }">
          Brands
        </button>
        <button @click="activeTab = 'partTypes'" :class="{ active: activeTab === 'partTypes' }">
          Part Types
        </button>
        <button @click="activeTab = 'locations'" :class="{ active: activeTab === 'locations' }">
          Locations
        </button>
        <button @click="activeTab = 'data'" :class="{ active: activeTab === 'data' }">
          Data Management
        </button>
      </div>
      <div class="tab-content" v-if="activeTab !== 'data'">
        <div class="content-header">
          <h3 v-if="activeTab === 'brands'">Manage Brands & Manufacturers</h3>
          <h3 v-if="activeTab === 'partTypes'">Manage Part Types</h3>
          <h3 v-if="activeTab === 'locations'">Manage Locations</h3>
          <button @click="openAddModal" class="action-button add-button">Add New</button>
        </div>
        <DataTable
          :headers="headers"
          :items="activeData"
          :visible-columns="headers.map((h) => h.value)"
          @row-click.stop
        >
          <template #cell-name="{ item }">{{ item.name }}</template>
          <template #cell-actions="{ item }"
            ><div class="actions-cell">
              <button @click="openEditModal(item)" class="action-button edit-button">Edit</button
              ><button @click="openDeleteItemModal(item)" class="action-button delete-button">
                Delete
              </button>
            </div></template
          >
        </DataTable>
      </div>
      <div class="tab-content" v-if="activeTab === 'data'">
        <div class="content-header"><h3>Data Management</h3></div>
        <div class="data-actions">
          <div class="action-item">
            <h4>Export Data & Files</h4>
            <p>
              Download a single ZIP archive containing your data as a CSV file and all your uploaded
              photos and files.
            </p>
            <button @click="exportData" class="action-button edit-button">Export Backup</button>
          </div>
          <div class="action-item">
            <h4>Restore from Backup</h4>
            <p>Wipe all current data and restore from a previously exported backup ZIP file.</p>
            <form @submit.prevent="initiateRestore" class="restore-form">
              <div class="form-group">
                <label for="backup-upload">Upload Backup File (*.zip)</label
                ><input
                  id="backup-upload"
                  type="file"
                  @change="handleRestoreUpload"
                  accept=".zip"
                  required
                />
              </div>
              <button type="submit" class="action-button edit-button">Restore from Backup</button>
            </form>
          </div>
        </div>
        <div class="danger-zone">
          <h4>Danger Zone</h4>
          <div class="action-item">
            <h4>Delete All Data</h4>
            <p>
              Permanently delete all inventory, printers, projects, and uploaded files. This cannot
              be undone.
            </p>
            <button @click="handleInitialDelete" class="action-button delete-button">
              Delete All Data & Files
            </button>
          </div>
        </div>
      </div>
    </div>

    <BaseModal
      :show="isDeleteModalVisible"
      title="Confirm Deletion"
      @close="isDeleteModalVisible = false"
    >
      <p>Are you sure you want to delete '{{ itemToDelete?.name }}'?</p>
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
    <BaseModal
      :show="isInitialRestoreModalVisible"
      title="Confirm Restore"
      @close="isInitialRestoreModalVisible = false"
    >
      <p>
        Restoring from a backup will delete ALL current data and files. This action is irreversible.
        Are you sure?
      </p>
      <template #footer
        ><button @click="proceedToFinalRestore" class="action-button delete-button">
          Yes, Delete and Restore</button
        ><button
          @click="isInitialRestoreModalVisible = false"
          type="button"
          class="action-button cancel-button"
        >
          Cancel
        </button></template
      >
    </BaseModal>
    <BaseModal
      :show="isFinalRestoreModalVisible"
      title="Final Restore Confirmation"
      @close="cancelFinalRestore"
    >
      <p>
        This is your last warning. To proceed, please type <strong>RESTORE</strong> in the box below
        and check the acknowledgment.
      </p>
      <div class="form-group">
        <label for="restore-confirm-text">Type RESTORE to confirm</label
        ><input id="restore-confirm-text" type="text" v-model="restoreConfirmationText" />
      </div>
      <div class="form-group checkbox-group">
        <input id="restore-confirm-check" type="checkbox" v-model="restoreCheckbox" /><label
          for="restore-confirm-check"
          >I understand this action is permanent and will overwrite all current data.</label
        >
      </div>
      <template #footer
        ><button
          @click="confirmRestore"
          :disabled="isFinalRestoreDisabled || isRestoring"
          class="action-button delete-button"
        >
          <span v-if="isRestoring">Restoring...</span>
          <span v-else>Permanently Restore Data</span></button
        ><button @click="cancelFinalRestore" type="button" class="action-button cancel-button">
          Cancel
        </button></template
      >
    </BaseModal>
    <InfoModal
      :show="isInfoModalVisible"
      :title="infoModalTitle"
      :message="infoModalMessage"
      :is-error="infoModalIsError"
      @close="handleInfoModalClose"
    />

    <BaseModal
      :show="isEditModalVisible"
      :title="editingItem && editingItem.id ? 'Edit Name' : 'Add New Name'"
      @close="isEditModalVisible = false"
    >
      <form @submit.prevent="saveItem">
        <div class="form-group">
          <label for="name">Name</label
          ><input id="name" type="text" v-model="editingItem.name" required />
        </div>
      </form>
      <template #footer
        ><button @click="saveItem" class="action-button save-button">Save</button
        ><button
          @click="isEditModalVisible = false"
          type="button"
          class="action-button cancel-button"
        >
          Cancel
        </button></template
      >
    </BaseModal>
    <BaseModal
      :show="isInitialDeleteModalVisible"
      title="Are you absolutely sure?"
      @close="isInitialDeleteModalVisible = false"
    >
      <p>This will delete ALL data and files. This action is permanent and cannot be undone.</p>
      <template #footer
        ><button @click="proceedToFinalDelete" class="action-button delete-button">
          Yes, Proceed</button
        ><button
          @click="isInitialDeleteModalVisible = false"
          type="button"
          class="action-button cancel-button"
        >
          Cancel
        </button></template
      >
    </BaseModal>
    <BaseModal
      :show="isFinalDeleteModalVisible"
      title="Final Confirmation"
      @close="cancelFinalDelete"
    >
      <p>
        This is your last warning. To proceed, please type <strong>DELETE ALL</strong> in the box
        below and check the acknowledgment.
      </p>
      <div class="form-group">
        <label for="delete-confirm-text">Type DELETE ALL to confirm</label
        ><input id="delete-confirm-text" type="text" v-model="deleteConfirmationText" />
      </div>
      <div class="form-group checkbox-group">
        <input id="delete-confirm-check" type="checkbox" v-model="deleteCheckbox" /><label
          for="delete-confirm-check"
          >I understand this action is permanent and cannot be undone.</label
        >
      </div>
      <template #footer
        ><button
          @click="handleFinalDelete"
          :disabled="isFinalDeleteDisabled"
          class="action-button delete-button"
        >
          Permanently Delete Everything</button
        ><button @click="cancelFinalDelete" type="button" class="action-button cancel-button">
          Cancel
        </button></template
      >
    </BaseModal>
  </div>
</template>

<style scoped>
.settings-container {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}
.tabs {
  display: flex;
  background-color: var(--color-background-mute);
  flex-wrap: wrap;
}
.tabs button {
  padding: 15px 20px;
  cursor: pointer;
  background-color: transparent;
  border: none;
  color: var(--color-text);
  font-size: 1rem;
  border-bottom: 3px solid transparent;
}
.tabs button.active {
  color: var(--color-heading);
  border-bottom-color: var(--color-blue);
}
.tab-content {
  padding: 20px;
}
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
.delete-button:disabled {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  cursor: not-allowed;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
}
.data-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 20px;
}
.action-item {
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  display: flex;
  flex-direction: column;
}
.action-item h4 {
  color: var(--color-heading);
  margin-top: 0;
}
.action-item p {
  margin: 10px 0;
  font-size: 0.9rem;
  flex-grow: 1;
}
.action-item .action-button {
  align-self: flex-start;
}
.restore-form {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
}
.restore-form .form-group {
  margin-bottom: 15px;
}
.restore-form label {
  font-size: 0.9rem;
  margin-bottom: 5px;
}
.danger-zone {
  margin-top: 40px;
  border-top: 2px solid var(--color-red);
  padding-top: 20px;
}
.danger-zone h4 {
  color: var(--color-red);
  margin-bottom: 20px;
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
.checkbox-group {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}
.checkbox-group input {
  width: auto;
}
.checkbox-group label {
  margin-bottom: 0;
  font-weight: normal;
  user-select: none;
  cursor: pointer;
}
@media (max-width: 992px) {
  .data-actions {
    grid-template-columns: 1fr;
  }
}
</style>
