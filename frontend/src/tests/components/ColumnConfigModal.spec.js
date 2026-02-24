import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ColumnConfigModal from '@/components/ColumnConfigModal.vue'

/**
 * Tests for ColumnConfigModal.vue — the column visibility/ordering modal used
 * across all table list views.
 *
 * Covers:
 * - Initial rendering of visible and hidden columns
 * - Move column from hidden → visible
 * - Move column from visible → hidden
 * - Move column up/down in visible list
 * - Disabled state for up/down buttons at boundaries
 * - Save emits 'save' with updated visible columns and 'close'
 * - Cancel emits 'close'
 * - Overlay click emits 'close'
 */

const ALL_COLUMNS = [
  { text: 'Name', value: 'name' },
  { text: 'Status', value: 'status' },
  { text: 'Photo', value: 'photo' },
  { text: 'Notes', value: 'notes' },
]

describe('ColumnConfigModal', () => {
  const mountModal = (visibleColumns = ['name', 'status']) =>
    mount(ColumnConfigModal, {
      props: {
        allColumns: ALL_COLUMNS,
        visibleColumns,
      },
      attachTo: document.body,
    })

  // ──────────────────────────────────────────────────────────────────────────
  // INITIAL RENDERING
  // ──────────────────────────────────────────────────────────────────────────

  it('renders visible column items', () => {
    const wrapper = mountModal(['name', 'status'])
    const visibleSection = wrapper.findAll('.column-list')[0]
    expect(visibleSection.text()).toContain('Name')
    expect(visibleSection.text()).toContain('Status')
  })

  it('renders hidden column items', () => {
    const wrapper = mountModal(['name', 'status'])
    const hiddenSection = wrapper.findAll('.column-list')[1]
    expect(hiddenSection.text()).toContain('Photo')
    expect(hiddenSection.text()).toContain('Notes')
  })

  it('does not show visible columns in hidden section', () => {
    const wrapper = mountModal(['name', 'status'])
    const hiddenSection = wrapper.findAll('.column-list')[1]
    expect(hiddenSection.text()).not.toContain('Name')
    expect(hiddenSection.text()).not.toContain('Status')
  })

  it('shows all columns as visible when all are in visibleColumns', () => {
    const wrapper = mountModal(['name', 'status', 'photo', 'notes'])
    const hiddenSection = wrapper.findAll('.column-list')[1]
    const hiddenItems = hiddenSection.findAll('.column-item')
    expect(hiddenItems).toHaveLength(0)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // MOVING COLUMNS
  // ──────────────────────────────────────────────────────────────────────────

  it('moves column from hidden to visible when < button clicked', async () => {
    const wrapper = mountModal(['name'])
    // Click the < button for 'Status' in hidden section
    const hiddenSection = wrapper.findAll('.column-list')[1]
    const statusItem = hiddenSection.findAll('.column-item').find((item) =>
      item.text().includes('Status'),
    )
    await statusItem.find('button.move-button').trigger('click')

    // Status should now be in visible section
    const visibleSection = wrapper.findAll('.column-list')[0]
    expect(visibleSection.text()).toContain('Status')
    // And not in hidden section anymore
    expect(hiddenSection.text()).not.toContain('Status')
  })

  it('moves column from visible to hidden when > button clicked', async () => {
    const wrapper = mountModal(['name', 'status'])
    // Click the > button for 'Status' in visible section (the last button in item actions)
    const visibleSection = wrapper.findAll('.column-list')[0]
    const statusItem = visibleSection.findAll('.column-item').find((item) =>
      item.text().includes('Status'),
    )
    // The > (move to hidden) button is the last button in .column-item-actions
    const buttons = statusItem.findAll('button.move-button')
    await buttons[buttons.length - 1].trigger('click')

    // Status should now be in hidden section
    const hiddenSection = wrapper.findAll('.column-list')[1]
    expect(hiddenSection.text()).toContain('Status')
    expect(visibleSection.text()).not.toContain('Status')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // UP/DOWN MOVEMENT
  // ──────────────────────────────────────────────────────────────────────────

  it('moves column up when ↑ button clicked', async () => {
    const wrapper = mountModal(['name', 'status', 'photo'])
    const visibleSection = wrapper.findAll('.column-list')[0]
    // Get the 'Status' item (index 1) and click ↑
    const statusItem = visibleSection.findAll('.column-item')[1]
    const upButton = statusItem.findAll('button.move-button')[0]
    await upButton.trigger('click')

    // Column order should now be status, name, photo
    const items = visibleSection.findAll('.column-item span')
    expect(items[0].text()).toBe('Status')
    expect(items[1].text()).toBe('Name')
  })

  it('moves column down when ↓ button clicked', async () => {
    const wrapper = mountModal(['name', 'status', 'photo'])
    const visibleSection = wrapper.findAll('.column-list')[0]
    // Get the 'Name' item (index 0) and click ↓
    const nameItem = visibleSection.findAll('.column-item')[0]
    const downButton = nameItem.findAll('button.move-button')[1]
    await downButton.trigger('click')

    // Column order should now be status, name, photo
    const items = visibleSection.findAll('.column-item span')
    expect(items[0].text()).toBe('Status')
    expect(items[1].text()).toBe('Name')
  })

  it('disables ↑ button for the first visible column', () => {
    const wrapper = mountModal(['name', 'status'])
    const visibleSection = wrapper.findAll('.column-list')[0]
    const firstItem = visibleSection.findAll('.column-item')[0]
    const upButton = firstItem.findAll('button.move-button')[0]
    expect(upButton.attributes('disabled')).toBeDefined()
  })

  it('disables ↓ button for the last visible column', () => {
    const wrapper = mountModal(['name', 'status'])
    const visibleSection = wrapper.findAll('.column-list')[0]
    const lastItem = visibleSection.findAll('.column-item')[1]
    const buttons = lastItem.findAll('button.move-button')
    const downButton = buttons[1]
    expect(downButton.attributes('disabled')).toBeDefined()
  })

  it('enables ↑ button for non-first visible columns', () => {
    const wrapper = mountModal(['name', 'status', 'photo'])
    const visibleSection = wrapper.findAll('.column-list')[0]
    const secondItem = visibleSection.findAll('.column-item')[1]
    const upButton = secondItem.findAll('button.move-button')[0]
    expect(upButton.attributes('disabled')).toBeUndefined()
  })

  // ──────────────────────────────────────────────────────────────────────────
  // SAVE / CLOSE / CANCEL
  // ──────────────────────────────────────────────────────────────────────────

  it('emits save with current visible columns when Save is clicked', async () => {
    const wrapper = mountModal(['name', 'status'])
    await wrapper.find('button.save-button').trigger('click')
    expect(wrapper.emitted('save')).toBeTruthy()
    expect(wrapper.emitted('save')[0][0]).toEqual(['name', 'status'])
  })

  it('emits close when Save is clicked', async () => {
    const wrapper = mountModal(['name'])
    await wrapper.find('button.save-button').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close when Cancel is clicked', async () => {
    const wrapper = mountModal(['name'])
    await wrapper.find('button.cancel-button').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('does NOT emit save when Cancel is clicked', async () => {
    const wrapper = mountModal(['name'])
    await wrapper.find('button.cancel-button').trigger('click')
    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('emits close when overlay is clicked', async () => {
    const wrapper = mountModal(['name'])
    await wrapper.find('.modal-overlay').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('does not emit close when modal content (not overlay) is clicked', async () => {
    const wrapper = mountModal(['name'])
    await wrapper.find('.modal-form').trigger('click')
    expect(wrapper.emitted('close')).toBeUndefined()
  })

  // ──────────────────────────────────────────────────────────────────────────
  // SAVE REFLECTS CHANGES
  // ──────────────────────────────────────────────────────────────────────────

  it('save emits updated columns after moving a column to visible', async () => {
    const wrapper = mountModal(['name'])
    // Move 'status' from hidden to visible
    const hiddenSection = wrapper.findAll('.column-list')[1]
    const statusItem = hiddenSection.findAll('.column-item').find((item) =>
      item.text().includes('Status'),
    )
    await statusItem.find('button.move-button').trigger('click')
    // Save
    await wrapper.find('button.save-button').trigger('click')
    const savedColumns = wrapper.emitted('save')[0][0]
    expect(savedColumns).toContain('name')
    expect(savedColumns).toContain('status')
  })
})
