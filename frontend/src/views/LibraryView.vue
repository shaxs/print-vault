<script setup>
/*
 * STL/3MF Library — two-pane file browser over the indexed network share.
 *
 * Left pane: folder tree rendered from ONE skeleton request
 * (library/folders/tree/); expand/collapse is client-side only.
 * Right pane: selected folder's contents (paginated, sortable, List/Grid
 * toggle persisted in localStorage), or root-wide search results while the
 * search box is active. Soft-deleted records can be shown, permanently
 * deleted per item, or bulk-purged from Settings.
 * Selected folder lives in the route query (?folder=) so refresh/back work.
 */
import { computed, onBeforeUnmount, onMounted, provide, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import APIService from '@/services/APIService'
import MainHeader from '@/components/MainHeader.vue'
import LibraryFolderTreeNode from '@/components/LibraryFolderTreeNode.vue'
import LibraryFileDetailModal from '@/components/LibraryFileDetailModal.vue'
import LibrarySettingsModal from '@/components/LibrarySettingsModal.vue'

const VIEW_MODE_KEY = 'library-view-mode'
const HIDE_EMPTY_KEY = 'library-hide-empty-folders'
const PAGE_SIZE = 100

const route = useRoute()
const router = useRouter()

const roots = ref([])
// Merged flat skeleton across ALL enabled roots: { id, name, parent_id, status, root }.
// Folder ids are globally unique, so one flat map works for every root's tree.
const folders = ref([])
const folderMap = computed(() => new Map(folders.value.map((f) => [f.id, f])))
const expandedIds = ref(new Set())
const selectedFolderId = ref(null)

const enabledRoots = computed(() => roots.value.filter((r) => r.enabled))
const selectedFolder = computed(() =>
  selectedFolderId.value != null ? folderMap.value.get(selectedFolderId.value) || null : null,
)
// The "active root" is whichever root owns the selected folder (falls back to
// the first enabled root). Drives the file modal's render color and the
// "Settings vs Configure" state. Null only when no enabled root exists.
const activeRoot = computed(() => {
  const folder = selectedFolder.value
  if (folder && folder.root != null) {
    const owner = roots.value.find((r) => r.id === folder.root)
    if (owner) return owner
  }
  return enabledRoots.value[0] || null
})
const hasAnyRoot = computed(() => roots.value.length > 0)

const contents = ref(null) // { folder, subfolders, files: {count,next,previous,results} }
const page = ref(1)
const sortField = ref('filename')
const sortDirection = ref('asc')
const viewMode = ref(localStorage.getItem(VIEW_MODE_KEY) || 'list')
const extensionFilter = ref('') // '' | 'stl' | '3mf'
const showDeleted = ref(false)
const hideEmptyFolders = ref(localStorage.getItem(HIDE_EMPTY_KEY) === 'true')

const loadingTree = ref(true)
const loadingContents = ref(false)
const loadError = ref(null)

const detailFileId = ref(null)
const showFileModal = ref(false)
const showSettingsModal = ref(false)
const thumbVersion = ref(0) // bumped after regeneration to bust stale img cache

// Search state — non-null searchResults switches the right pane to results
const searchQuery = ref('')
const searchResults = ref(null)
const searchPage = ref(1)
const searchLoading = ref(false)
let searchDebounce = null

// "New models since the last scan" mode — like search, it takes over the right
// pane with a flat, paginated file list (files first indexed by each root's
// most recent scan). Mutually exclusive with search.
const newFilesActive = ref(false)
const newFilesResults = ref(null)
const newFilesPage = ref(1)
const newFilesLoading = ref(false)

// Async job tracking — a single poll loop drives the progress banner for every
// in-flight job (full-root scan, scoped-folder rescan, and thumbnail
// regeneration alike). Seeded on mount from ?active=true so a page refresh (or
// navigating away and back) re-attaches to a running job instead of losing it.
const activeJobs = ref([]) // scan objects (status pending/running) being polled
const jobNotices = ref([]) // transient completion lines: { id, tone, text }
let jobPollTimer = null

const anyJobActive = computed(() => activeJobs.value.length > 0)
const scanJobActive = computed(() => activeJobs.value.some((j) => j.kind === 'scan'))

// Preview-coverage summary (files with no thumbnail and why) for the header.
const previewSummary = ref(null)
const previewIssueText = computed(() => {
  const s = previewSummary.value
  if (!s || !s.without_preview) return ''
  const parts = []
  if (s.too_large) parts.push(`${s.too_large} too large`)
  if (s.unrenderable) parts.push(`${s.unrenderable} unreadable`)
  const n = s.without_preview
  const suffix = parts.length ? ` (${parts.join(', ')})` : ''
  return `${n} file${n === 1 ? '' : 's'} without a preview${suffix}`
})

async function loadPreviewSummary() {
  try {
    const response = await APIService.getLibraryPreviewSummary()
    previewSummary.value = response.data
  } catch (err) {
    console.error('Failed to load preview summary:', err)
  }
}

// ---- Tree wiring (consumed by LibraryFolderTreeNode via inject) ----

const childrenIndex = computed(() => {
  const index = new Map()
  for (const folder of folders.value) {
    if (folder.parent_id == null) continue
    if (!index.has(folder.parent_id)) index.set(folder.parent_id, [])
    index.get(folder.parent_id).push(folder)
  }
  for (const list of index.values()) {
    list.sort((a, b) => a.name.localeCompare(b.name))
  }
  return index
})

// Whether each folder's subtree (itself + all descendants) holds any active 3D
// file. The tree payload carries `file_count` (direct active files) per folder;
// rolling it up once here lets the "hide empty folders" toggle drop whole
// branches that only contain empty subdirectories. Memoized post-order walk.
const subtreeHasFiles = computed(() => {
  const index = childrenIndex.value
  const result = new Map()
  const compute = (id) => {
    if (result.has(id)) return result.get(id)
    const folder = folderMap.value.get(id)
    let has = (folder?.file_count || 0) > 0
    for (const child of index.get(id) || []) {
      // Always recurse (don't short-circuit) so every node gets memoized.
      if (compute(child.id)) has = true
    }
    result.set(id, has)
    return has
  }
  for (const folder of folders.value) compute(folder.id)
  return result
})

// A folder is hidden only when we positively know its subtree is empty; unknown
// ids (e.g. soft-deleted folders absent from the active tree) stay visible.
function folderPassesEmptyFilter(id) {
  if (!hideEmptyFolders.value) return true
  return subtreeHasFiles.value.get(id) !== false
}

// One top-level node per enabled root (each root's tree has its own null-parent
// folder, named for the root). Ordered to match the roots list.
const rootFolders = computed(() => {
  const order = new Map(roots.value.map((r, i) => [r.id, i]))
  return folders.value
    .filter((f) => f.parent_id == null && folderPassesEmptyFilter(f.id))
    .slice()
    .sort((a, b) => (order.get(a.root) ?? 0) - (order.get(b.root) ?? 0))
})

// Subfolders shown in the right pane, with the same empty-folder filter applied.
const visibleSubfolders = computed(() =>
  (contents.value?.subfolders || []).filter((s) => folderPassesEmptyFilter(s.id)),
)

provide(
  'libraryTree',
  reactive({
    childrenOf: (id) => (childrenIndex.value.get(id) || []).filter((f) => folderPassesEmptyFilter(f.id)),
    isExpanded: (id) => expandedIds.value.has(id),
    get selectedId() {
      return selectedFolderId.value
    },
    select: (id) => selectFolder(id),
    toggle: (id) => {
      const next = new Set(expandedIds.value)
      next.has(id) ? next.delete(id) : next.add(id)
      expandedIds.value = next
    },
  }),
)

function expandAncestorsOf(folderId) {
  const next = new Set(expandedIds.value)
  let current = folderMap.value.get(folderId)
  while (current) {
    next.add(current.id)
    current = current.parent_id != null ? folderMap.value.get(current.parent_id) : null
  }
  expandedIds.value = next
}

// ---- Data loading ----

async function loadLibrary() {
  loadingTree.value = true
  loadError.value = null
  try {
    const rootsResponse = await APIService.getLibraryRoots()
    roots.value = rootsResponse.data
    if (!enabledRoots.value.length) return

    await reloadTree()

    const requested = Number(route.query.folder)
    const startId =
      requested && folderMap.value.has(requested) ? requested : rootFolders.value[0]?.id
    if (startId != null) {
      expandAncestorsOf(startId)
      selectedFolderId.value = startId
      await fetchContents(startId)
    }
  } catch (err) {
    console.error('Failed to load library:', err)
    loadError.value = 'Failed to load the library. Is the backend running?'
  } finally {
    loadingTree.value = false
  }
}

async function refreshRoots() {
  // Re-pull roots so the settings modal's per-root last-scan summary and
  // next-scan time stay current after a scan finishes. Best-effort: a failure
  // keeps the existing (slightly stale) roots rather than blanking the UI.
  try {
    const response = await APIService.getLibraryRoots()
    roots.value = response.data
  } catch (err) {
    console.error('Failed to refresh library roots:', err)
  }
}

async function reloadTree() {
  // Fetch every enabled root's skeleton in parallel and merge into one flat
  // list. Folder ids are globally unique, so folderMap/childrenIndex work
  // unchanged; each root's null-parent folder becomes a top-level tree node.
  const responses = await Promise.all(
    enabledRoots.value.map((r) => APIService.getLibraryFolderTree(r.id)),
  )
  folders.value = responses.flatMap((resp) => resp.data)
}

onMounted(async () => {
  await loadLibrary()
  await resumeActiveJobs()
  loadPreviewSummary()
})
onBeforeUnmount(() => {
  stopJobPolling()
  if (searchDebounce) clearTimeout(searchDebounce)
})

function selectFolder(id) {
  clearSearch()
  clearNewFiles()
  if (id === selectedFolderId.value) return
  router.replace({ query: { ...route.query, folder: id } })
}

watch(
  () => route.query.folder,
  async (value) => {
    const id = Number(value)
    if (!id || !folderMap.value.has(id) || id === selectedFolderId.value) return
    selectedFolderId.value = id
    expandAncestorsOf(id)
    page.value = 1
    await fetchContents(id)
  },
)

async function fetchContents(folderId) {
  loadingContents.value = true
  try {
    const ordering = sortDirection.value === 'desc' ? `-${sortField.value}` : sortField.value
    const params = { page: page.value, page_size: PAGE_SIZE, ordering }
    if (extensionFilter.value) params.extension = extensionFilter.value
    if (showDeleted.value) params.include_deleted = 'true'
    const response = await APIService.getLibraryFolderContents(folderId, params)
    contents.value = response.data
  } catch (err) {
    console.error('Failed to load folder contents:', err)
    loadError.value = 'Failed to load folder contents.'
  } finally {
    loadingContents.value = false
  }
}

function refreshCurrentView() {
  if (searchMode.value) {
    runSearch(searchPage.value)
  } else if (newFilesMode.value) {
    loadNewFiles(newFilesPage.value)
  } else if (selectedFolderId.value != null) {
    fetchContents(selectedFolderId.value)
  }
}

// ---- Search ----

const searchMode = computed(() => searchResults.value !== null)

watch(searchQuery, (value) => {
  if (searchDebounce) clearTimeout(searchDebounce)
  const q = value.trim()
  if (q.length < 2) {
    searchResults.value = null
    return
  }
  searchDebounce = setTimeout(() => runSearch(1), 300)
})

async function runSearch(pageN) {
  const q = searchQuery.value.trim()
  if (q.length < 2 || !enabledRoots.value.length) return
  if (newFilesActive.value) clearNewFiles() // search wins over new-models mode
  searchLoading.value = true
  searchPage.value = pageN
  try {
    // No root param — search spans every enabled root (results carry root_name).
    const params = { q, page: pageN, page_size: PAGE_SIZE }
    if (extensionFilter.value) params.extension = extensionFilter.value
    if (showDeleted.value) params.include_deleted = 'true'
    const response = await APIService.searchLibrary(params)
    searchResults.value = response.data
  } catch (err) {
    console.error('Search failed:', err)
    loadError.value = 'Search failed.'
  } finally {
    searchLoading.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = null
}

// ---- New models since last scan ----

const newFilesMode = computed(() => newFilesActive.value && !searchMode.value)
const newFilesCount = computed(() => newFilesResults.value?.count ?? 0)

async function loadNewFiles(pageN) {
  if (!enabledRoots.value.length) return
  newFilesLoading.value = true
  newFilesPage.value = pageN
  try {
    const params = { page: pageN, page_size: PAGE_SIZE }
    if (extensionFilter.value) params.extension = extensionFilter.value
    const response = await APIService.getNewLibraryFiles(params)
    newFilesResults.value = response.data
  } catch (err) {
    console.error('Failed to load new models:', err)
    loadError.value = 'Failed to load new models.'
  } finally {
    newFilesLoading.value = false
  }
}

function toggleNewFiles() {
  if (newFilesActive.value) {
    clearNewFiles()
    return
  }
  clearSearch()
  newFilesActive.value = true
  loadNewFiles(1)
}

function clearNewFiles() {
  newFilesActive.value = false
  newFilesResults.value = null
  newFilesPage.value = 1
}

// ---- Unified results pane (search OR new-models share one table + pager) ----

const resultsMode = computed(() => searchMode.value || newFilesMode.value)
const resultsData = computed(() => (searchMode.value ? searchResults.value : newFilesResults.value))
const resultsLoading = computed(() =>
  searchMode.value ? searchLoading.value : newFilesLoading.value,
)
const resultsPage = computed(() => (searchMode.value ? searchPage.value : newFilesPage.value))
const resultsTotalPages = computed(() =>
  resultsData.value ? Math.max(1, Math.ceil(resultsData.value.count / PAGE_SIZE)) : 1,
)

function gotoResultsPage(pageN) {
  if (searchMode.value) runSearch(pageN)
  else loadNewFiles(pageN)
}

// ---- Sorting / paging / view mode / filters ----

function sortBy(field) {
  if (sortField.value === field) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortField.value = field
    sortDirection.value = 'asc'
  }
  page.value = 1
  fetchContents(selectedFolderId.value)
}

function sortIndicator(field) {
  if (sortField.value !== field) return ''
  return sortDirection.value === 'asc' ? '▲' : '▼'
}

const totalPages = computed(() =>
  contents.value ? Math.max(1, Math.ceil(contents.value.files.count / PAGE_SIZE)) : 1,
)

function goToPage(newPage) {
  page.value = newPage
  fetchContents(selectedFolderId.value)
}

function setViewMode(mode) {
  viewMode.value = mode
  localStorage.setItem(VIEW_MODE_KEY, mode)
}

function setExtensionFilter(value) {
  if (extensionFilter.value === value) return
  extensionFilter.value = value
  page.value = 1
  newFilesPage.value = 1
  refreshCurrentView()
}

function toggleShowDeleted() {
  showDeleted.value = !showDeleted.value
  page.value = 1
  refreshCurrentView()
}

function toggleHideEmptyFolders() {
  hideEmptyFolders.value = !hideEmptyFolders.value
  localStorage.setItem(HIDE_EMPTY_KEY, String(hideEmptyFolders.value))
  // Purely a client-side view filter over data we already hold — no refetch.
}

// ---- Async job tracking (progress banner) ----

async function resumeActiveJobs() {
  try {
    const response = await APIService.getActiveLibraryScans()
    for (const scan of response.data) trackJob(scan)
  } catch (err) {
    console.error('Failed to load active library scans:', err)
  }
}

function trackJob(scan) {
  if (!scan || scan.id == null) return
  if (!activeJobs.value.some((j) => j.id === scan.id)) {
    activeJobs.value = [...activeJobs.value, scan]
  }
  startJobPolling()
}

function startJobPolling() {
  if (jobPollTimer || !activeJobs.value.length) return
  jobPollTimer = setInterval(pollJobs, 2000)
}

function stopJobPolling() {
  if (jobPollTimer) {
    clearInterval(jobPollTimer)
    jobPollTimer = null
  }
}

async function pollJobs() {
  if (!activeJobs.value.length) {
    stopJobPolling()
    return
  }
  // Poll each tracked job by id; a transient failure keeps the old snapshot
  // and retries next tick rather than dropping the job from the banner.
  const results = await Promise.all(
    activeJobs.value.map((job) =>
      APIService.getLibraryScan(job.id).then(
        (r) => r.data,
        () => null,
      ),
    ),
  )

  const stillActive = []
  const finished = []
  results.forEach((scan, i) => {
    if (scan && (scan.status === 'success' || scan.status === 'error')) {
      finished.push(scan)
    } else {
      stillActive.push(scan || activeJobs.value[i])
    }
  })
  activeJobs.value = stillActive

  if (finished.length) {
    const regenerated = finished.some((s) => s.kind === 'thumbnails' && s.status === 'success')
    finished.forEach(pushJobNotice)
    if (regenerated) thumbVersion.value = Date.now() // bust stale thumbnail cache
    await reloadTree()
    refreshCurrentView()
    loadPreviewSummary() // counts may have changed after a scan/regeneration
    refreshRoots() // refresh last-scan summary / next-scan time shown in Settings
  }

  if (!activeJobs.value.length) stopJobPolling()
}

function pushJobNotice(scan) {
  const rootName = scan.root_name || 'library'
  let notice
  if (scan.status === 'error') {
    const label = scan.kind === 'thumbnails' ? 'Thumbnail regeneration' : 'Scan'
    notice = {
      id: scan.id,
      tone: 'error',
      text: `${label} for ${rootName} failed${scan.error ? ': ' + scan.error : '.'}`,
    }
  } else {
    notice = {
      id: scan.id,
      tone: 'success',
      text:
        scan.kind === 'thumbnails'
          ? `Thumbnails for ${rootName} regenerated — ${scan.files_processed} re-rendered.`
          : `Scan of ${rootName} complete — ${scan.files_seen} files found, ${scan.files_processed} new or updated.`,
    }
  }
  jobNotices.value = [...jobNotices.value, notice]
  setTimeout(() => {
    jobNotices.value = jobNotices.value.filter((n) => n !== notice)
  }, 6000)
}

function jobLabel(job) {
  const rootName = job.root_name || 'library'
  return job.kind === 'thumbnails'
    ? `Regenerating thumbnails for ${rootName}… ${job.progress_percent}%`
    : `Scanning ${rootName}… ${job.files_seen} files found, ${job.progress_percent}% processed`
}

async function rescanCurrentFolder() {
  if (!selectedFolderId.value || anyJobActive.value) return
  try {
    const response = await APIService.rescanLibraryFolder(selectedFolderId.value)
    trackJob(response.data)
  } catch (err) {
    alert(
      err.response?.status === 409
        ? 'A scan is already in progress for this library.'
        : 'Failed to start the folder rescan.',
    )
  }
}

function onLibraryJobStarted(scan) {
  trackJob(scan)
}

// ---- Settings ----

function onSettingsSaved(updatedRoot) {
  roots.value = roots.value.map((r) => (r.id === updatedRoot.id ? updatedRoot : r))
  // enabling/disabling or a path change alters which roots' trees appear.
  reloadTree()
}

async function onRootCreated(newRoot) {
  roots.value = [...roots.value, newRoot]
  await loadLibrary()
}

async function onRootDeleted() {
  // Server is authoritative — reload roots + trees. A selection under the
  // now-gone root falls back to the first root folder inside loadLibrary().
  selectedFolderId.value = null
  await loadLibrary()
  loadPreviewSummary()
}

async function onLibraryRescanned() {
  // Purge is synchronous — refresh the tree/contents once it returns. Async
  // scans/regenerations refresh via the job poll loop instead.
  await reloadTree()
  refreshCurrentView()
  loadPreviewSummary()
}

function thumbSrc(file) {
  if (!file.thumbnail) return ''
  return thumbVersion.value ? file.thumbnail + '?v=' + thumbVersion.value : file.thumbnail
}

// ---- Deletion (soft-deleted records only; API enforces the guard) ----

async function deleteFolderRow(subfolder) {
  if (
    !confirm(
      `Permanently delete the record for folder "${subfolder.name}" and everything under it?`,
    )
  )
    return
  try {
    await APIService.deleteLibraryFolder(subfolder.id)
    await reloadTree()
    refreshCurrentView()
  } catch (err) {
    alert(err.response?.data?.error || 'Failed to delete the folder record.')
  }
}

function onFileDeleted() {
  showFileModal.value = false
  refreshCurrentView()
}

// ---- File modal ----

function openFile(file) {
  detailFileId.value = file.id
  showFileModal.value = true
}

// ---- Formatting ----

function formatSize(bytes) {
  if (bytes == null) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString() : ''
}

function parentPath(relativePath) {
  if (!relativePath || !relativePath.includes('/')) return ''
  return relativePath.slice(0, relativePath.lastIndexOf('/'))
}

const breadcrumbs = computed(() => contents.value?.folder?.breadcrumbs || [])
</script>

<template>
  <div class="library-page">
    <MainHeader title="Library">
      <template #actions>
        <template v-if="hasAnyRoot">
        <div class="ext-filter">
          <button
            class="btn"
            :class="extensionFilter === '' ? 'btn-primary' : 'btn-outline'"
            @click="setExtensionFilter('')"
          >
            All
          </button>
          <button
            class="btn"
            :class="extensionFilter === 'stl' ? 'btn-primary' : 'btn-outline'"
            @click="setExtensionFilter('stl')"
          >
            STL
          </button>
          <button
            class="btn"
            :class="extensionFilter === '3mf' ? 'btn-primary' : 'btn-outline'"
            @click="setExtensionFilter('3mf')"
          >
            3MF
          </button>
        </div>
        <div class="view-toggle">
          <button
            class="btn"
            :class="viewMode === 'list' ? 'btn-primary' : 'btn-outline'"
            @click="setViewMode('list')"
          >
            List
          </button>
          <button
            class="btn"
            :class="viewMode === 'grid' ? 'btn-primary' : 'btn-outline'"
            @click="setViewMode('grid')"
          >
            Grid
          </button>
        </div>
        <input
          type="text"
          v-model="searchQuery"
          class="search-input"
          placeholder="Search library…"
          spellcheck="false"
        />
        </template>
        <button class="btn btn-outline" @click="showSettingsModal = true">
          {{ hasAnyRoot ? 'Settings' : 'Configure Library' }}
        </button>
      </template>
    </MainHeader>
    <p
      v-if="previewIssueText"
      class="preview-summary-note"
      title="Files with no preview image. 'Too large' exceeds the render size cap; 'unreadable' means the 3D mesh couldn't be parsed for a thumbnail. The file itself is still indexed and openable."
    >
      {{ previewIssueText }}
    </p>

    <!-- No configured root yet -->
    <div v-if="!loadingTree && !hasAnyRoot" class="empty-state">
      <p>No library root is configured yet.</p>
      <p class="empty-hint">
        A library root points Print Vault at a folder of STL/3MF files (e.g. a mounted network
        share). Click "Configure Library" above to set one up, then run a scan.
      </p>
    </div>

    <div v-else-if="loadError" class="empty-state">
      <p>{{ loadError }}</p>
    </div>

    <template v-else>
      <!-- Async job progress banner: live scans/regenerations + transient
           completion notices, owned by this screen so it survives closing the
           settings modal and re-attaches after a page refresh. -->
      <div v-if="anyJobActive || jobNotices.length" class="job-banner">
        <div v-for="job in activeJobs" :key="`job-${job.id}`" class="job-line job-active">
          <span class="job-spinner" aria-hidden="true"></span>
          <span>{{ jobLabel(job) }}</span>
        </div>
        <div
          v-for="notice in jobNotices"
          :key="`notice-${notice.id}`"
          class="job-line"
          :class="notice.tone === 'error' ? 'job-error' : 'job-success'"
        >
          {{ notice.text }}
        </div>
      </div>

      <div class="library-layout">
      <!-- Left pane: folder tree -->
      <aside class="tree-pane">
        <div v-if="loadingTree" class="pane-state">Loading folders…</div>
        <ul v-else-if="rootFolders.length" class="tree-root">
          <LibraryFolderTreeNode v-for="rf in rootFolders" :key="rf.id" :folder="rf" />
        </ul>
        <div v-else class="pane-state">
          No folders indexed yet. Open Settings and use "Rescan Now" to populate the library.
        </div>
      </aside>

      <!-- Right pane: folder contents or search results -->
      <main class="contents-pane">
        <div class="contents-toolbar">
          <nav v-if="!resultsMode" class="breadcrumbs">
            <template v-for="(crumb, index) in breadcrumbs" :key="crumb.id">
              <span v-if="index > 0" class="crumb-separator">/</span>
              <a
                v-if="index < breadcrumbs.length - 1"
                href="#"
                @click.prevent="selectFolder(crumb.id)"
                >{{ crumb.name }}</a
              >
              <span v-else class="crumb-current">{{ crumb.name }}</span>
            </template>
          </nav>
          <div v-else-if="searchMode" class="search-summary">
            {{ searchResults.count }} result{{ searchResults.count === 1 ? '' : 's' }} for
            “{{ searchQuery.trim() }}”
            <button class="btn btn-sm btn-secondary" @click="clearSearch">Clear</button>
          </div>
          <div v-else class="search-summary">
            {{ newFilesCount }} new model{{ newFilesCount === 1 ? '' : 's' }} since the last scan
          </div>

          <div class="toolbar-toggles">
            <label v-if="!searchMode" class="browser-toggle">
              <input type="checkbox" :checked="newFilesActive" @change="toggleNewFiles" />
              Show new models
            </label>
            <label v-if="!resultsMode" class="browser-toggle">
              <input type="checkbox" :checked="hideEmptyFolders" @change="toggleHideEmptyFolders" />
              Hide empty folders
            </label>
            <label v-if="!newFilesMode" class="browser-toggle">
              <input type="checkbox" :checked="showDeleted" @change="toggleShowDeleted" />
              Show deleted
            </label>
            <button
              v-if="!resultsMode"
              class="btn btn-sm btn-secondary"
              :disabled="anyJobActive"
              @click="rescanCurrentFolder"
            >
              {{ scanJobActive ? 'Rescanning…' : 'Rescan This Folder' }}
            </button>
          </div>
        </div>

        <!-- RESULTS PANE (search OR new-models — shared flat file list) -->
        <template v-if="resultsMode">
          <div v-if="resultsLoading" class="pane-state">
            {{ searchMode ? 'Searching…' : 'Loading…' }}
          </div>
          <template v-else-if="resultsData">
            <table class="file-table">
              <thead>
                <tr>
                  <th class="col-thumb"></th>
                  <th class="col-name">Name</th>
                  <th class="col-path">Location</th>
                  <th class="col-size">Size</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="file in resultsData.results"
                  :key="`hit-${file.id}`"
                  class="row-clickable"
                  :class="{ 'row-deleted': file.status === 'deleted' }"
                  @click="openFile(file)"
                >
                  <td class="col-thumb">
                    <img v-if="file.thumbnail" :src="thumbSrc(file)" class="row-thumb" />
                    <span v-else class="row-thumb-placeholder">{{ file.extension }}</span>
                  </td>
                  <td class="col-name">
                    {{ file.filename }}
                    <span class="ext-badge">{{ file.extension }}</span>
                    <span v-if="file.status === 'deleted'" class="deleted-badge">deleted</span>
                  </td>
                  <td class="col-path">
                    <span class="hit-root">{{ file.root_name }}</span
                    >{{
                      parentPath(file.relative_path) ? ' / ' + parentPath(file.relative_path) : ''
                    }}
                  </td>
                  <td class="col-size">{{ formatSize(file.size_bytes) }}</td>
                </tr>
                <tr v-if="!resultsData.results.length">
                  <td colspan="4" class="pane-state">
                    {{ searchMode ? 'No matching files.' : 'No new models since the last scan.' }}
                  </td>
                </tr>
              </tbody>
            </table>

            <div v-if="resultsTotalPages > 1" class="pagination">
              <button
                class="btn btn-sm btn-secondary"
                :disabled="resultsPage <= 1"
                @click="gotoResultsPage(resultsPage - 1)"
              >
                Previous
              </button>
              <span class="page-label">Page {{ resultsPage }} of {{ resultsTotalPages }}</span>
              <button
                class="btn btn-sm btn-secondary"
                :disabled="resultsPage >= resultsTotalPages"
                @click="gotoResultsPage(resultsPage + 1)"
              >
                Next
              </button>
            </div>
          </template>
        </template>

        <div v-else-if="loadingContents" class="pane-state">Loading…</div>

        <template v-else-if="contents">
          <!-- LIST VIEW -->
          <table v-if="viewMode === 'list'" class="file-table">
            <thead>
              <tr>
                <th class="col-thumb"></th>
                <th class="col-name sortable" @click="sortBy('filename')">
                  Name <span class="sort-indicator">{{ sortIndicator('filename') }}</span>
                </th>
                <th class="col-size sortable" @click="sortBy('size_bytes')">
                  Size <span class="sort-indicator">{{ sortIndicator('size_bytes') }}</span>
                </th>
                <th class="col-date sortable" @click="sortBy('modified_time')">
                  Modified <span class="sort-indicator">{{ sortIndicator('modified_time') }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="subfolder in visibleSubfolders"
                :key="`folder-${subfolder.id}`"
                class="row-clickable"
                :class="{ 'row-deleted': subfolder.status === 'deleted' }"
                @click="subfolder.status === 'deleted' ? null : selectFolder(subfolder.id)"
              >
                <td class="col-thumb"><span class="folder-glyph"></span></td>
                <td class="col-name folder-name">
                  {{ subfolder.name }}
                  <span v-if="subfolder.status === 'deleted'" class="deleted-badge">deleted</span>
                  <button
                    v-if="subfolder.status === 'deleted'"
                    class="btn-icon-delete"
                    title="Delete permanently"
                    @click.stop="deleteFolderRow(subfolder)"
                  >
                    &times;
                  </button>
                </td>
                <td class="col-size">—</td>
                <td class="col-date">—</td>
              </tr>
              <tr
                v-for="file in contents.files.results"
                :key="`file-${file.id}`"
                class="row-clickable"
                :class="{ 'row-deleted': file.status === 'deleted' }"
                @click="openFile(file)"
              >
                <td class="col-thumb">
                  <img v-if="file.thumbnail" :src="thumbSrc(file)" class="row-thumb" />
                  <span v-else class="row-thumb-placeholder">{{ file.extension }}</span>
                </td>
                <td class="col-name">
                  {{ file.filename }}
                  <span class="ext-badge">{{ file.extension }}</span>
                  <span v-if="file.status === 'deleted'" class="deleted-badge">deleted</span>
                </td>
                <td class="col-size">{{ formatSize(file.size_bytes) }}</td>
                <td class="col-date">{{ formatDate(file.modified_time) }}</td>
              </tr>
              <tr v-if="!visibleSubfolders.length && !contents.files.results.length">
                <td colspan="4" class="pane-state">This folder is empty.</td>
              </tr>
            </tbody>
          </table>

          <!-- GRID VIEW -->
          <div v-else class="file-grid">
            <div
              v-for="subfolder in visibleSubfolders"
              :key="`folder-${subfolder.id}`"
              class="grid-card"
              :class="{ 'row-deleted': subfolder.status === 'deleted' }"
              @click="subfolder.status === 'deleted' ? null : selectFolder(subfolder.id)"
            >
              <div class="grid-thumb grid-thumb-folder"><span class="folder-glyph-large"></span></div>
              <div class="grid-label" :title="subfolder.name">{{ subfolder.name }}</div>
              <div v-if="subfolder.status === 'deleted'" class="grid-sublabel">
                <span class="deleted-badge">deleted</span>
              </div>
            </div>
            <div
              v-for="file in contents.files.results"
              :key="`file-${file.id}`"
              class="grid-card"
              :class="{ 'row-deleted': file.status === 'deleted' }"
              @click="openFile(file)"
            >
              <div class="grid-thumb">
                <img v-if="file.thumbnail" :src="thumbSrc(file)" />
                <span v-else class="grid-thumb-placeholder">{{ file.extension }}</span>
              </div>
              <div class="grid-label" :title="file.filename">{{ file.filename }}</div>
              <div class="grid-sublabel">
                {{ formatSize(file.size_bytes) }}
                <span v-if="file.status === 'deleted'" class="deleted-badge">deleted</span>
              </div>
            </div>
            <div
              v-if="!visibleSubfolders.length && !contents.files.results.length"
              class="pane-state"
            >
              This folder is empty.
            </div>
          </div>

          <!-- Pagination -->
          <div v-if="totalPages > 1" class="pagination">
            <button
              class="btn btn-sm btn-secondary"
              :disabled="page <= 1"
              @click="goToPage(page - 1)"
            >
              Previous
            </button>
            <span class="page-label">Page {{ page }} of {{ totalPages }}</span>
            <button
              class="btn btn-sm btn-secondary"
              :disabled="page >= totalPages"
              @click="goToPage(page + 1)"
            >
              Next
            </button>
          </div>
        </template>
      </main>
      </div>
    </template>

    <LibraryFileDetailModal
      :show="showFileModal"
      :file-id="detailFileId"
      :render-color="activeRoot?.thumbnail_color || ''"
      @close="showFileModal = false"
      @deleted="onFileDeleted"
    />

    <LibrarySettingsModal
      :show="showSettingsModal"
      :roots="roots"
      @close="showSettingsModal = false"
      @saved="onSettingsSaved"
      @created="onRootCreated"
      @deleted="onRootDeleted"
      @job-started="onLibraryJobStarted"
      @rescanned="onLibraryRescanned"
    />
  </div>
</template>

<style scoped>
.library-page {
  /* No padding here: the app shell's .main-content already supplies 20px, so
     the header aligns with the other views (e.g. Print Trackers). */
}

.preview-summary-note {
  margin: 0 0 16px;
  font-size: 0.85rem;
  color: var(--color-text);
  opacity: 0.75;
  cursor: help;
}

.empty-state {
  padding: 48px 24px;
  text-align: center;
  color: var(--color-text);
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.empty-hint {
  color: var(--color-text);
  opacity: 0.75;
  max-width: 480px;
  margin: 8px auto 0;
}

/* ---- Job progress banner ---- */

.job-banner {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 12px;
}

.job-line {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  color: var(--color-text);
}

.job-active {
  background-color: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
}

.job-success {
  background-color: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.job-error {
  background-color: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.job-spinner {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(59, 130, 246, 0.35);
  border-top-color: var(--color-blue);
  border-radius: 50%;
  animation: job-spin 0.8s linear infinite;
}

@keyframes job-spin {
  to {
    transform: rotate(360deg);
  }
}

.library-layout {
  display: flex;
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  background-color: var(--color-background-soft);
  min-height: 60vh;
}

/* ---- Left pane ---- */

.tree-pane {
  width: 280px;
  flex-shrink: 0;
  border-right: 1px solid var(--color-border);
  padding: 12px 8px;
  overflow: auto;
}

.tree-root {
  margin: 0;
  padding: 0;
}

.pane-state {
  padding: 24px;
  color: var(--color-text);
  opacity: 0.75;
  text-align: center;
}

/* ---- Right pane ---- */

.contents-pane {
  flex: 1;
  min-width: 0;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
}

.contents-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}

.breadcrumbs a {
  color: var(--color-text);
  text-decoration: none;
  word-break: break-word;
}

.breadcrumbs a:hover {
  text-decoration: underline;
}

.crumb-separator {
  color: var(--color-text);
  opacity: 0.6;
}

.crumb-current {
  color: var(--color-heading);
  font-weight: 600;
}

.search-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-heading);
  font-weight: 600;
}

.search-input {
  flex: none;
  width: 200px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1rem;
  height: 41px;
  box-sizing: border-box;
}

/* Search/filter inputs use the gray, no-shadow focus state (design system) */
.search-input:focus {
  border-color: var(--color-border);
  box-shadow: none;
  outline: none;
}

.ext-filter,
.view-toggle {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.toolbar-toggles {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.browser-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text);
  font-size: 0.9rem;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

/* ---- List view ---- */

.file-table {
  width: 100%;
  border-collapse: collapse;
}

.file-table th {
  text-align: left;
  padding: 8px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-heading);
  white-space: nowrap;
}

.file-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.sort-indicator {
  font-size: 0.7em;
  color: var(--color-text);
  opacity: 0.7;
}

.file-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text);
}

