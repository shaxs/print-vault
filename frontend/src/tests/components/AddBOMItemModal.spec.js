/**
 * Tests for AddBOMItemModal component pure logic
 *
 * AddBOMItemModal.vue is a modal form for adding a single BOM line item
 * to a project. It includes an inventory autocomplete search, a
 * "needs purchase" flag, and validation before submitting to the API.
 *
 * Tests cover:
 * - Input validation guards (description required, quantity ≥ 1)
 * - BOM payload status derivation (linked / unlinked / needs_purchase)
 * - BOM payload field construction (description trim, notes trim, etc.)
 * - APIService contract (getInventoryItems, createBOMItem exist)
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'

// ── Input validation logic ────────────────────────────────────────────────────
// Mirrors the guard block at the top of handleSubmit in AddBOMItemModal.vue:
//   if (!description.value.trim()) → 'Description is required.'
//   if (!quantityNeeded.value || quantityNeeded.value < 1) → 'Quantity must be at least 1.'

describe('AddBOMItemModal — description validation', () => {
  const validateDescription = (description) => {
    if (!description.trim()) return 'Description is required.'
    return null
  }

  it('returns error when description is empty', () => {
    expect(validateDescription('')).toBe('Description is required.')
  })

  it('returns error when description is only whitespace', () => {
    expect(validateDescription('   ')).toBe('Description is required.')
  })

  it('returns null when description has valid content', () => {
    expect(validateDescription('M3 hex nut')).toBeNull()
  })

  it('returns null when description has surrounding whitespace but non-empty content', () => {
    expect(validateDescription('  bolt  ')).toBeNull()
  })
})

describe('AddBOMItemModal — quantity validation', () => {
  const validateQuantity = (quantity) => {
    if (!quantity || quantity < 1) return 'Quantity must be at least 1.'
    return null
  }

  it('returns error when quantity is 0', () => {
    expect(validateQuantity(0)).toBe('Quantity must be at least 1.')
  })

  it('returns error when quantity is null', () => {
    expect(validateQuantity(null)).toBe('Quantity must be at least 1.')
  })

  it('returns error when quantity is undefined', () => {
    expect(validateQuantity(undefined)).toBe('Quantity must be at least 1.')
  })

  it('returns error when quantity is negative', () => {
    expect(validateQuantity(-5)).toBe('Quantity must be at least 1.')
  })

  it('returns null when quantity is 1', () => {
    expect(validateQuantity(1)).toBeNull()
  })

  it('returns null when quantity is a large positive number', () => {
    expect(validateQuantity(100)).toBeNull()
  })
})

// ── BOM payload status derivation ────────────────────────────────────────────
// Mirrors:
//   status: needsPurchase ? 'needs_purchase'
//           : selectedInventoryItem ? 'linked' : 'unlinked'
//   inventory_item: needsPurchase ? null : (selectedInventoryItem?.id ?? null)

describe('AddBOMItemModal — BOM payload status', () => {
  const buildStatus = (needsPurchase, selectedInventoryItem) =>
    needsPurchase
      ? 'needs_purchase'
      : selectedInventoryItem
        ? 'linked'
        : 'unlinked'

  const buildInventoryItemId = (needsPurchase, selectedInventoryItem) =>
    needsPurchase ? null : (selectedInventoryItem?.id ?? null)

  it('status is "unlinked" when not needs_purchase and no inventory item', () => {
    expect(buildStatus(false, null)).toBe('unlinked')
  })

  it('status is "linked" when not needs_purchase and an inventory item is selected', () => {
    expect(buildStatus(false, { id: 42, title: 'M3 Heat Insert' })).toBe('linked')
  })

  it('status is "needs_purchase" when needs_purchase is true, even with a selected item', () => {
    expect(buildStatus(true, { id: 42, title: 'Some Item' })).toBe('needs_purchase')
  })

  it('status is "needs_purchase" when needs_purchase is true and no item selected', () => {
    expect(buildStatus(true, null)).toBe('needs_purchase')
  })

  it('inventory_item id is set from selected item when not needs_purchase', () => {
    expect(buildInventoryItemId(false, { id: 7 })).toBe(7)
  })

  it('inventory_item is null when no item is selected', () => {
    expect(buildInventoryItemId(false, null)).toBeNull()
  })

  it('inventory_item is null when needs_purchase is true, regardless of selected item', () => {
    expect(buildInventoryItemId(true, { id: 99 })).toBeNull()
  })
})

// ── BOM payload field construction ────────────────────────────────────────────

describe('AddBOMItemModal — payload field construction', () => {
  const buildPayload = ({ projectId, description, quantity, needsPurchase, selectedItem, notes }) => ({
    project: projectId,
    description: description.trim(),
    quantity_needed: quantity,
    status: needsPurchase ? 'needs_purchase' : selectedItem ? 'linked' : 'unlinked',
    inventory_item: needsPurchase ? null : (selectedItem?.id ?? null),
    notes: notes.trim(),
  })

  it('trims description whitespace in the payload', () => {
    const p = buildPayload({ projectId: 1, description: '  hex nut  ', quantity: 2, needsPurchase: false, selectedItem: null, notes: '' })
    expect(p.description).toBe('hex nut')
  })

  it('trims notes whitespace in the payload', () => {
    const p = buildPayload({ projectId: 1, description: 'bolt', quantity: 1, needsPurchase: false, selectedItem: null, notes: '  check shelf  ' })
    expect(p.notes).toBe('check shelf')
  })

  it('sets the project id correctly', () => {
    const p = buildPayload({ projectId: 55, description: 'washer', quantity: 4, needsPurchase: false, selectedItem: null, notes: '' })
    expect(p.project).toBe(55)
  })

  it('sets quantity_needed correctly', () => {
    const p = buildPayload({ projectId: 1, description: 'screw', quantity: 12, needsPurchase: false, selectedItem: null, notes: '' })
    expect(p.quantity_needed).toBe(12)
  })
})

// ── APIService contract ───────────────────────────────────────────────────────

describe('AddBOMItemModal — APIService contract', () => {
  it('APIService.getInventoryItems exists (for autocomplete)', () => {
    expect(typeof APIService.getInventoryItems).toBe('function')
  })

  it('APIService.createBOMItem exists', () => {
    expect(typeof APIService.createBOMItem).toBe('function')
  })
})
