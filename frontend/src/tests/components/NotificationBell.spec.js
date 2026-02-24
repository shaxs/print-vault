/**
 * NotificationBell.spec.js
 *
 * Tests for the NotificationBell component in src/components/NotificationBell.vue.
 *
 * The component processes two prop arrays:
 *   - reminders: Array of printer objects with maintenance_reminder_date and/or
 *     carbon_reminder_date fields. Only dates <= today are surfaced.
 *   - lowStockItems: Array of inventory items that are low on stock.
 *
 * Key computed properties (tested via rendered output):
 *   - allReminders  – filters and sorts reminders by date
 *   - notificationCount – allReminders.length + lowStockItems.length
 *
 * The notification badge is only rendered when notificationCount > 0.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import NotificationBell from '@/components/NotificationBell.vue'

// ---------------------------------------------------------------------------
// Mock APIService (used in dismissReminder — not under test here)
// ---------------------------------------------------------------------------

vi.mock('@/services/APIService.js', () => ({
  default: {
    updatePrinter: vi.fn().mockResolvedValue({}),
    updateInventoryItem: vi.fn().mockResolvedValue({}),
  },
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const FIXED_TODAY = '2024-06-15' // Saturday

/** Build a minimal printer reminder object */
const mkPrinter = (id, maintenanceDate = null, carbonDate = null, title = `Printer ${id}`) => ({
  id,
  title,
  maintenance_reminder_date: maintenanceDate,
  carbon_reminder_date: carbonDate,
})

/** Build a minimal low-stock inventory item */
const mkItem = (id, title = `Item ${id}`) => ({ id, title, quantity: 2, low_stock_threshold: 5 })

let router

beforeEach(() => {
  // Fix today to a known date so date comparisons are deterministic
  vi.useFakeTimers()
  vi.setSystemTime(new Date(FIXED_TODAY + 'T12:00:00'))

  router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/', component: { template: '<div/>' } }],
  })
})

afterEach(() => {
  vi.useRealTimers()
})

/** Mount helper with default stubs */
const mountBell = (reminders = [], lowStockItems = []) =>
  mount(NotificationBell, {
    props: { reminders, lowStockItems },
    global: {
      plugins: [router],
      stubs: { BaseModal: true },
    },
  })

// ---------------------------------------------------------------------------

describe('NotificationBell – badge visibility', () => {
  it('does not render the badge when there are no reminders or low stock items', () => {
    const wrapper = mountBell([], [])
    expect(wrapper.find('.notification-badge').exists()).toBe(false)
  })

  it('renders the badge when there is at least one low stock item', () => {
    const wrapper = mountBell([], [mkItem(1)])
    expect(wrapper.find('.notification-badge').exists()).toBe(true)
  })

  it('renders the badge when there is at least one past-due reminder', () => {
    // 2024-06-10 is before today (2024-06-15)
    const wrapper = mountBell([mkPrinter(1, '2024-06-10')], [])
    expect(wrapper.find('.notification-badge').exists()).toBe(true)
  })

  it('does NOT render the badge for a future maintenance date', () => {
    // 2024-06-20 is after today
    const wrapper = mountBell([mkPrinter(1, '2024-06-20')], [])
    expect(wrapper.find('.notification-badge').exists()).toBe(false)
  })

  it('renders the badge for today\'s maintenance date (today <= today)', () => {
    const wrapper = mountBell([mkPrinter(1, FIXED_TODAY)], [])
    expect(wrapper.find('.notification-badge').exists()).toBe(true)
  })
})

// ---------------------------------------------------------------------------

describe('NotificationBell – notificationCount', () => {
  it('counts only low stock items when no reminders', () => {
    const wrapper = mountBell([], [mkItem(1), mkItem(2), mkItem(3)])
    expect(wrapper.find('.notification-badge').text()).toBe('3')
  })

  it('counts only past/today maintenance reminders', () => {
    // 1 past, 1 today, 1 future → count = 2
    const printers = [
      mkPrinter(1, '2024-06-10'), // past
      mkPrinter(2, FIXED_TODAY), // today
      mkPrinter(3, '2024-06-20'), // future (excluded)
    ]
    const wrapper = mountBell(printers, [])
    expect(wrapper.find('.notification-badge').text()).toBe('2')
  })

  it('counts carbon filter reminders separately from maintenance', () => {
    // Same printer with both types of reminders
    const printers = [mkPrinter(1, '2024-06-10', '2024-06-12')]
    const wrapper = mountBell(printers, [])
    expect(wrapper.find('.notification-badge').text()).toBe('2')
  })

  it('combines reminders and low stock items in the total', () => {
    const printers = [mkPrinter(1, '2024-06-10'), mkPrinter(2, '2024-06-11')]
    const items = [mkItem(1), mkItem(2), mkItem(3)]
    const wrapper = mountBell(printers, items)
    // 2 reminders + 3 low stock = 5
    expect(wrapper.find('.notification-badge').text()).toBe('5')
  })

  it('excludes future carbon filter dates from count', () => {
    const printers = [mkPrinter(1, null, '2024-07-01')] // future carbon, no maintenance
    const wrapper = mountBell(printers, [])
    expect(wrapper.find('.notification-badge').exists()).toBe(false)
  })

  it('handles printers with no reminder dates (null fields)', () => {
    const printers = [mkPrinter(1, null, null), mkPrinter(2, null, null)]
    const wrapper = mountBell(printers, [])
    expect(wrapper.find('.notification-badge').exists()).toBe(false)
  })

  it('handles empty reminders array with multiple low stock items', () => {
    const items = [mkItem(1), mkItem(2)]
    const wrapper = mountBell([], items)
    expect(wrapper.find('.notification-badge').text()).toBe('2')
  })
})

// ---------------------------------------------------------------------------

describe('NotificationBell – bell button', () => {
  it('renders the bell icon button', () => {
    const wrapper = mountBell()
    expect(wrapper.find('button.notification-button').exists()).toBe(true)
  })

  it('renders the bell SVG inside the button', () => {
    const wrapper = mountBell()
    expect(wrapper.find('button.notification-button svg').exists()).toBe(true)
  })
})

// ---------------------------------------------------------------------------

describe('NotificationBell – edge cases', () => {
  it('printer with maintenance exactly at midnight today is included', () => {
    // The component adds 'T00:00:00' to dates — should still be <= today
    const wrapper = mountBell([mkPrinter(1, FIXED_TODAY)], [])
    expect(wrapper.find('.notification-badge').text()).toBe('1')
  })

  it('multiple printers with same past maintenance date all counted', () => {
    const printers = [
      mkPrinter(1, '2024-01-01'),
      mkPrinter(2, '2024-01-01'),
      mkPrinter(3, '2024-01-01'),
    ]
    const wrapper = mountBell(printers, [])
    expect(wrapper.find('.notification-badge').text()).toBe('3')
  })

  it('a printer with both past maintenance and past carbon counts as 2', () => {
    const printers = [mkPrinter(1, '2024-06-01', '2024-06-05')]
    const wrapper = mountBell(printers, [])
    expect(wrapper.find('.notification-badge').text()).toBe('2')
  })

  it('single future date with low stock still shows low stock count only', () => {
    const printers = [mkPrinter(1, '2025-12-31')]
    const items = [mkItem(1)]
    const wrapper = mountBell(printers, items)
    expect(wrapper.find('.notification-badge').text()).toBe('1')
  })
})
