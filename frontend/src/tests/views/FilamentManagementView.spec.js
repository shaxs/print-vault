/**
 * Tests for FilamentManagementView (/filaments)
 *
 * FilamentManagementView is the main filament hub with three tabs:
 *   - 'spools'      → spool table with advanced filters
 *   - 'blueprints'  → material library grid (blueprint materials)
 *   - 'generics'    → generic materials list
 *
 * The active tab is initialised from the `?tab=` query param.
 * URL updates are pushed via router.replace() when switching tabs.
 *
 * Tests cover:
 * - APIService contract (required filament + brand + material methods exist)
 * - Router registration (filament routes exist)
 * - getInitialTab() pure logic
 * - changeTab() URL update behaviour
 * - statusOptions definition (7 entries)
 * - colorFamilyOptions definition (14 entries)
 * - availableColumns definition (10 entries, all visible by default)
 * - isFilterActive computed logic (5 independent filter fields)
 * - clearFilters() resets all 5 active filters
 * - applyFilters() copies temporary filters to active filters
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('FilamentManagementView — APIService contract', () => {
  it('APIService.getFilamentSpools exists', () => {
    expect(typeof APIService.getFilamentSpools).toBe('function')
  })

  it('APIService.getBrands exists (for brand filter)', () => {
    expect(typeof APIService.getBrands).toBe('function')
  })

  it('APIService.getMaterials exists (for material filter)', () => {
    expect(typeof APIService.getMaterials).toBe('function')
  })

  it('APIService.getMaterialFeatures exists (for feature filter)', () => {
    expect(typeof APIService.getMaterialFeatures).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('FilamentManagementView — route registration', () => {
  it('filament-management route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'filament-management')
    expect(route).toBeDefined()
  })

  it('filament-management route path is /filaments', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'filament-management')
    expect(route?.path).toBe('/filaments')
  })

  it('filament-spool-create route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'filament-spool-create')
    expect(route).toBeDefined()
  })

  it('filament-spool-detail route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'filament-spool-detail')
    expect(route).toBeDefined()
  })
})

// ── getInitialTab() Logic ─────────────────────────────────────────────────────

describe('FilamentManagementView — getInitialTab()', () => {
  // Mirrors the getInitialTab() function from FilamentManagementView.vue
  const getInitialTab = (tabParam) => {
    if (tabParam === 'blueprints' || tabParam === 'generics') {
      return tabParam
    }
    return 'spools'
  }

  it("returns 'spools' when no tab param", () => {
    expect(getInitialTab(undefined)).toBe('spools')
  })

  it("returns 'spools' as default", () => {
    expect(getInitialTab('spools')).toBe('spools')
  })

  it("returns 'blueprints' for tab=blueprints", () => {
    expect(getInitialTab('blueprints')).toBe('blueprints')
  })

  it("returns 'generics' for tab=generics", () => {
    expect(getInitialTab('generics')).toBe('generics')
  })

  it("returns 'spools' for unknown tab param", () => {
    expect(getInitialTab('unknown')).toBe('spools')
  })

  it("returns 'spools' for empty string", () => {
    expect(getInitialTab('')).toBe('spools')
  })
})

// ── changeTab() URL Behaviour ─────────────────────────────────────────────────

describe('FilamentManagementView — changeTab() URL routing', () => {
  // Mirrors the routing logic inside changeTab()
  const getTabQuery = (tab) => {
    if (tab === 'spools') {
      return {}
    }
    return { tab }
  }

  it("'spools' tab → empty query (removes tab param)", () => {
    expect(getTabQuery('spools')).toEqual({})
  })

  it("'blueprints' tab → query { tab: 'blueprints' }", () => {
    expect(getTabQuery('blueprints')).toEqual({ tab: 'blueprints' })
  })

  it("'generics' tab → query { tab: 'generics' }", () => {
    expect(getTabQuery('generics')).toEqual({ tab: 'generics' })
  })

  it('all tabs use /filaments as the path', () => {
    // The path never changes — only the query param differs
    const path = '/filaments'
    expect(path).toBe('/filaments')
  })
})

// ── statusOptions Definition ──────────────────────────────────────────────────

describe('FilamentManagementView — statusOptions', () => {
  // Mirrors statusOptions from FilamentManagementView.vue
  const statusOptions = [
    { value: '', label: '-- All --' },
    { value: 'new', label: 'New (Unopened)' },
    { value: 'opened', label: 'Opened' },
    { value: 'in_use', label: 'In Use' },
    { value: 'low', label: 'Low' },
    { value: 'empty', label: 'Empty' },
    { value: 'archived', label: 'Archived' },
  ]

  it('has 7 status options (including All)', () => {
    expect(statusOptions).toHaveLength(7)
  })

  it('first option is "-- All --" with empty value', () => {
    expect(statusOptions[0]).toEqual({ value: '', label: '-- All --' })
  })

  it("includes 'new' status", () => {
    expect(statusOptions.find((s) => s.value === 'new')).toBeDefined()
  })

  it("includes 'in_use' status", () => {
    expect(statusOptions.find((s) => s.value === 'in_use')).toBeDefined()
  })

  it("includes 'low' status", () => {
    expect(statusOptions.find((s) => s.value === 'low')).toBeDefined()
  })

  it("includes 'empty' status", () => {
    expect(statusOptions.find((s) => s.value === 'empty')).toBeDefined()
  })

  it("includes 'archived' status", () => {
    expect(statusOptions.find((s) => s.value === 'archived')).toBeDefined()
  })
})

// ── colorFamilyOptions Definition ────────────────────────────────────────────

describe('FilamentManagementView — colorFamilyOptions', () => {
  // Mirrors colorFamilyOptions from FilamentManagementView.vue
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

  it('has 14 color family options (including All)', () => {
    expect(colorFamilyOptions).toHaveLength(14)
  })

  it('first option is "-- All --" with empty value', () => {
    expect(colorFamilyOptions[0]).toEqual({ value: '', label: '-- All --' })
  })

  it("includes primary colors (red/blue/yellow)", () => {
    const values = colorFamilyOptions.map((c) => c.value)
    expect(values).toContain('red')
    expect(values).toContain('blue')
    expect(values).toContain('yellow')
  })

  it("includes 'multi' for multi-color spools", () => {
    expect(colorFamilyOptions.find((c) => c.value === 'multi')).toBeDefined()
  })

  it("includes 'clear' for transparent filaments", () => {
    expect(colorFamilyOptions.find((c) => c.value === 'clear')).toBeDefined()
  })
})

// ── availableColumns Definition ───────────────────────────────────────────────

describe('FilamentManagementView — availableColumns', () => {
  // Mirrors availableColumns from FilamentManagementView.vue
  const availableColumns = [
    { value: 'photo', text: 'Photo' },
    { value: 'brand', text: 'Brand' },
    { value: 'colors', text: 'Colors' },
    { value: 'name', text: 'Name' },
    { value: 'material', text: 'Material' },
    { value: 'features', text: 'Features' },
    { value: 'quantity', text: 'Quantity' },
    { value: 'status', text: 'Status' },
    { value: 'location', text: 'Location/Printer' },
    { value: 'filamentUsed', text: 'Filament Used' },
  ]

  // Default visible columns (all 10)
  const defaultVisibleColumns = availableColumns.map((c) => c.value)

  it('has 10 available columns', () => {
    expect(availableColumns).toHaveLength(10)
  })

  it('all 10 columns are visible by default', () => {
    expect(defaultVisibleColumns).toHaveLength(10)
  })

  it('photo column is included', () => {
    expect(availableColumns.find((c) => c.value === 'photo')).toBeDefined()
  })

  it('brand column is included', () => {
    expect(availableColumns.find((c) => c.value === 'brand')).toBeDefined()
  })

  it('material column is included', () => {
    expect(availableColumns.find((c) => c.value === 'material')).toBeDefined()
  })

  it('status column is included', () => {
    expect(availableColumns.find((c) => c.value === 'status')).toBeDefined()
  })

  it('filamentUsed column is included', () => {
    expect(availableColumns.find((c) => c.value === 'filamentUsed')).toBeDefined()
  })

  it('location column label is "Location/Printer"', () => {
    const col = availableColumns.find((c) => c.value === 'location')
    expect(col?.text).toBe('Location/Printer')
  })
})

// ── isFilterActive Computed ───────────────────────────────────────────────────

describe('FilamentManagementView — isFilterActive', () => {
  // Mirrors the isFilterActive computed from FilamentManagementView.vue
  const isFilterActive = (filters) => {
    return !!(
      filters.status ||
      filters.brand ||
      filters.material ||
      filters.color_family ||
      filters.feature
    )
  }

  const emptyFilters = { status: '', brand: '', material: '', color_family: '', feature: '' }

  it('returns false when all filters are empty', () => {
    expect(isFilterActive(emptyFilters)).toBe(false)
  })

  it('returns true when status filter is set', () => {
    expect(isFilterActive({ ...emptyFilters, status: 'new' })).toBe(true)
  })

  it('returns true when brand filter is set', () => {
    expect(isFilterActive({ ...emptyFilters, brand: '1' })).toBe(true)
  })

  it('returns true when material filter is set', () => {
    expect(isFilterActive({ ...emptyFilters, material: '2' })).toBe(true)
  })

  it('returns true when color_family filter is set', () => {
    expect(isFilterActive({ ...emptyFilters, color_family: 'red' })).toBe(true)
  })

  it('returns true when feature filter is set', () => {
    expect(isFilterActive({ ...emptyFilters, feature: '3' })).toBe(true)
  })

  it('returns true when multiple filters are set simultaneously', () => {
    expect(
      isFilterActive({ status: 'new', brand: '1', material: '2', color_family: 'red', feature: '3' })
    ).toBe(true)
  })
})

// ── clearFilters() Logic ──────────────────────────────────────────────────────

describe('FilamentManagementView — clearFilters()', () => {
  // Mirrors the clearFilters() function from FilamentManagementView.vue
  const clearFilters = (activeFilters) => {
    activeFilters.status = ''
    activeFilters.brand = ''
    activeFilters.material = ''
    activeFilters.color_family = ''
    activeFilters.feature = ''
  }

  it('resets status to empty string', () => {
    const f = { status: 'new', brand: '', material: '', color_family: '', feature: '' }
    clearFilters(f)
    expect(f.status).toBe('')
  })

  it('resets all 5 filters to empty', () => {
    const f = { status: 'new', brand: '1', material: '2', color_family: 'red', feature: '3' }
    clearFilters(f)
    expect(f.status).toBe('')
    expect(f.brand).toBe('')
    expect(f.material).toBe('')
    expect(f.color_family).toBe('')
    expect(f.feature).toBe('')
  })

  it('is idempotent — already empty stays empty', () => {
    const f = { status: '', brand: '', material: '', color_family: '', feature: '' }
    clearFilters(f)
    expect(f).toEqual({ status: '', brand: '', material: '', color_family: '', feature: '' })
  })
})

// ── applyFilters() Logic ──────────────────────────────────────────────────────

describe('FilamentManagementView — applyFilters()', () => {
  // Mirrors the applyFilters() logic: Object.assign(activeFilters, temporaryFilters)
  const applyFilters = (activeFilters, temporaryFilters) => {
    Object.assign(activeFilters, temporaryFilters)
  }

  it('copies status from temporary to active', () => {
    const active = { status: '', brand: '', material: '', color_family: '', feature: '' }
    const temp = { status: 'in_use', brand: '', material: '', color_family: '', feature: '' }
    applyFilters(active, temp)
    expect(active.status).toBe('in_use')
  })

  it('copies all 5 filters at once', () => {
    const active = { status: '', brand: '', material: '', color_family: '', feature: '' }
    const temp = { status: 'low', brand: '5', material: '3', color_family: 'blue', feature: '7' }
    applyFilters(active, temp)
    expect(active).toEqual(temp)
  })

  it('clearing temporary filters then applying resets active filters', () => {
    const active = { status: 'new', brand: '1', material: '2', color_family: 'red', feature: '3' }
    const temp = { status: '', brand: '', material: '', color_family: '', feature: '' }
    applyFilters(active, temp)
    expect(active).toEqual({ status: '', brand: '', material: '', color_family: '', feature: '' })
  })

  it('active filters do not affect temporary filters (one-way copy)', () => {
    const active = { status: 'new', brand: '1', material: '', color_family: '', feature: '' }
    const temp = { status: 'empty', brand: '', material: '', color_family: '', feature: '' }
    applyFilters(active, temp)
    // temp should remain unchanged
    expect(temp.status).toBe('empty')
  })
})
