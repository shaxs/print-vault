/**
 * Tests for pure state-setting functions extracted from FeaturesTab.vue.
 *
 * openEditModal(state, item) — shallow-copies item into state for editing
 * openAddModal(state)        — resets state to a blank new-feature form
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

describe('FeaturesTab – openEditModal', () => {
  it('sets isEditModalVisible to true', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 1, name: 'Matte' })
    expect(state.isEditModalVisible).toBe(true)
  })

  it('copies id and name into editingItem', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 11, name: 'High Speed' })
    expect(state.editingItem).toEqual({ id: 11, name: 'High Speed' })
  })

  it('creates a shallow copy — reassigning editingItem does not affect original', () => {
    const item = { id: 4, name: 'Glow in Dark' }
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, item)
    state.editingItem.name = 'CHANGED'
    expect(item.name).toBe('Glow in Dark')
  })

  it('replaces a previous editingItem', () => {
    const state = { editingItem: { id: 1, name: 'Old Feature' }, isEditModalVisible: true }
    openEditModal(state, { id: 77, name: 'Silk' })
    expect(state.editingItem).toEqual({ id: 77, name: 'Silk' })
  })
})

describe('FeaturesTab – openAddModal', () => {
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
    const state = { editingItem: { id: 4, name: 'Rainbow' }, isEditModalVisible: false }
    openAddModal(state)
    expect(state.editingItem).toEqual({ name: '' })
  })
})
