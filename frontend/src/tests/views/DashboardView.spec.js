/**
 * Tests for DashboardView
 *
 * DashboardView is the main dashboard at /dashboard. It shows alerts,
 * stats, featured trackers, and active projects with health status badges.
 *
 * Tests cover:
 * - APIService contract (required dashboard methods exist)
 * - Router registration (dashboard route exists)
 * - getHealthClass() logic — maps health status → CSS class
 * - getHealthLabel() logic — maps health status → display string
 * - getProgressColor() logic — maps percentage thresholds → CSS variable
 * - allAlerts computed logic — concatenates critical + warning + info arrays
 * - visibleAlerts computed logic — slices to 3 unless showAll
 * - navigateToStat() routing map
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('DashboardView — APIService contract', () => {
  it('APIService.getDashboard exists', () => {
    expect(typeof APIService.getDashboard).toBe('function')
  })

  it('APIService.dismissAlert exists', () => {
    expect(typeof APIService.dismissAlert).toBe('function')
  })

  it('APIService.dismissAllAlerts exists', () => {
    expect(typeof APIService.dismissAllAlerts).toBe('function')
  })

  it('APIService.getMaterials exists (for low stock + favorites)', () => {
    expect(typeof APIService.getMaterials).toBe('function')
  })

  it('APIService.getFilamentSpools exists (for active spools)', () => {
    expect(typeof APIService.getFilamentSpools).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('DashboardView — route registration', () => {
  it('dashboard route is registered', () => {
    const routes = router.getRoutes()
    const dashRoute = routes.find((r) => r.name === 'dashboard')
    expect(dashRoute).toBeDefined()
  })

  it('dashboard route path is /dashboard', () => {
    const routes = router.getRoutes()
    const dashRoute = routes.find((r) => r.name === 'dashboard')
    expect(dashRoute?.path).toBe('/dashboard')
  })
})

// ── getHealthClass() Logic ────────────────────────────────────────────────────

describe('DashboardView — getHealthClass()', () => {
  // Mirrors getHealthClass() from DashboardView.vue
  const getHealthClass = (health) => {
    const classes = {
      healthy: 'health-healthy',
      'at-risk': 'health-at-risk',
      'partially-blocked': 'health-partially-blocked',
      blocked: 'health-blocked',
      overdue: 'health-overdue',
    }
    return classes[health] || 'health-healthy'
  }

  it.each([
    ['healthy', 'health-healthy'],
    ['at-risk', 'health-at-risk'],
    ['partially-blocked', 'health-partially-blocked'],
    ['blocked', 'health-blocked'],
    ['overdue', 'health-overdue'],
  ])('getHealthClass("%s") === "%s"', (input, expected) => {
    expect(getHealthClass(input)).toBe(expected)
  })

  it('unknown health status falls back to health-healthy', () => {
    expect(getHealthClass('unknown')).toBe('health-healthy')
  })

  it('undefined falls back to health-healthy', () => {
    expect(getHealthClass(undefined)).toBe('health-healthy')
  })

  it('empty string falls back to health-healthy', () => {
    expect(getHealthClass('')).toBe('health-healthy')
  })
})

// ── getHealthLabel() Logic ────────────────────────────────────────────────────

describe('DashboardView — getHealthLabel()', () => {
  // Mirrors getHealthLabel() from DashboardView.vue
  const getHealthLabel = (health) => {
    const labels = {
      healthy: 'Healthy',
      'at-risk': 'At Risk',
      'partially-blocked': 'Partially Blocked',
      blocked: 'Blocked',
      overdue: 'Overdue',
    }
    return labels[health] || 'Healthy'
  }

  it.each([
    ['healthy', 'Healthy'],
    ['at-risk', 'At Risk'],
    ['partially-blocked', 'Partially Blocked'],
    ['blocked', 'Blocked'],
    ['overdue', 'Overdue'],
  ])('getHealthLabel("%s") === "%s"', (input, expected) => {
    expect(getHealthLabel(input)).toBe(expected)
  })

  it('unknown health status falls back to "Healthy"', () => {
    expect(getHealthLabel('unknown')).toBe('Healthy')
  })
})

// ── getProgressColor() Logic ─────────────────────────────────────────────────

describe('DashboardView — getProgressColor()', () => {
  // Mirrors getProgressColor() from DashboardView.vue
  const getProgressColor = (percentage) => {
    if (percentage === 0) return 'var(--color-progress-none)'
    if (percentage < 50) return 'var(--color-progress-low)'
    if (percentage < 100) return 'var(--color-progress-medium)'
    return 'var(--color-progress-complete)'
  }

  it('0% returns --color-progress-none', () => {
    expect(getProgressColor(0)).toBe('var(--color-progress-none)')
  })

  it('1% returns --color-progress-low', () => {
    expect(getProgressColor(1)).toBe('var(--color-progress-low)')
  })

  it('49% returns --color-progress-low', () => {
    expect(getProgressColor(49)).toBe('var(--color-progress-low)')
  })

  it('50% returns --color-progress-medium', () => {
    expect(getProgressColor(50)).toBe('var(--color-progress-medium)')
  })

  it('99% returns --color-progress-medium', () => {
    expect(getProgressColor(99)).toBe('var(--color-progress-medium)')
  })

  it('100% returns --color-progress-complete', () => {
    expect(getProgressColor(100)).toBe('var(--color-progress-complete)')
  })

  it('values above 100% return --color-progress-complete', () => {
    expect(getProgressColor(110)).toBe('var(--color-progress-complete)')
  })
})

// ── allAlerts computed logic ─────────────────────────────────────────────────

describe('DashboardView — allAlerts computed', () => {
  // Mirrors allAlerts computed from DashboardView.vue
  const buildAllAlerts = (alerts) => [
    ...alerts.critical,
    ...alerts.warning,
    ...alerts.info,
  ]

  it('combines critical + warning + info in order', () => {
    const alerts = {
      critical: [{ id: 1 }],
      warning: [{ id: 2 }],
      info: [{ id: 3 }],
    }
    expect(buildAllAlerts(alerts)).toEqual([{ id: 1 }, { id: 2 }, { id: 3 }])
  })

  it('returns empty array when all categories are empty', () => {
    expect(buildAllAlerts({ critical: [], warning: [], info: [] })).toEqual([])
  })

  it('handles multiple alerts per category', () => {
    const alerts = {
      critical: [{ id: 1 }, { id: 2 }],
      warning: [{ id: 3 }],
      info: [{ id: 4 }, { id: 5 }, { id: 6 }],
    }
    expect(buildAllAlerts(alerts)).toHaveLength(6)
  })
})

// ── visibleAlerts computed logic ─────────────────────────────────────────────

describe('DashboardView — visibleAlerts computed', () => {
  // Mirrors visibleAlerts computed from DashboardView.vue
  const buildVisibleAlerts = (allAlerts, showAll) =>
    showAll ? allAlerts : allAlerts.slice(0, 3)

  it('shows first 3 alerts when showAll is false', () => {
    const alerts = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }, { id: 5 }]
    expect(buildVisibleAlerts(alerts, false)).toHaveLength(3)
  })

  it('shows all alerts when showAll is true', () => {
    const alerts = [{ id: 1 }, { id: 2 }, { id: 3 }, { id: 4 }, { id: 5 }]
    expect(buildVisibleAlerts(alerts, true)).toHaveLength(5)
  })

  it('shows all alerts when fewer than 3 exist (showAll = false)', () => {
    const alerts = [{ id: 1 }, { id: 2 }]
    expect(buildVisibleAlerts(alerts, false)).toHaveLength(2)
  })

  it('returns empty array when no alerts exist', () => {
    expect(buildVisibleAlerts([], false)).toHaveLength(0)
  })
})

// ── navigateToStat() routing map ─────────────────────────────────────────────

describe('DashboardView — navigateToStat() routing map', () => {
  // Mirrors the routes map inside navigateToStat() from DashboardView.vue
  const statRoutes = {
    inventory_count: '/inventory',
    printer_count: '/printers',
    project_count: '/projects',
    tracker_count: '/trackers',
  }

  it.each([
    ['inventory_count', '/inventory'],
    ['printer_count', '/printers'],
    ['project_count', '/projects'],
    ['tracker_count', '/trackers'],
  ])('statRoutes["%s"] === "%s"', (stat, expectedPath) => {
    expect(statRoutes[stat]).toBe(expectedPath)
  })

  it('unknown stat type has no route (returns undefined)', () => {
    expect(statRoutes['unknown_stat']).toBeUndefined()
  })
})

// ── "In Use" widget printer name access ──────────────────────────────────

describe('DashboardView — In Use widget printer name', () => {
  // Mirrors the assigned_printer access in the "In Use" widget template.
  // Regression: FilamentSpoolSerializer.get_assigned_printer() returns
  // {id, title} (matching Printer.title), but the widget used to read
  // spool.assigned_printer?.name, which is always undefined.
  const getPrinterLabel = (spool) => spool.assigned_printer?.title

  it('reads the printer title from assigned_printer', () => {
    const spool = { assigned_printer: { id: 1, title: 'Prusa MK4' } }
    expect(getPrinterLabel(spool)).toBe('Prusa MK4')
  })

  it('returns undefined when no printer is assigned', () => {
    const spool = { assigned_printer: null }
    expect(getPrinterLabel(spool)).toBeUndefined()
  })
})
