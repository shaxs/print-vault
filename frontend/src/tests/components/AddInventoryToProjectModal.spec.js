/**
 * Tests for AddInventoryToProjectModal component pure logic
 *
 * AddInventoryToProjectModal.vue allows users to bulk-select inventory items
 * and add them to a project. It features multi-filter search (text, brand,
 * part type, location), individual item toggle, select-all, and deselect-all.
 *
 * Tests cover:
 * - availableItems: excludes already-linked inventory ids
 * - filterItems: text search (title, brand, part_type, location) + dropdown filters
 * - isSelected: id membership check in selection array
 * - toggleItem: array-based item selection toggle
 * - selectAll: union merge of current selection and filtered ids
 * - deselectAll: clears selection to empty array
 */
import { describe, it, expect } from 'vitest'

// ─── Helpers ──────────────────────────────────────────────────────────────────
// These helpers mirror the computed / method logic from AddInventoryToProjectModal.vue

const availableItems = (allItems, existingIds) =>
  allItems.filter((item) => !existingIds.includes(item.id))

const filterItems = (items, { searchQuery = '', brandFilter = '', partTypeFilter = '', locationFilter = '' } = {}) => {
  let result = items

  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase()
    result = result.filter((item) =>
      item.title.toLowerCase().includes(q) ||
      item.brand?.name.toLowerCase().includes(q) ||
      item.part_type?.name.toLowerCase().includes(q) ||
      item.location?.name.toLowerCase().includes(q)
    )
  }

  if (brandFilter) {
    result = result.filter((item) => item.brand?.name === brandFilter)
  }

  if (partTypeFilter) {
    result = result.filter((item) => item.part_type?.name === partTypeFilter)
  }

  if (locationFilter) {
    result = result.filter((item) => item.location?.name === locationFilter)
  }

  return result
}

const isSelected = (itemId, selectedItems) => selectedItems.includes(itemId)

const toggleItem = (itemId, selectedItems) => {
  const arr = [...selectedItems]
  const index = arr.indexOf(itemId)
  if (index > -1) {
    arr.splice(index, 1)
  } else {
    arr.push(itemId)
  }
  return arr
}

const selectAll = (currentSelected, filteredIds) =>
  [...new Set([...currentSelected, ...filteredIds])]

const deselectAll = () => []

// ─── Sample fixture data ───────────────────────────────────────────────────────
const ITEMS = [
  { id: 1, title: 'Brass Insert M3', brand: { name: 'Voron' }, part_type: { name: 'Fastener' }, location: { name: 'Bin A' } },
  { id: 2, title: 'PETG Spool 1kg', brand: { name: 'Polymaker' }, part_type: { name: 'Filament' }, location: { name: 'Shelf 1' } },
  { id: 3, title: 'Stepper Motor Nema17', brand: { name: 'LDO' }, part_type: { name: 'Electronics' }, location: { name: 'Bin A' } },
  { id: 4, title: 'Raspberry Pi 4', brand: null, part_type: { name: 'Electronics' }, location: null },
]

// ── availableItems ────────────────────────────────────────────────────────────

describe('AddInventoryToProjectModal — availableItems', () => {
  it('returns all items when existingIds is empty', () => {
    expect(availableItems(ITEMS, [])).toHaveLength(4)
  })

  it('excludes item ids that are already linked to the project', () => {
    const result = availableItems(ITEMS, [1, 3])
    expect(result.map((i) => i.id)).toEqual([2, 4])
  })

  it('returns an empty array when all items are already linked', () => {
    expect(availableItems(ITEMS, [1, 2, 3, 4])).toHaveLength(0)
  })

  it('returns items unchanged when existingIds has no overlap', () => {
    expect(availableItems(ITEMS, [99, 100])).toHaveLength(4)
  })
})

// ── filterItems — text search ────────────────────────────────────────────────

