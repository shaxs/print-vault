/**
 * useColumnManager.spec.js
 *
 * Tests for the useColumnManager composable in src/composables/useColumnManager.js.
 * Covers: getDefaultVisible fallback, localStorage persistence, invalid JSON recovery,
 * unknown value filtering, and saveColumns behavior.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { useColumnManager } from '../../composables/useColumnManager'

// ---------------------------------------------------------------------------
// Test data helpers
// ---------------------------------------------------------------------------

const ALL_COLUMNS = [
  { value: 'name', label: 'Name', defaultVisible: true },
  { value: 'brand', label: 'Brand', defaultVisible: true },
  { value: 'material', label: 'Material', defaultVisible: false },
  { value: 'color', label: 'Color', defaultVisible: false },
  { value: 'status', label: 'Status', defaultVisible: true },
]

const STORAGE_KEY = 'test_column_manager'

// ---------------------------------------------------------------------------
// localStorage mock helpers
// vi.stubGlobal is required because happy-dom's localStorage does not inherit
// from Storage.prototype in a way that allows prototype-level spying.
// ---------------------------------------------------------------------------

let mockStore = {}

beforeEach(() => {
  mockStore = {}
  vi.stubGlobal('localStorage', {
    getItem: vi.fn((key) => mockStore[key] ?? null),
    setItem: vi.fn((key, value) => {
      mockStore[key] = value
    }),
    removeItem: vi.fn((key) => {
      delete mockStore[key]
    }),
    clear: vi.fn(() => {
      mockStore = {}
    }),
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// ---------------------------------------------------------------------------

describe('useColumnManager – getDefaultVisible (no saved state)', () => {
  it('returns only columns with defaultVisible=true', () => {
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns.value).toEqual(['name', 'brand', 'status'])
  })

  it('does not include columns with defaultVisible=false', () => {
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns.value).not.toContain('material')
    expect(visibleColumns.value).not.toContain('color')
  })

  it('returns empty array when no columns have defaultVisible=true', () => {
    const cols = [
      { value: 'a', defaultVisible: false },
      { value: 'b', defaultVisible: false },
    ]
    const { visibleColumns } = useColumnManager(STORAGE_KEY, cols)
    expect(visibleColumns.value).toEqual([])
  })

  it('returns all columns when all have defaultVisible=true', () => {
    const cols = [
      { value: 'x', defaultVisible: true },
      { value: 'y', defaultVisible: true },
    ]
    const { visibleColumns } = useColumnManager(STORAGE_KEY, cols)
    expect(visibleColumns.value).toEqual(['x', 'y'])
  })
})

// ---------------------------------------------------------------------------

describe('useColumnManager – loadInitialColumns from localStorage', () => {
  it('loads saved column values from localStorage', () => {
    mockStore[STORAGE_KEY] = JSON.stringify(['brand', 'status'])
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns.value).toEqual(['brand', 'status'])
  })

  it('filters out saved values that no longer exist in allColumns', () => {
    mockStore[STORAGE_KEY] = JSON.stringify(['brand', 'deleted_column', 'status'])
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns.value).not.toContain('deleted_column')
    expect(visibleColumns.value).toContain('brand')
    expect(visibleColumns.value).toContain('status')
  })

  it('falls back to defaultVisible when localStorage contains invalid JSON', () => {
    mockStore[STORAGE_KEY] = 'not-valid-json}}}'
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns.value).toEqual(['name', 'brand', 'status'])
    consoleSpy.mockRestore()
  })

  it('falls back to defaultVisible when localStorage returns null', () => {
    // localStorage.getItem returns null when key doesn't exist
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns.value).toEqual(['name', 'brand', 'status'])
  })

  it('returns empty array from localStorage when saved value is []', () => {
    mockStore[STORAGE_KEY] = JSON.stringify([])
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns.value).toEqual([])
  })

  it('handles localStorage with all valid columns saved', () => {
    const allValues = ALL_COLUMNS.map((c) => c.value)
    mockStore[STORAGE_KEY] = JSON.stringify(allValues)
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns.value).toEqual(allValues)
  })
})

// ---------------------------------------------------------------------------

describe('useColumnManager – saveColumns', () => {
  it('updates visibleColumns.value', () => {
    const { visibleColumns, saveColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    saveColumns(['material', 'color'])
    expect(visibleColumns.value).toEqual(['material', 'color'])
  })

  it('persists to localStorage', () => {
    const { saveColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    saveColumns(['name', 'color'])
    expect(JSON.parse(mockStore[STORAGE_KEY])).toEqual(['name', 'color'])
  })

  it('overwrites previous localStorage value', () => {
    mockStore[STORAGE_KEY] = JSON.stringify(['brand'])
    const { saveColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    saveColumns(['status', 'material'])
    expect(JSON.parse(mockStore[STORAGE_KEY])).toEqual(['status', 'material'])
  })

  it('saves empty array to localStorage', () => {
    const { saveColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    saveColumns([])
    expect(JSON.parse(mockStore[STORAGE_KEY])).toEqual([])
  })

  it('uses the correct storage key', () => {
    const { saveColumns } = useColumnManager('custom_key', ALL_COLUMNS)
    saveColumns(['name'])
    expect(mockStore['custom_key']).toBe(JSON.stringify(['name']))
    // Different key should not be affected
    expect(mockStore[STORAGE_KEY]).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------

describe('useColumnManager – return shape', () => {
  it('returns visibleColumns and saveColumns', () => {
    const result = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(result).toHaveProperty('visibleColumns')
    expect(result).toHaveProperty('saveColumns')
  })

  it('visibleColumns is a Vue ref (has .value)', () => {
    const { visibleColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(visibleColumns).toHaveProperty('value')
  })

  it('saveColumns is a function', () => {
    const { saveColumns } = useColumnManager(STORAGE_KEY, ALL_COLUMNS)
    expect(typeof saveColumns).toBe('function')
  })
})

// ---------------------------------------------------------------------------

describe('useColumnManager – isolation between storage keys', () => {
  it('different storageKey instances do not share state', () => {
    mockStore['key_a'] = JSON.stringify(['name'])
    mockStore['key_b'] = JSON.stringify(['status', 'material'])

    const { visibleColumns: colsA } = useColumnManager('key_a', ALL_COLUMNS)
    const { visibleColumns: colsB } = useColumnManager('key_b', ALL_COLUMNS)

    expect(colsA.value).toEqual(['name'])
    expect(colsB.value).toEqual(['status', 'material'])
  })
})
