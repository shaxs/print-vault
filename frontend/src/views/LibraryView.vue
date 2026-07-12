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
import TagBadge from '@/components/TagBadge.vue'
import LibraryTagBrowser from '@/components/LibraryTagBrowser.vue'
import LibraryFolderMetadataModal from '@/components/LibraryFolderMetadataModal.vue'

const VIEW_MODE_KEY = 'library-view-mode'
const HIDE_EMPTY_KEY = 'library-hide-empty-folders'
const SEARCH_SCOPE_KEY = 'library-search-scope'
const PAGE_SIZE = 100

// Which field(s) a search matches against. `value` maps straight to the
// backend `fields` param ('all' is sent as an omitted param = every scope).
// Add { value: 'tags', label: 'Tags' } here when tags ship — the dropdown and
// request both build off this one list.
const SEARCH_SCOPES = [
  { value: 'all', label: 'All fields' },
  { value: 'name', label: 'File name' },
  { value: 'notes', label: 'Notes' },
  { value: 'tags', label: 'Tags' },
]

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

const tagBrowser = ref(null) // LibraryTagBrowser instance (for reload after tag edits)
const detailFileId = ref(null)
const showFileModal = ref(false)
const showFolderModal = ref(false)
const folderModalId = ref(null)
const folderModalName = ref('')
const showSettingsModal = ref(false)
const thumbVersion = ref(0) // bumped after regeneration to bust stale img cache

// Search state — non-null searchResults switches the right pane to results
const searchQuery = ref('')
const searchResults = ref(null)
const searchPage = ref(1)
const searchLoading = ref(false)
const searchScope = ref(
  SEARCH_SCOPES.some((s) => s.value === localStorage.getItem(SEARCH_SCOPE_KEY))
    ? localStorage.getItem(SEARCH_SCOPE_KEY)
    : 'all',
)
let searchDebounce = null

// "New models since the last scan" mode — like search, it takes over the right
// pane with a flat, paginated file list (files first indexed by each root's
// most recent scan). Mutually exclusive with search.
const newFilesActive = ref(false)
const newFilesResults = ref(null)
const newFilesPage = ref(1)
const newFilesLoading = ref(false)

// Browse-by-tag mode — like search/new-models, a cross-folder results view
// driven by the left-pane tag browser. Mutually exclusive with search and
// new-models (entering any one clears the others). OR semantics across tags.
const selectedTags = ref([]) // selected tag objects { id, name, slug }
const tagMatchMode = ref('all') // 'all' (AND) | 'any' (OR)
const tagResults = ref(null)
const tagPage = ref(1)
const tagLoading = ref(false)

