/**
 * Tests for pure / stateless functions extracted from
 * frontend/src/views/ProjectManageLinksView.vue
 *
 * Covered functions
 * ─────────────────────────────────────────────────────────
 * - resetForm(state)      clear editing state → isEditing=false, editableLink cleared
 * - startEdit(link, state) enter edit mode → isEditing=true, editableLink=spread of link
 *
 * Both functions mutate a shared state object (isEditing + editableLink). They
 * are the core of the add/edit workflow and have no network calls or side effects.
 */

import { describe, it, expect } from 'vitest'

// ─────────────────────────────────────────────────────────────────────────────
// Extracted functions (mirrors ProjectManageLinksView.vue logic exactly)
// ─────────────────────────────────────────────────────────────────────────────

function resetForm(state) {
  state.isEditing = false
  state.editableLink = { id: null, name: '', url: '' }
}

function startEdit(link, state) {
  state.isEditing = true
  state.editableLink = { ...link }
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const makeState = (overrides = {}) => ({
  isEditing: false,
  editableLink: { id: null, name: '', url: '' },
  ...overrides,
})

// ─────────────────────────────────────────────────────────────────────────────
// resetForm
// ─────────────────────────────────────────────────────────────────────────────

describe('resetForm', () => {
  it('sets isEditing to false', () => {
    const state = makeState({ isEditing: true })
    resetForm(state)
    expect(state.isEditing).toBe(false)
  })

  it('is idempotent when isEditing is already false', () => {
    const state = makeState({ isEditing: false })
    resetForm(state)
    expect(state.isEditing).toBe(false)
  })

  it('resets editableLink id to null', () => {
    const state = makeState({ editableLink: { id: 42, name: 'Guide', url: 'https://example.com' } })
    resetForm(state)
    expect(state.editableLink.id).toBeNull()
  })

  it('resets editableLink name to empty string', () => {
    const state = makeState({ editableLink: { id: 1, name: 'Old Name', url: 'https://a.com' } })
    resetForm(state)
    expect(state.editableLink.name).toBe('')
  })

  it('resets editableLink url to empty string', () => {
    const state = makeState({ editableLink: { id: 1, name: 'Old', url: 'https://old.com' } })
    resetForm(state)
    expect(state.editableLink.url).toBe('')
  })

  it('produces an editableLink with exactly three properties', () => {
    const state = makeState()
    resetForm(state)
    expect(Object.keys(state.editableLink)).toEqual(['id', 'name', 'url'])
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// startEdit
// ─────────────────────────────────────────────────────────────────────────────

describe('startEdit', () => {
  it('sets isEditing to true', () => {
    const state = makeState()
    startEdit({ id: 1, name: 'Guide', url: 'https://example.com' }, state)
    expect(state.isEditing).toBe(true)
  })

  it('copies the link id to editableLink', () => {
    const state = makeState()
    startEdit({ id: 7, name: 'Docs', url: 'https://docs.example.com' }, state)
    expect(state.editableLink.id).toBe(7)
  })

  it('copies the link name to editableLink', () => {
    const state = makeState()
    startEdit({ id: 2, name: 'Assembly Guide', url: 'https://site.com' }, state)
    expect(state.editableLink.name).toBe('Assembly Guide')
  })

  it('copies the link url to editableLink', () => {
    const state = makeState()
    startEdit({ id: 3, name: 'Repo', url: 'https://github.com/org/repo' }, state)
    expect(state.editableLink.url).toBe('https://github.com/org/repo')
  })

  it('creates a shallow copy — mutating editableLink does not affect original', () => {
    const original = { id: 5, name: 'Original', url: 'https://before.com' }
    const state = makeState()
    startEdit(original, state)
    state.editableLink.name = 'Modified'
    expect(original.name).toBe('Original')
  })

  it('overwrites an existing incomplete editableLink', () => {
    const state = makeState({
      isEditing: false,
      editableLink: { id: null, name: '', url: '' },
    })
    startEdit({ id: 99, name: 'New', url: 'https://new.com' }, state)
    expect(state.editableLink.id).toBe(99)
    expect(state.editableLink.name).toBe('New')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// resetForm / startEdit interaction
// ─────────────────────────────────────────────────────────────────────────────

describe('resetForm + startEdit interaction', () => {
  it('startEdit followed by resetForm leaves state clean', () => {
    const state = makeState()
    startEdit({ id: 10, name: 'Test', url: 'https://x.com' }, state)
    expect(state.isEditing).toBe(true)
    resetForm(state)
    expect(state.isEditing).toBe(false)
    expect(state.editableLink).toEqual({ id: null, name: '', url: '' })
  })

  it('multiple startEdit calls use the most recent link', () => {
    const state = makeState()
    startEdit({ id: 1, name: 'First', url: 'https://first.com' }, state)
    startEdit({ id: 2, name: 'Second', url: 'https://second.com' }, state)
    expect(state.editableLink.id).toBe(2)
    expect(state.editableLink.name).toBe('Second')
  })
})
