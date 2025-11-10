<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import APIService from '../services/APIService'
import FileConfigurationStep from '../components/FileConfigurationStep.vue'
import ImportURLsModal from '../components/ImportURLsModal.vue'
import UploadFilesWizardModal from '../components/UploadFilesWizardModal.vue'
import DownloadProgressModal from '../components/DownloadProgressModal.vue'

const router = useRouter()
const route = useRoute()

// Creation mode tracking
const creationMode = ref(null) // 'github' or 'manual'

// Step management
const currentStep = ref(1)
const totalSteps = computed(() => {
  if (creationMode.value === 'github') {
    return 4 // GitHub wizard: Choose Method → Project/Name/URL → Select Files → Configure Files
  } else if (creationMode.value === 'manual') {
    return 5 // Manual: Choose Method → Basic Info → Add Files → Configure Files → Review
  }
  return 1 // Just showing choice screen
})

function goToNextStep() {
  if (currentStep.value < totalSteps.value) {
    // Build manual file tree when transitioning to Step 4 (Configure Files)
    if (creationMode.value === 'manual' && currentStep.value === 3) {
      manualFileTree.value = buildManualFileTree()
    }
    currentStep.value++
  }
}

function goToPreviousStep() {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

// Start GitHub wizard flow
function startGitHubWizard() {
  creationMode.value = 'github'
  goToNextStep()
}

// Start manual creation flow
function startManualCreation() {
  creationMode.value = 'manual'
  goToNextStep()
}

// Step 1 & 2 data (GitHub mode)
const selectedProject = ref(null)
const trackerName = ref('')
const githubUrl = ref('')
const storageOption = ref('')

// Manual mode data
const manualFiles = ref([]) // Array of { name, url, source, category, size, quantity, color, material }
const manualFileTree = ref([]) // Hierarchical tree for FileConfigurationStep (built from manualFiles)
const collapsedManualCategories = ref(new Set()) // Track collapsed categories

// Projects data
const projects = ref([])
const loadingProjects = ref(false)
const projectsError = ref(null)

// Crawl state
const loading = ref(false)
const crawlError = ref(null)
const crawlWarnings = ref([])
const repoInfo = ref(null)
const apiFileTree = ref([])

// File tree for Step 3 & 4
const fileTree4 = ref([])

async function startCrawl() {
  if (!githubUrl.value.trim()) {
    crawlError.value = 'Please enter a GitHub URL'
    return
  }

  loading.value = true
  crawlError.value = null
  crawlWarnings.value = []

  try {
    const response = await APIService.crawlGitHub(githubUrl.value, false)

    if (response.data.success) {
      // Store API response
      repoInfo.value = response.data.repo_info
      apiFileTree.value = response.data.file_tree
      crawlWarnings.value = response.data.warnings || []

      // Transform API response to component structure
      fileTree4.value = buildFileTreeFromAPI(response.data.file_tree)

      // Initialize selection state
      initializeSelectionState(fileTree4.value)

      // Go to Step 3 (file selection)
      currentStep.value = 3
    } else {
      crawlError.value = response.data.error || 'Failed to crawl repository'
    }
  } catch (error) {
    console.error('GitHub crawl error:', error)

    // Handle specific error types
    if (error.response?.data?.error_type) {
      const errorType = error.response.data.error_type
      const errorMessage = error.response.data.error

      switch (errorType) {
        case 'invalid_url':
          crawlError.value = errorMessage
          break
        case 'repo_not_found':
          crawlError.value = 'Repository not found. Please check the URL and try again.'
          break
        case 'rate_limit':
          crawlError.value =
            'GitHub rate limit exceeded. Please try again later or add a GitHub token in settings.'
          break
        case 'empty_result':
          crawlError.value = 'No printable files found in this repository path.'
          break
        case 'network_error':
          crawlError.value = 'Network error. Please check your internet connection and try again.'
          break
        default:
          crawlError.value = errorMessage || 'An unexpected error occurred'
      }
    } else {
      crawlError.value = 'Failed to connect to server. Please try again.'
    }
  } finally {
    loading.value = false
  }
}

// Load projects from API
async function loadProjects() {
  loadingProjects.value = true
  projectsError.value = null

  try {
    const response = await APIService.getProjects()
    projects.value = response.data
  } catch (error) {
    console.error('Failed to load projects:', error)
    projectsError.value = 'Failed to load projects. You can still create a standalone tracker.'
  } finally {
    loadingProjects.value = false
  }
}

// Load projects on component mount
onMounted(async () => {
  await loadProjects()

  // Pre-fill project from query param if present (e.g., from ProjectDetailView)
  const prefilledProjectId = route.query.projectId
  if (prefilledProjectId) {
    selectedProject.value = parseInt(prefilledProjectId)
  }
})

function buildFileTreeFromAPI(apiTree) {
  /**
   * Transform API response to component structure.
   * API format: [{ directory_path: "path", files: [{filename, github_url, file_size, ...}] }]
   * Component format: [{ name: "dir", isSelected: true, children: [{ name: "file.stl", ...}] }]
   */
  const tree = []

  apiTree.forEach((dir) => {
    const dirPath = dir.directory_path
    const files = dir.files

    if (!dirPath || dirPath === '') {
      // Root level files - add directly to tree
      files.forEach((file) => {
        tree.push({
          name: file.filename,
          isSelected: !file.is_blocked, // Blocked files default unchecked
          isBlocked: file.is_blocked,
          isLarge: file.is_large,
          size: file.file_size,
          sizeMB: file.file_size_mb,
          githubUrl: file.github_url,
          sha: file.sha || '', // GitHub file hash
        })
      })
    } else {
      // Nested directory - create directory structure
      const pathParts = dirPath.split('/')
      let currentLevel = tree

      // Navigate/create directory structure
      pathParts.forEach((part, index) => {
        let existing = currentLevel.find((node) => node.name === part && node.children)

        if (!existing) {
          existing = {
            name: part,
            isSelected: true,
            isOpen: true,
            children: [],
          }
          currentLevel.push(existing)
        }

        if (index === pathParts.length - 1) {
          // Last part - add files here
          files.forEach((file) => {
            existing.children.push({
              name: file.filename,
              isSelected: !file.is_blocked,
              isBlocked: file.is_blocked,
              isLarge: file.is_large,
              size: file.file_size,
              sizeMB: file.file_size_mb,
              githubUrl: file.github_url,
              sha: file.sha || '', // GitHub file hash
            })
          })
        } else {
          currentLevel = existing.children
        }
      })
    }
  })

  return tree
}

// Final submission
const submitting = ref(false)
const submitError = ref(null)

// Download modal state
const showDownloadModal = ref(false)
const totalFilesToDownload = ref(0)

async function createTracker() {
  if (!trackerName.value.trim()) {
    submitError.value = 'Please enter a tracker name'
    return
  }

  if (!storageOption.value) {
    submitError.value = 'Please select a file storage option'
    return
  }

  submitting.value = true
  submitError.value = null

  try {
    // Collect selected files with their configuration
    const selectedFilesData = []

    function collectFiles(nodes, currentPath = '') {
      nodes.forEach((node) => {
        if (node.children) {
          // This is a directory, recurse with updated path
          const newPath = currentPath ? `${currentPath}/${node.name}` : node.name
          collectFiles(node.children, newPath)
        } else if (node.isSelected && !node.isBlocked) {
          // This is a file, add to collection
          selectedFilesData.push({
            filename: node.name,
            directory_path: currentPath,
            github_url: node.githubUrl || '',
            file_size: node.size || 0,
            sha: node.sha || '',
            color: node.color || 'Primary',
            material: node.material || 'ABS',
            quantity: node.quantity || 1,
            is_selected: true,
          })
        }
      })
    }

    collectFiles(fileTree4.value)

    // Check if we have at least one file (either from GitHub or uploaded files)
    if (selectedFilesData.length === 0 && manualFiles.value.length === 0) {
      submitError.value = 'Please select at least one file to track'
      submitting.value = false
      return
    }

    // Show download modal if storage type is 'download' (local)
    const willDownload = storageOption.value === 'local'
    if (willDownload) {
      totalFilesToDownload.value = selectedFilesData.length
      showDownloadModal.value = true
    }

    // Build tracker data matching TrackerCreateSerializer format
    const trackerData = {
      name: trackerName.value.trim(),
      project: selectedProject.value || null, // null if no project selected
      github_url: githubUrl.value.trim(),
      storage_type: storageOption.value, // 'link' or 'local'
      primary_color: '#1E40AF', // Default blue - TODO: Add color picker
      accent_color: '#DC2626', // Default red - TODO: Add color picker
      files: selectedFilesData.map((file) => ({
        filename: file.filename,
        directory_path: file.directory_path,
        github_url: file.github_url || '', // Don't encode - backend will handle it
        file_size: file.file_size,
        sha: file.sha,
        color: file.color,
        material: file.material,
        quantity: file.quantity,
        is_selected: file.is_selected,
      })),
    }

    // Submit to API
    const response = await APIService.createTracker(trackerData)

    if (response.data && response.data.tracker && response.data.tracker.id) {
      const trackerId = response.data.tracker.id

      // Close download modal
      showDownloadModal.value = false

      // Small delay to ensure modal closes, then redirect
      await new Promise((resolve) => setTimeout(resolve, 100))
      await router.push(`/trackers/${trackerId}`)
    } else {
      submitError.value = 'Failed to create tracker. Please try again.'
      showDownloadModal.value = false
    }
  } catch (error) {
    console.error('Create tracker error:', error)
    submitError.value =
      error.response?.data?.error ||
      error.response?.data?.detail ||
      'Failed to create tracker. Please try again.'
    showDownloadModal.value = false
  } finally {
    submitting.value = false
  }
}

// Step 3 functionality - File selection
const collapsedDirectories = ref(new Set())

function initializeSelectionState(tree) {
  tree.forEach((node) => {
    node.isSelected = true // Default all items to checked
    node.isOpen = true // Expand all directories

    if (node.children) {
      initializeSelectionState(node.children)
    }
  })
}

// Toggle file selection
function toggleFileSelection(file) {
  file.isSelected = !file.isSelected
}

// Toggle directory collapse state
function toggleDirectoryCollapse(dirPath) {
  const newSet = new Set(collapsedDirectories.value)
  if (newSet.has(dirPath)) {
    newSet.delete(dirPath)
  } else {
    newSet.add(dirPath)
  }
  collapsedDirectories.value = newSet
}

// Check if directory is collapsed
function isDirectoryCollapsed(dirPath) {
  return collapsedDirectories.value.has(dirPath)
}

// Select/deselect all files in a directory
function toggleDirectorySelection(files) {
  const allSelected = files.every((f) => f.isSelected)
  files.forEach((file) => {
    file.isSelected = !allSelected
  })
}

// Check if all files in directory are selected
function areAllFilesSelected(files) {
  return files.every((f) => f.isSelected)
}

// Toggle select all files
function toggleSelectAllFiles() {
  const allSelected = areAllFilesInTreeSelected()

  function setSelection(nodes, selected) {
    nodes.forEach((node) => {
      if (node.children) {
        setSelection(node.children, selected)
      } else {
        node.isSelected = selected
      }
    })
  }

  setSelection(fileTree4.value, !allSelected)
}

// Check if all files in tree are selected
function areAllFilesInTreeSelected() {
  function checkAll(nodes) {
    return nodes.every((node) => {
      if (node.children) {
        return checkAll(node.children)
      } else {
        return node.isSelected
      }
    })
  }
  return checkAll(fileTree4.value)
}

// Toggle expand/collapse all directories
function toggleExpandCollapseAll() {
  if (collapsedDirectories.value.size === 0) {
    // Currently all expanded, collapse all
    const newSet = new Set()
    Object.keys(groupedFiles.value).forEach((dirPath) => {
      newSet.add(dirPath)
    })
    collapsedDirectories.value = newSet
  } else {
    // Currently some collapsed, expand all
    collapsedDirectories.value = new Set()
  }
}

// Count selected files
function countSelectedFiles(tree) {
  let count = 0

  function traverse(nodes) {
    nodes.forEach((node) => {
      if (node.children) {
        traverse(node.children)
      } else if (node.isSelected) {
        count++
      }
    })
  }

  traverse(tree)
  return count
}

// Group files by directory for Step 3
const groupedFiles = computed(() => {
  const groups = {}

  function traverse(nodes, path = []) {
    nodes.forEach((node) => {
      if (node.children) {
        traverse(node.children, [...path, node.name])
      } else {
        const dirPath = path.join(' / ') || 'Root'
        if (!groups[dirPath]) {
          groups[dirPath] = []
        }
        groups[dirPath].push(node)
      }
    })
  }

  traverse(fileTree4.value)
  return groups
})

// ======================================
// Manual Creation Functions
// ======================================

// Get unique categories from manual files
function getUniqueCategories() {
  const categories = new Set()
  manualFiles.value.forEach((file) => {
    categories.add(file.category || '')
  })
  return Array.from(categories).sort()
}

// Get files by category
function getFilesByCategory(category) {
  return manualFiles.value.filter((file) => (file.category || '') === category)
}

// Delete a file
function deleteFile(fileToDelete) {
  if (confirm(`Delete "${fileToDelete.name}"?`)) {
    const index = manualFiles.value.findIndex((f) => f === fileToDelete)
    if (index > -1) {
      manualFiles.value.splice(index, 1)
    }
  }
}

// Delete entire category
function deleteCategory(category) {
  if (confirm(`Delete all files in "${category || 'Uncategorized'}" category?`)) {
    manualFiles.value = manualFiles.value.filter((file) => (file.category || '') !== category)
  }
}

// Manual category collapse functions
function toggleManualCategoryCollapse(category) {
  if (collapsedManualCategories.value.has(category)) {
    collapsedManualCategories.value.delete(category)
  } else {
    collapsedManualCategories.value.add(category)
  }
}

function isManualCategoryCollapsed(category) {
  return collapsedManualCategories.value.has(category)
}

// Build fileTree from manual files (similar to GitHub's buildFileTreeFromAPI)
// This converts the flat manualFiles array into hierarchical structure for FileConfigurationStep
function buildManualFileTree() {
  const tree = []
  const categories = getUniqueCategories()

  categories.forEach((category) => {
    const categoryFiles = getFilesByCategory(category)
    const categoryNode = {
      name: category || 'Uncategorized',
      type: 'directory',
      isOpen: true,
      isSelected: false,
      children: categoryFiles.map((file) => {
        // Add missing properties directly to the file object
        file.type = file.type || 'file'
        file.sizeMB = file.size ? (file.size / (1024 * 1024)).toFixed(2) : '0.00'
        file.isSelected = file.isSelected !== undefined ? file.isSelected : true

        // Return the SAME file object (not a copy) so modifications persist
        return file
      }),
    }
    tree.push(categoryNode)
  })

  return tree
}

// Check if all manual files are configured
const isManualConfigurationComplete = computed(() => {
  if (manualFiles.value.length === 0) return false

  // Check if all files in the original array have configuration
  return manualFiles.value.every((file) => file.quantity && file.color && file.material)
})

// Get configured files by category for review
// Since manualFileTree uses actual file object references, they already have configuration
function getConfiguredFilesByCategory(category) {
  const categoryNode = manualFileTree.value.find(
    (node) => node.name === (category || 'Uncategorized'),
  )
  return categoryNode ? categoryNode.children : []
}

// Modal state
const showImportURLsModal = ref(false)
const showUploadFilesModal = ref(false)

// Open modals
function openImportURLsModal() {
  showImportURLsModal.value = true
}

function openUploadFilesModal() {
  showUploadFilesModal.value = true
}

// Handle imported files from modal
function handleFilesImported(files) {
  manualFiles.value.push(...files)
  // Rebuild the file tree for FileConfigurationStep (consistent with GitHub wizard approach)
  manualFileTree.value = buildManualFileTree()
}

// Get color badge style (matches TrackerDetailView)
const getColorBadgeStyle = (color) => {
  // Using default colors since we don't have tracker colors yet in creation
  const primary = '#4a90e2'
  const accent = '#f5a623'

  switch (color?.toLowerCase()) {
    case 'primary':
      return { backgroundColor: primary }
    case 'accent':
      return { backgroundColor: accent }
    case 'multicolor':
      return { backgroundImage: `linear-gradient(to right, ${primary}, ${accent})` }
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

// Create manual tracker
async function createManualTracker() {
  submitting.value = true
  submitError.value = null

  try {
    // Collect configured files from the fileTree
    // Since manualFileTree contains the actual file objects (not copies),
    // they already have all properties including configuration
    // IMPORTANT: Only include URL-based files here. Uploaded files will be added via the upload endpoint.
    const configuredFiles = []
    manualFileTree.value.forEach((category) => {
      if (category.children) {
        category.children.forEach((file) => {
          if (file.isSelected) {
            // Skip uploaded files - they'll be uploaded separately
            if (file.source === 'Upload' || file.file instanceof File) {
              return
            }

            // Ensure url is a string (not null/undefined) to avoid NULL constraint errors
            const fileUrl = file.githubUrl || file.url
            configuredFiles.push({
              name: file.name,
              url: fileUrl === null || fileUrl === undefined ? '' : fileUrl,
              source: file.source,
              category: file.category || '',
              size: file.size,
              quantity: file.quantity,
              color: file.color,
              material: file.material,
            })
          }
        })
      }
    })

    const payload = {
      name: trackerName.value,
      project: selectedProject.value,
      storage_type: storageOption.value,
      files: configuredFiles,
      creation_mode: 'manual',
    }

    const response = await APIService.createManualTracker(payload)

    if (response.data.success) {
      const trackerId = response.data.tracker.id

      // Upload any local files (files with File objects)
      const filesToUpload = manualFiles.value.filter((f) => f.file instanceof File)

      if (filesToUpload.length > 0) {
        try {
          // Group files by category and upload
          const uploadsByCategory = {}
          filesToUpload.forEach((fileData) => {
            const category = fileData.category || 'Uploads'
            if (!uploadsByCategory[category]) {
              uploadsByCategory[category] = []
            }
            uploadsByCategory[category].push(fileData)
          })

          // Upload each file individually with its configuration
          for (const fileData of filesToUpload) {
            const formData = new FormData()

            formData.append('files', fileData.file)
            formData.append('category', fileData.category || 'Uploads')
            formData.append('color', fileData.color || 'Primary')
            formData.append('material', fileData.material || 'PLA')
            formData.append('quantity', fileData.quantity || 1)

            // Upload file with configuration
            await APIService.uploadTrackerFiles(trackerId, formData)
          }
        } catch (uploadError) {
          console.error('File upload error:', uploadError)
          // Continue to tracker detail view even if uploads fail
          // User can manually re-upload or see the error
        }
      }

      // Navigate to tracker detail view
      router.push(`/trackers/${trackerId}`)
    } else {
      submitError.value = response.data.error || 'Failed to create tracker'
    }
  } catch (error) {
    console.error('Failed to create manual tracker:', error)
    submitError.value =
      error.response?.data?.error || 'An error occurred while creating the tracker'
  } finally {
    submitting.value = false
  }
}

initializeSelectionState(fileTree4.value)
</script>

<template>
  <div class="wizard-container">
    <div class="card">
      <div class="card-body">
        <div class="wizard-header">
          <h1 class="wizard-title">Create New Tracker</h1>
          <p class="wizard-subtitle">Step {{ currentStep }} of {{ totalSteps }}</p>
        </div>

        <div class="wizard-body">
          <div v-if="loading" class="loading-screen">
            <h2>Crawling GitHub repository...</h2>
            <p>Analyzing files and directories...</p>
            <div class="spinner"></div>
          </div>

          <div v-else-if="currentStep === 1">
            <h2>Step 1: Choose Creation Method</h2>
            <div class="step-content">
              <button class="btn btn-primary" @click="startGitHubWizard">Use Wizard</button>
              <button class="btn btn-secondary" @click="startManualCreation">
                Manual Creation
              </button>
            </div>
          </div>

          <!-- GitHub Wizard Flow -->
          <div v-else-if="creationMode === 'github' && currentStep === 2">
            <h2>Step 2: Name Tracker and Associate Project</h2>
            <div class="step-content">
              <!-- Error message -->
              <div v-if="crawlError" class="alert alert-danger">
                <strong>Error:</strong> {{ crawlError }}
              </div>

              <!-- Warning messages -->
              <div v-if="crawlWarnings.length > 0" class="alert alert-warning">
                <strong>Warnings:</strong>
                <ul class="mb-0">
                  <li v-for="(warning, index) in crawlWarnings" :key="index">{{ warning }}</li>
                </ul>
              </div>

              <div class="form-group">
                <label for="trackerName">Tracker Name *</label>
                <input
                  type="text"
                  id="trackerName"
                  class="form-control"
                  v-model="trackerName"
                  placeholder="e.g., Voron V0.2 Parts"
                  required
                />
              </div>

              <div class="form-group">
                <label for="projectSelect">Associate with Project (Optional)</label>

                <div v-if="loadingProjects" class="loading-message">
                  <span class="spinner">⏳</span> Loading projects...
                </div>

                <div v-else-if="projectsError" class="error-message">
                  <span class="error-icon">⚠️</span> {{ projectsError }}
                </div>

                <select v-else id="projectSelect" class="form-control" v-model="selectedProject">
                  <option :value="null">None (Standalone Tracker)</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.project_name }}
                  </option>
                </select>
              </div>

              <div class="form-group">
                <label for="githubUrl">GitHub Repository URL</label>
                <input
                  type="text"
                  id="githubUrl"
                  class="form-control"
                  v-model="githubUrl"
                  placeholder="https://github.com/user/repo/tree/main/STLs"
                  required
                />
                <small class="form-text text-muted">
                  Enter a link to a GitHub directory containing 3D printable files.
                </small>
              </div>
              <div class="step-actions">
                <button class="btn btn-secondary" @click="goToPreviousStep">Back</button>
                <button class="btn btn-primary" @click="startCrawl" :disabled="loading">
                  {{ loading ? 'Crawling...' : 'Start Crawl' }}
                </button>
              </div>
            </div>
          </div>

          <div v-else-if="creationMode === 'github' && currentStep === 3">
            <h2>Step 3: Select Files to Track</h2>
            <p class="step-description">
              Choose which files you want to include in your tracker. You can select individual
              files or entire directories.
            </p>

            <div class="selection-summary">
              <span class="summary-text">{{ countSelectedFiles(fileTree4) }} files selected</span>
              <div class="summary-actions">
                <button
                  class="btn btn-sm"
                  :class="areAllFilesInTreeSelected() ? 'btn-secondary' : 'btn-primary'"
                  @click="toggleSelectAllFiles"
                >
                  {{ areAllFilesInTreeSelected() ? 'Unselect All' : 'Select All' }}
                </button>
                <button
                  class="btn btn-sm"
                  :class="collapsedDirectories.size === 0 ? 'btn-secondary' : 'btn-primary'"
                  @click="toggleExpandCollapseAll"
                >
                  {{ collapsedDirectories.size === 0 ? 'Collapse All' : 'Expand All' }}
                </button>
              </div>
            </div>

            <div class="file-selection-list">
              <div
                v-for="(files, directory) in groupedFiles"
                :key="directory"
                class="directory-card"
              >
                <div class="directory-card-header" @click="toggleDirectoryCollapse(directory)">
                  <div class="directory-info">
                    <input
                      type="checkbox"
                      :checked="areAllFilesSelected(files)"
                      @click.stop
                      @change="toggleDirectorySelection(files)"
                      class="directory-checkbox"
                    />
                    <span
                      class="directory-path"
                      :class="{ strikethrough: !areAllFilesSelected(files) }"
                      >{{ directory }}</span
                    >
                    <span class="file-count-badge">{{ files.length }}</span>
                  </div>
                  <span
                    class="collapse-arrow"
                    :class="{ collapsed: isDirectoryCollapsed(directory) }"
                  >
                    ▼
                  </span>
                </div>

                <div v-if="!isDirectoryCollapsed(directory)" class="directory-files">
                  <div
                    v-for="file in files"
                    :key="file.name"
                    class="file-selection-item"
                    :class="{ blocked: file.isBlocked }"
                    @click="!file.isBlocked && toggleFileSelection(file)"
                  >
                    <input
                      type="checkbox"
                      :checked="file.isSelected"
                      :disabled="file.isBlocked"
                      @click.stop
                      @change="toggleFileSelection(file)"
                      class="file-checkbox"
                    />

                    <!-- Blocked file (>100 MB) -->
                    <span
                      v-if="file.isBlocked"
                      class="file-name-text blocked-file"
                      :title="`File too large (${file.sizeMB} MB). Maximum: 100 MB`"
                    >
                      <span class="file-size-badge blocked">🚫 {{ file.sizeMB }} MB</span>
                      {{ file.name }}
                    </span>

                    <!-- Large file (10-100 MB) -->
                    <span
                      v-else-if="file.isLarge"
                      class="file-name-text"
                      :class="{ strikethrough: !file.isSelected }"
                    >
                      <span class="file-size-badge large">⚠️ {{ file.sizeMB }} MB</span>
                      {{ file.name }}
                    </span>

                    <!-- Normal file -->
                    <span
                      v-else
                      class="file-name-text"
                      :class="{ strikethrough: !file.isSelected }"
                    >
                      {{ file.name }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div class="wizard-actions">
              <button class="btn btn-secondary" @click="goToPreviousStep">Back</button>
              <button
                class="btn btn-primary"
                @click="goToNextStep"
                :disabled="countSelectedFiles(fileTree4) === 0"
              >
                Next: Configure Files
              </button>
            </div>
          </div>

          <div v-else-if="creationMode === 'github' && currentStep === 4">
            <!-- Submit error message -->
            <div v-if="submitError" class="alert alert-danger">
              <strong>Error:</strong> {{ submitError }}
            </div>

            <FileConfigurationStep
              :fileTree="fileTree4"
              @update:storageOption="storageOption = $event"
            />

            <div class="wizard-actions">
              <button class="btn btn-secondary" @click="goToPreviousStep" :disabled="submitting">
                Back
              </button>
              <button
                class="btn btn-primary"
                @click="createTracker"
                :disabled="!storageOption || submitting"
              >
                {{ submitting ? 'Creating Tracker...' : 'Create Tracker' }}
              </button>
            </div>
            <p v-if="!storageOption && !submitting" class="validation-message">
              Please select a file storage option before creating the tracker.
            </p>
          </div>

          <!-- Manual Creation Flow -->
          <div v-else-if="creationMode === 'manual' && currentStep === 2">
            <h2>Step 2: Basic Information</h2>
            <div class="step-content">
              <div class="form-group">
                <label for="manualTrackerName">Tracker Name *</label>
                <input
                  type="text"
                  id="manualTrackerName"
                  class="form-control"
                  v-model="trackerName"
                  placeholder="e.g., Custom Robot Build"
                  required
                />
              </div>

              <div class="form-group">
                <label for="manualProjectSelect">Associate with Project (Optional)</label>
                <div v-if="loadingProjects" class="loading-message">
                  <span class="spinner">⏳</span> Loading projects...
                </div>
                <div v-else-if="projectsError" class="error-message">
                  <span class="error-icon">⚠️</span> {{ projectsError }}
                </div>
                <select
                  v-else
                  id="manualProjectSelect"
                  class="form-control"
                  v-model="selectedProject"
                >
                  <option :value="null">None (Standalone Tracker)</option>
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.project_name }}
                  </option>
                </select>
              </div>

              <div class="wizard-actions">
                <button class="btn btn-secondary" @click="goToPreviousStep">Back</button>
                <button
                  class="btn btn-primary"
                  @click="goToNextStep"
                  :disabled="!trackerName.trim()"
                >
                  Next: Add Files
                </button>
              </div>
              <p v-if="!trackerName.trim()" class="validation-message">
                Please enter a tracker name before continuing.
              </p>
            </div>
          </div>

          <div v-else-if="creationMode === 'manual' && currentStep === 3">
            <h2>Step 3: Add Files</h2>
            <p class="step-description">
              Add files from URLs or upload local files. You can organize them into categories.
              You'll configure quantities, colors, and materials on the next page.
            </p>

            <div class="step-content">
              <!-- Action buttons -->
              <div class="file-actions">
                <button class="btn btn-primary" @click="openImportURLsModal">Import URLs</button>
                <button class="btn btn-primary" @click="openUploadFilesModal">Upload Files</button>
              </div>

              <!-- File list by category (matching GitHub wizard style) -->
              <div v-if="manualFiles.length > 0" class="file-selection-list">
                <div
                  v-for="category in getUniqueCategories()"
                  :key="category"
                  class="directory-card"
                >
                  <div
                    class="directory-card-header"
                    @click="toggleManualCategoryCollapse(category)"
                  >
                    <div class="directory-info">
                      <span class="directory-path">{{ category || 'Uncategorized' }}</span>
                      <span class="file-count-badge">{{
                        getFilesByCategory(category).length
                      }}</span>
                    </div>
                    <div class="header-actions">
                      <span
                        class="collapse-arrow"
                        :class="{ collapsed: isManualCategoryCollapsed(category) }"
                      >
                        ▼
                      </span>
                      <button
                        class="btn-icon delete-category"
                        @click.stop="deleteCategory(category)"
                        :title="`Delete ${category || 'Uncategorized'} category`"
                      >
                        ×
                      </button>
                    </div>
                  </div>

                  <div v-if="!isManualCategoryCollapsed(category)" class="directory-files">
                    <div
                      v-for="(file, index) in getFilesByCategory(category)"
                      :key="index"
                      class="file-selection-item"
                    >
                      <a
                        v-if="file.url"
                        :href="file.url"
                        target="_blank"
                        rel="noopener noreferrer"
                        class="file-name-link"
                        :title="`Open ${file.url} in new tab`"
                      >
                        {{ file.name }}
                      </a>
                      <span v-else class="file-name-text">
                        {{ file.name }}
                      </span>
                      <span class="source-badge">{{ file.source }}</span>
                      <button
                        class="btn-icon delete-file"
                        @click="deleteFile(file)"
                        title="Remove file"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <div v-else class="empty-state">
                <p>No files added yet. Click "Import URLs" or "Upload Files" to get started.</p>
              </div>

              <div class="wizard-actions">
                <button class="btn btn-secondary" @click="goToPreviousStep">Back</button>
                <button
                  class="btn btn-primary"
                  @click="goToNextStep"
                  :disabled="manualFiles.length === 0"
                >
                  Next: Configure Files
                </button>
              </div>
              <p v-if="manualFiles.length === 0" class="validation-message">
                Please add at least one file before continuing.
              </p>
            </div>
          </div>

          <div v-else-if="creationMode === 'manual' && currentStep === 4">
            <h2>Step 4: Configure Files</h2>
            <p class="step-description">
              Set material, color, and quantity for each file. Use smart defaults or bulk operations
              to configure multiple files at once.
            </p>

            <FileConfigurationStep
              :fileTree="manualFileTree"
              @update:storageOption="storageOption = $event"
            />

            <div class="wizard-actions">
              <button class="btn btn-secondary" @click="goToPreviousStep">Back</button>
              <button
                class="btn btn-primary"
                @click="goToNextStep"
                :disabled="!isManualConfigurationComplete || !storageOption"
              >
                Next: Review & Create
              </button>
            </div>
            <p v-if="!storageOption" class="validation-message">
              Please select a file storage option before continuing.
            </p>
            <p v-else-if="!isManualConfigurationComplete" class="validation-message">
              Please configure all files (quantity, color, material) before continuing.
            </p>
          </div>

          <div v-else-if="creationMode === 'manual' && currentStep === 5">
            <h2>Step 5: Review & Create</h2>

            <!-- Summary Card -->
            <div class="card mb-4">
              <div class="card-body">
                <div class="summary-inline">
                  <span class="summary-item"><strong>Name:</strong> {{ trackerName }}</span>
                  <span class="summary-item"
                    ><strong>Project:</strong>
                    {{
                      selectedProject
                        ? projects.find((p) => p.id === selectedProject)?.project_name
                        : 'None (Standalone)'
                    }}</span
                  >
                  <span class="summary-item"
                    ><strong>Storage Type:</strong>
                    {{ storageOption === 'link' ? 'Links Only' : 'Download to Server' }}</span
                  >
                </div>
                <div class="summary-inline">
                  <span class="summary-item"
                    ><strong>Total Files:</strong> {{ manualFiles.length }}</span
                  >
                  <span class="summary-item"
                    ><strong>Categories:</strong> {{ getUniqueCategories().length }}</span
                  >
                </div>
              </div>
            </div>

            <!-- Files Card -->
            <div class="card mb-4">
              <div class="card-body">
                <div
                  v-for="(category, index) in getUniqueCategories()"
                  :key="category"
                  class="category-group"
                  :class="{ 'no-border': index === getUniqueCategories().length - 1 }"
                >
                  <!-- Category Header -->
                  <div class="category-header-review">
                    <h4 class="category-title">{{ category || 'Uncategorized' }}</h4>
                  </div>

                  <!-- Category Files -->
                  <div class="category-content">
                    <div
                      v-for="file in getConfiguredFilesByCategory(category)"
                      :key="file.name"
                      class="file-row-review"
                    >
                      <div class="file-name-section">
                        <span class="file-name-text">{{ file.name }}</span>
                        <span class="color-tag" :style="getColorBadgeStyle(file.color)">{{
                          file.color
                        }}</span>
                        <span class="material-tag">{{ file.material }}</span>
                        <span class="quantity-indicator">Qty: {{ file.quantity }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Actions -->
            <div class="wizard-actions">
              <button class="btn btn-secondary" @click="goToPreviousStep" :disabled="submitting">
                Back
              </button>
              <button class="btn btn-primary" @click="createManualTracker" :disabled="submitting">
                {{ submitting ? 'Creating Tracker...' : 'Create Tracker' }}
              </button>
            </div>

            <!-- Error Message -->
            <div v-if="submitError" class="alert alert-danger mt-4">
              <strong>Error:</strong> {{ submitError }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Import URLs Modal -->
    <ImportURLsModal
      :show="showImportURLsModal"
      :existingCategories="getUniqueCategories()"
      :existingFiles="manualFiles"
      @close="showImportURLsModal = false"
      @filesImported="handleFilesImported"
    />

    <!-- Upload Files Modal -->
    <UploadFilesWizardModal
      :show="showUploadFilesModal"
      :existingCategories="getUniqueCategories()"
      :existingFiles="manualFiles"
      @close="showUploadFilesModal = false"
      @filesImported="handleFilesImported"
    />

    <!-- Download Progress Modal -->
    <DownloadProgressModal :isVisible="showDownloadModal" :totalFiles="totalFilesToDownload" />
  </div>
</template>

<style scoped>
.wizard-container {
  padding: 2rem;
  max-width: 1200px; /* Adjusted width to match inventory detail view */
  margin: 0 auto;
}
.card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  margin-bottom: 1.5rem;
}
.card-body {
  padding: 1rem 1.5rem;
}
.wizard-header {
  text-align: center;
  margin-bottom: 2rem;
}
.wizard-title {
  font-size: 2rem;
}
.wizard-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.wizard-body h2 {
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}

.step-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.step-actions {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.step-description {
  text-align: center;
  color: var(--color-text-soft);
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
}

.selection-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  margin-bottom: 1rem;
}

.summary-text {
  font-weight: 600;
  color: var(--color-heading);
  font-size: 0.95rem;
}

.summary-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-selection-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.directory-card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}

