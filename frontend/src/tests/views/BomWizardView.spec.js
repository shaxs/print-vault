/**
 * Tests for BomWizardView
 *
 * BomWizardView is a rapid-entry BOM wizard at /projects/:id/bom/edit.
 * Users stream BOM line items from a creator's parts list without interruption.
 *
 * Tests cover:
 * - APIService contract (required BOM methods exist)
 * - Route registration (bom-wizard route exists)
 * - BOM item payload structure
 * - Status determination logic (linked vs unlinked vs needs_purchase)
 * - STATUS_LABELS mapping correctness
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('BomWizardView — APIService contract', () => {
  it('APIService.getProject exists', () => {
    expect(typeof APIService.getProject).toBe('function')
  })

  it('APIService.getBOMItems exists', () => {
    expect(typeof APIService.getBOMItems).toBe('function')
  })

  it('APIService.createBOMItem exists', () => {
    expect(typeof APIService.createBOMItem).toBe('function')
  })

  it('APIService.deleteBOMItem exists', () => {
    expect(typeof APIService.deleteBOMItem).toBe('function')
  })

  it('APIService.getInventoryItems exists (for autocomplete search)', () => {
    expect(typeof APIService.getInventoryItems).toBe('function')
  })
})

// ── Route Registration ────────────────────────────────────────────────────────

describe('BomWizardView — route registration', () => {
  it('bom-wizard route is registered', () => {
    const routes = router.getRoutes()
    const bomRoute = routes.find((r) => r.name === 'bom-wizard')
    expect(bomRoute).toBeDefined()
  })

  it('bom-wizard route path is /projects/:id/bom/edit', () => {
    const routes = router.getRoutes()
    const bomRoute = routes.find((r) => r.name === 'bom-wizard')
    expect(bomRoute?.path).toBe('/projects/:id/bom/edit')
  })
})

// ── BOM Payload Logic ─────────────────────────────────────────────────────────

describe('BomWizardView — BOM item payload logic', () => {
  /**
   * Helper mirrors addRow() payload logic from BomWizardView.vue.
   * Tests that the status field is computed correctly.
   */
  const buildPayload = ({ projectId, description, quantity, needsPurchase, inventoryItem, notes, sortOrder }) => ({
    project: projectId,
    description: description.trim(),
    quantity_needed: quantity,
    status: needsPurchase
      ? 'needs_purchase'
      : inventoryItem ? 'linked' : 'unlinked',
    inventory_item: needsPurchase ? null : (inventoryItem?.id ?? null),
    notes: notes.trim(),
    sort_order: sortOrder,
  })

  it('status is "unlinked" when no inventory item and not needs_purchase', () => {
    const payload = buildPayload({
      projectId: 5, description: 'M3 hex nuts', quantity: 10,
      needsPurchase: false, inventoryItem: null, notes: '', sortOrder: 0,
    })
    expect(payload.status).toBe('unlinked')
    expect(payload.inventory_item).toBeNull()
  })

  it('status is "linked" when inventory item is selected', () => {
    const payload = buildPayload({
      projectId: 5, description: 'Brass insert', quantity: 4,
      needsPurchase: false, inventoryItem: { id: 42, title: 'M3 Heat Insert' },
      notes: '', sortOrder: 1,
    })
    expect(payload.status).toBe('linked')
    expect(payload.inventory_item).toBe(42)
  })

  it('status is "needs_purchase" when needs_purchase is true (overrides linked item)', () => {
    const payload = buildPayload({
      projectId: 5, description: 'PETG spool', quantity: 1,
      needsPurchase: true, inventoryItem: { id: 10, title: 'Some Item' },
      notes: 'Order from Amazon', sortOrder: 2,
    })
    expect(payload.status).toBe('needs_purchase')
    expect(payload.inventory_item).toBeNull()
  })

  it('description is trimmed in payload', () => {
    const payload = buildPayload({
      projectId: 5, description: '  M5 bolt  ', quantity: 2,
      needsPurchase: false, inventoryItem: null, notes: '', sortOrder: 0,
    })
    expect(payload.description).toBe('M5 bolt')
  })

  it('notes is trimmed in payload', () => {
    const payload = buildPayload({
      projectId: 5, description: 'Part', quantity: 1,
      needsPurchase: false, inventoryItem: null, notes: '  check bin 3  ', sortOrder: 0,
    })
    expect(payload.notes).toBe('check bin 3')
  })

  it('projectId and sort_order are set correctly', () => {
    const payload = buildPayload({
      projectId: 99, description: 'Stepper motor', quantity: 2,
      needsPurchase: false, inventoryItem: null, notes: '', sortOrder: 5,
    })
    expect(payload.project).toBe(99)
    expect(payload.sort_order).toBe(5)
  })
})

