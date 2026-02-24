/**
 * Tests for pure state-setting functions extracted from MaterialsTab.vue.
 *
 * MaterialsTab manages generic material types in the Settings page.
 *
 * openEditModal(state, item) — shallow-copies item into state for editing
 * openAddModal(state)        — resets state to a blank new-material form
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

describe('MaterialsTab – openEditModal', () => {
  it('sets isEditModalVisible to true', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 1, name: 'PLA' })
    expect(state.isEditModalVisible).toBe(true)
  })

  it('copies id and name into editingItem', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 2, name: 'PETG' })
    expect(state.editingItem).toEqual({ id: 2, name: 'PETG' })
  })

  it('creates a shallow copy — reassigning editingItem does not affect original', () => {
    const item = { id: 3, name: 'ABS' }
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, item)
    state.editingItem.name = 'CHANGED'
    expect(item.name).toBe('ABS')
  })

  it('replaces a previous editingItem', () => {
    const state = { editingItem: { id: 1, name: 'Old Material' }, isEditModalVisible: true }
    openEditModal(state, { id: 9, name: 'TPU' })
    expect(state.editingItem).toEqual({ id: 9, name: 'TPU' })
  })

  it('spreads all properties from item', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 5, name: 'Nylon', is_generic: true })
    expect(state.editingItem).toEqual({ id: 5, name: 'Nylon', is_generic: true })
  })
})

describe('MaterialsTab – openAddModal', () => {
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

  it('clears a previous editingItem with id', () => {
    const state = { editingItem: { id: 4, name: 'ASA', is_generic: true }, isEditModalVisible: false }
    openAddModal(state)
    expect(state.editingItem).toEqual({ name: '' })
    expect(state.editingItem.id).toBeUndefined()
  })
})
