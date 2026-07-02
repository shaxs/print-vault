/**
 * Tests for pure state-setting functions extracted from PartTypesTab.vue.
 *
 * openEditModal(state, item) — shallow-copies item into state for editing
 * openAddModal(state)        — resets state to a blank new-part-type form
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

describe('PartTypesTab – openEditModal', () => {
  it('sets isEditModalVisible to true', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 1, name: 'Bearing' })
    expect(state.isEditModalVisible).toBe(true)
  })

  it('copies id and name into editingItem', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 5, name: 'Fastener' })
    expect(state.editingItem).toEqual({ id: 5, name: 'Fastener' })
  })

  it('creates a shallow copy — reassigning editingItem does not affect original', () => {
    const item = { id: 2, name: 'Spring' }
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, item)
    state.editingItem.name = 'CHANGED'
    expect(item.name).toBe('Spring')
  })

  it('replaces a previous editingItem', () => {
    const state = { editingItem: { id: 1, name: 'Old' }, isEditModalVisible: true }
    openEditModal(state, { id: 20, name: 'Rod' })
    expect(state.editingItem).toEqual({ id: 20, name: 'Rod' })
  })
})

describe('PartTypesTab – openAddModal', () => {
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
    const state = { editingItem: { id: 3, name: 'Old Part Type' }, isEditModalVisible: false }
    openAddModal(state)
    expect(state.editingItem).toEqual({ name: '' })
  })
})
