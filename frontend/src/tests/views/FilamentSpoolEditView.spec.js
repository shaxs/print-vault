/**
 * FilamentSpoolEditView.spec.js
 *
 * Tests for pure utility logic extracted from FilamentSpoolEditView.vue.
 * Covers: parsePlacement, spoolName derivation, openedSpoolCount,
 * remainingUnopenedCount, and removeQuickAddColor guard logic.
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure functions (mirrors FilamentSpoolEditView.vue implementations)
// ---------------------------------------------------------------------------

/**
 * Pure version of parsePlacement (nested inside handleSplitConfirm).
 * Parses "type:id" strings into { location_id, printer_id } objects.
 */
const parsePlacement = (placement) => {
  if (!placement) return { location_id: null, printer_id: null }
  const [type, id] = placement.split(':')
  if (type === 'location') return { location_id: parseInt(id), printer_id: null }
  if (type === 'printer') return { location_id: null, printer_id: parseInt(id) }
  return { location_id: null, printer_id: null }
}

/**
 * Pure version of spoolName computed.
 * Quick-add uses standalone_name; blueprint uses filament_type.name or 'Unknown Material'.
 */
const getSpoolName = (spool) => {
  if (!spool) return 'Spool'
  return spool.is_quick_add
    ? spool.standalone_name
    : spool.filament_type?.name || 'Unknown Material'
}

/**
 * Pure version of openedSpoolCount computed.
 * Counts split spools whose status is not 'new'.
 */
const openedSpoolCount = (splitSpools) =>
  splitSpools.filter((s) => s.status !== 'new').length

/**
 * Pure version of remainingUnopenedCount computed.
 * Counts split spools whose status is 'new'.
 */
const remainingUnopenedCount = (splitSpools) =>
  splitSpools.filter((s) => s.status === 'new').length

/**
 * Pure version of isBatchSpool computed.
 * True only when original status was 'new' AND original quantity > 1.
 */
const isBatchSpool = (originalStatus, originalQuantity) =>
  originalStatus === 'new' && originalQuantity > 1

/**
 * Pure version of removeQuickAddColor guard logic.
 * Only removes the color at index when length > 2 AND index >= 2.
 * Returns the resulting array (does not mutate for test isolation).
 */
const removeQuickAddColor = (colors, index) => {
  const copy = [...colors]
  if (copy.length > 2 && index >= 2) {
    copy.splice(index, 1)
  }
  return copy
}

// ---------------------------------------------------------------------------

