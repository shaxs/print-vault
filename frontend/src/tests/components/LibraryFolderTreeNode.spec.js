/**
 * Unit tests for LibraryFolderTreeNode.vue — recursive tree node driven
 * entirely by the injected `libraryTree` contract from LibraryView.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { reactive } from 'vue'
import LibraryFolderTreeNode from '@/components/LibraryFolderTreeNode.vue'

const FOLDERS = {
  10: { id: 10, name: 'NAS', parent_id: null },
  11: { id: 11, name: 'widgets', parent_id: 10 },
  12: { id: 12, name: 'gears', parent_id: 11 },
}

describe('LibraryFolderTreeNode', () => {
  let tree

  beforeEach(() => {
    tree = reactive({
      childrenOf: (id) => Object.values(FOLDERS).filter((f) => f.parent_id === id),
      isExpanded: vi.fn(() => false),
      selectedId: null,
      select: vi.fn(),
      toggle: vi.fn(),
    })
  })

  function mountNode(folder) {
    return mount(LibraryFolderTreeNode, {
      props: { folder },
      global: { provide: { libraryTree: tree } },
    })
  }

  it('renders the folder name', () => {
    const wrapper = mountNode(FOLDERS[10])
    expect(wrapper.text()).toContain('NAS')
  })

  it('shows a caret only for folders with children', () => {
    expect(mountNode(FOLDERS[10]).find('.tree-caret').exists()).toBe(true)
    expect(mountNode(FOLDERS[12]).find('.tree-caret').exists()).toBe(false)
  })

  it('clicking the row selects the folder', async () => {
    const wrapper = mountNode(FOLDERS[10])

    await wrapper.find('.tree-row').trigger('click')

    expect(tree.select).toHaveBeenCalledWith(10)
  })

  it('clicking the caret toggles without selecting', async () => {
    const wrapper = mountNode(FOLDERS[10])

    await wrapper.find('.tree-caret').trigger('click')

    expect(tree.toggle).toHaveBeenCalledWith(10)
    expect(tree.select).not.toHaveBeenCalled()
  })

  it('renders children recursively when expanded', () => {
    tree.isExpanded = () => true

    const wrapper = mountNode(FOLDERS[10])

    expect(wrapper.text()).toContain('widgets')
    expect(wrapper.text()).toContain('gears')
  })

  it('collapsed nodes hide their children', () => {
    const wrapper = mountNode(FOLDERS[10])

    expect(wrapper.text()).not.toContain('widgets')
  })

  it('marks the selected folder', () => {
    tree.selectedId = 10

    const wrapper = mountNode(FOLDERS[10])

    expect(wrapper.find('.tree-row').classes()).toContain('tree-row-selected')
  })
})
