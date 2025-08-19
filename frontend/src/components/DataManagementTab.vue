<script setup>
import { ref, computed } from 'vue'
import APIService from '@/services/APIService.js'
import BaseModal from '@/components/BaseModal.vue'
import InfoModal from '@/components/InfoModal.vue'

const isInitialDeleteModalVisible = ref(false)
const isFinalDeleteModalVisible = ref(false)
const deleteConfirmationText = ref('')
const deleteCheckbox = ref(false)

const restoreFile = ref(null)
const isRestoring = ref(false)
const isInitialRestoreModalVisible = ref(false)
const isFinalRestoreModalVisible = ref(false)
const restoreConfirmationText = ref('')
const restoreCheckbox = ref(false)

const isInfoModalVisible = ref(false)
const infoModalTitle = ref('')
const infoModalMessage = ref('')
const infoModalIsError = ref(false)

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
  if (!restoreFile.value) {
    showInfoModal('Missing File', 'A backup ZIP file is required to restore data.', true)
    return
  }

  isRestoring.value = true
  try {
    const formData = new FormData()
    formData.append('backup_file', restoreFile.value) // Ensure the key matches the backend

    await APIService.restoreData(formData)
    cancelFinalRestore()
    showInfoModal('Success', 'Data has been successfully restored.')
  } catch (error) {
    const errorMessage =
      error.response?.data?.error || 'An error occurred during the restore process.'
    console.error('Failed to restore data:', error)
    showInfoModal('Restore Failed', errorMessage, true) // Display backend error message
  } finally {
    isRestoring.value = false
  }
}
</script>

<template>
  <div>
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
          Permanently delete all inventory, printers, projects, and uploaded files. This cannot be
          undone.
        </p>
        <button @click="handleInitialDelete" class="action-button delete-button">
          Delete All Data & Files
        </button>
      </div>
    </div>

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
/* Scoped styles copied from SettingsView.vue */
.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.content-header h3 {
  color: var(--color-heading);
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
.edit-button {
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
