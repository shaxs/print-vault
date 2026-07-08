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

vi.mock('@/services/APIService', () => ({
  default: {
    getLibraryRoots: vi.fn(),
    getLibraryFolderTree: vi.fn(),
    getLibraryFolderContents: vi.fn(),
    searchLibrary: vi.fn(),
    rescanLibraryFolder: vi.fn(),
    getLibraryScan: vi.fn(),
    getActiveLibraryScans: vi.fn(),
    getLibraryPreviewSummary: vi.fn(),
    deleteLibraryFolder: vi.fn(),
    getLibraryFileDownloadUrl: vi.fn((id) => `/api/library/files/${id}/download/`),
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

  it('loads tree and root folder contents on mount', async () => {
    const wrapper = await mountLoaded()

    expect(APIService.getLibraryFolderTree).toHaveBeenCalledWith(1)
    expect(APIService.getLibraryFolderContents).toHaveBeenCalledWith(
      10,
      expect.objectContaining({ page: 1, ordering: 'filename' }),
    )
    expect(wrapper.text()).toContain('widgets')
    expect(wrapper.text()).toContain('part.stl')
    expect(wrapper.text()).toContain('2.0 KB')
  })

  it('persists the view mode to localStorage', async () => {
    // Note: the global test setup replaces localStorage with a no-op mock,
    // so we assert the setItem call rather than reading a value back.
    const setItemSpy = vi.spyOn(localStorage, 'setItem')
    const wrapper = await mountLoaded()

    const gridBtn = wrapper.findAll('button').find((b) => b.text() === 'Grid')
    await gridBtn.trigger('click')

    expect(setItemSpy).toHaveBeenCalledWith('library-view-mode', 'grid')
    expect(wrapper.find('.file-grid').exists()).toBe(true)
  })

  it('extension filter refetches with the extension param', async () => {
    const wrapper = await mountLoaded()
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
    APIService.getLibraryFolderContents.mockClear()

    await wrapper.find('.show-deleted-toggle input').setValue(true)
    await flushPromises()

    expect(APIService.getLibraryFolderContents).toHaveBeenCalledWith(
      10,
      expect.objectContaining({ include_deleted: 'true' }),
    )
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
    expect(wrapper.text()).toContain('1 result for')
  })

  it('clicking a subfolder row navigates via the router query', async () => {
    const wrapper = await mountLoaded()

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
    expect(wrapper.text()).toContain('42 files seen, 30% processed')
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
