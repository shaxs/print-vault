/**
 * Tests for pure state-setting functions extracted from CategoriesTab.vue.
 *
 * CategoriesTab is a generic settings component used for brands, part types,
 * and locations.
 *
 * openEditModal(state, item) — shallow-copies item into state for editing
 * openAddModal(state)        — resets state to a blank new-item form
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

describe('CategoriesTab – openEditModal', () => {
  it('sets isEditModalVisible to true', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 1, name: 'Category A' })
    expect(state.isEditModalVisible).toBe(true)
  })

  it('copies id and name into editingItem', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 5, name: 'Category B' })
    expect(state.editingItem).toEqual({ id: 5, name: 'Category B' })
  })

  it('creates a shallow copy — reassigning editingItem does not affect original', () => {
    const item = { id: 2, name: 'Original' }
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, item)
    state.editingItem.name = 'CHANGED'
    expect(item.name).toBe('Original')
  })

  it('replaces a previous editingItem', () => {
    const state = { editingItem: { id: 1, name: 'Old' }, isEditModalVisible: true }
    openEditModal(state, { id: 33, name: 'New' })
    expect(state.editingItem).toEqual({ id: 33, name: 'New' })
  })

  it('spreads all properties from item', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 10, name: 'Full', extra: 'value' })
    expect(state.editingItem).toEqual({ id: 10, name: 'Full', extra: 'value' })
  })
})

describe('CategoriesTab – openAddModal', () => {
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
    const state = { editingItem: { id: 7, name: 'Old' }, isEditModalVisible: false }
    openAddModal(state)
    expect(state.editingItem).toEqual({ name: '' })
    expect(state.editingItem.id).toBeUndefined()
  })
})
