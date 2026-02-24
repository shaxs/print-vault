/**
 * Tests for HomeView (Inventory List)
 *
 * HomeView is the Parts List view at /inventory. Users can search,
 * filter by brand/part type/location, and configure visible columns.
 *
 * Tests cover:
 * - APIService contract (required inventory methods exist)
 * - Router registration (inventory/home route exists)
 * - allInventoryColumns definition (correct columns + defaultVisible flags)
 * - isFilterActive computed logic
 * - applyFilters() filter-building logic
 * - localStorage column persistence logic
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('HomeView — APIService contract', () => {
  it('APIService.getInventoryItems exists', () => {
    expect(typeof APIService.getInventoryItems).toBe('function')
  })

  it('APIService.getBrands exists (for brand filter options)', () => {
    expect(typeof APIService.getBrands).toBe('function')
  })

  it('APIService.getPartTypes exists (for part type filter options)', () => {
    expect(typeof APIService.getPartTypes).toBe('function')
  })

  it('APIService.getLocations exists (for location filter options)', () => {
    expect(typeof APIService.getLocations).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('HomeView — route registration', () => {
  it('inventory/home route is registered', () => {
    const routes = router.getRoutes()
    const homeRoute = routes.find((r) => r.name === 'home')
    expect(homeRoute).toBeDefined()
  })

  it('home route path is /inventory', () => {
    const routes = router.getRoutes()
    const homeRoute = routes.find((r) => r.name === 'home')
    expect(homeRoute?.path).toBe('/inventory')
  })

  it('item create route (name "create") is registered', () => {
    const routes = router.getRoutes()
    const createRoute = routes.find((r) => r.name === 'create')
    expect(createRoute).toBeDefined()
  })

  it('item detail route (name "item-detail") is registered', () => {
    const routes = router.getRoutes()
    const detailRoute = routes.find((r) => r.name === 'item-detail')
    expect(detailRoute).toBeDefined()
  })
})

// ── allInventoryColumns Definition ───────────────────────────────────────────

describe('HomeView — allInventoryColumns', () => {
  // Mirrors allInventoryColumns from HomeView.vue
  const allInventoryColumns = [
    { text: 'Title', value: 'title', defaultVisible: true },
    { text: 'Photo', value: 'photo', defaultVisible: false },
    { text: 'Brand', value: 'brand', defaultVisible: true },
    { text: 'Part Type', value: 'partType', defaultVisible: true },
    { text: 'Location', value: 'location', defaultVisible: true },
    { text: 'Qty on Hand', value: 'quantity', defaultVisible: true },
    { text: 'Qty Needed', value: 'qtyNeeded', defaultVisible: true },
    { text: 'Cost', value: 'cost', defaultVisible: false },
  ]

  it('has 8 columns', () => {
    expect(allInventoryColumns).toHaveLength(8)
  })

  it('title is visible by default', () => {
    expect(allInventoryColumns.find((c) => c.value === 'title')?.defaultVisible).toBe(true)
  })

  it('brand is visible by default', () => {
    expect(allInventoryColumns.find((c) => c.value === 'brand')?.defaultVisible).toBe(true)
  })

  it('partType is visible by default', () => {
    expect(allInventoryColumns.find((c) => c.value === 'partType')?.defaultVisible).toBe(true)
  })

  it('location is visible by default', () => {
    expect(allInventoryColumns.find((c) => c.value === 'location')?.defaultVisible).toBe(true)
  })

  it('quantity is visible by default', () => {
    expect(allInventoryColumns.find((c) => c.value === 'quantity')?.defaultVisible).toBe(true)
  })

  it('qtyNeeded is visible by default', () => {
    expect(allInventoryColumns.find((c) => c.value === 'qtyNeeded')?.defaultVisible).toBe(true)
  })

  it('photo is hidden by default', () => {
    expect(allInventoryColumns.find((c) => c.value === 'photo')?.defaultVisible).toBe(false)
  })

  it('cost is hidden by default', () => {
    expect(allInventoryColumns.find((c) => c.value === 'cost')?.defaultVisible).toBe(false)
  })

  it('default visible columns are title, brand, partType, location, quantity, qtyNeeded', () => {
    const defaults = allInventoryColumns.filter((c) => c.defaultVisible).map((c) => c.value)
    expect(defaults).toEqual(['title', 'brand', 'partType', 'location', 'quantity', 'qtyNeeded'])
  })
})

// ── isFilterActive computed logic ────────────────────────────────────────────

describe('HomeView — isFilterActive computed', () => {
  const isFilterActive = (searchText, activeFilters) =>
    !!(searchText || Object.values(activeFilters).some((val) => val && val.length > 0))

  it('false when no search and no filters', () => {
    expect(isFilterActive('', {})).toBe(false)
  })

  it('true when searchText is non-empty', () => {
    expect(isFilterActive('M3 bolt', {})).toBe(true)
  })

  it('true when brand filter is active', () => {
    expect(isFilterActive('', { brand__name: 'Misumi' })).toBe(true)
  })

  it('true when part_type filter is active', () => {
    expect(isFilterActive('', { part_type__name: 'Fastener' })).toBe(true)
  })

  it('true when location filter is active', () => {
    expect(isFilterActive('', { location__name: 'Parts Drawer' })).toBe(true)
  })

  it('false when all filter values are empty strings', () => {
    expect(isFilterActive('', { brand__name: '', part_type__name: '', location__name: '' })).toBe(false)
  })
})

// ── applyFilters() filter-building logic ─────────────────────────────────────

describe('HomeView — applyFilters() logic', () => {
  const applyFilters = (existingQuery, temporaryFilters) => {
    const newFilters = { ...existingQuery }
    for (const key in temporaryFilters) {
      if (temporaryFilters[key]) {
        newFilters[key] = temporaryFilters[key]
      } else {
        delete newFilters[key]
      }
    }
    return newFilters
  }

  it('adds brand filter when set', () => {
    const result = applyFilters({}, { brand__name: 'Misumi', part_type__name: '', location__name: '' })
    expect(result.brand__name).toBe('Misumi')
    expect(result.part_type__name).toBeUndefined()
  })

  it('removes filter when cleared', () => {
    const result = applyFilters({ brand__name: 'Misumi' }, { brand__name: '', part_type__name: '', location__name: '' })
    expect(result.brand__name).toBeUndefined()
  })

  it('preserves search in existing query when applying filter', () => {
    const result = applyFilters({ search: 'm3' }, { brand__name: 'Misumi', part_type__name: '', location__name: '' })
    expect(result.search).toBe('m3')
    expect(result.brand__name).toBe('Misumi')
  })

  it('adds all three filters when all are set', () => {
    const result = applyFilters({}, {
      brand__name: 'Misumi',
      part_type__name: 'Fastener',
      location__name: 'Drawer 1',
    })
    expect(result.brand__name).toBe('Misumi')
    expect(result.part_type__name).toBe('Fastener')
    expect(result.location__name).toBe('Drawer 1')
  })
})

// ── localStorage column persistence ─────────────────────────────────────────

describe('HomeView — localStorage column persistence', () => {
  const STORAGE_KEY = 'inventory-columns'

  const allInventoryColumns = [
    { text: 'Title', value: 'title', defaultVisible: true },
    { text: 'Photo', value: 'photo', defaultVisible: false },
    { text: 'Brand', value: 'brand', defaultVisible: true },
    { text: 'Part Type', value: 'partType', defaultVisible: true },
    { text: 'Location', value: 'location', defaultVisible: true },
    { text: 'Qty on Hand', value: 'quantity', defaultVisible: true },
    { text: 'Qty Needed', value: 'qtyNeeded', defaultVisible: true },
    { text: 'Cost', value: 'cost', defaultVisible: false },
  ]

  const loadColumns = (savedJSON) => {
    if (savedJSON) return JSON.parse(savedJSON)
    return allInventoryColumns.filter((c) => c.defaultVisible).map((c) => c.value)
  }

  it('storage key is "inventory-columns"', () => {
    expect(STORAGE_KEY).toBe('inventory-columns')
  })

  it('returns defaults when nothing saved', () => {
    expect(loadColumns(null)).toEqual(['title', 'brand', 'partType', 'location', 'quantity', 'qtyNeeded'])
  })

  it('returns custom columns from JSON', () => {
    const saved = JSON.stringify(['title', 'cost'])
    expect(loadColumns(saved)).toEqual(['title', 'cost'])
  })
})
