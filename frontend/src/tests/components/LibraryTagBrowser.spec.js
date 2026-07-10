/**
 * Unit tests for LibraryTagBrowser.vue — the left-pane "Browse by Tags" control.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LibraryTagBrowser from '@/components/LibraryTagBrowser.vue'

const TAGS = [
  { id: 1, name: 'toys', slug: 'toys', usage_count: 5 },
  { id: 2, name: 'tools', slug: 'tools', usage_count: 2 },
  { id: 3, name: 'gridfinity', slug: 'gridfinity', usage_count: 1 },
]

vi.mock('@/services/APIService', () => ({
  default: { getTags: vi.fn(() => Promise.resolve({ data: TAGS })) },
}))
import APIService from '@/services/APIService'

function mountBrowser(modelValue = []) {
  return mount(LibraryTagBrowser, { props: { modelValue } })
}

describe('LibraryTagBrowser', () => {
  beforeEach(() => vi.clearAllMocks())

  it('loads in-use tags on mount and hides the panel until expanded', async () => {
    const wrapper = mountBrowser()
    await flushPromises()

    // Only tags applied to a file (in_use) are browseable.
    expect(APIService.getTags).toHaveBeenCalledWith({ in_use: 'true' })
    expect(wrapper.find('.tag-panel').exists()).toBe(false)
  })

  it('shows each tag’s usage count on its chip', async () => {
    const wrapper = mountBrowser()
    await flushPromises()
    await wrapper.find('.tag-browse-toggle').trigger('click')

    const counts = wrapper.findAll('.tag-count').map((c) => c.text())
    expect(counts).toEqual(['5', '2', '1'])
  })

  it('expands the panel and lists tags as chips', async () => {
    const wrapper = mountBrowser()
    await flushPromises()

    await wrapper.find('.tag-browse-toggle').trigger('click')

    expect(wrapper.find('.tag-panel').exists()).toBe(true)
    expect(wrapper.findAll('.tag-chip')).toHaveLength(3)
  })

  it('filters the chip list by the filter box', async () => {
    const wrapper = mountBrowser()
    await flushPromises()
    await wrapper.find('.tag-browse-toggle').trigger('click')

    await wrapper.find('.tag-filter-input').setValue('too')

    const chips = wrapper.findAll('.tag-chip')
    expect(chips).toHaveLength(1)
    expect(chips[0].text()).toContain('tools')
  })

  it('emits a tag when an unselected chip is clicked', async () => {
    const wrapper = mountBrowser()
    await flushPromises()
    await wrapper.find('.tag-browse-toggle').trigger('click')

    await wrapper.findAll('.tag-chip')[0].trigger('click') // toys

    expect(wrapper.emitted('update:modelValue').at(-1)[0]).toEqual([TAGS[0]])
  })

  it('deselects an already-selected chip', async () => {
    const wrapper = mountBrowser([TAGS[0]])
    await flushPromises()
    await wrapper.find('.tag-browse-toggle').trigger('click')

    const toysChip = wrapper.findAll('.tag-chip').find((c) => c.text().includes('toys'))
    expect(toysChip.classes()).toContain('selected')

    await toysChip.trigger('click')

    expect(wrapper.emitted('update:modelValue').at(-1)[0]).toEqual([])
  })

  it('shows the All/Any match toggle only with 2+ tags and emits the mode', async () => {
    const one = mountBrowser([TAGS[0]])
    await flushPromises()
    await one.find('.tag-browse-toggle').trigger('click')
    expect(one.find('.match-toggle').exists()).toBe(false)

    const two = mountBrowser([TAGS[0], TAGS[1]])
    await flushPromises()
    await two.find('.tag-browse-toggle').trigger('click')
    expect(two.find('.match-toggle').exists()).toBe(true)

    const anyBtn = two.findAll('.match-toggle button').find((b) => b.text() === 'Any')
    await anyBtn.trigger('click')
    expect(two.emitted('update:matchMode').at(-1)[0]).toBe('any')
  })

  it('shows a selection count on the toggle button and clears via the panel', async () => {
    const wrapper = mountBrowser([TAGS[0], TAGS[1]])
    await flushPromises()

    expect(wrapper.find('.count-badge').text()).toBe('2')

    await wrapper.find('.tag-browse-toggle').trigger('click')
    await wrapper.find('.link-button').trigger('click') // Clear selection

    expect(wrapper.emitted('update:modelValue').at(-1)[0]).toEqual([])
  })
})
