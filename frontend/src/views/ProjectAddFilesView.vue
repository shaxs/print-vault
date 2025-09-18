<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import ProjectFilesForm from '@/components/ProjectFilesForm.vue'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.id)
const isSaving = ref(false)
const projectFiles = ref([])

const fetchProjectFiles = async () => {
  try {
    const response = await APIService.getProjectFiles(projectId)
    projectFiles.value = response.data
  } catch (error) {
    console.error('Failed to fetch project files:', error)
  }
}

const deleteFile = async (fileId) => {
  if (window.confirm('Are you sure you want to delete this file?')) {
    try {
      await APIService.deleteProjectFile(fileId)
      projectFiles.value = projectFiles.value.filter((file) => file.id !== fileId)
    } catch (error) {
      console.error('Failed to delete file:', error)
    }
  }
}

const handleSave = async ({ files }) => {
  isSaving.value = true
  try {
    for (const file of files) {
      const formData = new FormData()
      formData.append('project', projectId)
      formData.append('file', file)
      await APIService.createProjectFile(formData)
    }
    await fetchProjectFiles()
  } catch (error) {
    console.error('Failed to upload files:', error)
  } finally {
    isSaving.value = false
  }
}

const handleCancel = () => {
  router.back()
}

onMounted(fetchProjectFiles)
</script>

<template>
  <div class="form-page-container">
    <h1>Manage Files</h1>
    <ul v-if="projectFiles.length > 0" class="file-list">
      <li v-for="file in projectFiles" :key="file.id" class="file-item">
        <a :href="file.file" target="_blank">{{ file.name }}</a>
        <button @click="deleteFile(file.id)" class="btn btn-sm btn-danger">Remove</button>
      </li>
    </ul>
    <p v-else>No files associated with this project.</p>
    <div class="attach-files">
      <h4>Attach New Files</h4>
      <ProjectFilesForm :projectId="projectId" @save="handleSave" @cancel="handleCancel" />
    </div>
    <div v-if="isSaving">Uploading files...</div>
  </div>
</template>

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
.file-list {
  list-style-type: none;
  padding: 0;
  margin-bottom: 2rem;
}
.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--color-border);
}
.file-item a {
  text-decoration: none;
  color: var(--color-text);
}
.file-item a:hover {
  text-decoration: underline;
}
.file-item button {
  margin-left: 1rem;
}
.attach-files {
  margin-top: 2rem;
}
</style>
