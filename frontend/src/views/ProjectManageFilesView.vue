<template>
  <div class="form-page-container">
    <div v-if="isLoading">Loading...</div>
    <div v-else-if="project">
      <h1>Manage Files for {{ project.project_name }}</h1>
      <form @submit.prevent="save" class="item-form">
        <div class="form-group" v-if="existingFiles.length > 0">
          <label>Existing Files</label>
          <ul class="file-list">
            <li
              v-for="file in existingFiles"
              :key="file.id"
              class="file-list-item"
              :class="{ 'marked-for-deletion': filesToDelete.has(file.id) }"
            >
              <a :href="file.file" target="_blank" class="file-link">{{
                getFileName(file.file)
              }}</a>
              <button
                type="button"
                @click.stop="toggleFileForDeletion(file.id)"
                class="btn-icon-delete"
              >
                &times;
              </button>
            </li>
          </ul>
        </div>
        <div v-else class="form-group">
          <label>Existing Files</label>
          <p>No files have been uploaded for this project yet.</p>
        </div>

        <div class="form-group">
          <label>Attach New Files</label>
          <p>Drag and drop files below, or click to select.</p>
          <div
            class="drop-zone"
            @dragover.prevent
            @dragenter.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleFileDrop"
            :class="{ 'drag-over': isDragging }"
            @click="triggerFileInput"
          >
            <input
              type="file"
              multiple
              @change="handleFileSelect"
              class="file-input"
              ref="fileInputRef"
            />
            <div v-if="!newFiles.length" class="text-center">
              <p>Click here or drop files to upload</p>
            </div>
            <ul v-else class="file-list">
              <li v-for="(file, index) in newFiles" :key="index" class="file-list-item">
                <span>{{ file.name }}</span>
                <button type="button" @click.stop="removeNewFile(index)" class="btn-icon-delete">
                  &times;
                </button>
              </li>
            </ul>
          </div>
        </div>

        <div class="form-actions">
          <button type="submit" class="btn btn-primary">Save Changes</button>
          <button type="button" @click="cancel" class="btn btn-secondary">Cancel</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService'

const route = useRoute()
const router = useRouter()
const projectId = route.params.id

const project = ref(null)
const isLoading = ref(true)
const existingFiles = ref([])
const newFiles = ref([])
const filesToDelete = ref(new Set())
const isDragging = ref(false)
const fileInputRef = ref(null)

const fetchProjectDetails = async () => {
  try {
    const response = await APIService.getProject(projectId)
    project.value = response.data
    existingFiles.value = response.data.files || []
  } catch (error) {
    console.error('Failed to fetch project details:', error)
  } finally {
    isLoading.value = false
  }
}

const getFileName = (filePath) => {
  return filePath ? filePath.split('/').pop() : ''
}

const triggerFileInput = () => {
  fileInputRef.value.click()
}

const handleFileSelect = (event) => {
  addFiles(event.target.files)
}

const handleFileDrop = (event) => {
  isDragging.value = false
  addFiles(event.dataTransfer.files)
}

const addFiles = (fileList) => {
  newFiles.value.push(...Array.from(fileList))
}

const removeNewFile = (index) => {
  newFiles.value.splice(index, 1)
}

const toggleFileForDeletion = (fileId) => {
  if (filesToDelete.value.has(fileId)) {
    filesToDelete.value.delete(fileId)
  } else {
    filesToDelete.value.add(fileId)
  }
}

const save = async () => {
  isLoading.value = true
  try {
    // Delete marked files
    for (const fileId of filesToDelete.value) {
      await APIService.deleteProjectFile(fileId)
    }

    // Upload new files
    for (const file of newFiles.value) {
      const formData = new FormData()
      formData.append('project', projectId)
      formData.append('file', file)
      await APIService.createProjectFile(formData)
    }

    router.push({ name: 'project-detail', params: { id: projectId } })
  } catch (error) {
    console.error('Failed to save project files:', error)
    alert('An error occurred while saving files.')
  } finally {
    isLoading.value = false
  }
}

const cancel = () => {
  router.back()
}

onMounted(fetchProjectDetails)
</script>

<style scoped>
.form-page-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1rem;
}

.item-form {
  background-color: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
}

.form-group p {
  font-size: 0.9rem;
  color: var(--color-text-mute);
  margin-bottom: 0.75rem;
}

.file-input {
  display: none;
}

.drop-zone {
  border: 2px dashed var(--color-border);
  border-radius: 0.5rem;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: background-color 0.2s ease-in-out;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drop-zone.drag-over {
  background-color: var(--color-background-mute);
}

.file-list {
  list-style-type: none;
  padding: 0;
  margin-top: 1rem;
}

.file-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  transition: opacity 0.2s;
}

.file-list-item.marked-for-deletion {
  opacity: 0.6;
}

.file-list-item.marked-for-deletion .file-link {
  text-decoration: line-through;
}

.file-link {
  color: var(--color-heading);
  text-decoration: none;
  font-weight: 500;
}
.file-link:hover {
  text-decoration: underline;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  border-top: 1px solid var(--color-border);
  padding-top: 1.5rem;
}
</style>