.directory-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.25rem;
  background-color: var(--color-background-mute);
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  user-select: none;
}

.directory-card-header:hover {
  background-color: var(--color-background);
}

.directory-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.directory-checkbox {
  cursor: pointer;
  margin: 0;
}

.directory-path {
  font-weight: 600;
  color: var(--color-heading);
  font-size: 0.95rem;
}

.file-count-badge {
  font-size: 0.85rem;
  color: var(--color-text-soft);
  background-color: var(--color-background);
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  border: 1px solid var(--color-border);
}

.collapse-arrow {
  color: var(--color-text-soft);
  font-size: 0.8rem;
  transition: transform 0.2s ease;
}

.collapse-arrow.collapsed {
  transform: rotate(-90deg);
}

.directory-files {
  padding: 0.5rem 0;
}

.file-selection-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 1.25rem;
  cursor: pointer;
  transition: background-color 0.15s;
}

.file-selection-item:hover {
  background-color: var(--color-background-mute);
}

.file-selection-item.blocked {
  cursor: not-allowed;
  opacity: 0.6;
}

.file-selection-item.blocked:hover {
  background-color: transparent;
}

.file-checkbox {
  cursor: pointer;
  margin: 0;
  flex-shrink: 0;
}

.file-checkbox:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.file-name-text {
  font-size: 0.9rem;
  color: var(--color-text);
  word-break: break-word;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.file-name-text.blocked-file {
  text-decoration: line-through;
  color: var(--color-text-soft);
}

.file-size-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

.file-size-badge.large {
  background-color: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}

.file-size-badge.blocked {
  background-color: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}

.strikethrough {
  text-decoration: line-through;
  opacity: 0.5;
}

.alert {
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  border-left: 4px solid;
}

.alert ul {
  margin: 0.5rem 0 0 1.5rem;
  padding: 0;
}

.alert-danger {
  background-color: #fee2e2;
  color: #991b1b;
  border-left-color: #dc2626;
}

.alert-warning {
  background-color: #fef3c7;
  color: #92400e;
  border-left-color: #f59e0b;
}

.form-text {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.875rem;
}

.text-muted {
  color: var(--color-text-soft);
}

.btn-xs {
  padding: 0.25rem 0.5rem;
  font-size: 0.8rem;
}

.wizard-actions {
  display: flex;
  gap: 1rem;
  justify-content: space-between;
  margin-top: 1.5rem;
}

.validation-message {
  color: var(--color-red);
  font-size: 0.85rem;
  text-align: center;
  margin-top: 0.5rem;
  font-weight: 500;
}

.loading-screen {
  text-align: center;
  padding: 2rem;
}
.spinner {
  width: 50px;
  height: 50px;
  border: 5px solid #ccc;
  border-top: 5px solid #007bff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.loading-message {
  padding: 0.75rem;
  background-color: #f0f9ff;
  color: #1e40af;
  border-radius: 6px;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.loading-message .spinner {
  display: inline-block;
  width: auto;
  height: auto;
  border: none;
  animation: none;
}

.error-message {
  padding: 0.75rem;
  background-color: #fef2f2;
  color: #991b1b;
  border-radius: 6px;
  border-left: 4px solid #dc2626;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.error-icon {
  font-size: 1.2rem;
}

/* Manual Creation Styles */
.file-actions {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  font-size: 1.5rem;
  color: #dc2626;
  transition: color 0.2s;
}

.btn-icon:hover {
  color: #b91c1c;
}

.delete-file {
  margin-left: auto;
}

.file-name-link {
  color: var(--color-text);
  text-decoration: none;
  cursor: pointer;
}

.file-name-link:hover {
  text-decoration: underline;
}

.file-name-link:visited {
  color: var(--color-text);
}

.source-badge {
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 500;
  background-color: #6b7280;
  color: white;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: #6b7280;
  background-color: #f9fafb;
  border-radius: 8px;
  margin: 2rem 0;
}

.empty-state p {
  margin: 0;
  font-size: 0.95rem;
}

.review-section {
  margin-bottom: 2rem;
}

.review-section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 1rem;
}

.review-list {
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1.5rem;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.75rem 1.5rem;
}

.review-list dt {
  font-weight: 600;
  color: #374151;
}

.review-list dd {
  margin: 0;
  color: #111827;
}

.category-review {
  margin-bottom: 1.5rem;
}

.category-review h4 {
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.files-review-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.file-review-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.file-review-item .file-name {
  font-size: 0.9rem;
  color: #111827;
  font-weight: 500;
}

.file-config-summary {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.config-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  background-color: #e5e7eb;
  color: #374151;
}

.config-badge.color-badge {
  background-color: #dbeafe;
  color: #1e40af;
}

.config-badge.material-badge {
  background-color: #d1fae5;
  color: #065f46;
}

.source-badge-sm {
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 0.65rem;
  font-weight: 500;
  background-color: #6b7280;
  color: white;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Step 5 Review Styles - Matches TrackerDetailView exactly */
.mb-4 {
  margin-bottom: 1.5rem;
}

.mt-4 {
  margin-top: 1.5rem;
}

/* Summary inline layout */
.summary-inline {
  display: flex;
  gap: 2rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}

.summary-item {
  font-size: 0.95rem;
  color: var(--color-text);
}

.summary-item strong {
  font-weight: 600;
  margin-right: 0.25rem;
}

/* Category styles matching TrackerDetailView */
.category-group {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.75rem;
  margin-bottom: 0.75rem;
}

.category-group.no-border {
  border-bottom: none;
  margin-bottom: 0;
}

.category-header-review {
  padding: 0.5rem 0;
}

.category-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0;
}

.category-content {
  padding-top: 0.5rem;
}

/* File row - single line layout like TrackerDetailView */
.file-row-review {
  display: flex;
  align-items: center;
  padding: 0.5rem;
  border-radius: 6px;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.file-row-review:last-child {
  margin-bottom: 0;
}

.file-name-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.file-name-text {
  color: var(--color-text);
  font-size: 0.9rem;
}

/* Color tag - rounded with colored background */
.color-tag {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.7rem;
  font-weight: 500;
  color: white;
  white-space: nowrap;
}

/* Material tag - outlined square */
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

/* Quantity indicator */
.quantity-indicator {
  font-size: 0.8rem;
  color: var(--color-text);
  opacity: 0.7;
}
</style>
