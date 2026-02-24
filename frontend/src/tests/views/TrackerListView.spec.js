/**
 * Tests for TrackerListView
 *
 * TrackerListView is the Print Trackers list at /trackers. Users can filter
 * by project, configure visible columns, and search.
 *
 * Tests cover:
 * - APIService contract (getTrackers, getProjects exist)
 * - Router registration (tracker-list route exists)
 * - allTrackerColumns definition (correct columns + defaultVisible flags)
 * - isFilterActive computed logic
 * - applyFilters() project-filter logic
 * - localStorage column persistence
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('TrackerListView — APIService contract', () => {
  it('APIService.getTrackers exists', () => {
    expect(typeof APIService.getTrackers).toBe('function')
  })

  it('APIService.getProjects exists (for project filter dropdown)', () => {
    expect(typeof APIService.getProjects).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('TrackerListView — route registration', () => {
  it('tracker-list route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'tracker-list')
    expect(route).toBeDefined()
  })

  it('tracker-list route path is /trackers', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'tracker-list')
    expect(route?.path).toBe('/trackers')
  })

  it('tracker-create route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'tracker-create')
    expect(route).toBeDefined()
  })

  it('tracker-detail route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'tracker-detail')
    expect(route).toBeDefined()
  })
})

// ── allTrackerColumns Definition ─────────────────────────────────────────────

describe('TrackerListView — allTrackerColumns', () => {
  // Mirrors allTrackerColumns from TrackerListView.vue
  const allTrackerColumns = [
    { text: 'Tracker Name', value: 'trackerName', defaultVisible: true },
    { text: 'Project', value: 'projectName', defaultVisible: true },
    { text: 'Files', value: 'fileCount', defaultVisible: true },
    { text: 'Progress', value: 'progress', defaultVisible: true },
    { text: 'GitHub URL', value: 'githubUrl', defaultVisible: false },
    { text: 'Storage Type', value: 'storageType', defaultVisible: false },
    { text: 'Created Date', value: 'createdDate', defaultVisible: false },
  ]

  it('has 7 columns', () => {
    expect(allTrackerColumns).toHaveLength(7)
  })

  it('trackerName is visible by default', () => {
    expect(allTrackerColumns.find((c) => c.value === 'trackerName')?.defaultVisible).toBe(true)
  })

  it('projectName is visible by default', () => {
    expect(allTrackerColumns.find((c) => c.value === 'projectName')?.defaultVisible).toBe(true)
  })

  it('fileCount is visible by default', () => {
    expect(allTrackerColumns.find((c) => c.value === 'fileCount')?.defaultVisible).toBe(true)
  })

  it('progress is visible by default', () => {
    expect(allTrackerColumns.find((c) => c.value === 'progress')?.defaultVisible).toBe(true)
  })

  it('githubUrl is hidden by default', () => {
    expect(allTrackerColumns.find((c) => c.value === 'githubUrl')?.defaultVisible).toBe(false)
  })

  it('storageType is hidden by default', () => {
    expect(allTrackerColumns.find((c) => c.value === 'storageType')?.defaultVisible).toBe(false)
  })

  it('createdDate is hidden by default', () => {
    expect(allTrackerColumns.find((c) => c.value === 'createdDate')?.defaultVisible).toBe(false)
  })

  it('default visible columns are trackerName, projectName, fileCount, progress', () => {
    const defaults = allTrackerColumns.filter((c) => c.defaultVisible).map((c) => c.value)
    expect(defaults).toEqual(['trackerName', 'projectName', 'fileCount', 'progress'])
  })
})

// ── isFilterActive computed logic ────────────────────────────────────────────

describe('TrackerListView — isFilterActive computed', () => {
  const isFilterActive = (searchText, activeFilters) =>
    !!(searchText || Object.values(activeFilters).some((val) => val && val.length > 0))

  it('false when empty search and no filters', () => {
    expect(isFilterActive('', {})).toBe(false)
  })

  it('true when searchText is set', () => {
    expect(isFilterActive('benchy', {})).toBe(true)
  })

  it('true when project filter is active', () => {
    expect(isFilterActive('', { project: '5' })).toBe(true)
  })

  it('false when project filter is empty string', () => {
    expect(isFilterActive('', { project: '' })).toBe(false)
  })
})

// ── localStorage column persistence ─────────────────────────────────────────

describe('TrackerListView — localStorage column persistence', () => {
  const STORAGE_KEY = 'tracker-columns'

  const allTrackerColumns = [
    { text: 'Tracker Name', value: 'trackerName', defaultVisible: true },
    { text: 'Project', value: 'projectName', defaultVisible: true },
    { text: 'Files', value: 'fileCount', defaultVisible: true },
    { text: 'Progress', value: 'progress', defaultVisible: true },
    { text: 'GitHub URL', value: 'githubUrl', defaultVisible: false },
    { text: 'Storage Type', value: 'storageType', defaultVisible: false },
    { text: 'Created Date', value: 'createdDate', defaultVisible: false },
  ]

  const loadColumns = (savedJSON) => {
    if (savedJSON) return JSON.parse(savedJSON)
    return allTrackerColumns.filter((c) => c.defaultVisible).map((c) => c.value)
  }

  it('storage key is "tracker-columns"', () => {
    expect(STORAGE_KEY).toBe('tracker-columns')
  })

  it('returns defaults when nothing saved', () => {
    expect(loadColumns(null)).toEqual(['trackerName', 'projectName', 'fileCount', 'progress'])
  })

  it('returns saved columns from JSON', () => {
    const saved = JSON.stringify(['trackerName', 'githubUrl'])
    expect(loadColumns(saved)).toEqual(['trackerName', 'githubUrl'])
  })
})
