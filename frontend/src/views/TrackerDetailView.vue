<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService.js'
import DeleteTrackerModal from '@/components/DeleteTrackerModal.vue'

const route = useRoute()
const router = useRouter()

// Data
const tracker = ref(null)
const loading = ref(true)
const error = ref(null)
const searchQuery = ref('')
const showDeleteConfirm = ref(false)
const deleting = ref(false)
const collapsedCategories = ref(new Set())

// Filter state
const isFilterModalVisible = ref(false)
const activeFilters = ref({
  color: '',
  material: '',
  status: '',
  missingConfig: false, // New filter for unconfigured files
})

// Temporary filter state for modal (prevents immediate filtering)
const tempFilters = ref({
  color: '',
  material: '',
  status: '',
  missingConfig: false,
})

// Edit file state
const isEditFileModalVisible = ref(false)
const editingFile = ref(null)
const editFileForm = ref({
  color: '',
  material: '',
  quantity: 1,
})

// Delete file state
const deletingFile = ref(false)

// Materials from API
const materials = ref([])
const loadingMaterials = ref(false)

// Load materials from API
const loadMaterials = async () => {
  loadingMaterials.value = true
  try {
    const response = await APIService.getMaterials()
    materials.value = response.data.map((m) => m.name)

    // If no materials loaded, use fallback
    if (materials.value.length === 0) {
      materials.value = ['ABS', 'PLA', 'PETG', 'TPU', 'Nylon', 'ASA', 'Other']
    }
  } catch (error) {
    console.error('Failed to load materials:', error)
    // Fallback to default materials
    materials.value = ['ABS', 'PLA', 'PETG', 'TPU', 'Nylon', 'ASA', 'Other']
  } finally {
    loadingMaterials.value = false
  }
}

// Load tracker data
const loadTracker = async () => {
  loading.value = true
  error.value = null
  try {
    const response = await APIService.getTracker(route.params.id)
    tracker.value = response.data
  } catch (err) {
    console.error('Failed to load tracker:', err)
    error.value = 'Failed to load tracker. Please try again.'
  } finally {
    loading.value = false
  }
}

// Group files by directory
const groupedFiles = computed(() => {
  if (!tracker.value || !tracker.value.files) return []

  const groups = {}

  tracker.value.files.forEach((file) => {
    const dir = file.directory_path || 'Root'
    if (!groups[dir]) {
      groups[dir] = {
        name: dir,
        isOpen: !collapsedCategories.value.has(dir),
        files: [],
      }
    }
    groups[dir].files.push(file)
  })

  return Object.values(groups)
})

// Filter files by search query and active filters
const filteredCategories = computed(() => {
  let categories = groupedFiles.value

  // Apply search filter
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    categories = categories
      .map((category) => ({
        ...category,
        files: category.files.filter((file) => file.filename.toLowerCase().includes(query)),
      }))
      .filter((category) => category.files.length > 0)
  }

  // Apply active filters
  categories = categories
    .map((category) => ({
      ...category,
      files: category.files.filter((file) => {
        // Color filter
        if (activeFilters.value.color && file.color !== activeFilters.value.color) {
          return false
        }
        // Material filter
        if (activeFilters.value.material && file.material !== activeFilters.value.material) {
          return false
        }
        // Status filter
        if (activeFilters.value.status && file.status !== activeFilters.value.status) {
          return false
        }
        // Missing config filter
        if (activeFilters.value.missingConfig && file.color && file.material) {
          return false // Hide files that HAVE config when filter is active
        }
        return true
      }),
    }))
    .filter((category) => category.files.length > 0)

  return categories
})

// Count files missing configuration (no color or material)
const unconfiguredFilesCount = computed(() => {
  if (!tracker.value || !tracker.value.files) return 0
  return tracker.value.files.filter((file) => !file.color || !file.material).length
})

// Toggle category open/closed
const toggleCategory = (category) => {
  if (collapsedCategories.value.has(category.name)) {
    collapsedCategories.value.delete(category.name)
  } else {
    collapsedCategories.value.add(category.name)
  }
}

// Collapse/Expand all categories
const allCollapsed = computed(() => {
  if (!filteredCategories.value || filteredCategories.value.length === 0) return false
  return filteredCategories.value.every((cat) => collapsedCategories.value.has(cat.name))
})

const toggleCollapseAll = () => {
  if (allCollapsed.value) {
    // Expand all
    collapsedCategories.value.clear()
  } else {
    // Collapse all
    const newSet = new Set()
    filteredCategories.value.forEach((cat) => {
      newSet.add(cat.name)
    })
    collapsedCategories.value = newSet
  }
}

