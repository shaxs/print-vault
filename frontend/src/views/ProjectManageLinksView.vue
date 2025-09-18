<template>
  <div class="form-page-container">
    <div v-if="isLoading">Loading project details...</div>
    <div v-else-if="project">
      <h1>Manage Links for {{ project.project_name }}</h1>
      <div class="item-form">
        <form @submit.prevent="saveLink" class="link-form">
          <div class="form-group">
            <label for="linkName">Link Name</label>
            <input
              type="text"
              id="linkName"
              v-model="editableLink.name"
              placeholder="e.g., Assembly Guide"
              required
            />
          </div>
          <div class="form-group">
            <label for="linkUrl">URL</label>
            <input
              type="url"
              id="linkUrl"
              v-model="editableLink.url"
              placeholder="e.g., https://www.instructables.com/..."
              required
            />
          </div>
          <div class="form-actions form-actions-inline">
            <button type="submit" class="btn btn-primary">
              {{ isEditing ? 'Update Link' : 'Add Link' }}
            </button>
            <button v-if="isEditing" type="button" @click="cancelEdit" class="btn btn-secondary">
              Cancel
            </button>
          </div>
        </form>

        <hr class="section-divider" />

        <div class="form-group">
          <label>Existing Links</label>
          <ul v-if="links.length > 0" class="link-list">
            <li v-for="link in links" :key="link.id" class="link-list-item">
              <div class="link-info">
                <a :href="link.url" target="_blank" class="link-name">{{ link.name }}</a>
                <span class="link-url">{{ link.url }}</span>
              </div>
              <div class="link-actions">
                <button @click="startEdit(link)" class="btn-icon btn-edit">✎</button>
                <button @click="deleteLink(link.id)" class="btn-delete-file">&times;</button>
              </div>
            </li>
          </ul>
          <p v-else>No links have been added to this project yet.</p>
        </div>

        <div class="form-actions">
          <button type="button" @click="goBack" class="btn btn-secondary">Back to Project</button>
        </div>
      </div>
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
const links = ref([])
const isLoading = ref(true)
const isEditing = ref(false)
const editableLink = ref({ id: null, name: '', url: '' })

const fetchProjectDetails = async () => {
  try {
    const response = await APIService.getProject(projectId)
    project.value = response.data
    links.value = response.data.links || []
  } catch (error) {
    console.error('Failed to fetch project details:', error)
  } finally {
    isLoading.value = false
  }
}

const resetForm = () => {
  isEditing.value = false
  editableLink.value = { id: null, name: '', url: '' }
}

const startEdit = (link) => {
  isEditing.value = true
  editableLink.value = { ...link }
}

const cancelEdit = () => {
  resetForm()
}

const saveLink = async () => {
  const payload = {
    project: projectId,
    name: editableLink.value.name,
    url: editableLink.value.url,
  }

  try {
    if (isEditing.value) {
      // Update existing link
      await APIService.updateProjectLink(editableLink.value.id, payload)
    } else {
      // Create new link
      await APIService.createProjectLink(payload)
    }
    await fetchProjectDetails() // Refresh the list
    resetForm()
  } catch (error) {
    console.error('Failed to save link:', error)
    alert('An error occurred while saving the link.')
  }
}

const deleteLink = async (linkId) => {
  if (confirm('Are you sure you want to delete this link?')) {
    try {
      await APIService.deleteProjectLink(linkId)
      await fetchProjectDetails() // Refresh the list
    } catch (error) {
      console.error('Failed to delete link:', error)
      alert('An error occurred while deleting the link.')
    }
  }
}

const goBack = () => {
  router.push({ name: 'project-detail', params: { id: projectId } })
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

input[type='text'],
input[type='url'] {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
}

.link-form {
  margin-bottom: 2rem;
}

.section-divider {
  border: 0;
  border-top: 1px solid var(--color-border);
  margin: 2rem 0;
}

.link-list {
  list-style-type: none;
  padding: 0;
}

.link-list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.link-info {
  display: flex;
  flex-direction: column;
}

.link-name {
  font-weight: 600;
  color: var(--color-heading);
  text-decoration: none;
}
.link-name:hover {
  text-decoration: underline;
}

.link-url {
  font-size: 0.8rem;
  color: var(--color-text-mute);
}

.link-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
}

.btn-edit {
  color: var(--color-blue);
}

.btn-delete-file {
  background: none;
  border: none;
  color: #ef4444;
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0 0.5rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--color-border);
}

.form-actions-inline {
  justify-content: flex-start;
  border-top: none;
  padding-top: 0;
  margin-top: 1rem;
}
</style>
