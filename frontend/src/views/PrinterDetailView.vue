<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '../services/APIService'
import BaseModal from '../components/BaseModal.vue'
import ErrorModal from '../components/ErrorModal.vue'
import InfoModal from '../components/InfoModal.vue'

const route = useRoute()
const router = useRouter()
const printer = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')
const isErrorModalVisible = ref(false)

const isAddModModalVisible = ref(false)
const newMod = ref({ name: '', link: '', status: 'Planned' })
const newModFiles = ref([])

const isEditModModalVisible = ref(false)
const editingMod = ref(null)
const newFiles = ref([]) // For adding new files in edit mode
const filesToDelete = ref(new Set()) // For marking files for deletion

const isInfoModalVisible = ref(false)
const infoModalMessage = ref('')

// New state for the photo lightbox
const isPhotoModalVisible = ref(false)

const fetchPrinter = async () => {
  try {
    isLoading.value = true
    const response = await APIService.getPrinter(route.params.id)
    printer.value = response.data
  } catch (error) {
    console.error('Failed to fetch printer details:', error)
    errorMessage.value = 'Failed to load printer details. Please try again.'
    isErrorModalVisible.value = true
  } finally {
    isLoading.value = false
  }
}

const triggerFileInput = (inputId) => {
  document.getElementById(inputId).click()
}

const handleNewModFileUpload = (event) => {
  newModFiles.value = Array.from(event.target.files)
}

const handleEditModFileUpload = (event) => {
  newFiles.value = Array.from(event.target.files)
}

const addMod = async () => {
  if (!newMod.value.name) {
    alert('Mod name is required.')
    return
  }

  const formData = new FormData()
  formData.append('printer', printer.value.id)
  formData.append('name', newMod.value.name)
  formData.append('link', newMod.value.link)
  formData.append('status', newMod.value.status)

  try {
    const response = await APIService.createMod(formData)
    const modId = response.data.id

    if (newModFiles.value.length > 0) {
      for (const file of newModFiles.value) {
        const fileFormData = new FormData()
        fileFormData.append('mod', modId)
        fileFormData.append('file', file)
        await APIService.createModFile(fileFormData)
      }
    }

    closeAddModModal()
    await fetchPrinter()
  } catch (error) {
    console.error('Failed to add mod:', error)
    errorMessage.value = 'Failed to add mod. Please try again.'
    isErrorModalVisible.value = true
  }
}

const openEditModModal = (mod) => {
  editingMod.value = { ...mod, files: [...mod.files] }
  isEditModModalVisible.value = true
}

const markFileForDeletion = (fileId) => {
  if (filesToDelete.value.has(fileId)) {
    filesToDelete.value.delete(fileId)
  } else {
    filesToDelete.value.add(fileId)
  }
}

const updateMod = async () => {
  if (!editingMod.value || !editingMod.value.id) return

  const modId = editingMod.value.id
  const modData = {
    name: editingMod.value.name,
    link: editingMod.value.link,
    status: editingMod.value.status,
  }

  try {
    // 1. Update mod details
    await APIService.updateMod(modId, modData)

    // 2. Delete marked files
    for (const fileId of filesToDelete.value) {
      await APIService.deleteModFile(fileId)
    }

    // 3. Upload new files
    if (newFiles.value.length > 0) {
      for (const file of newFiles.value) {
        const formData = new FormData()
        formData.append('mod', modId)
        formData.append('file', file)
        await APIService.createModFile(formData)
      }
    }

    closeEditModModal()
    await fetchPrinter()
  } catch (error) {
    console.error('Failed to update mod:', error)
    errorMessage.value = 'Failed to update mod. Please try again.'
    isErrorModalVisible.value = true
  }
}

const deleteMod = async (modId) => {
  if (confirm('Are you sure you want to delete this mod and all its files?')) {
    try {
      await APIService.deleteMod(modId)
      infoModalMessage.value = 'Mod deleted successfully.'
      isInfoModalVisible.value = true
      await fetchPrinter()
    } catch (error) {
      console.error('Failed to delete mod:', error)
      errorMessage.value = 'Failed to delete mod. Please try again.'
      isErrorModalVisible.value = true
    }
  }
}

const closeAddModModal = () => {
  isAddModModalVisible.value = false
  newMod.value = { name: '', link: '', status: 'Planned' }
  newModFiles.value = []
}

const closeEditModModal = () => {
  isEditModModalVisible.value = false
  editingMod.value = null
  newFiles.value = []
  filesToDelete.value.clear()
}

