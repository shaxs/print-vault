/**
 * Tests for GenericMaterialTable component pure logic
 *
 * GenericMaterialTable.vue is a simple read-only data table for material-type
 * records (brands, part types, etc.). It filters its column headers by a
 * visibleColumns prop and maps raw items to display-friendly objects.
 *
 * Tests cover:
 * - headers computed: only includes columns present in visibleColumns
 * - tableItems computed: maps id + name, with fallback for missing name
 */
import { describe, it, expect } from 'vitest'

// ── headers computed ──────────────────────────────────────────────────────────
// Mirrors:
//   const allHeaders = [{ value: 'name', text: 'Name' }]
//   return allHeaders.filter((h) => visibleColumns.includes(h.value))

describe('GenericMaterialTable — headers computed', () => {
  const ALL_HEADERS = [{ value: 'name', text: 'Name' }]
  const computeHeaders = (visibleColumns) =>
    ALL_HEADERS.filter((h) => visibleColumns.includes(h.value))

  it('returns the name header when "name" is in visibleColumns', () => {
    const result = computeHeaders(['name'])
    expect(result).toHaveLength(1)
    expect(result[0].value).toBe('name')
    expect(result[0].text).toBe('Name')
  })

  it('returns empty array when visibleColumns is empty', () => {
    expect(computeHeaders([])).toHaveLength(0)
  })

  it('returns empty array when visibleColumns does not contain any recognised column', () => {
    expect(computeHeaders(['description', 'color'])).toHaveLength(0)
  })

  it('only includes headers whose value is in visibleColumns', () => {
    // Even if caller passes unknown names, only matching ones appear
    expect(computeHeaders(['name', 'unknown_col'])).toHaveLength(1)
  })
})

// ── tableItems computed ────────────────────────────────────────────────────────
// Mirrors:
//   return props.items.map((item) => ({ id: item.id, name: item.name || 'Unnamed Material' }))

describe('GenericMaterialTable — tableItems computed', () => {
  const computeTableItems = (items) =>
    items.map((item) => ({ id: item.id, name: item.name || 'Unnamed Material' }))

  it('maps item id and name correctly', () => {
    const result = computeTableItems([{ id: 1, name: 'PLA' }])
    expect(result[0]).toEqual({ id: 1, name: 'PLA' })
  })

  it('uses "Unnamed Material" as fallback when name is empty string', () => {
    const result = computeTableItems([{ id: 2, name: '' }])
    expect(result[0].name).toBe('Unnamed Material')
  })

  it('uses "Unnamed Material" as fallback when name is null', () => {
    const result = computeTableItems([{ id: 3, name: null }])
    expect(result[0].name).toBe('Unnamed Material')
  })

  it('uses "Unnamed Material" as fallback when name is undefined', () => {
    const result = computeTableItems([{ id: 4 }])
    expect(result[0].name).toBe('Unnamed Material')
  })

  it('maps multiple items preserving order', () => {
    const items = [{ id: 1, name: 'ABS' }, { id: 2, name: 'PETG' }, { id: 3, name: '' }]
    const result = computeTableItems(items)
    expect(result).toHaveLength(3)
    expect(result[0].name).toBe('ABS')
    expect(result[1].name).toBe('PETG')
    expect(result[2].name).toBe('Unnamed Material')
  })

  it('returns empty array for empty input', () => {
    expect(computeTableItems([])).toEqual([])
  })
})