.row-clickable {
  cursor: pointer;
}

.row-clickable:hover {
  background-color: var(--color-background-mute);
}

.row-deleted {
  opacity: 0.55;
}

.col-thumb {
  width: 48px;
}

.row-thumb {
  width: 40px;
  height: 40px;
  object-fit: contain;
  display: block;
}

.row-thumb-placeholder,
.grid-thumb-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 1px dashed var(--color-border);
  border-radius: 4px;
  color: var(--color-text);
  opacity: 0.7;
  font-size: 0.7rem;
  text-transform: uppercase;
}

.col-size,
.col-date {
  white-space: nowrap;
  width: 110px;
}

.col-path {
  color: var(--color-text);
  opacity: 0.8;
  word-break: break-word;
}

.hit-root {
  color: var(--color-heading);
  font-weight: 600;
}

.folder-name {
  font-weight: 600;
}

.ext-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 6px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  font-size: 0.7rem;
  text-transform: uppercase;
  color: var(--color-text);
  opacity: 0.8;
}

.deleted-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 6px;
  border: 1px solid rgba(239, 68, 68, 0.3);
  background-color: rgba(239, 68, 68, 0.1);
  border-radius: 10px;
  font-size: 0.7rem;
  text-transform: uppercase;
  color: var(--color-text);
}

