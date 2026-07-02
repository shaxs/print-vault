/**
 * Tests for InlineBOMLinker component
 *
 * InlineBOMLinker is an inline search widget that activates inside a BOM
 * table cell to let users link an existing inventory item to a BOM row.
 *
 * Tests cover:
 * - Default inactive state: shows trigger text
 * - emit('activate') when trigger is clicked
 * - Active state: shows search input, hides trigger
 * - emit('deactivate') when cancel button is clicked
 * - Dropdown results display title + location
 * - Dropdown item title attribute contains full name + location
 * - emit('linked') after a successful item selection
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import InlineBOMLinker from '@/components/InlineBOMLinker.vue'

// ── Mock APIService ────────────────────────────────────────────────────────
vi.mock('@/services/APIService', () => ({
  default: {
    getInventoryItems: vi.fn(),
    updateBOMItem: vi.fn(),
  },
}))

import APIService from '@/services/APIService'

// ── Mock getBoundingClientRect (used by computeDropdownPosition) ───────────
Object.defineProperty(HTMLElement.prototype, 'getBoundingClientRect', {
  configurable: true,
  value: () => ({ top: 100, bottom: 120, left: 10, right: 160, width: 150, height: 20 }),
})

// ── Helpers ────────────────────────────────────────────────────────────────
const mockBomItem = { id: 7, description: 'NEMA17 Motor', quantity_needed: 4, status: 'unlinked' }

const mockInventoryResults = [
  { id: 1, title: 'NEMA17 Stepper', quantity: 6, location: { id: 3, name: 'Bin A2' } },
  { id: 2, title: 'NEMA17 Alt',     quantity: 0, location: null },
]

function mountLinker(bomItem = mockBomItem) {
  return mount(InlineBOMLinker, {
    props: { bomItem },
    attachTo: document.body,
    global: {
      // Stub Teleport so teleported content renders inline — makes it findable
      stubs: { Teleport: true },
    },
  })
}

// ── activate helper ────────────────────────────────────────────────────────
async function activateLinker(wrapper) {
  await wrapper.find('.bom-linker-trigger').trigger('click')
}

// ============================================================================
// Inactive state
// ============================================================================

describe('InlineBOMLinker — inactive state', () => {
  it('shows trigger text when inactive', () => {
    const wrapper = mountLinker()
    expect(wrapper.find('.bom-linker-trigger').exists()).toBe(true)
    expect(wrapper.find('.bom-linker-trigger-text').text()).toContain('Link item')
  })

  it('does not show the input when inactive', () => {
    const wrapper = mountLinker()
    expect(wrapper.find('.bom-linker-input').exists()).toBe(false)
  })
})

// ============================================================================
// Activation
// ============================================================================

describe('InlineBOMLinker — activation', () => {
  it('emits activate when trigger is clicked', async () => {
    const wrapper = mountLinker()
    await activateLinker(wrapper)
    expect(wrapper.emitted('activate')).toBeTruthy()
    expect(wrapper.emitted('activate')).toHaveLength(1)
  })

  it('shows input after trigger click', async () => {
    const wrapper = mountLinker()
    await activateLinker(wrapper)
    expect(wrapper.find('.bom-linker-input').exists()).toBe(true)
    expect(wrapper.find('.bom-linker-trigger').exists()).toBe(false)
  })
})

// ============================================================================
// Deactivation
// ============================================================================

describe('InlineBOMLinker — deactivation', () => {
  it('emits deactivate when cancel button is clicked', async () => {
    const wrapper = mountLinker()
    await activateLinker(wrapper)
    await wrapper.find('.bom-linker-cancel').trigger('click')
    expect(wrapper.emitted('deactivate')).toBeTruthy()
  })

  it('returns to trigger state after cancel', async () => {
    const wrapper = mountLinker()
    await activateLinker(wrapper)
    await wrapper.find('.bom-linker-cancel').trigger('click')
    expect(wrapper.find('.bom-linker-trigger').exists()).toBe(true)
    expect(wrapper.find('.bom-linker-input').exists()).toBe(false)
  })

  it('emits deactivate on Escape key', async () => {
    const wrapper = mountLinker()
    await activateLinker(wrapper)
    await wrapper.find('.bom-linker-input').trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('deactivate')).toBeTruthy()
  })
})

// ============================================================================
// Dropdown — result display
// ============================================================================

describe('InlineBOMLinker — dropdown display', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    APIService.getInventoryItems.mockResolvedValue({
      data: { results: mockInventoryResults },
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  /**
   * Helper: activate and type a query, advance the 250 ms debounce, flush promises.
   * Returns the mounted wrapper already in search-results-shown state.
   */
  async function openAndSearch(query = 'NEMA') {
    const wrapper = mountLinker()
    await activateLinker(wrapper)
    const input = wrapper.find('.bom-linker-input')
    await input.setValue(query)
    await input.trigger('input')
    vi.advanceTimersByTime(300) // advance past the 250 ms debounce
    await flushPromises()       // resolve the API call
    return wrapper
  }

  it('shows location in parentheses after item title', async () => {
    const wrapper = await openAndSearch()
    const titles = wrapper.findAll('.bom-linker-result-title')
    expect(titles).toHaveLength(2)
    // First item has a location — must appear in the title span
    expect(titles[0].text()).toContain('Bin A2')
  })

  it('items without a location show no parenthetical', async () => {
    const wrapper = await openAndSearch()
    const titles = wrapper.findAll('.bom-linker-result-title')
    // Second item has no location — no parens expected
    expect(titles[1].text()).not.toContain('(')
  })

  it('dropdown items have title attribute with full name and location', async () => {
    const wrapper = await openAndSearch()
    const items = wrapper.findAll('.bom-linker-dropdown-item')
    expect(items).toHaveLength(2)

    const firstTitle = items[0].attributes('title')
    expect(firstTitle).toContain('NEMA17 Stepper')
    expect(firstTitle).toContain('Bin A2')

    // Second item has no location — title attribute should only contain the name
    const secondTitle = items[1].attributes('title')
    expect(secondTitle).toBe('NEMA17 Alt')
  })
})

// ============================================================================
// Item selection → emit linked
// ============================================================================

describe('InlineBOMLinker — item selection', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    APIService.getInventoryItems.mockResolvedValue({
      data: { results: mockInventoryResults },
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('calls updateBOMItem and emits linked on item select', async () => {
    const updatedBomItem = { id: 7, status: 'linked', allocation_status: 'covered' }
    APIService.updateBOMItem.mockResolvedValue({ data: updatedBomItem })

    const wrapper = mountLinker()
    await activateLinker(wrapper)

    // Type to trigger search results
    const input = wrapper.find('.bom-linker-input')
    await input.setValue('NEMA')
    await input.trigger('input')
    vi.advanceTimersByTime(300)
    await flushPromises()

    // Click first dropdown item
    const firstItem = wrapper.find('.bom-linker-dropdown-item')
    await firstItem.trigger('mousedown')
    await flushPromises()

    expect(APIService.updateBOMItem).toHaveBeenCalledWith(7, {
      inventory_item: 1,
      status: 'linked',
    })
    expect(wrapper.emitted('linked')).toBeTruthy()
    expect(wrapper.emitted('linked')[0][0]).toEqual(updatedBomItem)
    // selectItem calls deactivate() after emitting linked
    expect(wrapper.emitted('deactivate')).toBeTruthy()
  })
})
