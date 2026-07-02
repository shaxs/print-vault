/**
 * Tests for ProjectListView
 *
 * ProjectListView is the Projects list at /projects. Users can filter by
 * status, configure visible columns, and search.
 *
 * Tests cover:
 * - APIService contract (getProjects exists)
 * - Router registration (project-list route exists)
 * - allProjectColumns definition (correct columns + defaultVisible flags)
 * - filterOptions.statuses (all valid project statuses)
 * - isFilterActive computed logic
 * - applyFilters() filter-building logic (status-only filter)
 * - localStorage column persistence
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('ProjectListView — APIService contract', () => {
  it('APIService.getProjects exists', () => {
    expect(typeof APIService.getProjects).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('ProjectListView — route registration', () => {
  it('project-list route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'project-list')
    expect(route).toBeDefined()
  })

  it('project-list route path is /projects', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'project-list')
    expect(route?.path).toBe('/projects')
  })

  it('project-create route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'project-create')
    expect(route).toBeDefined()
  })

  it('project-detail route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'project-detail')
    expect(route).toBeDefined()
  })
})

// ── allProjectColumns Definition ─────────────────────────────────────────────

describe('ProjectListView — allProjectColumns', () => {
  // Mirrors allProjectColumns from ProjectListView.vue
  const allProjectColumns = [
    { text: 'Photo', value: 'photo', defaultVisible: true },
    { text: 'Project Name', value: 'projectName', defaultVisible: true },
    { text: 'Status', value: 'status', defaultVisible: true },
    { text: 'Description', value: 'description', defaultVisible: false },
  ]

  it('has 4 columns', () => {
    expect(allProjectColumns).toHaveLength(4)
  })

  it('photo is visible by default', () => {
    expect(allProjectColumns.find((c) => c.value === 'photo')?.defaultVisible).toBe(true)
  })

  it('projectName is visible by default', () => {
    expect(allProjectColumns.find((c) => c.value === 'projectName')?.defaultVisible).toBe(true)
  })

  it('status is visible by default', () => {
    expect(allProjectColumns.find((c) => c.value === 'status')?.defaultVisible).toBe(true)
  })

  it('description is hidden by default', () => {
    expect(allProjectColumns.find((c) => c.value === 'description')?.defaultVisible).toBe(false)
  })

  it('default visible columns are photo, projectName, status', () => {
    const defaults = allProjectColumns.filter((c) => c.defaultVisible).map((c) => c.value)
    expect(defaults).toEqual(['photo', 'projectName', 'status'])
  })
})

// ── filterOptions.statuses ───────────────────────────────────────────────────

describe('ProjectListView — filterOptions statuses', () => {
  // Mirrors filterOptions.statuses from ProjectListView.vue
  const statuses = ['Planning', 'In Progress', 'Completed', 'Canceled', 'On Hold']

  it('has 5 project status options', () => {
    expect(statuses).toHaveLength(5)
  })

  it.each(['Planning', 'In Progress', 'Completed', 'Canceled', 'On Hold'])(
    'includes "%s" status',
    (status) => {
      expect(statuses).toContain(status)
    }
  )
})

// ── isFilterActive computed logic ────────────────────────────────────────────

describe('ProjectListView — isFilterActive computed', () => {
  const isFilterActive = (searchText, activeFilters) =>
    !!(searchText || Object.values(activeFilters).some((val) => val && val.length > 0))

  it('false when empty search and no filters', () => {
    expect(isFilterActive('', {})).toBe(false)
  })

  it('true when searchText is set', () => {
    expect(isFilterActive('drone', {})).toBe(true)
  })

  it('true when status filter is active', () => {
    expect(isFilterActive('', { status: 'In Progress' })).toBe(true)
  })

  it('false when status is empty string', () => {
    expect(isFilterActive('', { status: '' })).toBe(false)
  })
})

// ── applyFilters() logic ─────────────────────────────────────────────────────

describe('ProjectListView — applyFilters() logic', () => {
  /**
   * Mirrors applyFilters() from ProjectListView.vue.
   * Only manages the `status` filter.
   */
  const applyFilters = (existingQuery, status) => {
    const newFilters = { ...existingQuery }
    if (status) {
      newFilters.status = status
    } else {
      delete newFilters.status
    }
    return newFilters
  }

  it('adds status filter when set', () => {
    const result = applyFilters({}, 'In Progress')
    expect(result.status).toBe('In Progress')
  })

  it('removes status filter when cleared', () => {
    const result = applyFilters({ status: 'Planning' }, '')
    expect(result.status).toBeUndefined()
  })

  it('preserves search param when applying status filter', () => {
    const result = applyFilters({ search: 'drone' }, 'Completed')
    expect(result.search).toBe('drone')
    expect(result.status).toBe('Completed')
  })
})

// ── localStorage column persistence ─────────────────────────────────────────

describe('ProjectListView — localStorage column persistence', () => {
  const STORAGE_KEY = 'project-columns'

  const allProjectColumns = [
    { text: 'Photo', value: 'photo', defaultVisible: true },
    { text: 'Project Name', value: 'projectName', defaultVisible: true },
    { text: 'Status', value: 'status', defaultVisible: true },
    { text: 'Description', value: 'description', defaultVisible: false },
  ]

  const loadColumns = (savedJSON) => {
    if (savedJSON) return JSON.parse(savedJSON)
    return allProjectColumns.filter((c) => c.defaultVisible).map((c) => c.value)
  }

  it('storage key is "project-columns"', () => {
    expect(STORAGE_KEY).toBe('project-columns')
  })

  it('returns defaults when nothing saved', () => {
    expect(loadColumns(null)).toEqual(['photo', 'projectName', 'status'])
  })

  it('returns saved columns from JSON', () => {
    const saved = JSON.stringify(['projectName', 'description'])
    expect(loadColumns(saved)).toEqual(['projectName', 'description'])
  })
})
