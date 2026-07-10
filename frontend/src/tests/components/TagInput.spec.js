/**
 * Unit tests for TagInput.vue — the vue-multiselect wrapper is stubbed; we
 * verify the load-on-mount and create-on-tag logic and the v-model contract.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import TagInput from '@/components/TagInput.vue'

vi.mock('@/services/APIService', () => ({
  default: {
    getTags: vi.fn(() => Promise.resolve({ data: [{ id: 1, name: 'toys', slug: 'toys' }] })),
    createTag: vi.fn((name) =>
      Promise.resolve({ data: { id: 2, name, slug: name.toLowerCase() } }),
    ),
  },
}))
import APIService from '@/services/APIService'

// Replace vue-multiselect (and its CSS side-effect import) with a stand-in we
// can drive; the real component is a heavy third-party widget.
vi.mock('vue-multiselect', () => ({
  default: {
    name: 'Multiselect',
    props: ['modelValue', 'options'],
    emits: ['tag', 'update:modelValue'],
    template: '<div class="multiselect-stub"></div>',
  },
}))
vi.mock('vue-multiselect/dist/vue-multiselect.css', () => ({}))

const findMultiselect = (wrapper) => wrapper.findComponent({ name: 'Multiselect' })

function mountInput(modelValue = []) {
  return mount(TagInput, { props: { modelValue } })
}

describe('TagInput', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads existing tags into the options on mount', async () => {
    const wrapper = mountInput()
    await flushPromises()

    expect(APIService.getTags).toHaveBeenCalled()
    expect(findMultiselect(wrapper).props('options')).toEqual([
      { id: 1, name: 'toys', slug: 'toys' },
    ])
  })

  it('creates a tag on @tag and appends it to the selection', async () => {
    const wrapper = mountInput([])
    await flushPromises()

    await findMultiselect(wrapper).vm.$emit('tag', 'Gridfinity')
    await flushPromises()

    expect(APIService.createTag).toHaveBeenCalledWith('Gridfinity')
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted.at(-1)[0]).toEqual([{ id: 2, name: 'Gridfinity', slug: 'gridfinity' }])
  })

  it('does not duplicate a tag that is already selected', async () => {
    const existing = { id: 2, name: 'Gridfinity', slug: 'gridfinity' }
    const wrapper = mountInput([existing])
    await flushPromises()

    await findMultiselect(wrapper).vm.$emit('tag', 'Gridfinity')
    await flushPromises()

    // createTag returns the same id (2); it's already selected, so no re-emit.
    expect(wrapper.emitted('update:modelValue')).toBeFalsy()
  })
})