const formatPurchasePrice = (price) => {
  if (price === null || price === undefined) {
    return 'N/A'
  }
  return `$${Number(price).toFixed(2)}`
}

const buildVolume = computed(() => {
  if (
    !printer.value ||
    printer.value.build_size_x == null ||
    printer.value.build_size_y == null ||
    printer.value.build_size_z == null
  ) {
    return 'N/A'
  }
  return `${printer.value.build_size_x}mm x ${printer.value.build_size_y}mm x ${printer.value.build_size_z}mm`
})

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const options = { year: 'numeric', month: 'long', day: 'numeric' }
  return new Date(dateString).toLocaleDateString(undefined, options)
}

const deletePrinter = async () => {
  if (confirm('Are you sure you want to delete this printer? This action cannot be undone.')) {
    try {
      await APIService.deletePrinter(printer.value.id)
      router.push({ name: 'printer-list' })
    } catch (error) {
      console.error('Failed to delete printer:', error)
      errorMessage.value = 'Failed to delete printer. Please try again.'
      isErrorModalVisible.value = true
    }
  }
}

const getFileName = (filePath) => {
  if (!filePath) return ''
  return filePath.split('/').pop()
}

onMounted(fetchPrinter)
</script>

<template>
  <div class="page-container">
    <div v-if="isLoading" class="loading-state">
      <p>Loading printer details...</p>
    </div>

    <div v-if="!isLoading && printer" class="content-container">
      <div class="detail-header">
        <div class="header-content">
          <img
            :src="printer.photo"
            v-if="printer.photo"
            alt="Printer Photo"
            class="detail-photo clickable"
            @click="isPhotoModalVisible = true"
          />
          <div class="header-info">
            <h1>{{ printer.title }}</h1>
            <p class="manufacturer-serial">
              {{ printer.manufacturer.name }} | Serial:
              {{ printer.serial_number || 'N/A' }}
            </p>
          </div>
        </div>
        <div class="header-actions">
          <router-link
            :to="{ name: 'printer-edit', params: { id: printer.id } }"
            class="btn btn-primary"
            >Edit Printer</router-link
          >
          <button @click="deletePrinter" class="btn btn-danger">Delete</button>
        </div>
      </div>

      <div class="detail-grid">
        <div class="card">
          <div class="card-header">
            <h3>Printer Details</h3>
          </div>
          <div class="card-body">
            <p>
              <strong>Status:</strong>
              <span
                :class="[
                  'status-badge',
                  `status-${printer.status.toLowerCase().replace(/ /g, '-').replace(/\//g, '-')}`,
                ]"
                >{{ printer.status }}</span
              >
            </p>
            <p>
              <strong>Build Volume:</strong>
              <span>{{ buildVolume }}</span>
            </p>
            <p><strong>Purchase Date:</strong> {{ formatDate(printer.purchase_date) }}</p>
            <p>
              <strong>Purchase Price:</strong>
              {{ formatPurchasePrice(printer.purchase_price) }}
            </p>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Notes</h3>
          </div>
          <div class="card-body">
            <p>{{ printer.notes || 'No notes available.' }}</p>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Maintenance</h3>
            <router-link
              :to="{ name: 'maintenance-edit', params: { id: printer.id } }"
              class="btn btn-sm btn-primary"
              >Edit</router-link
            >
          </div>
          <div class="card-body">
            <p>
              <strong>Last Maintained:</strong>
              {{ formatDate(printer.last_maintained_date) }}
            </p>
            <p>
              <strong>Maintenance Reminder:</strong>
              {{ formatDate(printer.maintenance_reminder_date) }}
            </p>
            <p>
              <strong>Last Carbon Filter Replacement:</strong>
              {{ formatDate(printer.last_carbon_replacement_date) }}
            </p>
            <p>
              <strong>Carbon Filter Reminder:</strong>
              {{ formatDate(printer.carbon_reminder_date) }}
            </p>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3>Maintenance Notes</h3>
            <router-link
              :to="{ name: 'maintenance-edit', params: { id: printer.id } }"
              class="btn btn-sm btn-primary"
              >Edit</router-link
            >
          </div>
          <div class="card-body">
            <p>{{ printer.maintenance_notes || 'No maintenance notes available.' }}</p>
          </div>
        </div>

        <div class="card card-full-width">
          <div class="card-header">
            <h3>Mods</h3>
            <button @click="isAddModModalVisible = true" class="btn btn-secondary">Add Mod</button>
          </div>
          <div class="card-body">
            <ul v-if="printer.mods && printer.mods.length > 0" class="mods-list">
              <li v-for="mod in printer.mods" :key="mod.id" class="mod-item">
                <div class="mod-info">
                  <a v-if="mod.link" :href="mod.link" target="_blank" class="mod-name-link">
                    <strong>{{ mod.name }}</strong>
                  </a>
                  <strong v-else>{{ mod.name }}</strong>
                  -
                  <span :class="['status-badge', `status-${mod.status.toLowerCase()}`]">{{
                    mod.status
                  }}</span>
                  <div v-if="mod.files && mod.files.length > 0" class="mod-files">
                    <ul>
                      <li v-for="file in mod.files" :key="file.id">
                        <a :href="file.file" target="_blank">{{ getFileName(file.file) }}</a>
                      </li>
                    </ul>
                  </div>
                </div>
                <div class="mod-actions">
                  <button @click="openEditModModal(mod)" class="btn btn-sm btn-primary">
                    Edit
                  </button>
                  <button @click="deleteMod(mod.id)" class="btn btn-sm btn-danger">Delete</button>
                </div>
              </li>
            </ul>
            <p v-else>No mods added yet.</p>
          </div>
        </div>
      </div>
    </div>

    <BaseModal :show="isAddModModalVisible" title="Add New Mod" @close="closeAddModModal">
      <form @submit.prevent="addMod">
        <div class="form-group">
          <label for="modName">Mod Name</label>
          <input type="text" id="modName" v-model="newMod.name" class="form-control" required />
        </div>
        <div class="form-group">
          <label for="modLink">Link</label>
          <input
            type="url"
            id="modLink"
            v-model="newMod.link"
            class="form-control"
            placeholder="https://..."
          />
        </div>
        <div class="form-group">
          <label for="modStatus">Status</label>
          <select id="modStatus" v-model="newMod.status" class="form-control">
            <option>Planned</option>
            <option>In Progress</option>
            <option>Completed</option>
            <option>On Hold</option>
          </select>
        </div>
        <div class="form-group">
          <label>Attach Files</label>
          <button
            type="button"
            @click="triggerFileInput('newModFileInput')"
            class="btn btn-outline"
          >
            Choose Files
          </button>
          <input
            type="file"
            id="newModFileInput"
            multiple
            @change="handleNewModFileUpload"
            class="file-input"
          />
          <ul v-if="newModFiles.length > 0" class="file-list">
            <li v-for="(file, index) in newModFiles" :key="index">
              {{ file.name }}
            </li>
          </ul>
        </div>
      </form>
      <template #footer>
        <button @click="addMod" class="btn btn-primary">Save</button>
        <button type="button" @click="closeAddModModal" class="btn btn-secondary">Cancel</button>
      </template>
    </BaseModal>

    <BaseModal :show="isEditModModalVisible" title="Edit Mod" @close="closeEditModModal">
      <form v-if="editingMod" @submit.prevent="updateMod">
        <div class="form-group">
          <label for="editModName">Mod Name</label>
          <input
            type="text"
            id="editModName"
            v-model="editingMod.name"
            class="form-control"
            required
          />
        </div>
        <div class="form-group">
          <label for="editModLink">Link</label>
          <input
            type="url"
            id="editModLink"
            v-model="editingMod.link"
            class="form-control"
            placeholder="https://..."
          />
        </div>
        <div class="form-group">
          <label for="editModStatus">Status</label>
          <select id="editModStatus" v-model="editingMod.status" class="form-control">
            <option>Planned</option>
            <option>In Progress</option>
            <option>Completed</option>
            <option>On Hold</option>
          </select>
        </div>

        <div class="form-group" v-if="editingMod.files && editingMod.files.length > 0">
          <label>Existing Files</label>
          <ul class="file-list existing-files">
            <li
              v-for="file in editingMod.files"
              :key="file.id"
              :class="{ 'marked-for-deletion': filesToDelete.has(file.id) }"
            >
              <a :href="file.file" target="_blank">{{ getFileName(file.file) }}</a>
              <button type="button" @click="markFileForDeletion(file.id)" class="btn-delete-file">
                &times;
              </button>
            </li>
          </ul>
        </div>

        <div class="form-group">
          <label>Attach New Files</label>
          <button
            type="button"
            @click="triggerFileInput('editModFileInput')"
            class="btn btn-outline"
          >
            Choose Files
          </button>
          <input
            type="file"
            id="editModFileInput"
            multiple
            @change="handleEditModFileUpload"
            class="file-input"
          />
          <ul v-if="newFiles.length > 0" class="file-list">
            <li v-for="(file, index) in newFiles" :key="index">{{ file.name }}</li>
          </ul>
        </div>
      </form>
      <template #footer>
        <button @click="updateMod" class="btn btn-primary">Save Changes</button>
        <button type="button" @click="closeEditModModal" class="btn btn-secondary">Cancel</button>
      </template>
    </BaseModal>

    <div v-if="isPhotoModalVisible" class="modal-overlay" @click="isPhotoModalVisible = false">
      <div class="modal-content" @click.stop>
        <button @click="isPhotoModalVisible = false" class="close-button">&times;</button>
        <img :src="printer.photo" alt="Full size printer photo" class="modal-image" />
      </div>
    </div>

    <ErrorModal
      :show="isErrorModalVisible"
      :message="errorMessage"
      @close="isErrorModalVisible = false"
    />
    <InfoModal
      :show="isInfoModalVisible"
      :message="infoModalMessage"
      @close="isInfoModalVisible = false"
    />
  </div>