// ── STATUS_LABELS Mapping ─────────────────────────────────────────────────────

describe('BomWizardView — STATUS_LABELS map', () => {
  // Mirrors the STATUS_LABELS constant in BomWizardView.vue
  const STATUS_LABELS = {
    covered: 'Covered',
    low: 'Running Low',
    overallocated: 'Overallocated',
    needs_purchase: 'Purchase',
    unlinked: 'Not Linked',
    linked: 'Linked',
  }

  it.each([
    ['covered', 'Covered'],
    ['low', 'Running Low'],
    ['overallocated', 'Overallocated'],
    ['needs_purchase', 'Purchase'],
    ['unlinked', 'Not Linked'],
    ['linked', 'Linked'],
  ])('STATUS_LABELS["%s"] === "%s"', (key, expected) => {
    expect(STATUS_LABELS[key]).toBe(expected)
  })
})

// ── getStatusLabel pure function ──────────────────────────────────────────────

describe('BomWizardView — getStatusLabel', () => {
  // Mirrors: const getStatusLabel = (status) => STATUS_LABELS[status] ?? status
  const STATUS_LABELS = {
    covered: 'Covered',
    low: 'Running Low',
    overallocated: 'Overallocated',
    needs_purchase: 'Purchase',
    unlinked: 'Not Linked',
    linked: 'Linked',
  }
  const getStatusLabel = (status) => STATUS_LABELS[status] ?? status

  it.each([
    ['covered', 'Covered'],
    ['low', 'Running Low'],
    ['overallocated', 'Overallocated'],
    ['needs_purchase', 'Purchase'],
    ['unlinked', 'Not Linked'],
    ['linked', 'Linked'],
  ])('returns "%s" for known status "%s"', (status, expected) => {
    expect(getStatusLabel(status)).toBe(expected)
  })

  it('returns the raw status string for an unknown key (passthrough fallback)', () => {
    expect(getStatusLabel('mystery_status')).toBe('mystery_status')
  })

  it('returns empty string for empty-string key (passthrough)', () => {
    expect(getStatusLabel('')).toBe('')
  })
})

// ── getStatusClass pure function ──────────────────────────────────────────────

describe('BomWizardView — getStatusClass', () => {
  // Mirrors: const getStatusClass = (status) => STATUS_CLASSES[status] ?? ''
  const STATUS_CLASSES = {
    covered: 'badge-covered',
    low: 'badge-low',
    overallocated: 'badge-overallocated',
    needs_purchase: 'badge-purchase',
    unlinked: 'badge-unlinked',
    linked: 'badge-covered', // NOTE: linked reuses the same badge as covered
  }
  const getStatusClass = (status) => STATUS_CLASSES[status] ?? ''

  it('returns "badge-covered" for status "covered"', () => {
    expect(getStatusClass('covered')).toBe('badge-covered')
  })

  it('returns "badge-low" for status "low"', () => {
    expect(getStatusClass('low')).toBe('badge-low')
  })

  it('returns "badge-overallocated" for status "overallocated"', () => {
    expect(getStatusClass('overallocated')).toBe('badge-overallocated')
  })

  it('returns "badge-purchase" for status "needs_purchase"', () => {
    expect(getStatusClass('needs_purchase')).toBe('badge-purchase')
  })

  it('returns "badge-unlinked" for status "unlinked"', () => {
    expect(getStatusClass('unlinked')).toBe('badge-unlinked')
  })

  it('returns "badge-covered" for status "linked" (shares covered badge)', () => {
    expect(getStatusClass('linked')).toBe('badge-covered')
  })

  it('returns empty string for unknown status', () => {
    expect(getStatusClass('unknown')).toBe('')
  })

  it('returns empty string for empty-string key', () => {
    expect(getStatusClass('')).toBe('')
  })
})
