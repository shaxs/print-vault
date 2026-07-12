/**
 * Unit tests for LibraryFolderMetadataModal.vue
 *
 * APIService is mocked; TagInput is stubbed (it wraps vue-multiselect + fetches
 * on mount). BaseModal renders for real so the footer buttons exist.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LibraryFolderMetadataModal from '@/components/LibraryFolderMetadataModal.vue'

vi.mock('@/services/APIService', () => ({
  default: {
    getLibraryFolderMetadata: vi.fn(),
    updateLibraryFolderMetadata: vi.fn((id, data) =>
      Promise.resolve({ data: { id, ...data, affected_files: 3, affected_folders: 1 } }),
    ),
    resyncLibraryFolder: vi.fn(() =>
      Promise.resolve({ data: { affected_files: 5, affected_folders: 2 } }),
    ),
  },
}))
import APIService from '@/services/APIService'

const META = {
  id: 7,
  name: '10 inch rack',
  relative_path: 'STL/10 inch rack',
  notes: 'racks',
  tags: [{ id: 1, name: 'rack', slug: 'rack' }],
}

const TagInputStub = {
  name: 'TagInput',
  props: { modelValue: { type: Array, default: () => [] } },
  emits: ['update:modelValue'],
  template: '<div class="tag-input-stub"></div>',
}

describe('LibraryFolderMetadataModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    APIService.getLibraryFolderMetadata.mockResolvedValue({ data: META })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  async function open(overrides = {}) {
    APIService.getLibraryFolderMetadata.mockResolvedValue({ data: { ...META, ...overrides } })
    const wrapper = mount(LibraryFolderMetadataModal, {
      props: { show: false, folderId: 7, folderName: '10 inch rack' },
      global: { stubs: { TagInput: TagInputStub } },
    })
    await wrapper.setProps({ show: true })
    await flushPromises()
    return wrapper
  }

  const tagInput = (wrapper) => wrapper.findComponent(TagInputStub)

  it('loads folder tags + notes when opened', async () => {
    const wrapper = await open()

    expect(APIService.getLibraryFolderMetadata).toHaveBeenCalledWith(7)
    expect(tagInput(wrapper).props('modelValue')).toEqual([{ id: 1, name: 'rack', slug: 'rack' }])
    expect(wrapper.find('.notes-input').element.value).toBe('racks')
  })

  it('saves tag_ids + notes and emits saved', async () => {
    const wrapper = await open()

    await tagInput(wrapper).vm.$emit('update:modelValue', [
      { id: 1, name: 'rack', slug: 'rack' },
      { id: 2, name: 'mmu', slug: 'mmu' },
    ])
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()

    expect(APIService.updateLibraryFolderMetadata).toHaveBeenCalledWith(7, {
      tag_ids: [1, 2],
      notes: 'racks',
    })
    expect(wrapper.emitted('saved').at(-1)[0].affected_files).toBe(3)
  })

  it('shows a removal warning and confirms before removing a tag', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = await open()

    await tagInput(wrapper).vm.$emit('update:modelValue', []) // dropped the only tag
    await flushPromises()
    expect(wrapper.find('.removal-warning').exists()).toBe(true)

    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalled()
    expect(APIService.updateLibraryFolderMetadata).toHaveBeenCalledWith(7, { tag_ids: [], notes: 'racks' })
  })

  it('aborts the save when a removal is not confirmed', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = await open()

    await tagInput(wrapper).vm.$emit('update:modelValue', [])
    await flushPromises()
    await wrapper.find('.btn-primary').trigger('click')
    await flushPromises()

    expect(APIService.updateLibraryFolderMetadata).not.toHaveBeenCalled()
  })

  it('re-apply persists then resyncs the subtree', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = await open()

    await wrapper.find('.btn-outline').trigger('click')
    await flushPromises()

    expect(APIService.updateLibraryFolderMetadata).toHaveBeenCalled()
    expect(APIService.resyncLibraryFolder).toHaveBeenCalledWith(7)
    expect(wrapper.emitted('saved')).toBeTruthy()
  })
})