// Update file printed quantity
const updateFilePrintedQuantity = async (file, newValue) => {
  const printed = parseInt(newValue) || 0
  const clamped = Math.max(0, Math.min(printed, file.quantity))

  // Auto-complete when printed equals quantity
  const newStatus =
    clamped >= file.quantity
      ? 'completed'
      : file.status === 'completed'
        ? 'in_progress'
        : file.status

  // Optimistic update for immediate UI feedback
  const previousPrinted = file.printed_quantity
  const previousStatus = file.status
  file.printed_quantity = clamped
  file.status = newStatus

  try {
    await APIService.updateTrackerFileStatus(file.id, newStatus, clamped)

    // Reload full tracker to get updated aggregate stats
    const response = await APIService.getTracker(route.params.id)

    // ✅ FIX: Replace entire tracker with fresh data
    // Computed properties (overallProgressStyle, fileProgressPercentage) will auto-update
    tracker.value = response.data
  } catch (err) {
    console.error('Failed to update printed quantity:', err)
    // Revert on error
    file.printed_quantity = previousPrinted
    file.status = previousStatus
    alert('Failed to update printed quantity')
  }
}

// Update file quantity
const updateFileQuantity = async (file, newValue) => {
  const quantity = parseInt(newValue) || 1
  const clamped = Math.max(1, quantity)

  try {
    await APIService.updateTrackerFileConfiguration(file.id, file.color, file.material, clamped)
    file.quantity = clamped
    await loadTracker()
  } catch (err) {
    console.error('Failed to update file quantity:', err)
    alert('Failed to update file quantity')
  }
}

// Toggle file completion
const toggleFileCompletion = async (file) => {
  const newStatus = file.status === 'completed' ? 'not_started' : 'completed'
  const newPrinted = newStatus === 'completed' ? file.quantity : 0

  // Store old values for revert on error
  const previousStatus = file.status
  const previousPrinted = file.printed_quantity

  // Optimistic update
  file.status = newStatus
  file.printed_quantity = newPrinted

  try {
    await APIService.updateTrackerFileStatus(file.id, newStatus, newPrinted)

    // Reload full tracker to get updated aggregate stats
    const response = await APIService.getTracker(route.params.id)

    // ✅ FIX: Replace entire tracker with fresh data
    // Computed properties (overallProgressStyle, fileProgressPercentage) will auto-update
    tracker.value = response.data
  } catch (err) {
    console.error('Failed to toggle file completion:', err)
    // Revert optimistic change on error
    file.status = previousStatus
    file.printed_quantity = previousPrinted
    alert('Failed to update file status')
  }
}

// Get multicolor gradient
const getMulticolorGradient = computed(() => {
  const primary = tracker.value?.primary_color || '#4a90e2'
  const accent = tracker.value?.accent_color || '#f5a623'
  return `linear-gradient(to right, ${primary}, ${accent})`
})

// Get color badge style
const getColorBadgeStyle = (color) => {
  const primary = tracker.value?.primary_color || '#4a90e2'
  const accent = tracker.value?.accent_color || '#f5a623'

  switch (color?.toLowerCase()) {
    case 'primary':
      return { backgroundColor: primary }
    case 'accent':
      return { backgroundColor: accent }
    case 'multicolor':
      return { backgroundImage: getMulticolorGradient.value }
    case 'clear':
      return {
        backgroundColor: '#e2e8f0',
        color: '#4a5568',
        border: '1px solid #cbd5e0',
      }
    case 'other':
      return { backgroundColor: '#78716c' }
    default:
      return { backgroundColor: '#94a3b8' }
  }
}

// Get file URL for opening
const getFileUrl = (file) => {
  // For files with local_file (uploaded or downloaded), use the local file URL
  // Backend returns relative URLs (/media/...) which browser resolves with correct protocol
  if (file.local_file) {
    return file.local_file
  }
  // For GitHub links, use the GitHub URL
  return file.github_url || '#'
}

