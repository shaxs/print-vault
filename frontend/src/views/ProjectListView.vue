<script setup>
import { ref, onMounted, watch, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '../components/MainHeader.vue'
import ProjectList from '../components/ProjectList.vue'
import ColumnConfigModal from '../components/ColumnConfigModal.vue'

const route = useRoute()
const router = useRouter()
const allProjectColumns = ref([
  { text: 'Project Name', value: 'projectName', defaultVisible: true },
  { text: 'Status', value: 'status', defaultVisible: true },
  { text: 'Description', value: 'description', defaultVisible: false },
])
const visibleColumns = ref([])
const storageKey = 'project-columns'

const loadColumns = () => {
  const saved = localStorage.getItem(storageKey)
  if (saved) {
    visibleColumns.value = JSON.parse(saved)
  } else {
    visibleColumns.value = allProjectColumns.value
      .filter((c) => c.defaultVisible)
      .map((c) => c.value)
  }
}
const saveColumns = (newColumns) => {
  visibleColumns.value = newColumns
  localStorage.setItem(storageKey, JSON.stringify(newColumns))
}

const projects = ref([])
const searchText = ref('')
const isFilterModalVisible = ref(false)
const isColumnModalVisible = ref(false)
const activeFilters = ref({})
const temporaryFilters = reactive({ status: '' })
const filterStorageKey = 'project-filters'

const filterOptions = ref({
  statuses: ['Planning', 'In Progress', 'Completed', 'Canceled', 'On Hold'],
})

const isFilterActive = computed(() => {
  return searchText.value || Object.values(activeFilters.value).some((val) => val && val.length > 0)
})

const loadProjects = async () => {
  try {
    const params = { ...activeFilters.value }
    if (searchText.value) {
      params.search = searchText.value
    }
    const response = await APIService.getProjects(params)
    projects.value = response.data
  } catch (error) {
    console.error('Failed to load projects:', error)
  }
}

watch(searchText, (newSearchText) => {
  const query = { ...route.query }
  if (newSearchText) {
    query.search = newSearchText
  } else {
    delete query.search
  }
  router.replace({ query })
})

watch(
  () => route.query,
  (newQuery) => {
    activeFilters.value = { ...newQuery }
    searchText.value = newQuery.search || ''
    loadProjects()
  },
  { immediate: true },
)

const openFilterModal = () => {
  temporaryFilters.status = activeFilters.value.status || ''
  isFilterModalVisible.value = true
}

const applyFilters = () => {
  const newFilters = { status: temporaryFilters.status || undefined }
  localStorage.setItem(filterStorageKey, JSON.stringify(newFilters))
  isFilterModalVisible.value = false
  router.push({ query: { ...route.query, ...newFilters } })
}

const clearFilters = () => {
  temporaryFilters.status = ''
  localStorage.removeItem(filterStorageKey)
  router.push({ query: { search: searchText.value || undefined } })
}

onMounted(() => {
  loadColumns()
})
</script>

<template>
  <main>
    <MainHeader
      title="Projects"
      createUrl="/projects/create"
      v-model="searchText"
      @open-filter="openFilterModal"
      @open-columns="isColumnModalVisible = true"
    />
    <div class="filter-indicator" v-if="isFilterActive">
      <span>Filters are active.</span>
      <button @click="clearFilters">Clear Filters</button>
    </div>
    <ProjectList :items="projects" :visible-columns="visibleColumns" />

    <Teleport to="body">
      <ColumnConfigModal
        v-if="isColumnModalVisible"
        :all-columns="allProjectColumns"
        :visible-columns="visibleColumns"
        @close="isColumnModalVisible = false"
        @save="saveColumns"
      />

      <div v-if="isFilterModalVisible" class="modal-overlay" @click="isFilterModalVisible = false">
        <div class="modal-form" @click.stop>
          <h3>Filter Projects</h3>
          <form @submit.prevent="applyFilters">
            <div class="form-group">
              <label>Status</label>
              <select v-model="temporaryFilters.status">
                <option value="">-- All --</option>
                <option v-for="status in filterOptions.statuses" :key="status" :value="status">
                  {{ status }}
                </option>
              </select>
            </div>
            <div class="form-actions">
              <button type="submit" class="save-button">Apply Filters</button>
              <button @click="isFilterModalVisible = false" type="button" class="cancel-button">
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </main>
</template>

<style scoped>
.filter-indicator {
  padding: 10px;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-indicator button {
  background: none;
  border: none;
  color: var(--color-text);
  cursor: pointer;
  text-decoration: underline;
  font-size: 0.9rem;
}
.filter-indicator button:hover {
  color: var(--color-heading);
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
  max-width: 400px;
}
.modal-form h3 {
  color: var(--color-heading);
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
.form-group select {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
}
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.save-button,
.cancel-button {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  text-decoration: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: bold;
}
.save-button {
  background-color: var(--color-blue);
  color: white;
}
.cancel-button {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
  border: 1px solid var(--color-border);
}
</style>