describe('AddInventoryToProjectModal — filterItems text search', () => {
  it('returns all items when searchQuery is empty', () => {
    expect(filterItems(ITEMS)).toHaveLength(4)
  })

  it('filters by item title (case-insensitive)', () => {
    const result = filterItems(ITEMS, { searchQuery: 'brass' })
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(1)
  })

  it('filters by brand name', () => {
    const result = filterItems(ITEMS, { searchQuery: 'polymaker' })
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(2)
  })

  it('filters by part_type name', () => {
    const result = filterItems(ITEMS, { searchQuery: 'electronics' })
    expect(result).toHaveLength(2)
    expect(result.map((i) => i.id)).toContain(3)
    expect(result.map((i) => i.id)).toContain(4)
  })

  it('filters by location name', () => {
    const result = filterItems(ITEMS, { searchQuery: 'bin a' })
    expect(result).toHaveLength(2)
    expect(result.map((i) => i.id)).toContain(1)
    expect(result.map((i) => i.id)).toContain(3)
  })

  it('returns empty array when query matches nothing', () => {
    expect(filterItems(ITEMS, { searchQuery: 'zzznomatch' })).toHaveLength(0)
  })

  it('does not throw when item has null brand/location (optional chaining)', () => {
    expect(() => filterItems(ITEMS, { searchQuery: 'raspberry' })).not.toThrow()
    const result = filterItems(ITEMS, { searchQuery: 'raspberry' })
    expect(result[0].id).toBe(4)
  })
})

// ── filterItems — dropdown filters ───────────────────────────────────────────

describe('AddInventoryToProjectModal — filterItems dropdown filters', () => {
  it('applies brandFilter to restrict items', () => {
    const result = filterItems(ITEMS, { brandFilter: 'LDO' })
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(3)
  })

  it('applies partTypeFilter to restrict items', () => {
    const result = filterItems(ITEMS, { partTypeFilter: 'Filament' })
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(2)
  })

  it('applies locationFilter to restrict items', () => {
    const result = filterItems(ITEMS, { locationFilter: 'Shelf 1' })
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(2)
  })

  it('multiple filters compose (AND logic)', () => {
    const result = filterItems(ITEMS, { partTypeFilter: 'Electronics', locationFilter: 'Bin A' })
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(3)
  })

  it('returns empty array when filters find no match', () => {
    expect(filterItems(ITEMS, { brandFilter: 'NonExistent' })).toHaveLength(0)
  })
})

// ── isSelected ────────────────────────────────────────────────────────────────

describe('AddInventoryToProjectModal — isSelected', () => {
  it('returns true when itemId is in the selection array', () => {
    expect(isSelected(2, [1, 2, 3])).toBe(true)
  })

  it('returns false when itemId is not in the selection array', () => {
    expect(isSelected(99, [1, 2, 3])).toBe(false)
  })

  it('returns false for an empty selection array', () => {
    expect(isSelected(1, [])).toBe(false)
  })
})

// ── toggleItem ────────────────────────────────────────────────────────────────

describe('AddInventoryToProjectModal — toggleItem', () => {
  it('adds an item id that is not yet selected', () => {
    const result = toggleItem(5, [1, 2])
    expect(result).toContain(5)
    expect(result).toHaveLength(3)
  })

  it('removes an item id that is already selected', () => {
    const result = toggleItem(2, [1, 2, 3])
    expect(result).not.toContain(2)
    expect(result).toHaveLength(2)
  })

  it('does not mutate the original array', () => {
    const original = [1, 2, 3]
    toggleItem(4, original)
    expect(original).toHaveLength(3)
  })

  it('toggling twice returns to the original state', () => {
    const start = [1, 3]
    const added = toggleItem(2, start)
    const restored = toggleItem(2, added)
    expect(restored).toEqual([1, 3])
  })
})

// ── selectAll ────────────────────────────────────────────────────────────────

describe('AddInventoryToProjectModal — selectAll', () => {
  it('merges filtered ids into current selection', () => {
    const result = selectAll([1], [2, 3])
    expect(result).toContain(1)
    expect(result).toContain(2)
    expect(result).toContain(3)
  })

  it('deduplicates ids that are already in the current selection', () => {
    const result = selectAll([1, 2], [2, 3])
    expect(result.filter((id) => id === 2)).toHaveLength(1)
    expect(result).toHaveLength(3)
  })

  it('returns all filtered ids when current selection is empty', () => {
    expect(selectAll([], [4, 5, 6])).toEqual([4, 5, 6])
  })

  it('returns current selection unchanged when no new filtered ids', () => {
    expect(selectAll([1, 2], [])).toEqual([1, 2])
  })
})

// ── deselectAll ───────────────────────────────────────────────────────────────

describe('AddInventoryToProjectModal — deselectAll', () => {
  it('returns an empty array', () => {
    expect(deselectAll()).toEqual([])
  })

  it('returns empty array regardless of prior selection', () => {
    // deselectAll() simply returns []; the caller replaces selectedItems.value
    expect(deselectAll()).toHaveLength(0)
  })
})