// Open or download file
const openFile = async (file) => {
  const url = getFileUrl(file)
  if (!url || url === '#') return

  // For local files, add ?download=1 to trigger download via nginx Content-Disposition header
  if (file.local_file) {
    const downloadUrl = url.includes('?') ? `${url}&download=1` : `${url}?download=1`
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = file.filename || 'download'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } else {
    // For external links (GitHub URLs), convert to raw URL and trigger download
    let downloadUrl = url

    // Convert GitHub blob URLs to raw URLs for direct download
    if (url.includes('github.com') && url.includes('/blob/')) {
      downloadUrl = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
    }

    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = file.filename || 'download'
    link.target = '_blank'
    link.rel = 'noopener noreferrer'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}

// Delete tracker
const confirmDelete = () => {
  showDeleteConfirm.value = true
}

const cancelDelete = () => {
  showDeleteConfirm.value = false
  deleting.value = false
}

const deleteTracker = async () => {
  deleting.value = true
  try {
    await APIService.deleteTracker(tracker.value.id)
    router.push('/trackers')
  } catch (err) {
    console.error('Failed to delete tracker:', err)
    alert('Failed to delete tracker')
    deleting.value = false
    showDeleteConfirm.value = false
  }
}

const downloadAndDeleteTracker = async () => {
  deleting.value = true
  try {
    // First, download the ZIP file
    const response = await APIService.downloadTrackerFiles(tracker.value.id)

    // Create a blob and trigger download
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${tracker.value.name}_files.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    // Small delay to ensure download starts
    await new Promise((resolve) => setTimeout(resolve, 500))

    // Then delete the tracker
    await APIService.deleteTracker(tracker.value.id)
    router.push('/trackers')
  } catch (err) {
    console.error('Failed to download and delete tracker:', err)
    alert('Failed to download files or delete tracker')
    deleting.value = false
    showDeleteConfirm.value = false
  }
}

// Navigate to project
const goToProject = () => {
  if (tracker.value.project) {
    router.push(`/projects/${tracker.value.project}`)
  }
}

// Filter functions
const openFilterModal = () => {
  // Copy current active filters to temp filters when opening modal
  tempFilters.value = { ...activeFilters.value }
  isFilterModalVisible.value = true
}

const applyFilters = () => {
  // Apply temp filters to active filters
  activeFilters.value = { ...tempFilters.value }
  isFilterModalVisible.value = false
}

const cancelFilters = () => {
  // Discard temp filters without applying
  isFilterModalVisible.value = false
}

const clearFilters = () => {
  activeFilters.value = {
    color: '',
    material: '',
    status: '',
    missingConfig: false,
  }
}

const filterUnconfiguredFiles = () => {
  clearFilters()
  activeFilters.value.missingConfig = true
  // Don't open modal - just apply filter directly
}

const clearFiltersAndClose = () => {
  clearFilters()
  tempFilters.value = { ...activeFilters.value }
  isFilterModalVisible.value = false
}

// Download all files as ZIP
const downloadingZip = ref(false)

const hasFiles = computed(() => {
  return tracker.value && tracker.value.files && tracker.value.files.length > 0
})

const downloadAllAsZip = async () => {
  if (!tracker.value || downloadingZip.value) return

  downloadingZip.value = true

  try {
    const response = await APIService.downloadTrackerZip(tracker.value.id)

    // Create a blob from the response
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = window.URL.createObjectURL(blob)

    // Create download link and trigger it
    const link = document.createElement('a')
    link.href = url
    link.download = `${tracker.value.name.replace(/[^a-z0-9]/gi, '_')}_files.zip`
    document.body.appendChild(link)
    link.click()

    // Cleanup
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Failed to download ZIP:', err)
    alert('Failed to download files. Please try again.')
  } finally {
    downloadingZip.value = false
  }
}

// Edit file functions
const openEditFileModal = (file) => {
  editingFile.value = file
  editFileForm.value = {
    color: file.color || '',
    material: file.material || '',
    quantity: file.quantity || 1,
  }
  isEditFileModalVisible.value = true
}

const closeEditFileModal = () => {
  isEditFileModalVisible.value = false
  editingFile.value = null
}

const saveFileConfiguration = async () => {
  if (!editingFile.value) return

  try {
    await APIService.updateTrackerFileConfiguration(
      editingFile.value.id,
      editFileForm.value.color,
      editFileForm.value.material,
      editFileForm.value.quantity,
    )

    // Reload tracker to get updated data
    await loadTracker()
    closeEditFileModal()
  } catch (err) {
    console.error('Failed to update file configuration:', err)
    alert('Failed to update file configuration. Please try again.')
  }
}

// Delete file functions
const confirmDeleteFile = () => {
  if (!editingFile.value) return

  const confirmed = confirm(
    `Are you sure you want to delete "${editingFile.value.filename}"?\n\nThis action cannot be undone.`,
  )

  if (confirmed) {
    deleteFile()
  }
}

const deleteFile = async () => {
  if (!editingFile.value) return

  deletingFile.value = true

  try {
    await APIService.deleteTrackerFile(editingFile.value.id)

    // Close modal and reload tracker
    closeEditFileModal()
    await loadTracker()
  } catch (err) {
    console.error('Failed to delete file:', err)
    alert('Failed to delete file. Please try again.')
  } finally {
    deletingFile.value = false
  }
}

// Get unique filter options from files
const filterOptions = computed(() => {
  if (!tracker.value || !tracker.value.files) {
    return { colors: [], materials: [], statuses: [] }
  }

  const colors = [...new Set(tracker.value.files.map((f) => f.color).filter(Boolean))]
  const materials = [...new Set(tracker.value.files.map((f) => f.material).filter(Boolean))]
  const statuses = [
    { value: 'not_started', label: 'Not Started' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'completed', label: 'Completed' },
  ]

  return { colors, materials, statuses }
})

// Check if any filters are active
const isFilterActive = computed(() => {
  return (
    activeFilters.value.color ||
    activeFilters.value.material ||
    activeFilters.value.status ||
    activeFilters.value.missingConfig
  )
})

// Computed style for overall progress bar
const overallProgressStyle = computed(() => {
  const percentage = tracker.value?.progress_percentage || 0
  return {
    width: `${percentage}%`,
    height: '100%',
    backgroundColor: getProgressColor(percentage),
    transition: 'width 0.3s ease',
  }
})

// Get progress bar color
const getProgressColor = (percentage) => {
  if (percentage === 0) return 'var(--color-progress-none)' // gray
  if (percentage < 50) return 'var(--color-progress-low)' // red
  if (percentage < 100) return 'var(--color-progress-medium)' // orange
  return 'var(--color-progress-complete)' // green
}

// Computed style for individual file progress
const fileProgressStyle = (file) => {
  const percentage =
    file.quantity > 0 ? Math.round((file.printed_quantity / file.quantity) * 100) : 0
  return {
    width: `${percentage}%`,
    height: '100%',
    backgroundColor: getProgressColor(percentage),
    transition: 'width 0.3s ease',
  }
}

// Add Files functionality
const openAddFilesModal = () => {
  if (tracker.value && tracker.value.id) {
    router.push({ name: 'tracker-add-files', params: { id: tracker.value.id } })
  }
}

onMounted(() => {
  loadTracker()
  loadMaterials()
})
</script>

<template>
  <div class="page-container">
    <div class="content-container">
      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading tracker...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <span class="error-icon">⚠️</span>
        <p>{{ error }}</p>
        <button @click="loadTracker" class="btn btn-primary">Retry</button>
      </div>

      <!-- Tracker Content -->
      <div v-else-if="tracker">
        <!-- Header with Actions -->
        <div class="detail-header">
          <div class="header-content">
            <div class="header-info">
              <h1>
                {{ tracker.name }}
                <span v-if="tracker.show_on_dashboard" class="featured-badge alert-info"
                  >Featured</span
                >
              </h1>
              <p class="tracker-subtitle">
                Associated Project:
                <a v-if="tracker.project_name" @click="goToProject" class="project-link">
                  {{ tracker.project_name }}
                </a>
                <span v-else class="text-muted">No Project</span>
              </p>
            </div>
          </div>
          <div class="header-actions">
            <button @click="openFilterModal" class="btn btn-secondary">Filter</button>
            <div class="search-container">
              <input
                type="search"
                v-model="searchQuery"
                placeholder="Search files..."
                class="search-input"
              />
              <button v-if="searchQuery" @click="searchQuery = ''" class="search-clear-button">
                &times;
              </button>
            </div>
            <router-link
              :to="{ name: 'tracker-edit', params: { id: tracker.id } }"
              class="btn btn-primary"
              >Edit</router-link
            >
            <button @click="confirmDelete" class="btn btn-danger">Delete</button>
          </div>
        </div>

        <!-- Filters Active Banner (below header) -->
        <div v-if="isFilterActive" class="filters-active-banner-header">
          <span>Filters are active.</span>
          <button @click="clearFilters" class="clear-filters-link">Clear Filters</button>
        </div>

        <!-- Tracker Info Card -->
        <div class="card mb-6">
          <div class="card-body">
            <!-- Progress Bar -->
            <div class="mt-4">
              <div class="flex justify-between mb-1">
                <span class="progress-label">Overall Progress</span>
                <span class="progress-percentage">{{ tracker.progress_percentage || 0 }}%</span>
              </div>
              <div class="progress-bar-bg">
                <div class="progress-bar-fg" :style="overallProgressStyle"></div>
              </div>

              <!-- Stats -->
              <div class="stats-container">
                <div>
                  <p class="stat-number">{{ tracker.total_quantity || 0 }}</p>
                  <p class="stat-label">Total Parts</p>
                </div>
                <div>
                  <p class="stat-number stat-printed">{{ tracker.printed_quantity_total || 0 }}</p>
                  <p class="stat-label">Printed</p>
                </div>
                <div>
                  <p class="stat-number stat-pending">
                    {{ tracker.pending_quantity || 0 }}
                  </p>
                  <p class="stat-label">Pending</p>
                </div>
              </div>
            </div>

            <!-- Warning for unconfigured files -->
            <div
              v-if="unconfiguredFilesCount > 0"
              class="alert alert-warning"
              style="margin-top: 1rem; cursor: pointer"
              @click="filterUnconfiguredFiles"
            >
              ⚠️ {{ unconfiguredFilesCount }} file{{ unconfiguredFilesCount !== 1 ? 's' : '' }}
              missing configuration (color/material/quantity).
              <span style="text-decoration: underline">Click to filter</span>
            </div>
          </div>
        </div>

        <!-- Collapse/Expand All and Add Files Buttons -->
        <div class="add-files-section">
          <button
            v-if="filteredCategories.length > 0"
            @click="toggleCollapseAll"
            class="btn btn-sm btn-secondary"
          >
            {{ allCollapsed ? 'Expand All' : 'Collapse All' }}
          </button>
          <button
            @click="downloadAllAsZip"
            class="btn btn-sm btn-secondary"
            :disabled="downloadingZip || !hasFiles"
          >
            <span v-if="downloadingZip">Preparing Download...</span>
            <span v-else>Download All Files</span>
          </button>
          <button @click="openAddFilesModal" class="btn btn-sm btn-primary" :disabled="!tracker">
            Add Files
          </button>
        </div>

        <!-- Files by Category -->
        <div class="card">
          <div class="card-body">
            <div class="space-y-2">
              <div
                v-for="category in filteredCategories"
                :key="category.name"
                class="category-group"
              >
                <!-- Category Header -->
                <div
                  class="category-header"
                  @click="toggleCategory(category)"
                  :class="{ 'is-collapsed': !category.isOpen }"
                >
                  <h2 class="category-title">{{ category.name }}</h2>
                  <span class="arrow">&#9660;</span>
                </div>

                <!-- Category Files -->
                <div v-if="category.isOpen" class="category-content">
                  <div
                    v-for="file in category.files"
                    :key="file.id"
                    class="file-row"
                    :class="{ 'completed-row': file.status === 'completed' }"
                  >
                    <!-- File Name and Color -->
                    <div class="file-name">
                      <input
                        type="checkbox"
                        :checked="file.status === 'completed'"
                        @change="toggleFileCompletion(file)"
                        class="file-checkbox"
                      />
                      <a
                        @click="openFile(file)"
                        :class="{ 'line-through': file.status === 'completed' }"
                        class="file-link"
                      >
                        {{ file.filename }}
                      </a>

                      <!-- Warning icon for missing configuration -->
                      <span
                        v-if="!file.color || !file.material"
                        class="missing-config-icon"
                        title="Missing color, material, and/or quantity configuration"
                      >
                        ⚠️
                      </span>

                      <span class="color-tag" :style="getColorBadgeStyle(file.color)">
                        {{ file.color }}
                      </span>

                      <span class="material-tag">{{ file.material }}</span>

                      <button
                        @click.stop="openEditFileModal(file)"
                        class="edit-file-btn"
                        title="Edit file configuration"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          stroke-width="2"
                          stroke-linecap="round"
                          stroke-linejoin="round"
                        >
                          <path
                            d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"
                          ></path>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                      </button>
                    </div>

                    <!-- File Actions -->
                    <div class="file-actions">
                      <label class="printed-label">Quantity:</label>
                      <input
                        type="number"
                        :value="file.quantity"
                        @change="updateFileQuantity(file, $event.target.value)"
                        class="form-control quantity-input"
                        :disabled="file.status === 'completed'"
                        min="1"
                      />

                      <label class="printed-label">Printed:</label>
                      <div class="printed-control">
                        <button
                          class="printed-btn minus-btn"
                          @click="
                            updateFilePrintedQuantity(
                              file,
                              Math.max(0, (file.printed_quantity || 0) - 1),
                            )
                          "
                          :disabled="
                            file.status === 'completed' || (file.printed_quantity || 0) <= 0
                          "
                        >
                          −
                        </button>
                        <input
                          type="number"
                          :value="file.printed_quantity || 0"
                          @input="updateFilePrintedQuantity(file, $event.target.value)"
                          class="form-control printed-input"
                          :disabled="file.status === 'completed'"
                          :max="file.quantity"
                          min="0"
                        />
                        <button
                          class="printed-btn plus-btn"
                          @click="
                            updateFilePrintedQuantity(
                              file,
                              Math.min(file.quantity, (file.printed_quantity || 0) + 1),
                            )
                          "
                          :disabled="
                            file.status === 'completed' ||
                            (file.printed_quantity || 0) >= file.quantity
                          "
                        >
                          +
                        </button>
                      </div>
                      <span class="required-amount">/ {{ file.quantity }}</span>

                      <!-- Progress Bar -->
                      <div class="progress-bar-bg small">
                        <div
                          class="progress-bar-fg"
                          :class="file.status === 'completed' ? 'bg-green' : 'bg-blue'"
                          :style="fileProgressStyle(file)"
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Empty State -->
              <div v-if="filteredCategories.length === 0" class="empty-state">
                <p v-if="searchQuery">No files match your search.</p>
                <p v-else>No files found in this tracker.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Delete Tracker Modal -->
      <DeleteTrackerModal
        :isVisible="showDeleteConfirm"
        :trackerName="tracker?.name || ''"
        :storageType="tracker?.storage_type || 'link'"
        :fileCount="tracker?.total_count || 0"
        :totalStorageUsed="tracker?.total_storage_used || 0"
        :filesDownloaded="tracker?.files_downloaded || false"
        @close="cancelDelete"
        @delete="deleteTracker"
        @downloadAndDelete="downloadAndDeleteTracker"
      />

      <!-- Filter Modal -->
      <Teleport to="body">
        <div
          v-if="isFilterModalVisible"
          class="modal-overlay"
          @click="isFilterModalVisible = false"
        >
          <div class="modal-form" @click.stop>
            <h3>Filter Files</h3>
            <form @submit.prevent="applyFilters">
              <div class="form-group">
                <label>Color</label>
                <select v-model="tempFilters.color">
                  <option value="">-- All --</option>
                  <option v-for="color in filterOptions.colors" :key="color" :value="color">
                    {{ color }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>Material</label>
                <select v-model="tempFilters.material">
                  <option value="">-- All --</option>
                  <option
                    v-for="material in filterOptions.materials"
                    :key="material"
                    :value="material"
                  >
                    {{ material }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>Status</label>
                <select v-model="tempFilters.status">
                  <option value="">-- All --</option>
                  <option
                    v-for="status in filterOptions.statuses"
                    :key="status.value"
                    :value="status.value"
                  >
                    {{ status.label }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" v-model="tempFilters.missingConfig" />
                  <span>Show only files missing configuration</span>
                </label>
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
                  <button @click="cancelFilters" type="button" class="btn btn-secondary">
                    Cancel
                  </button>
                  <button type="submit" class="btn btn-primary">Apply Filters</button>
                </div>
              </div>
            </form>
          </div>
        </div>

        <!-- Edit File Modal -->
        <div v-if="isEditFileModalVisible" class="modal-overlay" @click="closeEditFileModal">
          <div class="modal-form" @click.stop>
            <h3>Edit File Configuration</h3>
            <p class="edit-filename">{{ editingFile?.filename }}</p>
            <form @submit.prevent="saveFileConfiguration">
              <div class="form-group">
                <label>Color</label>
                <select v-model="editFileForm.color" required>
                  <option value="">-- Select Color --</option>
                  <option value="Primary">Primary</option>
                  <option value="Accent">Accent</option>
                  <option value="Multicolor">Multicolor</option>
                  <option value="Clear">Clear</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <div class="form-group">
                <label>Material</label>
                <select v-model="editFileForm.material" required :disabled="loadingMaterials">
                  <option value="">-- Select Material --</option>
                  <option v-for="material in materials" :key="material" :value="material">
                    {{ material }}
                  </option>
                </select>
              </div>
              <div class="form-group">
                <label>Quantity</label>
                <input
                  type="number"
                  v-model.number="editFileForm.quantity"
                  min="1"
                  max="99"
                  required
                  class="form-control"
                />
              </div>
              <div class="form-actions">
                <button
                  @click.prevent="confirmDeleteFile"
                  type="button"
                  class="btn btn-danger"
                  :disabled="deletingFile"
                >
                  {{ deletingFile ? 'Deleting...' : 'Delete' }}
                </button>
                <div class="form-actions-right">
                  <button type="submit" class="btn btn-primary">Save Changes</button>
                  <button @click="closeEditFileModal" type="button" class="btn btn-secondary">
                    Cancel
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </Teleport>

      <!-- Filter Indicator -->
      <div v-if="isFilterActive" class="filter-indicator">
        <span>Filters are active.</span>
        <button @click="clearFilters">Clear Filters</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Base Styles */
.page-container {
  padding: 2rem;
}
.content-container {
  max-width: 1200px;
  margin: 0 auto;
}

/* Loading and Error States */
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 20px;
}

.spinner {
  border: 4px solid var(--color-background-mute);
  border-top: 4px solid var(--color-brand);
  border-radius: 50%;
  width: 50px;
  height: 50px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.error-icon {
  font-size: 3rem;
}

/* Header */
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

.header-info h1 {
  font-size: 2.5rem;
  font-weight: 600;
  margin: 0;
  color: var(--color-heading);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.featured-badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 12px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  white-space: nowrap;
  letter-spacing: 0.025em;
}

.featured-badge.alert-info {
  background: color-mix(in srgb, var(--color-alert-info), transparent 85%);
  color: var(--color-alert-info);
  border: 1px solid color-mix(in srgb, var(--color-alert-info), transparent 70%);
}

.tracker-subtitle {
  font-size: 1.1rem;
  color: var(--color-text);
  margin: 0.25rem 0 0.5rem;
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
}

.search-container {
  position: relative;
}

.search-input {
  padding: 8px 30px 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  min-width: 250px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1rem;
  height: 41px;
}

.search-clear-button {
  position: absolute;
  right: 5px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--color-text);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 5px;
}

/* Controls */
.list-controls {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.form-control {
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  background-color: var(--color-background);
  color: var(--color-text);
  flex-grow: 1;
}

/* Card */
.card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.card-body {
  padding: 1.5rem;
}

/* Subtitle */
.subtitle {
  color: var(--color-text);
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.project-link {
  color: var(--color-brand);
  text-decoration: none;
  cursor: pointer;
}

.project-link:hover {
  text-decoration: underline;
}

.text-muted {
  color: var(--color-text);
  opacity: 0.6;
}

/* Progress */
.progress-label {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-heading);
}

.progress-percentage {
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--color-brand);
}

.progress-bar-bg {
  width: 100%;
  background-color: var(--color-background);
  border-radius: 9999px;
  height: 0.75rem;
}

.progress-bar-fg {
  background-color: var(--color-brand);
  height: 0.75rem;
  border-radius: 9999px;
  transition: width 0.3s ease;
}

.progress-bar-bg.small {
  width: 6rem;
  height: 0.5rem;
}

.progress-bar-fg.bg-blue {
  background-color: var(--color-brand);
}

.progress-bar-fg.bg-green {
  background-color: #22c55e;
}

/* Stats */
.stats-container {
  display: flex;
  justify-content: space-between;
  text-align: center;
  margin-top: 1rem;
  border-top: 1px solid var(--color-border);
  padding-top: 0.75rem;
}

.stat-number {
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--color-heading);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--color-text);
  opacity: 0.7;
}

.stat-printed {
  color: #22c55e;
}

.stat-pending {
  color: #f5a623;
}

/* Categories */
.category-group {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.75rem;
  margin-bottom: 0.75rem;
}

.category-group:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.category-header {
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
}

.category-header:hover {
  background-color: var(--color-background-mute);
}

.category-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-heading);
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  flex: 1;
  min-width: 0;
}

