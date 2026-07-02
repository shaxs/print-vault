/**
 * Tests for pure state-setting functions extracted from VendorsTab.vue.
 *
 * openEditModal(state, item) — shallow-copies item into state for editing
 * openAddModal(state)        — resets state to a blank new-vendor form
 */
import { describe, it, expect } from 'vitest'

function openEditModal(state, item) {
  state.editingItem = { ...item }
  state.isEditModalVisible = true
}

function openAddModal(state) {
  state.editingItem = { name: '' }
  state.isEditModalVisible = true
}

describe('VendorsTab – openEditModal', () => {
  it('sets isEditModalVisible to true', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 1, name: 'Amazon' })
    expect(state.isEditModalVisible).toBe(true)
  })

  it('copies id and name into editingItem', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 3, name: 'MatterHackers' })
    expect(state.editingItem).toEqual({ id: 3, name: 'MatterHackers' })
  })

  it('creates a shallow copy — reassigning editingItem does not affect original', () => {
    const item = { id: 4, name: 'Printed Solid' }
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, item)
    state.editingItem.name = 'CHANGED'
    expect(item.name).toBe('Printed Solid')
  })

  it('replaces a previous editingItem', () => {
    const state = { editingItem: { id: 1, name: 'Old' }, isEditModalVisible: true }
    openEditModal(state, { id: 50, name: 'New Vendor' })
    expect(state.editingItem).toEqual({ id: 50, name: 'New Vendor' })
  })
})

describe('VendorsTab – openAddModal', () => {
  it('sets isEditModalVisible to true', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openAddModal(state)
    expect(state.isEditModalVisible).toBe(true)
  })

  it('sets editingItem to { name: "" }', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openAddModal(state)
    expect(state.editingItem).toEqual({ name: '' })
  })

  it('editingItem has exactly one property (name)', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openAddModal(state)
    expect(Object.keys(state.editingItem)).toEqual(['name'])
  })

  it('clears a previous editingItem', () => {
    const state = { editingItem: { id: 9, name: 'Old Vendor' }, isEditModalVisible: false }
    openAddModal(state)
    expect(state.editingItem).toEqual({ name: '' })
  })
})
