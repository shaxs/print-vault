/**
 * Unit tests for LibraryView.vue — the two-pane library browser.
 *
 * APIService and vue-router are mocked; the folder tree node renders for
 * real (it only needs the provide/inject contract), while the two modals
 * are stubbed (each has its own spec).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { reactive } from 'vue'
import LibraryView from '@/views/LibraryView.vue'
import LibraryTagBrowser from '@/components/LibraryTagBrowser.vue'

vi.mock('@/services/APIService', () => ({
  default: {
    getLibraryRoots: vi.fn(),
    getLibraryFolderTree: vi.fn(),
    getLibraryFolderContents: vi.fn(),
    searchLibrary: vi.fn(),
    getNewLibraryFiles: vi.fn(),
    rescanLibraryFolder: vi.fn(),
    getLibraryScan: vi.fn(),
    getActiveLibraryScans: vi.fn(),
    getLibraryPreviewSummary: vi.fn(),
    deleteLibraryFolder: vi.fn(),
    getLibraryFileDownloadUrl: vi.fn((id) => `/api/library/files/${id}/download/`),
    getTags: vi.fn(() => Promise.resolve({ data: [] })),
    updateLibraryFile: vi.fn((id, data) => Promise.resolve({ data: { id, ...data } })),
  },
}))
import APIService from '@/services/APIService'

const mockRoute = reactive({ query: {} })
const mockRouter = { replace: vi.fn() }
vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => mockRouter,
}))

const ROOT = { id: 1, name: 'NAS', path: '/mnt/nas', enabled: true, thumbnail_color: '#94a3b8' }
const TREE = [
  { id: 10, name: 'NAS', parent_id: null, status: 'active', root: 1 },
  { id: 11, name: 'widgets', parent_id: 10, status: 'active', root: 1 },
]
const CONTENTS = {
  folder: { id: 10, name: 'NAS', breadcrumbs: [{ id: 10, name: 'NAS' }] },
  subfolders: [{ id: 11, name: 'widgets', parent_id: 10, status: 'active' }],
  files: {
    count: 1,
    next: null,
    previous: null,
    results: [
      {
        id: 5,
        filename: 'part.stl',
        extension: 'stl',
        size_bytes: 2048,
        modified_time: '2026-01-01T00:00:00Z',
        status: 'active',
        thumbnail: null,
      },
    ],
  },
}

function mountView() {
  return mount(LibraryView, {
    global: {
      stubs: { LibraryFileDetailModal: true, LibrarySettingsModal: true },
    },
  })
}

async function mountLoaded() {
  const wrapper = mountView()
  await flushPromises()
  return wrapper
}

// A fresh landing auto-selects no folder. Selecting one navigates via the
// router (route.query.folder); the mocked router is a no-op, so simulate that
// query change directly — the view loads contents off route.query.folder.
async function selectRootFolder() {
  mockRoute.query = { ...mockRoute.query, folder: '10' }
  await flushPromises()
}

describe('LibraryView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mockRoute.query = {}
    APIService.getLibraryRoots.mockResolvedValue({ data: [ROOT] })
    APIService.getLibraryFolderTree.mockResolvedValue({ data: TREE })
    APIService.getLibraryFolderContents.mockResolvedValue({ data: CONTENTS })
    APIService.getActiveLibraryScans.mockResolvedValue({ data: [] })
    APIService.getLibraryPreviewSummary.mockResolvedValue({
      data: { total: 1, rendered: 1, pending: 0, too_large: 0, unrenderable: 0, without_preview: 0 },
    })
    APIService.searchLibrary.mockResolvedValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        // search results carry relative_path + owning-root name (unlike folder-contents rows)
        results: [
          { ...CONTENTS.files.results[0], relative_path: 'widgets/part.stl', root_name: 'NAS' },
        ],
      },
    })
    APIService.getNewLibraryFiles.mockResolvedValue({
      data: { count: 0, next: null, previous: null, results: [] },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('shows the configure empty state when no enabled root exists', async () => {
    APIService.getLibraryRoots.mockResolvedValue({ data: [] })

    const wrapper = await mountLoaded()

    expect(wrapper.text()).toContain('No library root is configured yet.')
    expect(wrapper.text()).toContain('Configure Library')
    expect(APIService.getLibraryFolderTree).not.toHaveBeenCalled()
  })

  it('opens the top root contents on mount but leaves the tree collapsed', async () => {
    const wrapper = await mountLoaded()

    expect(APIService.getLibraryFolderTree).toHaveBeenCalledWith(1)
    // The top root's contents load on landing…
    expect(APIService.getLibraryFolderContents).toHaveBeenCalledWith(
      10,
      expect.objectContaining({ page: 1, ordering: 'filename' }),
    )
    expect(wrapper.text()).toContain('part.stl')
    expect(wrapper.text()).toContain('2.0 KB')
    // …but the tree stays collapsed (no child folders expanded in the left nav).
    expect(wrapper.find('.tree-children').exists()).toBe(false)
  })

  it('persists the view mode to localStorage', async () => {
    // Note: the global test setup replaces localStorage with a no-op mock,
    // so we assert the setItem call rather than reading a value back.
    const setItemSpy = vi.spyOn(localStorage, 'setItem')
    const wrapper = await mountLoaded()
    await selectRootFolder(wrapper)

    const gridBtn = wrapper.findAll('button').find((b) => b.text() === 'Grid')
    await gridBtn.trigger('click')

    expect(setItemSpy).toHaveBeenCalledWith('library-view-mode', 'grid')
    expect(wrapper.find('.file-grid').exists()).toBe(true)
  })

  it('extension filter refetches with the extension param', async () => {
    const wrapper = await mountLoaded()
    await selectRootFolder(wrapper)
    APIService.getLibraryFolderContents.mockClear()

    const btn3mf = wrapper.findAll('button').find((b) => b.text() === '3MF')
    await btn3mf.trigger('click')
    await flushPromises()

    expect(APIService.getLibraryFolderContents).toHaveBeenCalledWith(
      10,
      expect.objectContaining({ extension: '3mf' }),
    )
  })

  it('show deleted checkbox refetches with include_deleted', async () => {
    const wrapper = await mountLoaded()
    await selectRootFolder(wrapper)
    APIService.getLibraryFolderContents.mockClear()

    const showDeleted = wrapper
      .findAll('.browser-toggle')
      .find((l) => l.text().includes('Show deleted'))
    await showDeleted.find('input').setValue(true)
    await flushPromises()

    expect(APIService.getLibraryFolderContents).toHaveBeenCalledWith(
      10,
      expect.objectContaining({ include_deleted: 'true' }),
    )
  })

  it('hides folders whose subtree has no 3D files when "hide empty folders" is on', async () => {
    APIService.getLibraryFolderTree.mockResolvedValue({
      data: [
        { id: 10, name: 'NAS', parent_id: null, status: 'active', root: 1, file_count: 0 },
        { id: 11, name: 'widgets', parent_id: 10, status: 'active', root: 1, file_count: 2 },
        { id: 12, name: 'attic', parent_id: 10, status: 'active', root: 1, file_count: 0 },
      ],
    })
    APIService.getLibraryFolderContents.mockResolvedValue({
      data: {
        folder: { id: 10, name: 'NAS', breadcrumbs: [{ id: 10, name: 'NAS' }] },
        subfolders: [
          { id: 11, name: 'widgets', parent_id: 10, status: 'active' },
          { id: 12, name: 'attic', parent_id: 10, status: 'active' },
        ],
        files: { count: 0, next: null, previous: null, results: [] },
      },
    })

    // The global setup mocks localStorage as a no-op, so spy on setItem.
    const setItemSpy = vi.spyOn(localStorage, 'setItem')
    const wrapper = await mountLoaded()
    // Expand the root so its child folders render in the collapsed-by-default tree.
    await wrapper.find('.tree-caret').trigger('click')
    await flushPromises()
    // Both subfolders show while the toggle is off.
    expect(wrapper.text()).toContain('widgets')
    expect(wrapper.text()).toContain('attic')

    const hideEmpty = wrapper
      .findAll('.browser-toggle')
      .find((l) => l.text().includes('Hide empty folders'))
    await hideEmpty.find('input').setValue(true)
    await flushPromises()

    // 'attic' (no files anywhere in its subtree) is filtered out of both the
    // tree and the content pane; 'widgets' (2 files) stays. Purely client-side.
    expect(wrapper.text()).toContain('widgets')
    expect(wrapper.text()).not.toContain('attic')
    expect(setItemSpy).toHaveBeenCalledWith('library-hide-empty-folders', 'true')
  })

  it('search input debounces and shows results header', async () => {
    const wrapper = await mountLoaded()
    vi.useFakeTimers()

    await wrapper.find('.search-input').setValue('gear')
    expect(APIService.searchLibrary).not.toHaveBeenCalled()

    vi.advanceTimersByTime(350)
    vi.useRealTimers()
    await flushPromises()

    // Multi-root: search spans all enabled roots — no root param is sent.
    expect(APIService.searchLibrary).toHaveBeenCalledWith(expect.objectContaining({ q: 'gear' }))
    expect(APIService.searchLibrary.mock.calls[0][0]).not.toHaveProperty('root')
    // Default scope ('all fields') sends no fields param — the backend default.
    expect(APIService.searchLibrary.mock.calls[0][0]).not.toHaveProperty('fields')
    expect(wrapper.text()).toContain('1 result for')
  })

  it('the Notes search scope re-runs the search with fields=notes and persists', async () => {
    const setItemSpy = vi.spyOn(localStorage, 'setItem')
    const wrapper = await mountLoaded()
    vi.useFakeTimers()

    await wrapper.find('.search-input').setValue('fan')
    vi.advanceTimersByTime(350)
    vi.useRealTimers()
    await flushPromises()

    await wrapper.find('.search-scope').setValue('notes')
    await flushPromises()

    const lastCall = APIService.searchLibrary.mock.calls.at(-1)[0]
    expect(lastCall).toMatchObject({ q: 'fan', fields: 'notes' })
    expect(setItemSpy).toHaveBeenCalledWith('library-search-scope', 'notes')
  })

  it('shows a notes preview column with a full-text tooltip in search results', async () => {
    APIService.searchLibrary.mockResolvedValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            ...CONTENTS.files.results[0],
            relative_path: 'widgets/part.stl',
            root_name: 'NAS',
            notes: 'Fits a 140mm fan for cooling',
          },
        ],
      },
    })
    const wrapper = await mountLoaded()
    vi.useFakeTimers()

    await wrapper.find('.search-input').setValue('part')
    vi.advanceTimersByTime(350)
    vi.useRealTimers()
    await flushPromises()

    const preview = wrapper.find('.notes-preview')
    expect(preview.exists()).toBe(true)
    // Truncation is CSS; the full note is available via the native title tooltip.
    expect(preview.attributes('title')).toBe('Fits a 140mm fan for cooling')
  })

  it('offers a Tags search scope', async () => {
    const wrapper = await mountLoaded()
    const options = wrapper.findAll('.search-scope option').map((o) => o.text())
    expect(options).toContain('Tags')
  })

  it('renders tag badges on search results', async () => {
    APIService.searchLibrary.mockResolvedValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            ...CONTENTS.files.results[0],
            relative_path: 'widgets/part.stl',
            root_name: 'NAS',
            tags: [{ id: 1, name: 'gridfinity', slug: 'gridfinity' }],
          },
        ],
      },
    })
    const wrapper = await mountLoaded()
    vi.useFakeTimers()

    await wrapper.find('.search-input').setValue('part')
    vi.advanceTimersByTime(350)
    vi.useRealTimers()
    await flushPromises()

    const badge = wrapper.find('.row-tags .tag-badge')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('gridfinity')
  })

  it('Show favorites loads the favorites results via the favorites param', async () => {
    APIService.searchLibrary.mockResolvedValue({
      data: {
        count: 1,
        next: null,
        previous: null,
        results: [
          { id: 9, filename: 'fav.stl', extension: 'stl', size_bytes: 1024, status: 'active', thumbnail: null, relative_path: 'fav.stl', root_name: 'NAS', is_favorite: true },
        ],
      },
    })
    const wrapper = await mountLoaded()

    const favToggle = wrapper
      .findAll('.browser-toggle')
      .find((l) => l.text().includes('Show favorites'))
    await favToggle.find('input').setValue(true)
    await flushPromises()

    expect(APIService.searchLibrary).toHaveBeenCalledWith(
      expect.objectContaining({ favorites: 'true' }),
    )
    expect(wrapper.text()).toContain('1 favorite')
    expect(wrapper.text()).toContain('fav.stl')
  })

  it('a row star quick-toggles the favorite via PATCH', async () => {
    const wrapper = await mountLoaded()
    await selectRootFolder()

    const star = wrapper.find('.row-star')
    expect(star.exists()).toBe(true)
    await star.trigger('click')
    await flushPromises()

    expect(APIService.updateLibraryFile).toHaveBeenCalledWith(5, { is_favorite: true })
  })

  it('browse-by-tag loads results via the tags param and shows a summary', async () => {
    APIService.searchLibrary.mockResolvedValue({
      data: {
        count: 2,
        next: null,
        previous: null,
        results: [
          { id: 7, filename: 'a.stl', extension: 'stl', size_bytes: 1024, status: 'active', thumbnail: null, relative_path: 'a.stl', root_name: 'NAS' },
          { id: 8, filename: 'b.stl', extension: 'stl', size_bytes: 1024, status: 'active', thumbnail: null, relative_path: 'b.stl', root_name: 'NAS' },
        ],
      },
    })
    const wrapper = await mountLoaded()

    // Drive the tag browser's selection (its own UI has its own spec).
    const browser = wrapper.findComponent(LibraryTagBrowser)
    await browser.vm.$emit('update:modelValue', [{ id: 1, name: 'toys', slug: 'toys' }])
    await flushPromises()

    expect(APIService.searchLibrary).toHaveBeenCalledWith(
      expect.objectContaining({ tags: 'toys' }),
    )
    expect(wrapper.text()).toContain('2 files tagged')
    expect(wrapper.text()).toContain('a.stl')
  })

  it('New Models toggle loads and shows the new-files results pane', async () => {
    APIService.getNewLibraryFiles.mockResolvedValue({
      data: {
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 7,
            filename: 'new_a.stl',
            extension: 'stl',
            size_bytes: 1024,
            status: 'active',
            thumbnail: null,
            relative_path: 'widgets/new_a.stl',
            root_name: 'NAS',
          },
          {
            id: 8,
            filename: 'new_b.stl',
            extension: 'stl',
            size_bytes: 1024,
            status: 'active',
            thumbnail: null,
            relative_path: 'new_b.stl',
            root_name: 'NAS',
          },
        ],
      },
    })
    const wrapper = await mountLoaded()

    const newToggle = wrapper
      .findAll('.browser-toggle')
      .find((l) => l.text().includes('Show new models'))
    await newToggle.find('input').setValue(true)
    await flushPromises()

    expect(APIService.getNewLibraryFiles).toHaveBeenCalled()
    expect(wrapper.text()).toContain('2 new models since the last scan')
    expect(wrapper.text()).toContain('new_a.stl')
    expect(wrapper.text()).toContain('new_b.stl')
  })

  it('New models empty state renders when nothing is new since the last scan', async () => {
    const wrapper = await mountLoaded()

    const newToggle = wrapper
      .findAll('.browser-toggle')
      .find((l) => l.text().includes('Show new models'))
    await newToggle.find('input').setValue(true)
    await flushPromises()

    expect(wrapper.text()).toContain('No new models since the last scan')
  })

  it('unchecking Show new models returns to folder contents', async () => {
    const wrapper = await mountLoaded()
    await selectRootFolder(wrapper)
    const newToggle = () =>
      wrapper.findAll('.browser-toggle').find((l) => l.text().includes('Show new models'))

    await newToggle().find('input').setValue(true)
    await flushPromises()
    expect(wrapper.text()).toContain('No new models since the last scan')

    await newToggle().find('input').setValue(false)
    await flushPromises()
    // Back to the folder view — the mounted folder's file is shown again.
    expect(wrapper.text()).toContain('part.stl')
  })

  it('clicking a subfolder row navigates via the router query', async () => {
    const wrapper = await mountLoaded()
    await selectRootFolder(wrapper)

    const folderRow = wrapper
      .findAll('tr.row-clickable')
      .find((row) => row.text().includes('widgets'))
    await folderRow.trigger('click')

    expect(mockRouter.replace).toHaveBeenCalledWith({ query: { folder: 11 } })
  })

  it('deleted subfolders do not navigate and offer permanent delete', async () => {
    APIService.getLibraryFolderContents.mockResolvedValue({
      data: {
        ...CONTENTS,
        subfolders: [{ id: 12, name: 'old_stuff', parent_id: 10, status: 'deleted' }],
      },
    })
    const wrapper = await mountLoaded()
    await selectRootFolder(wrapper)

    const folderRow = wrapper
      .findAll('tr.row-clickable')
      .find((row) => row.text().includes('old_stuff'))
    await folderRow.trigger('click')

    expect(mockRouter.replace).not.toHaveBeenCalled()
    expect(folderRow.find('.btn-icon-delete').exists()).toBe(true)
    expect(folderRow.text()).toContain('deleted')
  })

  it('opens the file detail modal when a file row is clicked', async () => {
    const wrapper = await mountLoaded()
    await selectRootFolder(wrapper)

    const fileRow = wrapper
      .findAll('tr.row-clickable')
      .find((row) => row.text().includes('part.stl'))
    await fileRow.trigger('click')

    const modal = wrapper.findComponent({ name: 'LibraryFileDetailModal' })
    expect(modal.attributes('show')).toBeTruthy()
    expect(modal.attributes('fileid')).toBe('5')
  })

  it('re-attaches the progress banner to an active scan on mount', async () => {
    // A scan already running when the page (re)loads is surfaced via
    // ?active=true so a refresh doesn't lose the in-flight job.
    APIService.getActiveLibraryScans.mockResolvedValue({
      data: [
        {
          id: 99,
          root_name: 'NAS',
          kind: 'scan',
          status: 'running',
          files_seen: 42,
          progress_percent: 30,
        },
      ],
    })

    const wrapper = await mountLoaded()

    expect(wrapper.find('.job-banner').exists()).toBe(true)
    expect(wrapper.text()).toContain('Scanning NAS…')
    expect(wrapper.text()).toContain('42 files found, 30% processed')
  })

  it('renders a top-level tree node per enabled root (merged multi-root tree)', async () => {
    APIService.getLibraryRoots.mockResolvedValue({
      data: [
        ROOT,
        { id: 2, name: 'SSD', path: '/mnt/ssd', enabled: true, thumbnail_color: '#94a3b8' },
      ],
    })
    APIService.getLibraryFolderTree.mockImplementation((rootId) =>
      Promise.resolve({
        data:
          rootId === 1
            ? [{ id: 10, name: 'NAS', parent_id: null, status: 'active', root: 1 }]
            : [{ id: 20, name: 'SSD', parent_id: null, status: 'active', root: 2 }],
      }),
    )
    APIService.getLibraryFolderContents.mockResolvedValue({
      data: {
        folder: { id: 10, name: 'NAS', breadcrumbs: [{ id: 10, name: 'NAS' }] },
        subfolders: [],
        files: { count: 0, next: null, previous: null, results: [] },
      },
    })

    const wrapper = await mountLoaded()

    expect(APIService.getLibraryFolderTree).toHaveBeenCalledWith(1)
    expect(APIService.getLibraryFolderTree).toHaveBeenCalledWith(2)
    const treeText = wrapper.find('.tree-pane').text()
    expect(treeText).toContain('NAS')
    expect(treeText).toContain('SSD')
  })

  it('shows the preview-coverage note when files lack previews', async () => {
    APIService.getLibraryPreviewSummary.mockResolvedValue({
      data: {
        total: 100,
        rendered: 15,
        pending: 0,
        too_large: 20,
        unrenderable: 65,
        without_preview: 85,
      },
    })

    const wrapper = await mountLoaded()

    const note = wrapper.find('.preview-summary-note')
    expect(note.exists()).toBe(true)
    expect(note.text()).toContain('85 files without a preview')
    expect(note.text()).toContain('20 too large')
    expect(note.text()).toContain('65 unreadable')
  })
})