/* Folder glyph: pure CSS tab-folder shape (no emoji) */
.folder-glyph,
.folder-glyph-large {
  display: block;
  position: relative;
  width: 26px;
  height: 18px;
  background-color: var(--color-text);
  opacity: 0.65;
  border-radius: 2px 3px 3px 3px;
}

.folder-glyph::before,
.folder-glyph-large::before {
  content: '';
  position: absolute;
  top: -4px;
  left: 0;
  width: 40%;
  height: 4px;
  background-color: var(--color-text);
  border-radius: 2px 2px 0 0;
}

.folder-glyph-large {
  width: 56px;
  height: 40px;
  border-radius: 3px 6px 6px 6px;
}

.folder-glyph-large::before {
  top: -8px;
  height: 8px;
}

/* ---- Grid view ---- */

.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
  align-content: start;
}

.grid-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px;
  cursor: pointer;
  text-align: center;
  background-color: var(--color-background);
}

.grid-card:hover {
  background-color: var(--color-background-mute);
}

.grid-thumb {
  height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.grid-thumb img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.grid-label {
  color: var(--color-text);
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.grid-sublabel {
  color: var(--color-text);
  opacity: 0.75;
  font-size: 0.75rem;
}

/* ---- Pagination ---- */

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 12px;
}

.page-label {
  color: var(--color-text);
}

/* ---- Responsive ---- */

@media (max-width: 768px) {
  .library-layout {
    flex-direction: column;
  }

  .tree-pane {
    width: 100%;
    max-height: 240px;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
