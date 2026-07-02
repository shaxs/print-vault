import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTable from '@/components/DataTable.vue'

/**
 * Tests for DataTable.vue — the primary list/table component used across all list views.
 *
 * Covers:
 * - Header rendering based on visibleColumns
 * - Row rendering and data display
 * - Empty state display
 * - row-click event emission
 * - Photo column thumbnail rendering
 * - Custom slot rendering
 */

const makeHeaders = () => [
  { text: 'Name', value: 'name' },
  { text: 'Status', value: 'status' },
  { text: 'Photo', value: 'photo' },
]

const makeItems = () => [
  { id: 1, name: 'Alpha Item', status: 'Active', photo: 'http://example.com/a.jpg' },
  { id: 2, name: 'Beta Item', status: 'Sold', photo: null },
]

describe('DataTable', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(DataTable, {
      props: {
        headers: makeHeaders(),
        items: makeItems(),
        visibleColumns: ['name', 'status', 'photo'],
      },
      attachTo: document.body,
    })
  })

  // ──────────────────────────────────────────────────────────────────────────
  // HEADER RENDERING
  // ──────────────────────────────────────────────────────────────────────────

  it('renders all visible column headers', () => {
    const ths = wrapper.findAll('thead th')
    expect(ths).toHaveLength(3)
    expect(ths[0].text()).toBe('Name')
    expect(ths[1].text()).toBe('Status')
    expect(ths[2].text()).toBe('Photo')
  })

  it('only renders headers in visibleColumns order', async () => {
    await wrapper.setProps({ visibleColumns: ['status', 'name'] })
    const ths = wrapper.findAll('thead th')
    expect(ths).toHaveLength(2)
    expect(ths[0].text()).toBe('Status')
    expect(ths[1].text()).toBe('Name')
  })

  it('renders no headers when visibleColumns is empty', async () => {
    await wrapper.setProps({ visibleColumns: [] })
    const ths = wrapper.findAll('thead th')
    expect(ths).toHaveLength(0)
  })

  it('ignores visibleColumns values not in headers', async () => {
    await wrapper.setProps({ visibleColumns: ['name', 'nonexistent'] })
    const ths = wrapper.findAll('thead th')
    // Only 'name' should render — 'nonexistent' is skipped
    expect(ths).toHaveLength(1)
    expect(ths[0].text()).toBe('Name')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // ROW RENDERING
  // ──────────────────────────────────────────────────────────────────────────

  it('renders one row per item', () => {
    const rows = wrapper.findAll('tbody tr.clickable-row')
    expect(rows).toHaveLength(2)
  })

  it('renders cell text from item fields', () => {
    const firstRow = wrapper.findAll('tbody tr.clickable-row')[0]
    const cells = firstRow.findAll('td')
    // photo column is handled separately (img or nothing), check name + status
    expect(cells[0].text()).toBe('Alpha Item')
    expect(cells[1].text()).toBe('Active')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // EMPTY STATE
  // ──────────────────────────────────────────────────────────────────────────

  it('shows "No items found." row when items is empty', async () => {
    await wrapper.setProps({ items: [] })
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toBe('No items found.')
  })

  it('does not show empty state row when items exist', () => {
    const emptyRow = wrapper.find('.no-items')
    expect(emptyRow.exists()).toBe(false)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // ROW-CLICK EVENT
  // ──────────────────────────────────────────────────────────────────────────

  it('emits row-click with item when row is clicked', async () => {
    const firstRow = wrapper.findAll('tbody tr.clickable-row')[0]
    await firstRow.trigger('click')
    expect(wrapper.emitted('row-click')).toBeTruthy()
    expect(wrapper.emitted('row-click')[0][0]).toEqual(makeItems()[0])
  })

  it('emits row-click with correct item when second row is clicked', async () => {
    const rows = wrapper.findAll('tbody tr.clickable-row')
    await rows[1].trigger('click')
    expect(wrapper.emitted('row-click')[0][0]).toEqual(makeItems()[1])
  })

  // ──────────────────────────────────────────────────────────────────────────
  // PHOTO COLUMN
  // ──────────────────────────────────────────────────────────────────────────

  it('renders img thumbnail for item with photo in photo column', () => {
    const thumbnails = wrapper.findAll('img.table-thumbnail')
    expect(thumbnails).toHaveLength(1)
    expect(thumbnails[0].attributes('src')).toBe('http://example.com/a.jpg')
  })

  it('renders nothing for photo column when item has no photo', () => {
    // Second item has null photo — should render no img
    const rows = wrapper.findAll('tbody tr.clickable-row')
    const secondRowPhotoCell = rows[1].findAll('td')[2]
    expect(secondRowPhotoCell.find('img').exists()).toBe(false)
  })

  it('does not show photo modal by default', () => {
    // Photo modal should be hidden initially
    const modal = wrapper.find('.photo-modal-overlay, .lightbox')
    // The modal v-if keeps it out of DOM when not visible
    expect(modal.exists()).toBe(false)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // DATA-LABEL ATTRIBUTE (responsive)
  // ──────────────────────────────────────────────────────────────────────────

  it('sets data-label attribute on each cell matching the column header text', () => {
    const firstRow = wrapper.findAll('tbody tr.clickable-row')[0]
    const cells = firstRow.findAll('td')
    expect(cells[0].attributes('data-label')).toBe('Name')
    expect(cells[1].attributes('data-label')).toBe('Status')
    expect(cells[2].attributes('data-label')).toBe('Photo')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // SLOT RENDERING
  // ──────────────────────────────────────────────────────────────────────────

  it('renders default slot content (item field value) when no named slot provided', () => {
    const firstRow = wrapper.findAll('tbody tr.clickable-row')[0]
    const nameCell = firstRow.findAll('td')[0]
    expect(nameCell.text()).toBe('Alpha Item')
  })

  it('renders custom slot content when named slot provided', () => {
    const customWrapper = mount(DataTable, {
      props: {
        headers: [{ text: 'Name', value: 'name' }],
        items: [{ id: 1, name: 'Custom Item' }],
        visibleColumns: ['name'],
      },
      slots: {
        'cell-name': '<span class="custom-cell">CUSTOM</span>',
      },
    })
    expect(customWrapper.find('.custom-cell').text()).toBe('CUSTOM')
  })
})