.arrow {
  transition: transform 0.2s ease-in-out;
}

.category-header.is-collapsed .arrow {
  transform: rotate(-90deg);
}

.category-content {
  padding-top: 0.5rem;
}

/* File Row */
.file-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem;
  border-radius: 6px;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.completed-row {
  background-color: rgba(34, 197, 94, 0.1);
}

.completed-row .line-through {
  text-decoration: line-through;
  opacity: 0.6;
}

.file-name {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.file-link {
  color: var(--color-text);
  text-decoration: none;
  cursor: pointer;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
}

.file-link:hover {
  text-decoration: underline;
}

.file-link:visited {
  color: var(--color-text);
}

.file-link.line-through {
  text-decoration: line-through;
  opacity: 0.6;
}

.file-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.color-select,
.material-select {
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 0.85rem;
  cursor: pointer;
}

.color-select:disabled,
.material-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.file-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.printed-label {
  font-size: 0.8rem;
  color: var(--color-text);
  opacity: 0.7;
}

.printed-control {
  display: flex;
  align-items: center;
  gap: 0;
}

.printed-btn {
  display: none; /* Hidden on desktop by default */
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  width: 32px;
  height: 32px;
  font-size: 1.2rem;
  font-weight: bold;
  cursor: pointer;
  transition: background-color 0.2s;
  padding: 0;
  line-height: 1;
}

.printed-btn:hover:not(:disabled) {
  background-color: var(--color-background-mute);
}

.printed-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.printed-btn.minus-btn {
  border-radius: 4px 0 0 4px;
  border-right: none;
}

.printed-btn.plus-btn {
  border-radius: 0 4px 4px 0;
  border-left: none;
}

.printed-input,
.quantity-input {
  width: 3.5rem;
  text-align: center;
  padding: 0.25rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
}

.printed-control .printed-input {
  border-radius: 4px; /* Default for desktop */
}

.printed-input:disabled,
.quantity-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.required-amount {
  font-size: 0.9rem;
  color: var(--color-text);
  opacity: 0.7;
}

/* Color Tags */
.color-tag {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 500;
  color: white;
  white-space: nowrap;
}

/* Material Tags */
.material-tag {
  padding: 3px 8px;
  border-radius: 3px;
  font-size: 0.7rem;
  font-weight: 500;
  background-color: transparent;
  border: 1.5px solid var(--color-border);
  color: var(--color-text);
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Missing Config Warning Icon */
.missing-config-icon {
  margin-left: 8px;
  font-size: 1rem;
  cursor: help;
  opacity: 0.9;
  animation: pulse-warning 2s ease-in-out infinite;
}

@keyframes pulse-warning {
  0%,
  100% {
    opacity: 0.9;
  }
  50% {
    opacity: 0.6;
  }
}

/* Edit File Button */
.edit-file-btn {
  background: none;
  border: none;
  padding: 4px;
  margin-left: 8px;
  cursor: pointer;
  color: var(--color-text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
  opacity: 0.6;
}

.edit-file-btn:hover {
  opacity: 1;
  background-color: var(--color-background-mute);
  color: var(--color-brand);
  transform: scale(1.1);
}

.edit-file-btn svg {
  width: 14px;
  height: 14px;
}

/* Edit filename in modal */
.edit-filename {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
  font-family: monospace;
  padding: 0.5rem;
  background: var(--color-background-mute);
  border-radius: 4px;
  word-break: break-all;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--color-text);
  opacity: 0.7;
}

/* Modal */
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
  padding: 2rem;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
}

.modal-form h3 {
  color: var(--color-heading);
  margin-bottom: 1rem;
}

.modal-form p {
  color: var(--color-text);
  margin-bottom: 1.5rem;
}

.modal-form .form-group {
  margin-bottom: 1rem;
}

.modal-form .form-group label {
  display: block;
  color: var(--color-text);
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.modal-form .form-group select {
  width: 100%;
  padding: 0.5rem;
  background-color: var(--color-background);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.9rem;
}

.modal-form .form-group select:focus {
  outline: none;
  border-color: var(--color-primary);
}

.filter-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--color-text);
  padding: 0.25rem 0.75rem;
  background-color: var(--color-background-soft);
  border-radius: 4px;
}

