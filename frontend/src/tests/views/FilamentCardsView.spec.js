/**
 * Tests for FilamentCardsView (/filaments/cards)
 *
 * FilamentCardsView shows filament spools in a card grid.
 * It supports inline status filtering via a dropdown and real-time text search.
 * Local computed `filteredSpools` filters client-side (after API fetch).
 *
 * Tests cover:
 * - APIService contract (getFilamentSpools exists)
 * - Router registration (filament-cards route)
 * - statusOptions definition (7 entries, first = "All Statuses")
 * - getStatusClass() CSS class mapping
 * - getStatusLabel() label lookup + "(Unopened)" suffix stripping
 * - filteredSpools computed: text search across name/colorName/brand
 * - filteredSpools computed: status filter
 * - filteredSpools computed: combined search + status filter
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('FilamentCardsView — APIService contract', () => {
  it('APIService.getFilamentSpools exists', () => {
    expect(typeof APIService.getFilamentSpools).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('FilamentCardsView — route registration', () => {
  it('filament-cards route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'filament-cards')
    expect(route).toBeDefined()
  })

  it('filament-cards route path is /filaments/cards', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'filament-cards')
    expect(route?.path).toBe('/filaments/cards')
  })
})

// ── statusOptions Definition ──────────────────────────────────────────────────

describe('FilamentCardsView — statusOptions', () => {
  // Mirrors statusOptions from FilamentCardsView.vue
  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'new', label: 'New (Unopened)' },
    { value: 'opened', label: 'Opened' },
    { value: 'in_use', label: 'In Use' },
    { value: 'low', label: 'Low' },
    { value: 'empty', label: 'Empty' },
    { value: 'archived', label: 'Archived' },
  ]

  it('has 7 status options', () => {
    expect(statusOptions).toHaveLength(7)
  })

  it('first option is "All Statuses" with empty value', () => {
    expect(statusOptions[0]).toEqual({ value: '', label: 'All Statuses' })
  })

  it("new status label is 'New (Unopened)'", () => {
    const opt = statusOptions.find((s) => s.value === 'new')
    expect(opt?.label).toBe('New (Unopened)')
  })

  it("includes all 6 non-empty status values", () => {
    const values = statusOptions.filter((s) => s.value).map((s) => s.value)
    expect(values).toEqual(['new', 'opened', 'in_use', 'low', 'empty', 'archived'])
  })
})

// ── getStatusClass() Mapping ──────────────────────────────────────────────────

describe('FilamentCardsView — getStatusClass()', () => {
  // Mirrors getStatusClass() from FilamentCardsView.vue
  const getStatusClass = (status) => {
    const statusMap = {
      new: 'status-new',
      opened: 'status-opened',
      in_use: 'status-in-use',
      low: 'status-low',
      empty: 'status-empty',
      archived: 'status-archived',
    }
    return statusMap[status] || ''
  }

  it("maps 'new' → 'status-new'", () => {
    expect(getStatusClass('new')).toBe('status-new')
  })

  it("maps 'opened' → 'status-opened'", () => {
    expect(getStatusClass('opened')).toBe('status-opened')
  })

  it("maps 'in_use' → 'status-in-use'", () => {
    expect(getStatusClass('in_use')).toBe('status-in-use')
  })

  it("maps 'low' → 'status-low'", () => {
    expect(getStatusClass('low')).toBe('status-low')
  })

  it("maps 'empty' → 'status-empty'", () => {
    expect(getStatusClass('empty')).toBe('status-empty')
  })

  it("maps 'archived' → 'status-archived'", () => {
    expect(getStatusClass('archived')).toBe('status-archived')
  })

  it("returns '' for unknown status", () => {
    expect(getStatusClass('unknown')).toBe('')
  })

  it("returns '' for empty string", () => {
    expect(getStatusClass('')).toBe('')
  })
})

// ── getStatusLabel() Logic ────────────────────────────────────────────────────

describe('FilamentCardsView — getStatusLabel()', () => {
  // Mirrors getStatusLabel()
  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'new', label: 'New (Unopened)' },
    { value: 'opened', label: 'Opened' },
    { value: 'in_use', label: 'In Use' },
    { value: 'low', label: 'Low' },
    { value: 'empty', label: 'Empty' },
    { value: 'archived', label: 'Archived' },
  ]
  const getStatusLabel = (status) => {
    const option = statusOptions.find((opt) => opt.value === status)
    return option ? option.label.replace(' (Unopened)', '') : status
  }

  it("'new' → 'New' (strips '(Unopened)')", () => {
    expect(getStatusLabel('new')).toBe('New')
  })

  it("'opened' → 'Opened'", () => {
    expect(getStatusLabel('opened')).toBe('Opened')
  })

  it("'in_use' → 'In Use'", () => {
    expect(getStatusLabel('in_use')).toBe('In Use')
  })

  it("'low' → 'Low'", () => {
    expect(getStatusLabel('low')).toBe('Low')
  })

  it("'empty' → 'Empty'", () => {
    expect(getStatusLabel('empty')).toBe('Empty')
  })

  it("'archived' → 'Archived'", () => {
    expect(getStatusLabel('archived')).toBe('Archived')
  })

  it("unknown status falls back to the raw value", () => {
    expect(getStatusLabel('custom_status')).toBe('custom_status')
  })
})

// ── filteredSpools Computed: Text Search ──────────────────────────────────────

describe('FilamentCardsView — filteredSpools text search', () => {
  // Mirrors filteredSpools computed from FilamentCardsView.vue
  const filterSpools = (spools, searchText, statusFilter) => {
    let filtered = spools

    if (searchText) {
      const search = searchText.toLowerCase()
      filtered = filtered.filter(
        (spool) =>
          spool.filament_type?.color_name?.toLowerCase().includes(search) ||
          spool.filament_type?.name.toLowerCase().includes(search) ||
          spool.filament_type?.brand?.name.toLowerCase().includes(search),
      )
    }

    if (statusFilter) {
      filtered = filtered.filter((spool) => spool.status === statusFilter)
    }

    return filtered
  }

  const spools = [
    {
      id: 1,
      status: 'new',
      filament_type: { name: 'Galaxy Black', color_name: 'Black', brand: { name: 'Hatchbox' } },
    },
    {
      id: 2,
      status: 'in_use',
      filament_type: { name: 'Silk Blue', color_name: 'Blue', brand: { name: 'eSUN' } },
    },
    {
      id: 3,
      status: 'low',
      filament_type: { name: 'Matte White', color_name: 'White', brand: { name: 'Hatchbox' } },
    },
  ]

  it('returns all spools when both filters are empty', () => {
    expect(filterSpools(spools, '', '')).toHaveLength(3)
  })

  it('filters by filament_type.name (case-insensitive)', () => {
    const result = filterSpools(spools, 'galaxy', '')
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(1)
  })

  it('filters by color_name (case-insensitive)', () => {
    const result = filterSpools(spools, 'blue', '')
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(2)
  })

  it('filters by brand name (case-insensitive)', () => {
    const result = filterSpools(spools, 'hatchbox', '')
    expect(result).toHaveLength(2)
  })

  it('returns empty array when search text matches nothing', () => {
    const result = filterSpools(spools, 'PETG', '')
    expect(result).toHaveLength(0)
  })
})

// ── filteredSpools Computed: Status Filter ────────────────────────────────────

describe('FilamentCardsView — filteredSpools status filter', () => {
  const filterSpools = (spools, searchText, statusFilter) => {
    let filtered = spools
    if (searchText) {
      const search = searchText.toLowerCase()
      filtered = filtered.filter(
        (spool) =>
          spool.filament_type?.color_name?.toLowerCase().includes(search) ||
          spool.filament_type?.name.toLowerCase().includes(search) ||
          spool.filament_type?.brand?.name.toLowerCase().includes(search),
      )
    }
    if (statusFilter) {
      filtered = filtered.filter((spool) => spool.status === statusFilter)
    }
    return filtered
  }

  const spools = [
    {
      id: 1,
      status: 'new',
      filament_type: { name: 'Black', color_name: 'Black', brand: { name: 'A' } },
    },
    {
      id: 2,
      status: 'in_use',
      filament_type: { name: 'Blue', color_name: 'Blue', brand: { name: 'B' } },
    },
    {
      id: 3,
      status: 'in_use',
      filament_type: { name: 'Red', color_name: 'Red', brand: { name: 'C' } },
    },
  ]

  it("filters to only 'new' spools", () => {
    const result = filterSpools(spools, '', 'new')
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(1)
  })

  it("filters to multiple 'in_use' spools", () => {
    const result = filterSpools(spools, '', 'in_use')
    expect(result).toHaveLength(2)
  })

  it("returns empty when status matches none", () => {
    const result = filterSpools(spools, '', 'empty')
    expect(result).toHaveLength(0)
  })
})

// ── filteredSpools Computed: Combined ────────────────────────────────────────

describe('FilamentCardsView — filteredSpools combined search + status', () => {
  const filterSpools = (spools, searchText, statusFilter) => {
    let filtered = spools
    if (searchText) {
      const search = searchText.toLowerCase()
      filtered = filtered.filter(
        (spool) =>
          spool.filament_type?.color_name?.toLowerCase().includes(search) ||
          spool.filament_type?.name.toLowerCase().includes(search) ||
          spool.filament_type?.brand?.name.toLowerCase().includes(search),
      )
    }
    if (statusFilter) {
      filtered = filtered.filter((spool) => spool.status === statusFilter)
    }
    return filtered
  }

  const spools = [
    {
      id: 1,
      status: 'new',
      filament_type: { name: 'Hatchbox Black', color_name: 'Black', brand: { name: 'Hatchbox' } },
    },
    {
      id: 2,
      status: 'in_use',
      filament_type: { name: 'Hatchbox Blue', color_name: 'Blue', brand: { name: 'Hatchbox' } },
    },
    {
      id: 3,
      status: 'new',
      filament_type: { name: 'eSUN White', color_name: 'White', brand: { name: 'eSUN' } },
    },
  ]

  it('narrows results using both search text and status filter', () => {
    // search "hatchbox" + status "new" → only spool 1
    const result = filterSpools(spools, 'hatchbox', 'new')
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(1)
  })

  it('returns empty when combined filters match nothing', () => {
    const result = filterSpools(spools, 'esun', 'in_use')
    expect(result).toHaveLength(0)
  })

  it('combined search and status applied independently (AND logic)', () => {
    // "hatchbox" matches 2 spools; status "in_use" of those is only spool 2
    const result = filterSpools(spools, 'hatchbox', 'in_use')
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe(2)
  })
})
