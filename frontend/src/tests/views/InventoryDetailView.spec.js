/**
 * InventoryDetailView.spec.js
 *
 * Tests for the pure utility functions and computed derivations from
 * InventoryDetailView.vue. Covers: formatProjectStatus, allocationStatusLabel,
 * allocationStatusClass, and availableClass.
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure functions (mirrors InventoryDetailView.vue implementations)
// ---------------------------------------------------------------------------

const formatProjectStatus = (status) =>
  status ? status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : '—'

/**
 * Pure version of the allocationStatusLabel computed.
 * @param {object|null} allocation
 * @param {object|null} item
 */
const allocationStatusLabel = (allocation, item) => {
  if (!allocation) return null
  const { qty_on_hand, qty_needed, is_overallocated } = allocation
  if (qty_needed === 0) return null
  if (is_overallocated) return 'Overallocated'
  if (item?.is_consumable && item?.low_stock_threshold) {
    if (qty_on_hand - qty_needed <= item.low_stock_threshold) return 'Running Low'
  }
  return 'Covered'
}

/**
 * Pure version of allocationStatusClass computed.
 */
const allocationStatusClass = (statusLabel) => {
  if (statusLabel === 'Overallocated') return 'alloc-overallocated'
  if (statusLabel === 'Running Low') return 'alloc-low'
  if (statusLabel === 'Covered') return 'alloc-covered'
  return ''
}

/**
 * Pure version of availableClass computed.
 * @param {object|null} allocation
 * @param {object|null} item
 */
const availableClass = (allocation, item) => {
  if (!allocation) return ''
  const avail = allocation.qty_available
  if (avail < 0) return 'avail-negative'
  if (avail === 0) return 'avail-zero'
  if (
    item?.is_consumable &&
    item?.low_stock_threshold &&
    avail <= item.low_stock_threshold
  )
    return 'avail-low'
  return 'avail-ok'
}

// ---------------------------------------------------------------------------

describe('InventoryDetailView – formatProjectStatus', () => {
  it('capitalizes a single word status', () => {
    expect(formatProjectStatus('active')).toBe('Active')
  })

  it('replaces underscores with spaces and capitalizes each word', () => {
    expect(formatProjectStatus('in_progress')).toBe('In Progress')
  })

  it('handles three-word status', () => {
    expect(formatProjectStatus('waiting_for_parts')).toBe('Waiting For Parts')
  })

  it('returns em-dash for null', () => {
    expect(formatProjectStatus(null)).toBe('—')
  })

  it('returns em-dash for empty string', () => {
    expect(formatProjectStatus('')).toBe('—')
  })

  it('returns em-dash for undefined', () => {
    expect(formatProjectStatus(undefined)).toBe('—')
  })

  it('leaves already-capitalized words intact', () => {
    expect(formatProjectStatus('DONE')).toBe('DONE')
  })

  it('handles status without underscores', () => {
    expect(formatProjectStatus('completed')).toBe('Completed')
  })
})

// ---------------------------------------------------------------------------

