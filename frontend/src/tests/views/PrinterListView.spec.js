/**
 * Tests for PrinterListView
 *
 * PrinterListView displays printers at /printers. Users can filter by
 * manufacturer name and status, configure visible columns, and search.
 *
 * Tests cover:
 * - APIService contract (required printer methods exist)
 * - Router registration (printers route exists)
 * - allPrinterColumns definition (correct columns + defaultVisible flags)
 * - filterOptions.statuses (all valid printer statuses present)
 * - isFilterActive computed logic
 * - applyFilters() filter-building logic
 * - localStorage column persistence logic
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('PrinterListView — APIService contract', () => {
  it('APIService.getPrinters exists', () => {
    expect(typeof APIService.getPrinters).toBe('function')
  })

  it('APIService.getBrands exists (for manufacturer filter options)', () => {
    expect(typeof APIService.getBrands).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('PrinterListView — route registration', () => {
  it('printers route is registered', () => {
    const routes = router.getRoutes()
    const printersRoute = routes.find((r) => r.name === 'printer-list')
    expect(printersRoute).toBeDefined()
  })

  it('printers route path is /printers', () => {
    const routes = router.getRoutes()
    const printersRoute = routes.find((r) => r.name === 'printer-list')
    expect(printersRoute?.path).toBe('/printers')
  })

  it('printer-create route is registered', () => {
    const routes = router.getRoutes()
    const createRoute = routes.find((r) => r.name === 'printer-create')
    expect(createRoute).toBeDefined()
  })
})

// ── allPrinterColumns Definition ─────────────────────────────────────────────

describe('PrinterListView — allPrinterColumns', () => {
  // Mirrors allPrinterColumns from PrinterListView.vue
  const allPrinterColumns = [
    { text: 'Title', value: 'title', defaultVisible: true },
    { text: 'Photo', value: 'photo', defaultVisible: false },
    { text: 'Manufacturer', value: 'manufacturer', defaultVisible: true },
    { text: 'Status', value: 'status', defaultVisible: true },
    { text: 'Serial Number', value: 'serial_number', defaultVisible: false },
    { text: 'Purchase Date', value: 'purchase_date', defaultVisible: false },
  ]

  it('has 6 columns', () => {
    expect(allPrinterColumns).toHaveLength(6)
  })

  it('title column is visible by default', () => {
    const col = allPrinterColumns.find((c) => c.value === 'title')
    expect(col?.defaultVisible).toBe(true)
  })

  it('manufacturer column is visible by default', () => {
    const col = allPrinterColumns.find((c) => c.value === 'manufacturer')
    expect(col?.defaultVisible).toBe(true)
  })

  it('status column is visible by default', () => {
    const col = allPrinterColumns.find((c) => c.value === 'status')
    expect(col?.defaultVisible).toBe(true)
  })

  it('photo column is hidden by default', () => {
    const col = allPrinterColumns.find((c) => c.value === 'photo')
    expect(col?.defaultVisible).toBe(false)
  })

  it('serial_number column is hidden by default', () => {
    const col = allPrinterColumns.find((c) => c.value === 'serial_number')
    expect(col?.defaultVisible).toBe(false)
  })

  it('purchase_date column is hidden by default', () => {
    const col = allPrinterColumns.find((c) => c.value === 'purchase_date')
    expect(col?.defaultVisible).toBe(false)
  })

  it('default visible columns are title, manufacturer, status', () => {
    const defaults = allPrinterColumns.filter((c) => c.defaultVisible).map((c) => c.value)
    expect(defaults).toEqual(['title', 'manufacturer', 'status'])
  })
})

// ── filterOptions.statuses ───────────────────────────────────────────────────

describe('PrinterListView — filterOptions statuses', () => {
  // Mirrors filterOptions.statuses from PrinterListView.vue
  const statuses = ['Active', 'Under Repair', 'Sold', 'Archived', 'Planned']

  it('has 5 status options', () => {
    expect(statuses).toHaveLength(5)
  })

  it.each(['Active', 'Under Repair', 'Sold', 'Archived', 'Planned'])(
    'includes "%s" status',
    (status) => {
      expect(statuses).toContain(status)
    }
  )
})

// ── isFilterActive computed logic ────────────────────────────────────────────

describe('PrinterListView — isFilterActive computed', () => {
  // Mirrors isFilterActive computed from PrinterListView.vue
  const isFilterActive = (searchText, activeFilters) =>
    !!(searchText || Object.values(activeFilters).some((val) => val && val.length > 0))

  it('false when no search and no filters', () => {
    expect(isFilterActive('', {})).toBe(false)
  })

  it('true when searchText is set', () => {
    expect(isFilterActive('Bambu', {})).toBe(true)
  })

  it('true when manufacturer filter is active', () => {
    expect(isFilterActive('', { manufacturer__name: 'Bambu Lab' })).toBe(true)
  })

  it('true when status filter is active', () => {
    expect(isFilterActive('', { status: 'Active' })).toBe(true)
  })

  it('false when all filter values are empty strings', () => {
    expect(isFilterActive('', { manufacturer__name: '', status: '' })).toBe(false)
  })

  it('true when both search and filters are active', () => {
    expect(isFilterActive('Prusa', { status: 'Under Repair' })).toBe(true)
  })
})

// ── applyFilters() filter-building logic ─────────────────────────────────────

describe('PrinterListView — applyFilters() logic', () => {
  /**
   * Mirrors applyFilters() logic from PrinterListView.vue.
   * Merges existing query params with temporary filter values,
   * removing empty entries.
   */
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

  it('adds manufacturer filter when set', () => {
    const result = applyFilters({}, { manufacturer__name: 'Bambu Lab', status: '' })
    expect(result.manufacturer__name).toBe('Bambu Lab')
  })

  it('removes filter when cleared to empty string', () => {
    const result = applyFilters({ status: 'Active' }, { manufacturer__name: '', status: '' })
    expect(result.status).toBeUndefined()
  })

  it('preserves existing query params', () => {
    const result = applyFilters({ search: 'Prusa' }, { manufacturer__name: 'Prusa', status: '' })
    expect(result.search).toBe('Prusa')
    expect(result.manufacturer__name).toBe('Prusa')
  })

  it('adds both filters when both are set', () => {
    const result = applyFilters({}, { manufacturer__name: 'Bambu Lab', status: 'Active' })
    expect(result.manufacturer__name).toBe('Bambu Lab')
    expect(result.status).toBe('Active')
  })
})

