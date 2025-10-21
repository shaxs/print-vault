<script setup>
import { ref, onMounted, watch, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import MainHeader from '../components/MainHeader.vue'
import TrackerList from '../components/TrackerList.vue'
import ColumnConfigModal from '../components/ColumnConfigModal.vue'

const route = useRoute()
const router = useRouter()
const allTrackerColumns = ref([
  { text: 'Tracker Name', value: 'trackerName', defaultVisible: true },
  { text: 'Project', value: 'projectName', defaultVisible: true },
  { text: 'Files', value: 'fileCount', defaultVisible: true },
  { text: 'Progress', value: 'progress', defaultVisible: true },
  { text: 'GitHub URL', value: 'githubUrl', defaultVisible: false },
  { text: 'Storage Type', value: 'storageType', defaultVisible: false },
  { text: 'Created Date', value: 'createdDate', defaultVisible: false },
])
const visibleColumns = ref([])
const storageKey = 'tracker-columns'

const loadColumns = () => {
  const saved = localStorage.getItem(storageKey)
  if (saved) {
    visibleColumns.value = JSON.parse(saved)
  } else {
    visibleColumns.value = allTrackerColumns.value
      .filter((c) => c.defaultVisible)
      .map((c) => c.value)
  }
}
const saveColumns = (newColumns) => {
  visibleColumns.value = newColumns
  localStorage.setItem(storageKey, JSON.stringify(newColumns))
}

const trackers = ref([])
const searchText = ref('')
const isFilterModalVisible = ref(false)
const isColumnModalVisible = ref(false)
const activeFilters = ref({})
const temporaryFilters = reactive({ project: '' })
const filterStorageKey = 'tracker-filters'

const filterOptions = ref({
  projects: [],
})

const isFilterActive = computed(() => {
  return searchText.value || Object.values(activeFilters.value).some((val) => val && val.length > 0)
})

const loadTrackers = async () => {
  try {
    const params = { ...activeFilters.value }
    if (searchText.value) {
      params.search = searchText.value
    }
    const response = await APIService.getTrackers(params)
    trackers.value = response.data
  } catch (error) {
    console.error('Failed to load trackers:', error)
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
    loadTrackers()
  },
  { immediate: true },
)

const openFilterModal = async () => {
  try {
    temporaryFilters.project = activeFilters.value.project || ''
    if (filterOptions.value.projects.length === 0) {
      const projectsRes = await APIService.getProjects()
      filterOptions.value.projects = projectsRes.data
    }
    isFilterModalVisible.value = true
  } catch (error) {
    console.error('Failed to load filter options:', error)
  }
}

const applyFilters = () => {
  const newFilters = {}
  for (const key in temporaryFilters) {
    if (temporaryFilters[key]) {
      newFilters[key] = temporaryFilters[key]
    }
  }
  localStorage.setItem(filterStorageKey, JSON.stringify(newFilters))
  isFilterModalVisible.value = false
  router.push({ query: { ...route.query, ...newFilters } })
}

const clearFilters = () => {
  temporaryFilters.project = ''
  localStorage.removeItem(filterStorageKey)
  router.push({ query: { search: searchText.value || undefined } })
}

const clearFiltersAndClose = () => {
  clearFilters()
  isFilterModalVisible.value = false
}

onMounted(() => {
  loadColumns()
})
</script>

<template>
  <main>
    <MainHeader
      title="Print Trackers"
      createUrl="/trackers/create"
      v-model="searchText"
      @open-filter="openFilterModal"
      @open-columns="isColumnModalVisible = true"
    />
    <div class="filter-indicator" v-if="isFilterActive">
      <span>Filters are active.</span>
      <button @click="clearFilters">Clear Filters</button>
    </div>
    <TrackerList :items="trackers" :visible-columns="visibleColumns" />

    <Teleport to="body">
      <ColumnConfigModal
        v-if="isColumnModalVisible"
        :all-columns="allTrackerColumns"
        :visible-columns="visibleColumns"
        @close="isColumnModalVisible = false"
        @save="saveColumns"
      />

      <div v-if="isFilterModalVisible" class="modal-overlay" @click="isFilterModalVisible = false">
        <div class="modal-form" @click.stop>
          <h3>Filter Print Trackers</h3>
          <form @submit.prevent="applyFilters">
            <div class="form-group">
              <label>Project</label>
              <select v-model="temporaryFilters.project">
                <option value="">-- All --</option>
                <option
                  v-for="project in filterOptions.projects"
                  :key="project.id"
                  :value="project.id"
                >
                  {{ project.project_name }}
                </option>
              </select>
            </div>
            <div class="form-actions">
              <button
                v-if="isFilterActive"
                @click="clearFiltersAndClose"
                type="button"
                class="btn btn-danger"
              >
                Remove Filters
              </button>
              <div class="form-actions-right">
                <button type="submit" class="btn btn-primary">Apply Filters</button>
                <button
                  @click="isFilterModalVisible = false"
                  type="button"
                  class="btn btn-secondary"
                >
                  Cancel
                </button>
              </div>
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
  margin-bottom: 15px;
}
.form-group label {
  display: block;
  margin-bottom: 5px;
  color: var(--color-text);
  font-weight: bold;
}
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1rem;
}
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 20px;
}
.form-actions-right {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
</style>