describe('InventoryDetailView – allocationStatusLabel', () => {
  it('returns null when allocation is null', () => {
    expect(allocationStatusLabel(null, null)).toBeNull()
  })

  it('returns null when qty_needed is 0', () => {
    const alloc = { qty_on_hand: 5, qty_needed: 0, is_overallocated: false }
    expect(allocationStatusLabel(alloc, null)).toBeNull()
  })

  it('returns Overallocated when is_overallocated is true', () => {
    const alloc = { qty_on_hand: 1, qty_needed: 5, is_overallocated: true }
    expect(allocationStatusLabel(alloc, null)).toBe('Overallocated')
  })

  it('returns Running Low for consumable item when available qty is at threshold', () => {
    const alloc = { qty_on_hand: 5, qty_needed: 3, is_overallocated: false }
    const item = { is_consumable: true, low_stock_threshold: 2 }
    // qty_on_hand - qty_needed = 2 <= threshold 2 → Running Low
    expect(allocationStatusLabel(alloc, item)).toBe('Running Low')
  })

  it('returns Running Low for consumable item when available qty is below threshold', () => {
    const alloc = { qty_on_hand: 4, qty_needed: 3, is_overallocated: false }
    const item = { is_consumable: true, low_stock_threshold: 2 }
    // 4 - 3 = 1 <= 2 → Running Low
    expect(allocationStatusLabel(alloc, item)).toBe('Running Low')
  })

  it('returns Covered for consumable item when available qty exceeds threshold', () => {
    const alloc = { qty_on_hand: 10, qty_needed: 3, is_overallocated: false }
    const item = { is_consumable: true, low_stock_threshold: 2 }
    // 10 - 3 = 7 > 2 → Covered
    expect(allocationStatusLabel(alloc, item)).toBe('Covered')
  })

  it('returns Covered when item is not consumable', () => {
    const alloc = { qty_on_hand: 5, qty_needed: 3, is_overallocated: false }
    const item = { is_consumable: false, low_stock_threshold: 2 }
    expect(allocationStatusLabel(alloc, item)).toBe('Covered')
  })

  it('returns Covered when item has no low_stock_threshold', () => {
    const alloc = { qty_on_hand: 5, qty_needed: 3, is_overallocated: false }
    const item = { is_consumable: true, low_stock_threshold: 0 }
    // low_stock_threshold is falsy (0) → skip Running Low check
    expect(allocationStatusLabel(alloc, item)).toBe('Covered')
  })

  it('returns Covered with null item', () => {
    const alloc = { qty_on_hand: 5, qty_needed: 2, is_overallocated: false }
    expect(allocationStatusLabel(alloc, null)).toBe('Covered')
  })

  it('is_overallocated takes priority over Running Low', () => {
    const alloc = { qty_on_hand: 2, qty_needed: 5, is_overallocated: true }
    const item = { is_consumable: true, low_stock_threshold: 10 }
    expect(allocationStatusLabel(alloc, item)).toBe('Overallocated')
  })
})

// ---------------------------------------------------------------------------

describe('InventoryDetailView – allocationStatusClass', () => {
  it('returns alloc-overallocated for Overallocated', () => {
    expect(allocationStatusClass('Overallocated')).toBe('alloc-overallocated')
  })

  it('returns alloc-low for Running Low', () => {
    expect(allocationStatusClass('Running Low')).toBe('alloc-low')
  })

  it('returns alloc-covered for Covered', () => {
    expect(allocationStatusClass('Covered')).toBe('alloc-covered')
  })

  it('returns empty string for null', () => {
    expect(allocationStatusClass(null)).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(allocationStatusClass(undefined)).toBe('')
  })

  it('returns empty string for unrecognized label', () => {
    expect(allocationStatusClass('Unknown')).toBe('')
  })
})

// ---------------------------------------------------------------------------

describe('InventoryDetailView – availableClass', () => {
  it('returns empty string when allocation is null', () => {
    expect(availableClass(null, null)).toBe('')
  })

  it('returns avail-negative when qty_available is negative', () => {
    const alloc = { qty_available: -1 }
    expect(availableClass(alloc, null)).toBe('avail-negative')
  })

  it('returns avail-zero when qty_available is 0', () => {
    const alloc = { qty_available: 0 }
    expect(availableClass(alloc, null)).toBe('avail-zero')
  })

  it('returns avail-low for consumable item at or below threshold', () => {
    const alloc = { qty_available: 2 }
    const item = { is_consumable: true, low_stock_threshold: 2 }
    expect(availableClass(alloc, item)).toBe('avail-low')
  })

  it('returns avail-low for consumable item below threshold', () => {
    const alloc = { qty_available: 1 }
    const item = { is_consumable: true, low_stock_threshold: 3 }
    expect(availableClass(alloc, item)).toBe('avail-low')
  })

  it('returns avail-ok for consumable item above threshold', () => {
    const alloc = { qty_available: 5 }
    const item = { is_consumable: true, low_stock_threshold: 2 }
    expect(availableClass(alloc, item)).toBe('avail-ok')
  })

  it('returns avail-ok for non-consumable item', () => {
    const alloc = { qty_available: 1 }
    const item = { is_consumable: false, low_stock_threshold: 5 }
    expect(availableClass(alloc, item)).toBe('avail-ok')
  })

  it('returns avail-ok when item has no low_stock_threshold', () => {
    const alloc = { qty_available: 1 }
    const item = { is_consumable: true, low_stock_threshold: 0 }
    expect(availableClass(alloc, item)).toBe('avail-ok')
  })

  it('returns avail-ok when item is null but avail is positive', () => {
    const alloc = { qty_available: 3 }
    expect(availableClass(alloc, null)).toBe('avail-ok')
  })

  it('avail-negative takes priority over avail-low check', () => {
    const alloc = { qty_available: -1 }
    const item = { is_consumable: true, low_stock_threshold: 5 }
    expect(availableClass(alloc, item)).toBe('avail-negative')
  })
})