// Favorites mode — a results view of favorited files, like new-models. Mutually
// exclusive with search / tag-browse / new-models.
const favoritesActive = ref(false)
const favoritesResults = ref(null)
const favoritesPage = ref(1)
const favoritesLoading = ref(false)

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
    openMetadata: (folder) => openFolderMetadata(folder),
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
    const hasRequested = requested && folderMap.value.has(requested)
    const startId = hasRequested ? requested : rootFolders.value[0]?.id
    if (startId != null) {
      // Open the top root's contents on load (or the URL-requested folder), but
      // only EXPAND the tree for a deep link — a fresh landing shows the root's
      // files while leaving the tree collapsed (selecting ≠ expanding).
      if (hasRequested) expandAncestorsOf(startId)
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
  } else if (tagBrowseMode.value) {
    loadTagResults(tagPage.value)
  } else if (favoritesMode.value) {
    loadFavorites(favoritesPage.value)
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
  if (selectedTags.value.length) clearTagBrowse() // and over tag-browse
  if (favoritesActive.value) clearFavorites() // and over favorites
  searchLoading.value = true
  searchPage.value = pageN
  try {
    // No root param — search spans every enabled root (results carry root_name).
    const params = { q, page: pageN, page_size: PAGE_SIZE }
    if (extensionFilter.value) params.extension = extensionFilter.value
    if (showDeleted.value) params.include_deleted = 'true'
    // 'all' searches every field, which is the backend default when `fields`
    // is omitted — so only send the param for a narrowed scope.
    if (searchScope.value !== 'all') params.fields = searchScope.value
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

function setSearchScope(value) {
  if (searchScope.value === value) return
  searchScope.value = value
  localStorage.setItem(SEARCH_SCOPE_KEY, value)
  // Re-run an in-flight search against the newly selected field(s).
  if (searchQuery.value.trim().length >= 2) runSearch(1)
}

// ---- New models since last scan ----

const newFilesMode = computed(
  () => newFilesActive.value && !searchMode.value && !tagBrowseMode.value && !favoritesMode.value,
)
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
  clearTagBrowse()
  clearFavorites()
  newFilesActive.value = true
  loadNewFiles(1)
}

function clearNewFiles() {
  newFilesActive.value = false
  newFilesResults.value = null
  newFilesPage.value = 1
}

// ---- Browse by tag ----

const tagBrowseMode = computed(() => tagResults.value !== null)
const tagCount = computed(() => tagResults.value?.count ?? 0)

// Driven by the left-pane tag browser's v-model. Selecting the first tag takes
// over the right pane (clearing search/new-models); clearing all tags returns
// to the folder view.
function onTagSelectionChange(tags) {
  selectedTags.value = tags
  if (!tags.length) {
    tagResults.value = null
    tagPage.value = 1
    return
  }
  clearSearch()
  clearNewFiles()
  clearFavorites()
  loadTagResults(1)
}

async function loadTagResults(pageN) {
  if (!selectedTags.value.length || !enabledRoots.value.length) return
  tagLoading.value = true
  tagPage.value = pageN
  try {
    const params = {
      tags: selectedTags.value.map((t) => t.slug).join(','),
      page: pageN,
      page_size: PAGE_SIZE,
    }
    // 'all' (AND) is the backend default — only send tag_mode to opt into 'any'.
    if (tagMatchMode.value === 'any') params.tag_mode = 'any'
    if (extensionFilter.value) params.extension = extensionFilter.value
    if (showDeleted.value) params.include_deleted = 'true'
    const response = await APIService.searchLibrary(params)
    tagResults.value = response.data
  } catch (err) {
    console.error('Tag browse failed:', err)
    loadError.value = 'Failed to load tagged files.'
  } finally {
    tagLoading.value = false
  }
}

function clearTagBrowse() {
  selectedTags.value = []
  tagResults.value = null
  tagPage.value = 1
}

function removeTag(tag) {
  onTagSelectionChange(selectedTags.value.filter((t) => t.slug !== tag.slug))
}

function onTagMatchModeChange(mode) {
  tagMatchMode.value = mode
  if (selectedTags.value.length) loadTagResults(1)
}

// ---- Favorites ----

const favoritesMode = computed(
  () => favoritesActive.value && !searchMode.value && !tagBrowseMode.value,
)
const favoritesCount = computed(() => favoritesResults.value?.count ?? 0)

async function loadFavorites(pageN) {
  if (!enabledRoots.value.length) return
  favoritesLoading.value = true
  favoritesPage.value = pageN
  try {
    const params = { favorites: 'true', page: pageN, page_size: PAGE_SIZE }
    if (extensionFilter.value) params.extension = extensionFilter.value
    if (showDeleted.value) params.include_deleted = 'true'
    const response = await APIService.searchLibrary(params)
    favoritesResults.value = response.data
  } catch (err) {
    console.error('Failed to load favorites:', err)
    loadError.value = 'Failed to load favorites.'
  } finally {
    favoritesLoading.value = false
  }
}

function toggleFavoritesMode() {
  if (favoritesActive.value) {
    clearFavorites()
    return
  }
  clearSearch()
  clearTagBrowse()
  clearNewFiles()
  favoritesActive.value = true
  loadFavorites(1)
}

function clearFavorites() {
  favoritesActive.value = false
  favoritesResults.value = null
  favoritesPage.value = 1
}

// Keep a visible row's star in sync after the detail modal toggles it, without
// a refetch. If a file is un-favorited while browsing favorites, drop it.
function onFavoriteChanged({ id, is_favorite }) {
  for (const list of [
    contents.value?.files?.results,
    searchResults.value?.results,
    tagResults.value?.results,
    favoritesResults.value?.results,
    newFilesResults.value?.results,
  ]) {
    const row = list?.find((f) => f.id === id)
    if (row) row.is_favorite = is_favorite
  }
  if (favoritesMode.value && !is_favorite) {
    loadFavorites(favoritesPage.value)
  }
}

// Keep a visible row's tag badges in sync after the detail modal edits them, and
// refresh the left-pane tag browser so a newly created (or newly orphaned) tag
// shows up in / drops out of the filter list without a page reload.
function onFileTagsChanged({ id, tags }) {
  for (const list of [
    contents.value?.files?.results,
    searchResults.value?.results,
    tagResults.value?.results,
    favoritesResults.value?.results,
    newFilesResults.value?.results,
  ]) {
    const row = list?.find((f) => f.id === id)
    if (row) row.tags = tags
  }
  tagBrowser.value?.reload()
}

// ---- Folder tags & notes (right-click a folder in the tree) ----

function openFolderMetadata(folder) {
  folderModalId.value = folder.id
  folderModalName.value = folder.name
  showFolderModal.value = true
}

function onFolderMetadataSaved(result) {
  showFolderModal.value = false
  // Folder tags cascaded down: refresh the tree, the current file view (so tag
  // badges/filters reflect the change), and the tag browser's usage counts.
  reloadTree()
  refreshCurrentView()
  tagBrowser.value?.reload()
  const n = result?.affected_files ?? 0
  const notice = {
    id: `folder-tags-${Date.now()}`,
    tone: 'success',
    text: `Folder tags applied to ${n} file${n === 1 ? '' : 's'}.`,
  }
  jobNotices.value = [...jobNotices.value, notice]
  setTimeout(() => {
    jobNotices.value = jobNotices.value.filter((x) => x !== notice)
  }, 6000)
}

// ---- Unified results pane (search / tag-browse / new-models share one table) ----

const resultsMode = computed(
  () => searchMode.value || tagBrowseMode.value || favoritesMode.value || newFilesMode.value,
)
const resultsData = computed(() => {
  if (searchMode.value) return searchResults.value
  if (tagBrowseMode.value) return tagResults.value
  if (favoritesMode.value) return favoritesResults.value
  return newFilesResults.value
})
const resultsLoading = computed(() => {
  if (searchMode.value) return searchLoading.value
  if (tagBrowseMode.value) return tagLoading.value
  if (favoritesMode.value) return favoritesLoading.value
  return newFilesLoading.value
})
const resultsPage = computed(() => {
  if (searchMode.value) return searchPage.value
  if (tagBrowseMode.value) return tagPage.value
  if (favoritesMode.value) return favoritesPage.value
  return newFilesPage.value
})
const resultsTotalPages = computed(() =>
  resultsData.value ? Math.max(1, Math.ceil(resultsData.value.count / PAGE_SIZE)) : 1,
)

function gotoResultsPage(pageN) {
  if (searchMode.value) runSearch(pageN)
  else if (tagBrowseMode.value) loadTagResults(pageN)
  else if (favoritesMode.value) loadFavorites(pageN)
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

// Quick favorite toggle from a grid/list row (doesn't open the file).
async function toggleRowFavorite(file) {
  const next = !file.is_favorite
  file.is_favorite = next // optimistic
  try {
    await APIService.updateLibraryFile(file.id, { is_favorite: next })
    // If un-favorited while browsing favorites, drop it from the list.
    if (favoritesMode.value && !next) loadFavorites(favoritesPage.value)
  } catch (err) {
    console.error('Failed to update favorite:', err)
    file.is_favorite = !next // roll back
  }
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
        <div class="search-group">
          <select
            class="search-scope"
            :value="searchScope"
            aria-label="Search in"
            @change="setSearchScope($event.target.value)"
          >
            <option v-for="scope in SEARCH_SCOPES" :key="scope.value" :value="scope.value">
              {{ scope.label }}
            </option>
          </select>
          <input
            type="text"
            v-model="searchQuery"
            class="search-input"
            placeholder="Search library…"
            spellcheck="false"
          />
        </div>
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
      <!-- Left pane: browse-by-tag control + folder tree -->
      <aside class="tree-pane">
        <LibraryTagBrowser
          ref="tagBrowser"
          :model-value="selectedTags"
          :match-mode="tagMatchMode"
          @update:model-value="onTagSelectionChange"
          @update:match-mode="onTagMatchModeChange"
        />
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
          <div v-else-if="tagBrowseMode" class="search-summary tag-summary">
            <span>{{ tagCount }} file{{ tagCount === 1 ? '' : 's' }} tagged</span>
            <TagBadge
              v-for="tag in selectedTags"
              :key="tag.id"
              :tag="tag"
              :removable="true"
              @remove="removeTag"
            />
            <button class="btn btn-sm btn-secondary" @click="clearTagBrowse">Clear</button>
          </div>
          <div v-else-if="favoritesMode" class="search-summary">
            {{ favoritesCount }} favorite{{ favoritesCount === 1 ? '' : 's' }}
          </div>
          <div v-else class="search-summary">
            {{ newFilesCount }} new model{{ newFilesCount === 1 ? '' : 's' }} since the last scan
          </div>

          <div class="toolbar-toggles">
            <div class="ext-filter">
              <button
                class="btn btn-sm"
                :class="extensionFilter === '' ? 'btn-primary' : 'btn-outline'"
                @click="setExtensionFilter('')"
              >
                All
              </button>
              <button
                class="btn btn-sm"
                :class="extensionFilter === 'stl' ? 'btn-primary' : 'btn-outline'"
                @click="setExtensionFilter('stl')"
              >
                STL
              </button>
              <button
                class="btn btn-sm"
                :class="extensionFilter === '3mf' ? 'btn-primary' : 'btn-outline'"
                @click="setExtensionFilter('3mf')"
              >
                3MF
              </button>
            </div>
            <div v-if="!resultsMode" class="view-toggle">
              <button
                class="btn btn-sm"
                :class="viewMode === 'list' ? 'btn-primary' : 'btn-outline'"
                @click="setViewMode('list')"
              >
                List
              </button>
              <button
                class="btn btn-sm"
                :class="viewMode === 'grid' ? 'btn-primary' : 'btn-outline'"
                @click="setViewMode('grid')"
              >
                Grid
              </button>
            </div>
            <span class="toolbar-divider" aria-hidden="true"></span>
            <label v-if="!searchMode" class="browser-toggle">
              <input type="checkbox" :checked="newFilesActive" @change="toggleNewFiles" />
              Show new models
            </label>
            <label v-if="!searchMode" class="browser-toggle">
              <input type="checkbox" :checked="favoritesActive" @change="toggleFavoritesMode" />
              Show favorites
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
              v-if="!resultsMode && selectedFolderId != null"
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
            <!-- Folder hits: only in text-search mode, matched on folder name/notes -->
            <div
              v-if="searchMode && searchResults.folders && searchResults.folders.length"
              class="folder-hits"
            >
              <div class="folder-hits-label">Folders</div>
              <button
                v-for="fhit in searchResults.folders"
                :key="`fhit-${fhit.id}`"
                type="button"
                class="folder-hit"
                @click="selectFolder(fhit.id)"
              >
                <span class="folder-glyph" aria-hidden="true"></span>
                <span class="folder-hit-name">{{ fhit.name }}</span>
                <span class="folder-hit-path">
                  {{ fhit.root_name
                  }}{{ parentPath(fhit.relative_path) ? ' / ' + parentPath(fhit.relative_path) : '' }}
                </span>
              </button>
            </div>
            <table class="file-table">
              <thead>
                <tr>
                  <th class="col-thumb"></th>
                  <th class="col-name">Name</th>
                  <th class="col-path">Location</th>
                  <th class="col-notes">Notes</th>
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
                    <button
                      type="button"
                      class="row-star"
                      :class="{ active: file.is_favorite }"
                      :title="file.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
                      @click.stop="toggleRowFavorite(file)"
                    >
                      {{ file.is_favorite ? '★' : '☆' }}
                    </button>
                    {{ file.filename }}
                    <span class="ext-badge">{{ file.extension }}</span>
                    <span v-if="file.status === 'deleted'" class="deleted-badge">deleted</span>
                    <span v-if="file.tags && file.tags.length" class="row-tags">
                      <TagBadge v-for="tag in file.tags" :key="tag.id" :tag="tag" />
                    </span>
                  </td>
                  <td class="col-path">
                    <span class="hit-root">{{ file.root_name }}</span
                    >{{
                      parentPath(file.relative_path) ? ' / ' + parentPath(file.relative_path) : ''
                    }}
                  </td>
                  <td class="col-notes">
                    <span v-if="file.notes" class="notes-preview" :title="file.notes">{{
                      file.notes
                    }}</span>
                  </td>
                  <td class="col-size">{{ formatSize(file.size_bytes) }}</td>
                </tr>
                <tr v-if="!resultsData.results.length">
                  <td colspan="5" class="pane-state">
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
                  <button
                    type="button"
                    class="row-star"
                    :class="{ active: file.is_favorite }"
                    :title="file.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
                    @click.stop="toggleRowFavorite(file)"
                  >
                    {{ file.is_favorite ? '★' : '☆' }}
                  </button>
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
              <button
                type="button"
                class="grid-star"
                :class="{ active: file.is_favorite }"
                :title="file.is_favorite ? 'Remove from favorites' : 'Add to favorites'"
                @click.stop="toggleRowFavorite(file)"
              >
                {{ file.is_favorite ? '★' : '☆' }}
              </button>
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

        <div v-else class="pane-state">
          Select a folder from the tree to browse its files — or use Browse by Tags or search.
        </div>
      </main>
      </div>
    </template>

    <LibraryFileDetailModal
      :show="showFileModal"
      :file-id="detailFileId"
      :render-color="activeRoot?.thumbnail_color || ''"
      @close="showFileModal = false"
      @deleted="onFileDeleted"
      @favorite-changed="onFavoriteChanged"
      @tags-changed="onFileTagsChanged"
    />

    <LibraryFolderMetadataModal
      :show="showFolderModal"
      :folder-id="folderModalId"
      :folder-name="folderModalName"
      @close="showFolderModal = false"
      @saved="onFolderMetadataSaved"
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

.tag-summary {
  flex-wrap: wrap;
}

.search-group {
  display: flex;
  align-items: stretch;
  gap: 6px;
  /* min-width:0 lets the group shrink below its content width when the header
     runs out of room, so the input flex-shrinks instead of overflowing onto
     the Settings button. */
  flex: 1 1 auto;
  min-width: 0;
  max-width: 340px;
}

.search-scope {
  flex: 0 0 auto;
  width: 120px; /* explicit cap — a bare <select> renders far too wide otherwise */
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1rem;
  height: 41px;
  box-sizing: border-box;
  cursor: pointer;
}

/* Search/filter control — gray, no-shadow focus state (design system) */
.search-scope:focus {
  border-color: var(--color-border);
  box-shadow: none;
  outline: none;
}

.search-input {
  flex: 1 1 150px;
  width: auto;
  min-width: 120px;
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

/* Extra separation so the extension filter and the list/grid toggle read as
   two distinct control groups (not one run of buttons). */
.view-toggle {
  margin-left: 12px;
}

.toolbar-toggles {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* Subtle separator between the view controls (filter + list/grid) and the
   option toggles, for a file-manager toolbar feel. */
.toolbar-divider {
  width: 1px;
  align-self: stretch;
  min-height: 20px;
  background-color: var(--color-border);
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

/* One-line notes preview in search results; the max-width on the inner span
   bounds the column (table stays auto-layout) and drives the ellipsis, while
   the native title tooltip shows the full note on hover. */
.notes-preview {
  display: block;
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text);
  opacity: 0.8;
}

.hit-root {
  color: var(--color-heading);
  font-weight: 600;
}

/* ---- Folder hits (search results) ---- */

.folder-hits {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.folder-hits-label {
  color: var(--color-heading);
  font-weight: 600;
  margin-right: 4px;
}

.folder-hit {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background-color: var(--color-background);
  color: var(--color-text);
  cursor: pointer;
  font-size: 0.85rem;
}

.folder-hit:hover {
  background-color: var(--color-background-mute);
  border-color: var(--color-border-hover, var(--color-border));
}

.folder-hit-name {
  font-weight: 600;
  color: var(--color-heading);
}

.folder-hit-path {
  color: var(--color-text);
  opacity: 0.7;
}

.row-tags {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-left: 6px;
  vertical-align: middle;
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
  position: relative;
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

/* Favorite stars — amber when active, subtle otherwise. */
.row-star {
  background: none;
  border: none;
  padding: 0 4px 0 0;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  color: var(--color-text);
  opacity: 0.55;
  vertical-align: middle;
}

.row-star:hover {
  opacity: 1;
}

.row-star.active {
  color: #f59e0b;
  opacity: 1;
}

.grid-star {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 1;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 1px 6px;
  cursor: pointer;
  font-size: 0.95rem;
  line-height: 1.2;
  color: var(--color-text);
  opacity: 0.7;
}

.grid-star:hover {
  opacity: 1;
}

.grid-star.active {
  color: #f59e0b;
  opacity: 1;
  border-color: #f59e0b;
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