</template>

<style scoped>
.page-container {
  padding: 2rem;
}

.content-container {
  max-width: 1200px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.header-content {
  display: flex;
  align-items: center;
}

.detail-photo {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 8px;
  margin-right: 1.5rem;
  border: 1px solid var(--color-border);
}

.detail-photo.clickable {
  cursor: pointer;
}

.header-info h1 {
  font-size: 2.5rem;
  font-weight: 600;
  margin: 0;
  color: var(--color-heading);
}

.manufacturer-serial {
  font-size: 1.1rem;
  color: var(--color-text-soft);
  margin: 0.25rem 0 0.5rem;
}

.status-badge {
  display: inline-block;
  padding: 0.2rem 0.6rem;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: white; /* Default text color */
}

/* Status Colors */
.status-active,
.status-operational,
.status-completed {
  background-color: #28a745; /* Green */
}

.status-under-repair,
.status-under-maintenance {
  background-color: #dc3545; /* Red */
}

.status-inprogress,
.status-onhold {
  background-color: #ffc107; /* Yellow */
  color: #333;
}

.status-decommissioned,
.status-planned,
.status-sold,
.status-archived {
  background-color: #6c757d; /* Grey */
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.card.card-full-width {
  grid-column: 1 / -1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
}

.card-header h3 {
  margin: 0;
  font-size: 1.2rem;
  color: var(--color-heading);
}

.card-body {
  padding: 1.5rem;
}

.card-body p {
  margin: 0 0 0.75rem 0;
  line-height: 1.6;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.card-body p:last-child {
  margin-bottom: 0;
}

/* Mods List Styles */
.mods-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.mod-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem 0;
  border-bottom: 1px solid var(--color-border);
}

.mod-item:last-child {
  border-bottom: none;
}

.mod-info {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.mod-name-link {
  color: var(--color-text-soft);
  text-decoration: none;
}

.mod-name-link:hover {
  text-decoration: underline;
}

.mod-name-link:visited {
  color: var(--color-text-soft);
}

.mod-files {
  margin-top: 0.75rem;
  font-size: 0.9rem;
  width: 100%;
}

.mod-files ul {
  list-style: none;
  padding-left: 1rem;
  margin: 0;
}

.mod-files li a {
  color: var(--color-text);
  text-decoration: none;
}
.mod-files li a:hover {
  text-decoration: underline;
}

.mod-actions {
  display: flex;
  gap: 0.5rem;
  flex-shrink: 0;
  margin-left: 1rem;
}

.file-input {
  display: none;
}

.file-list {
  list-style: none;
  padding: 0;
  margin-top: 1rem;
}

.file-list li {
  background: var(--color-background);
  padding: 0.5rem 1rem;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  border: 1px solid var(--color-border);
  font-size: 0.9rem;
}

.existing-files li {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.existing-files li.marked-for-deletion a {
  text-decoration: line-through;
  opacity: 0.6;
}

.btn-delete-file {
  background: none;
  border: none;
  color: #dc3545;
  font-size: 1.5rem;
  font-weight: bold;
  cursor: pointer;
  padding: 0 0.5rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
}

/* From inventory form for modals */
.form-group {
  margin-bottom: 1rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
  color: var(--color-heading);
}
.form-control {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
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
</style>
