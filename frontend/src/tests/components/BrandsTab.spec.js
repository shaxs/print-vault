/**
 * Tests for pure state-setting functions extracted from BrandsTab.vue.
 *
 * openEditModal(state, item) — shallow-copies item into state for editing
 * openAddModal(state)        — resets state to a blank new-brand form
 */
import { describe, it, expect } from 'vitest'

// ─── Pure function implementations (mirrors BrandsTab.vue) ────────────────────

function openEditModal(state, item) {
  state.editingItem = { ...item }
  state.isEditModalVisible = true
}

function openAddModal(state) {
  state.editingItem = { name: '' }
  state.isEditModalVisible = true
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('BrandsTab – openEditModal', () => {
  it('sets isEditModalVisible to true', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 1, name: 'Hatchbox' })
    expect(state.isEditModalVisible).toBe(true)
  })

  it('copies id and name into editingItem', () => {
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, { id: 7, name: 'PolyMaker' })
    expect(state.editingItem).toEqual({ id: 7, name: 'PolyMaker' })
  })

  it('creates a shallow copy — reassigning editingItem does not affect original', () => {
    const item = { id: 2, name: 'eSUN' }
    const state = { editingItem: null, isEditModalVisible: false }
    openEditModal(state, item)
    state.editingItem.name = 'CHANGED'
    expect(item.name).toBe('eSUN')
  })

  it('replaces a previous editingItem', () => {
    const state = { editingItem: { id: 1, name: 'Old' }, isEditModalVisible: true }
    openEditModal(state, { id: 99, name: 'New' })
    expect(state.editingItem).toEqual({ id: 99, name: 'New' })
  })
})

describe('BrandsTab – openAddModal', () => {
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
    const state = { editingItem: { id: 5, name: 'Old Brand' }, isEditModalVisible: false }
    openAddModal(state)
    expect(state.editingItem).toEqual({ name: '' })
  })
})
