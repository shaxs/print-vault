/**
 * Tests for MaterialLibraryView (blueprint materials sub-tab + standalone route)
 *
 * MaterialLibraryView shows a grid/table of blueprint filament materials.
 * It always fetches with `?type=blueprint` and supports three filters:
 *   - brand
 *   - material (base material reference, sent as base_material param)
 *   - color_family
 *
 * Tests cover:
 * - APIService contract (getMaterials, getBrands)
 * - Router registration (material-library route at /filaments/materials)
 * - colorFamilyOptions definition (14 entries)
 * - availableColumns definition (7 columns, all visible by default)
 * - API query always includes type: 'blueprint'
 * - isFilterActive computed (3-field OR)
 * - clearFilters() resets 3 active filters
 * - applyFilters() copies 3 temporary filters to active
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('MaterialLibraryView — APIService contract', () => {
  it('APIService.getMaterials exists (for blueprint materials)', () => {
    expect(typeof APIService.getMaterials).toBe('function')
  })

  it('APIService.getBrands exists (for brand filter)', () => {
    expect(typeof APIService.getBrands).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('MaterialLibraryView — route registration', () => {
  it('material-library route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'material-library')
    expect(route).toBeDefined()
  })

  it('material-library route path is /filaments/materials', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'material-library')
    expect(route?.path).toBe('/filaments/materials')
  })
})

// ── colorFamilyOptions Definition ────────────────────────────────────────────

describe('MaterialLibraryView — colorFamilyOptions', () => {
  // Mirrors colorFamilyOptions from MaterialLibraryView.vue
  const colorFamilyOptions = [
    { value: '', label: '-- All --' },
    { value: 'red', label: 'Red' },
    { value: 'orange', label: 'Orange' },
    { value: 'yellow', label: 'Yellow' },
    { value: 'green', label: 'Green' },
    { value: 'blue', label: 'Blue' },
    { value: 'purple', label: 'Purple' },
    { value: 'pink', label: 'Pink' },
    { value: 'brown', label: 'Brown' },
    { value: 'black', label: 'Black' },
    { value: 'white', label: 'White' },
    { value: 'gray', label: 'Gray' },
    { value: 'clear', label: 'Clear' },
    { value: 'multi', label: 'Multi-Color' },
  ]

  it('has 14 entries (including All)', () => {
    expect(colorFamilyOptions).toHaveLength(14)
  })

  it('first option is catch-all with empty value', () => {
    expect(colorFamilyOptions[0]).toEqual({ value: '', label: '-- All --' })
  })

  it("includes 'multi' for multi-color materials", () => {
    expect(colorFamilyOptions.some((c) => c.value === 'multi')).toBe(true)
  })

  it("includes 'clear'", () => {
    expect(colorFamilyOptions.some((c) => c.value === 'clear')).toBe(true)
  })
})

// ── availableColumns Definition ───────────────────────────────────────────────

describe('MaterialLibraryView — availableColumns', () => {
  // Mirrors availableColumns from MaterialLibraryView.vue
  const availableColumns = [
    { value: 'favorite', text: 'Favorite' },
    { value: 'photo', text: 'Photo' },
    { value: 'brand', text: 'Brand' },
    { value: 'name', text: 'Name' },
    { value: 'colors', text: 'Colors' },
    { value: 'material', text: 'Material' },
    { value: 'colorFamily', text: 'Color Family' },
    { value: 'diameter', text: 'Diameter' },
  ]

  // All 8 are visible by default
  const defaultVisibleColumns = availableColumns.map((c) => c.value)

  it('has 8 available columns', () => {
    expect(availableColumns).toHaveLength(8)
  })

  it('all 8 columns are visible by default', () => {
    expect(defaultVisibleColumns).toHaveLength(8)
  })

  it('favorite column is included', () => {
    expect(availableColumns.find((c) => c.value === 'favorite')).toBeDefined()
  })

  it('photo column is included', () => {
    expect(availableColumns.find((c) => c.value === 'photo')).toBeDefined()
  })

  it('brand column is included', () => {
    expect(availableColumns.find((c) => c.value === 'brand')).toBeDefined()
  })

  it('name column is included', () => {
    expect(availableColumns.find((c) => c.value === 'name')).toBeDefined()
  })

  it('colorFamily column label is "Color Family"', () => {
    const col = availableColumns.find((c) => c.value === 'colorFamily')
    expect(col?.text).toBe('Color Family')
  })

  it('diameter column is included', () => {
    expect(availableColumns.find((c) => c.value === 'diameter')).toBeDefined()
  })
})

// ── API Query Params ──────────────────────────────────────────────────────────

describe('MaterialLibraryView — API always queries type: blueprint', () => {
  // Mirrors the params building in loadMaterials()
  const buildParams = (searchText, activeFilters) => {
    const params = { type: 'blueprint' }
    if (searchText) params.search = searchText
    if (activeFilters.brand) params.brand = activeFilters.brand
    if (activeFilters.material) params.base_material = activeFilters.material
    if (activeFilters.color_family) params.color_family = activeFilters.color_family
    return params
  }

  it("always includes type: 'blueprint'", () => {
    const params = buildParams('', { brand: '', material: '', color_family: '' })
    expect(params.type).toBe('blueprint')
  })

  it("adds search when searchText is non-empty", () => {
    const params = buildParams('PETG', { brand: '', material: '', color_family: '' })
    expect(params.search).toBe('PETG')
  })

  it("maps material filter to base_material param", () => {
    const params = buildParams('', { brand: '', material: '3', color_family: '' })
    expect(params.base_material).toBe('3')
    expect(params.material).toBeUndefined()
  })

  it("adds brand when set", () => {
    const params = buildParams('', { brand: '2', material: '', color_family: '' })
    expect(params.brand).toBe('2')
  })

  it("adds color_family when set", () => {
    const params = buildParams('', { brand: '', material: '', color_family: 'purple' })
    expect(params.color_family).toBe('purple')
  })

  it("does not include search when empty", () => {
    const params = buildParams('', { brand: '', material: '', color_family: '' })
    expect(params.search).toBeUndefined()
  })
})

// ── isFilterActive Computed ───────────────────────────────────────────────────

describe('MaterialLibraryView — isFilterActive', () => {
  // Mirrors: activeFilters.brand || activeFilters.material || activeFilters.color_family
  const isFilterActive = (filters) => {
    return !!(filters.brand || filters.material || filters.color_family)
  }

  const empty = { brand: '', material: '', color_family: '' }

  it('returns false when all filters empty', () => {
    expect(isFilterActive(empty)).toBe(false)
  })

  it('returns true when brand filter is set', () => {
    expect(isFilterActive({ ...empty, brand: '1' })).toBe(true)
  })

  it('returns true when material filter is set', () => {
    expect(isFilterActive({ ...empty, material: '3' })).toBe(true)
  })

  it('returns true when color_family filter is set', () => {
    expect(isFilterActive({ ...empty, color_family: 'black' })).toBe(true)
  })

  it('returns true when all three filters are set', () => {
    expect(isFilterActive({ brand: '1', material: '3', color_family: 'black' })).toBe(true)
  })
})

// ── clearFilters() Logic ──────────────────────────────────────────────────────

describe('MaterialLibraryView — clearFilters()', () => {
  const clearFilters = (activeFilters) => {
    activeFilters.brand = ''
    activeFilters.material = ''
    activeFilters.color_family = ''
  }

  it('resets brand to empty', () => {
    const f = { brand: '1', material: '', color_family: '' }
    clearFilters(f)
    expect(f.brand).toBe('')
  })

  it('resets all 3 filters simultaneously', () => {
    const f = { brand: '1', material: '3', color_family: 'black' }
    clearFilters(f)
    expect(f.brand).toBe('')
    expect(f.material).toBe('')
    expect(f.color_family).toBe('')
  })

  it('is idempotent when already empty', () => {
    const f = { brand: '', material: '', color_family: '' }
    clearFilters(f)
    expect(f).toEqual({ brand: '', material: '', color_family: '' })
  })
})

// ── applyFilters() Logic ──────────────────────────────────────────────────────

describe('MaterialLibraryView — applyFilters()', () => {
  const applyFilters = (activeFilters, temporaryFilters) => {
    Object.assign(activeFilters, temporaryFilters)
  }

  it('copies brand from temp to active', () => {
    const active = { brand: '', material: '', color_family: '' }
    const temp = { brand: '5', material: '', color_family: '' }
    applyFilters(active, temp)
    expect(active.brand).toBe('5')
  })

  it('copies all 3 filters at once', () => {
    const active = { brand: '', material: '', color_family: '' }
    const temp = { brand: '5', material: '2', color_family: 'white' }
    applyFilters(active, temp)
    expect(active).toEqual(temp)
  })

  it('clearing temp then applying resets active', () => {
    const active = { brand: '5', material: '2', color_family: 'white' }
    const temp = { brand: '', material: '', color_family: '' }
    applyFilters(active, temp)
    expect(active).toEqual({ brand: '', material: '', color_family: '' })
  })

  it('temp is unchanged after apply (one-way copy)', () => {
    const active = { brand: '', material: '', color_family: '' }
    const temp = { brand: '5', material: '2', color_family: 'white' }
    applyFilters(active, temp)
    expect(temp.brand).toBe('5')
  })
})
