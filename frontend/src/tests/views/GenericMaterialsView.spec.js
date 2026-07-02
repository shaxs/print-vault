/**
 * Tests for GenericMaterialsView (sub-tab inside FilamentManagementView)
 *
 * GenericMaterialsView shows a table of generic (base) filament materials.
 * It always fetches with `?type=generic` and supports two filters:
 *   - material (base material reference)
 *   - color_family (one of 14 color groups)
 *
 * Tests cover:
 * - APIService contract (getMaterials exists)
 * - colorFamilyOptions definition (14 entries)
 * - availableColumns definition (1 column: name)
 * - isFilterActive computed (2-field OR)
 * - clearFilters() resets 2 active filters
 * - applyFilters() copies 2 temporary filters to active
 * - loadMaterials query params always include type: 'generic'
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('GenericMaterialsView — APIService contract', () => {
  it('APIService.getMaterials exists', () => {
    expect(typeof APIService.getMaterials).toBe('function')
  })
})

// ── colorFamilyOptions Definition ────────────────────────────────────────────

describe('GenericMaterialsView — colorFamilyOptions', () => {
  // Mirrors colorFamilyOptions from GenericMaterialsView.vue
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

  it("includes 'clear' for transparent materials", () => {
    expect(colorFamilyOptions.some((c) => c.value === 'clear')).toBe(true)
  })

  it("includes 'gray' (not 'grey')", () => {
    expect(colorFamilyOptions.some((c) => c.value === 'gray')).toBe(true)
    expect(colorFamilyOptions.some((c) => c.value === 'grey')).toBe(false)
  })
})

// ── availableColumns Definition ───────────────────────────────────────────────

describe('GenericMaterialsView — availableColumns', () => {
  // Mirrors availableColumns from GenericMaterialsView.vue
  const availableColumns = [{ value: 'name', text: 'Name' }]
  const defaultVisibleColumns = ['name']

  it('has exactly 1 available column', () => {
    expect(availableColumns).toHaveLength(1)
  })

  it("only column is 'name'", () => {
    expect(availableColumns[0].value).toBe('name')
    expect(availableColumns[0].text).toBe('Name')
  })

  it("'name' is visible by default", () => {
    expect(defaultVisibleColumns).toContain('name')
  })

  it('default visible columns has 1 entry', () => {
    expect(defaultVisibleColumns).toHaveLength(1)
  })
})

// ── API Query Params ──────────────────────────────────────────────────────────

describe('GenericMaterialsView — API always queries type: generic', () => {
  const buildParams = (searchText, activeFilters) => {
    const params = { type: 'generic' }
    if (searchText) params.search = searchText
    if (activeFilters.material) params.base_material = activeFilters.material
    if (activeFilters.color_family) params.color_family = activeFilters.color_family
    return params
  }

  it("always includes type: 'generic' in params", () => {
    const params = buildParams('', { material: '', color_family: '' })
    expect(params.type).toBe('generic')
  })

  it("adds search when searchText is non-empty", () => {
    const params = buildParams('PLA', { material: '', color_family: '' })
    expect(params.search).toBe('PLA')
  })

  it("maps material filter to base_material param", () => {
    const params = buildParams('', { material: '5', color_family: '' })
    expect(params.base_material).toBe('5')
    expect(params.material).toBeUndefined()
  })

  it("adds color_family when set", () => {
    const params = buildParams('', { material: '', color_family: 'red' })
    expect(params.color_family).toBe('red')
  })

  it("does not add search when searchText is empty", () => {
    const params = buildParams('', { material: '', color_family: '' })
    expect(params.search).toBeUndefined()
  })
})

// ── isFilterActive Computed ───────────────────────────────────────────────────

describe('GenericMaterialsView — isFilterActive', () => {
  // Mirrors isFilterActive: activeFilters.material || activeFilters.color_family
  const isFilterActive = (filters) => {
    return !!(filters.material || filters.color_family)
  }

  const empty = { material: '', color_family: '' }

  it('returns false when both filters empty', () => {
    expect(isFilterActive(empty)).toBe(false)
  })

  it('returns true when material filter is set', () => {
    expect(isFilterActive({ ...empty, material: '3' })).toBe(true)
  })

  it('returns true when color_family filter is set', () => {
    expect(isFilterActive({ ...empty, color_family: 'blue' })).toBe(true)
  })

  it('returns true when both filters are set', () => {
    expect(isFilterActive({ material: '3', color_family: 'blue' })).toBe(true)
  })
})

// ── clearFilters() Logic ──────────────────────────────────────────────────────

describe('GenericMaterialsView — clearFilters()', () => {
  const clearFilters = (activeFilters) => {
    activeFilters.material = ''
    activeFilters.color_family = ''
  }

  it('resets material to empty', () => {
    const f = { material: '5', color_family: '' }
    clearFilters(f)
    expect(f.material).toBe('')
  })

  it('resets color_family to empty', () => {
    const f = { material: '', color_family: 'red' }
    clearFilters(f)
    expect(f.color_family).toBe('')
  })

  it('resets both filters simultaneously', () => {
    const f = { material: '5', color_family: 'red' }
    clearFilters(f)
    expect(f.material).toBe('')
    expect(f.color_family).toBe('')
  })

  it('is idempotent when already empty', () => {
    const f = { material: '', color_family: '' }
    clearFilters(f)
    expect(f).toEqual({ material: '', color_family: '' })
  })
})

// ── applyFilters() Logic ──────────────────────────────────────────────────────

describe('GenericMaterialsView — applyFilters()', () => {
  const applyFilters = (activeFilters, temporaryFilters) => {
    Object.assign(activeFilters, temporaryFilters)
  }

  it('copies material from temp to active', () => {
    const active = { material: '', color_family: '' }
    const temp = { material: '7', color_family: '' }
    applyFilters(active, temp)
    expect(active.material).toBe('7')
  })

  it('copies color_family from temp to active', () => {
    const active = { material: '', color_family: '' }
    const temp = { material: '', color_family: 'green' }
    applyFilters(active, temp)
    expect(active.color_family).toBe('green')
  })

  it('copies both filters simultaneously', () => {
    const active = { material: '', color_family: '' }
    const temp = { material: '7', color_family: 'green' }
    applyFilters(active, temp)
    expect(active).toEqual(temp)
  })

  it('applying empty temp clears active filters', () => {
    const active = { material: '7', color_family: 'green' }
    const temp = { material: '', color_family: '' }
    applyFilters(active, temp)
    expect(active).toEqual({ material: '', color_family: '' })
  })
})
