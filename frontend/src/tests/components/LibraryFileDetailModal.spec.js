/**
 * Unit tests for LibraryFileDetailModal.vue
 *
 * APIService is mocked; ModelViewer is stubbed (WebGL doesn't exist in the
 * test DOM and the viewer has its own spec). BaseModal renders for real.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LibraryFileDetailModal from '@/components/LibraryFileDetailModal.vue'

vi.mock('@/services/APIService', () => ({
  default: {
    getLibraryFile: vi.fn(),
    getLibraryFileDownloadUrl: vi.fn((id) => `/api/library/files/${id}/download/`),
    updateLibraryFile: vi.fn((id, data) => Promise.resolve({ data: { id, ...data } })),
    deleteLibraryFile: vi.fn(() => Promise.resolve({})),
  },
}))
import APIService from '@/services/APIService'

const FILE = {
  id: 5,
  filename: 'part.stl',
  relative_path: 'widgets/part.stl',
  extension: 'stl',
  size_bytes: 2048,
  modified_time: '2026-01-01T00:00:00Z',
  status: 'active',
  sha256_hash: 'a'.repeat(64),
  thumbnail: null,
  bounding_box_x: 10,
  bounding_box_y: 20,
  bounding_box_z: 30,
  embedded_metadata: {},
  notes: '',
  tags: [],
  is_favorite: false,
}

// Minimal stand-in for TagInput: exposes its modelValue and lets a test emit a
// new selection, so we can verify the modal persists tag changes.
const TagInputStub = {
  name: 'TagInput',
  props: { modelValue: { type: Array, default: () => [] } },
  emits: ['update:modelValue'],
  template: '<div class="tag-input-stub"></div>',
}

describe('LibraryFileDetailModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    APIService.getLibraryFile.mockResolvedValue({ data: FILE })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  async function open(fileOverrides = {}) {
    APIService.getLibraryFile.mockResolvedValue({ data: { ...FILE, ...fileOverrides } })
    const wrapper = mount(LibraryFileDetailModal, {
      props: { show: false, fileId: 5 },
      // TagInput wraps vue-multiselect + fetches tags on mount; stub it (like
      // ModelViewer) and drive its update:modelValue directly.
      global: { stubs: { ModelViewer: true, TagInput: TagInputStub } },
    })
    await wrapper.setProps({ show: true })
    await flushPromises()
    return wrapper
  }

  it('fetches and displays file details when opened', async () => {
    const wrapper = await open()

    expect(APIService.getLibraryFile).toHaveBeenCalledWith(5)
    expect(wrapper.text()).toContain('part.stl')
    expect(wrapper.text()).toContain('widgets/part.stl')
    expect(wrapper.text()).toContain('2.0 KB')
    expect(wrapper.text()).toContain('10.0 × 20.0 × 30.0 mm')
  })

  it('hides slicer metadata section when embedded_metadata is empty', async () => {
    const wrapper = await open()

    expect(wrapper.text()).not.toContain('Slicer Metadata')
  })

  it('explains a missing preview: too large', async () => {
    const wrapper = await open({ thumbnail: null, thumbnail_status: 'too_large' })

    expect(wrapper.find('.preview-notice').exists()).toBe(true)
    expect(wrapper.text()).toContain('exceeds the preview-render size limit')
  })

  it('explains a missing preview: unrenderable', async () => {
    const wrapper = await open({ thumbnail: null, thumbnail_status: 'unrenderable' })

    expect(wrapper.text()).toContain('mesh could not be read')
  })

  it('shows no preview notice when the thumbnail rendered', async () => {
    const wrapper = await open({ thumbnail_status: 'rendered' })

    expect(wrapper.find('.preview-notice').exists()).toBe(false)
  })

  it('shows no preview notice for a file that has a thumbnail (stale pending status)', async () => {
    const wrapper = await open({
      thumbnail: '/media/library_file_thumbnails/5_thumb.png',
      thumbnail_status: 'pending',
    })

    expect(wrapper.find('.preview-notice').exists()).toBe(false)
  })

  it('shows slicer metadata for 3mf files', async () => {
    const wrapper = await open({
      extension: '3mf',
      embedded_metadata: {
        slicer_name: 'OrcaSlicer',
        slicer_version: '2.1.1',
        printer_profile: 'P1S',
      },
    })

    expect(wrapper.text()).toContain('Slicer Metadata')
    expect(wrapper.text()).toContain('OrcaSlicer 2.1.1')
    expect(wrapper.text()).toContain('P1S')
  })

  it('background toggle persists to localStorage', async () => {
    // Note: the global test setup replaces localStorage with a no-op mock,
    // so we assert the setItem call rather than reading a value back.
    const setItemSpy = vi.spyOn(localStorage, 'setItem')
    const wrapper = await open()
    const toggleBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Switch to Light Background'))

    await toggleBtn.trigger('click')

    expect(setItemSpy).toHaveBeenCalledWith('library-viewer-background', 'light')
    expect(toggleBtn.text()).toContain('Switch to Dark Background')
  })

  it('has no permanent delete button for active files', async () => {
    const wrapper = await open()

    const deleteBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Delete Permanently'))
    expect(deleteBtn).toBeFalsy()
  })

  it('permanent delete for deleted files emits deleted', async () => {
    const wrapper = await open({ status: 'deleted' })
    vi.spyOn(window, 'confirm').mockReturnValue(true)

    const deleteBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Delete Permanently'))
    await deleteBtn.trigger('click')
    await flushPromises()

    expect(APIService.deleteLibraryFile).toHaveBeenCalledWith(5)
    expect(wrapper.emitted('deleted')).toBeTruthy()
  })

  it('declining the confirmation aborts the delete', async () => {
    const wrapper = await open({ status: 'deleted' })
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    const deleteBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('Delete Permanently'))
    await deleteBtn.trigger('click')
    await flushPromises()

    expect(APIService.deleteLibraryFile).not.toHaveBeenCalled()
  })

  // ---- Notes ----

  const notesTextarea = (wrapper) => wrapper.find('.notes-input')
  const saveNotesBtn = (wrapper) =>
    wrapper.findAll('button').find((b) => b.text().includes('Save Notes'))

  it('shows existing notes in the textarea', async () => {
    const wrapper = await open({ notes: 'Uses a 140mm fan' })

    expect(notesTextarea(wrapper).element.value).toBe('Uses a 140mm fan')
  })

  it('Save Notes is disabled until the notes are edited', async () => {
    const wrapper = await open({ notes: 'original' })

    expect(saveNotesBtn(wrapper).attributes('disabled')).toBeDefined()

    await notesTextarea(wrapper).setValue('edited')

    expect(saveNotesBtn(wrapper).attributes('disabled')).toBeUndefined()
  })

  it('saving notes PATCHes the file and shows a saved indicator', async () => {
    const wrapper = await open({ notes: '' })
    await notesTextarea(wrapper).setValue('Uses a 140mm fan')

    await saveNotesBtn(wrapper).trigger('click')
    await flushPromises()

    expect(APIService.updateLibraryFile).toHaveBeenCalledWith(5, { notes: 'Uses a 140mm fan' })
    expect(wrapper.find('.notes-saved').exists()).toBe(true)
    // Button returns to disabled once the draft matches the saved value.
    expect(saveNotesBtn(wrapper).attributes('disabled')).toBeDefined()
  })

  // ---- Fullscreen viewer ----

  const fullscreenBtn = (wrapper) =>
    wrapper.findAll('button').find((b) => b.text().trim() === 'Fullscreen')

  it('fullscreen toggle expands the viewer and dispatches a resize', async () => {
    const wrapper = await open()
    const dispatchSpy = vi.spyOn(window, 'dispatchEvent')

    expect(wrapper.find('.viewer-wrap.is-fullscreen').exists()).toBe(false)

    await fullscreenBtn(wrapper).trigger('click')
    await flushPromises()

    expect(wrapper.find('.viewer-wrap.is-fullscreen').exists()).toBe(true)
    // ModelViewer refits via the window resize handler (no remount).
    expect(dispatchSpy.mock.calls.some(([e]) => e.type === 'resize')).toBe(true)

    const exitBtn = wrapper.findAll('button').find((b) => b.text().includes('Exit Fullscreen'))
    await exitBtn.trigger('click')

    expect(wrapper.find('.viewer-wrap.is-fullscreen').exists()).toBe(false)
  })

  // ---- Tags ----

  it('passes the file tags to the TagInput', async () => {
    const wrapper = await open({ tags: [{ id: 1, name: 'toys', slug: 'toys' }] })

    const tagInput = wrapper.findComponent(TagInputStub)
    expect(tagInput.props('modelValue')).toEqual([{ id: 1, name: 'toys', slug: 'toys' }])
  })

  it('persists tag changes immediately via PATCH tag_ids', async () => {
    const newTags = [
      { id: 1, name: 'toys', slug: 'toys' },
      { id: 2, name: 'gridfinity', slug: 'gridfinity' },
    ]
    APIService.updateLibraryFile.mockResolvedValue({ data: { id: 5, notes: '', tags: newTags } })
    const wrapper = await open()

    await wrapper.findComponent(TagInputStub).vm.$emit('update:modelValue', newTags)
    await flushPromises()

    expect(APIService.updateLibraryFile).toHaveBeenCalledWith(5, { tag_ids: [1, 2] })
  })

  // ---- Favorite ----

  const starToggle = (wrapper) => wrapper.find('.star-toggle')

  it('toggling favorite PATCHes is_favorite and emits favorite-changed', async () => {
    APIService.updateLibraryFile.mockResolvedValue({ data: { id: 5, is_favorite: true } })
    const wrapper = await open({ is_favorite: false })

    expect(starToggle(wrapper).text()).toContain('Favorite')
    expect(starToggle(wrapper).classes()).not.toContain('active')

    await starToggle(wrapper).trigger('click')
    await flushPromises()

    expect(APIService.updateLibraryFile).toHaveBeenCalledWith(5, { is_favorite: true })
    expect(starToggle(wrapper).classes()).toContain('active')
    expect(starToggle(wrapper).text()).toContain('Favorited')
    expect(wrapper.emitted('favorite-changed').at(-1)[0]).toEqual({ id: 5, is_favorite: true })
  })

  it('rolls back the favorite on a failed save', async () => {
    APIService.updateLibraryFile.mockRejectedValue(new Error('nope'))
    const wrapper = await open({ is_favorite: false })

    await starToggle(wrapper).trigger('click')
    await flushPromises()

    expect(starToggle(wrapper).classes()).not.toContain('active')
  })
})