.filter-indicator button {
  background: none;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  text-decoration: underline;
  font-size: 0.85rem;
  padding: 0;
}

.filter-indicator button:hover {
  opacity: 0.8;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.form-actions-right {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

/* Utility Classes */
.mb-6 {
  margin-bottom: 1.5rem;
}

.mt-4 {
  margin-top: 1rem;
}

.mb-1 {
  margin-bottom: 0.25rem;
}

.mb-2 {
  margin-bottom: 0.5rem;
}

.space-y-2 > :not([hidden]) ~ :not([hidden]) {
  margin-top: 0.5rem;
}

.flex {
  display: flex;
}

.justify-between {
  justify-content: space-between;
}

.items-center {
  align-items: center;
}

.font-bold {
  font-weight: 700;
}

.text-xl {
  font-size: 1.25rem;
}

.line-through {
  text-decoration: line-through;
}

/* Mobile Responsive Styles */
@media (max-width: 768px) {
  /* Reduce padding to maximize usable space */
  .main-content {
    padding: 0.5rem !important;
  }

  .card {
    padding: 0.5rem;
  }

  .card-body {
    padding: 0.5rem;
  }

  /* Header adjustments for mobile */
  .detail-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }

  .header-info h1 {
    font-size: 1.75rem;
  }

  .featured-badge {
    font-size: 0.65rem;
    padding: 0.2rem 0.5rem;
  }

  .tracker-subtitle {
    font-size: 1rem;
  }

  .header-actions {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0.5rem;
  }

  /* Filter button and Search on first row */
  .header-actions .btn-secondary:first-child {
    grid-column: 1;
    grid-row: 1;
  }

  .header-actions .search-container {
    grid-column: 2;
    grid-row: 1;
  }

  /* Edit and Delete buttons on second row, span full width and split equally */
  .header-actions .btn-primary {
    grid-column: 1 / -1;
    grid-row: 2;
    width: calc(50% - 0.25rem);
  }

  .header-actions .btn-danger {
    grid-column: 1 / -1;
    grid-row: 2;
    width: calc(50% - 0.25rem);
    margin-left: calc(50% + 0.25rem);
  }

  .search-input {
    min-width: 0;
    width: 100%;
  }

  /* Make file rows stack vertically on mobile */
  .file-row {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.75rem;
  }

  .file-name {
    width: 100%;
    flex-wrap: wrap;
  }

  .file-actions {
    width: 100%;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 0.5rem 0.75rem;
  }

  /* Quantity label and input on first row */
  .file-actions > label:nth-child(1) {
    grid-column: 1;
  }

  .file-actions > .quantity-input {
    grid-column: 2 / -1;
  }

  /* Printed label, control, and total on second row */
  .file-actions > label:nth-child(3) {
    grid-column: 1;
  }

  .file-actions > .printed-control {
    grid-column: 2;
    display: flex;
    align-items: center;
    gap: 0;
  }

  .file-actions > .required-amount {
    grid-column: 3;
    margin-left: 0.5rem;
  }

  /* Progress bar spans full width on third row */
  .file-actions > .progress-bar-bg {
    grid-column: 1 / -1;
  }

  /* Show +/- buttons on mobile */
  .printed-btn {
    display: block;
  }

  .printed-control .printed-input {
    border-radius: 0; /* Remove radius when buttons are visible */
    width: 4rem;
    padding: 0.5rem;
    font-size: 1rem;
  }

  /* Larger touch targets for mobile */
  .file-checkbox {
    width: 24px;
    height: 24px;
  }

  .quantity-input {
    width: 4rem;
    padding: 0.5rem;
    font-size: 1rem;
  }

  /* Category header - larger touch target */
  .category-header {
    padding: 0.75rem;
  }

  .category-title {
    font-size: 1rem;
  }

  /* Progress bar adjustments */
  .progress-bar-bg.small {
    width: 100%;
    margin-top: 0.5rem;
  }

  /* Stats container */
  .stats-container {
    gap: 0.5rem;
  }

  .stat-number {
    font-size: 1.25rem;
  }
}

/* Tablet adjustments */
@media (min-width: 769px) and (max-width: 1024px) {
  .header-actions {
    flex-wrap: wrap;
  }

  .search-input {
    min-width: 150px;
  }
}

/* Add Files Section */
.add-files-section {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  margin: 1.5rem 0;
  gap: 0.75rem;
}

/* Filters Active Banner (Header Version) */
.filters-active-banner-header {
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: var(--color-text);
  padding: 10px 16px;
  border-radius: 6px;
  margin: 0.75rem 0 1rem 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.9rem;
}

.clear-filters-link {
  background: none;
  border: none;
  color: var(--color-brand);
  text-decoration: underline;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  padding: 0;
}

.clear-filters-link:hover {
  color: var(--color-brand-dark);
}

/* Configure Files Modal */
.modal-configure-files {
  background-color: var(--color-background-soft);
  border-radius: 8px;
  max-width: 900px;
  width: 90%;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-heading);
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.75rem;
  color: var(--color-text-muted);
  cursor: pointer;
  line-height: 1;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  color: var(--color-text);
}

.modal-body {
  padding: 1.5rem;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--color-border);
}

.mt-4 {
  margin-top: 1rem;
}

/* Alert Styles */
.alert {
  padding: 12px 16px;
  border-radius: 6px;
  font-size: 0.95rem;
  line-height: 1.5;
}

.alert-warning {
  background-color: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: var(--color-text);
}

.alert-warning:hover {
  background-color: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.4);
}

/* Checkbox label styling */
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  font-weight: normal;
}

.checkbox-label input[type='checkbox'] {
  cursor: pointer;
  margin-right: 4px;
}
</style>