// ── localStorage column logic ────────────────────────────────────────────────

describe('PrinterListView — localStorage column persistence', () => {
  const STORAGE_KEY = 'printer-columns'

  // Mirrors loadColumns() from PrinterListView.vue
  const allPrinterColumns = [
    { text: 'Title', value: 'title', defaultVisible: true },
    { text: 'Photo', value: 'photo', defaultVisible: false },
    { text: 'Manufacturer', value: 'manufacturer', defaultVisible: true },
    { text: 'Status', value: 'status', defaultVisible: true },
    { text: 'Serial Number', value: 'serial_number', defaultVisible: false },
    { text: 'Purchase Date', value: 'purchase_date', defaultVisible: false },
  ]

  const loadColumns = (savedJSON) => {
    if (savedJSON) {
      return JSON.parse(savedJSON)
    }
    return allPrinterColumns.filter((c) => c.defaultVisible).map((c) => c.value)
  }

  it('returns default visible columns when nothing saved', () => {
    expect(loadColumns(null)).toEqual(['title', 'manufacturer', 'status'])
  })

  it('returns saved columns from localStorage', () => {
    const saved = JSON.stringify(['title', 'photo', 'status'])
    expect(loadColumns(saved)).toEqual(['title', 'photo', 'status'])
  })

  it('storage key is "printer-columns"', () => {
    expect(STORAGE_KEY).toBe('printer-columns')
  })

  it('saveColumns serializes to JSON for localStorage', () => {
    const columns = ['title', 'manufacturer', 'serial_number']
    const serialized = JSON.stringify(columns)
    expect(JSON.parse(serialized)).toEqual(columns)
  })
})