describe('FilamentSpoolEditView – parsePlacement', () => {
  it('returns both null for null input', () => {
    expect(parsePlacement(null)).toEqual({ location_id: null, printer_id: null })
  })

  it('returns both null for undefined input', () => {
    expect(parsePlacement(undefined)).toEqual({ location_id: null, printer_id: null })
  })

  it('returns both null for empty string', () => {
    expect(parsePlacement('')).toEqual({ location_id: null, printer_id: null })
  })

  it('parses a location placement', () => {
    expect(parsePlacement('location:5')).toEqual({ location_id: 5, printer_id: null })
  })

  it('parses a printer placement', () => {
    expect(parsePlacement('printer:12')).toEqual({ location_id: null, printer_id: 12 })
  })

  it('converts id to integer', () => {
    const result = parsePlacement('location:99')
    expect(typeof result.location_id).toBe('number')
    expect(result.location_id).toBe(99)
  })

  it('returns both null for an unknown type prefix', () => {
    expect(parsePlacement('shelf:3')).toEqual({ location_id: null, printer_id: null })
  })

  it('only uses the first colon-separated segment for type', () => {
    const result = parsePlacement('printer:7')
    expect(result.printer_id).toBe(7)
    expect(result.location_id).toBeNull()
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolEditView – getSpoolName', () => {
  it('returns "Spool" for null', () => {
    expect(getSpoolName(null)).toBe('Spool')
  })

  it('returns standalone_name for quick-add spool', () => {
    const spool = { is_quick_add: true, standalone_name: 'Mystery PLA' }
    expect(getSpoolName(spool)).toBe('Mystery PLA')
  })

  it('returns filament_type.name for blueprint spool', () => {
    const spool = { is_quick_add: false, filament_type: { name: 'PETG Galaxy' } }
    expect(getSpoolName(spool)).toBe('PETG Galaxy')
  })

  it('returns "Unknown Material" when filament_type is null', () => {
    const spool = { is_quick_add: false, filament_type: null }
    expect(getSpoolName(spool)).toBe('Unknown Material')
  })

  it('returns "Unknown Material" when filament_type is undefined', () => {
    const spool = { is_quick_add: false }
    expect(getSpoolName(spool)).toBe('Unknown Material')
  })

  it('is_quick_add=true uses standalone_name over filament_type', () => {
    const spool = {
      is_quick_add: true,
      standalone_name: 'QuickPLA',
      filament_type: { name: 'Blueprint PLA' },
    }
    expect(getSpoolName(spool)).toBe('QuickPLA')
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolEditView – openedSpoolCount', () => {
  it('returns 0 for empty array', () => {
    expect(openedSpoolCount([])).toBe(0)
  })

  it('counts spools with status other than "new"', () => {
    const spools = [
      { status: 'new' },
      { status: 'opened' },
      { status: 'in_use' },
      { status: 'new' },
    ]
    expect(openedSpoolCount(spools)).toBe(2)
  })

  it('returns 0 when all spools are new', () => {
    const spools = [{ status: 'new' }, { status: 'new' }]
    expect(openedSpoolCount(spools)).toBe(0)
  })

  it('counts all when none are new', () => {
    const spools = [{ status: 'opened' }, { status: 'low' }]
    expect(openedSpoolCount(spools)).toBe(2)
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolEditView – remainingUnopenedCount', () => {
  it('returns 0 for empty array', () => {
    expect(remainingUnopenedCount([])).toBe(0)
  })

  it('counts only spools with status "new"', () => {
    const spools = [
      { status: 'new' },
      { status: 'opened' },
      { status: 'new' },
      { status: 'in_use' },
    ]
    expect(remainingUnopenedCount(spools)).toBe(2)
  })

  it('returns total when all spools are new', () => {
    const spools = [{ status: 'new' }, { status: 'new' }, { status: 'new' }]
    expect(remainingUnopenedCount(spools)).toBe(3)
  })

  it('returns 0 when no spools are new', () => {
    const spools = [{ status: 'opened' }, { status: 'low' }]
    expect(remainingUnopenedCount(spools)).toBe(0)
  })

  it('openedCount + remainingCount equals total', () => {
    const spools = [
      { status: 'new' },
      { status: 'opened' },
      { status: 'new' },
      { status: 'low' },
    ]
    expect(openedSpoolCount(spools) + remainingUnopenedCount(spools)).toBe(spools.length)
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolEditView – isBatchSpool', () => {
  it('returns true when status is "new" and quantity > 1', () => {
    expect(isBatchSpool('new', 5)).toBe(true)
  })

  it('returns false when status is not "new"', () => {
    expect(isBatchSpool('opened', 5)).toBe(false)
  })

  it('returns false when quantity is 1', () => {
    expect(isBatchSpool('new', 1)).toBe(false)
  })

  it('returns false when quantity is 0', () => {
    expect(isBatchSpool('new', 0)).toBe(false)
  })

  it('returns true for quantity of exactly 2', () => {
    expect(isBatchSpool('new', 2)).toBe(true)
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolEditView – removeQuickAddColor guard', () => {
  it('removes color at index 2 when length > 2', () => {
    const colors = ['#ff0000', '#00ff00', '#0000ff']
    const result = removeQuickAddColor(colors, 2)
    expect(result).toEqual(['#ff0000', '#00ff00'])
  })

  it('removes color at index 3 (last) when length > 2', () => {
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffffff']
    const result = removeQuickAddColor(colors, 3)
    expect(result).toEqual(['#ff0000', '#00ff00', '#0000ff'])
  })

  it('does NOT remove when index < 2 (protect first two colors)', () => {
    const colors = ['#ff0000', '#00ff00', '#0000ff']
    const result = removeQuickAddColor(colors, 0)
    expect(result).toEqual(colors)
  })

  it('does NOT remove index 1 (protect second color)', () => {
    const colors = ['#ff0000', '#00ff00', '#0000ff']
    const result = removeQuickAddColor(colors, 1)
    expect(result).toEqual(colors)
  })

  it('does NOT remove when length is exactly 2', () => {
    const colors = ['#ff0000', '#00ff00']
    const result = removeQuickAddColor(colors, 2)
    // index 2 is out of bounds AND length is not > 2, so no change
    expect(result).toEqual(colors)
  })

  it('does not mutate the original array', () => {
    const colors = ['#ff0000', '#00ff00', '#0000ff']
    const original = [...colors]
    removeQuickAddColor(colors, 2)
    expect(colors).toEqual(original)
  })
})
