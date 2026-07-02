import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import MainHeader from '@/components/MainHeader.vue'

/**
 * Tests for MainHeader.vue — the primary page header used on all list/detail views.
 *
 * Covers:
 * - Title rendering
 * - showSearch / showFilterButton / showColumnButton / showAddButton prop flags
 * - v-model search input (update:modelValue events)
 * - Search clear button behavior
 * - open-filter and open-columns event emissions
 * - Search input type is "text" (not "search" — prevents double clear button in Chrome)
 */

describe('MainHeader', () => {
  let router

  beforeEach(() => {
    router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: { template: '<div/>' } }],
    })
  })

  const mountHeader = (props = {}) =>
    mount(MainHeader, {
      props: { title: 'Test Page', ...props },
      global: { plugins: [router] },
    })

  // ──────────────────────────────────────────────────────────────────────────
  // TITLE
  // ──────────────────────────────────────────────────────────────────────────

  it('renders the title prop', () => {
    const wrapper = mountHeader({ title: 'Inventory List' })
    expect(wrapper.find('h1.header-title').text()).toBe('Inventory List')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // VISIBILITY PROPS
  // ──────────────────────────────────────────────────────────────────────────

  it('shows Filter button by default', () => {
    const wrapper = mountHeader()
    expect(wrapper.find('button:first-child').text()).toBe('Filter')
  })

  it('hides Filter button when showFilterButton is false', () => {
    const wrapper = mountHeader({ showFilterButton: false })
    const buttons = wrapper.findAll('button')
    const filterBtn = buttons.find((b) => b.text() === 'Filter')
    expect(filterBtn).toBeUndefined()
  })

  it('shows Columns button by default', () => {
    const wrapper = mountHeader()
    const buttons = wrapper.findAll('button')
    const colBtn = buttons.find((b) => b.text() === 'Columns')
    expect(colBtn).toBeTruthy()
  })

  it('hides Columns button when showColumnButton is false', () => {
    const wrapper = mountHeader({ showColumnButton: false })
    const buttons = wrapper.findAll('button')
    const colBtn = buttons.find((b) => b.text() === 'Columns')
    expect(colBtn).toBeUndefined()
  })

  it('shows search input by default', () => {
    const wrapper = mountHeader({ modelValue: '' })
    expect(wrapper.find('input.search-bar').exists()).toBe(true)
  })

  it('hides search input when showSearch is false', () => {
    const wrapper = mountHeader({ showSearch: false })
    expect(wrapper.find('input.search-bar').exists()).toBe(false)
  })

  it('shows Add button by default', () => {
    const wrapper = mountHeader({ createUrl: '/inventory/create' })
    expect(wrapper.find('a.add-button').exists()).toBe(true)
  })

  it('hides Add button when showAddButton is false', () => {
    const wrapper = mountHeader({ showAddButton: false })
    expect(wrapper.find('a.add-button').exists()).toBe(false)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // SEARCH INPUT
  // ──────────────────────────────────────────────────────────────────────────

  it('search input uses type="text" (not "search")', () => {
    const wrapper = mountHeader({ modelValue: '' })
    const input = wrapper.find('input.search-bar')
    // Must be "text" — using type="search" causes double clear buttons in Chromium
    expect(input.attributes('type')).toBe('text')
  })

  it('binds modelValue to the search input value', () => {
    const wrapper = mountHeader({ modelValue: 'hello' })
    const input = wrapper.find('input.search-bar')
    expect(input.element.value).toBe('hello')
  })

  it('emits update:modelValue when user types in search box', async () => {
    const wrapper = mountHeader({ modelValue: '' })
    const input = wrapper.find('input.search-bar')
    await input.setValue('test query')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0][0]).toBe('test query')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // CLEAR BUTTON
  // ──────────────────────────────────────────────────────────────────────────

  it('shows clear button when modelValue is non-empty', () => {
    const wrapper = mountHeader({ modelValue: 'some text' })
    expect(wrapper.find('button.search-clear-button').exists()).toBe(true)
  })

  it('hides clear button when modelValue is empty string', () => {
    const wrapper = mountHeader({ modelValue: '' })
    expect(wrapper.find('button.search-clear-button').exists()).toBe(false)
  })

  it('hides clear button when modelValue is undefined', () => {
    const wrapper = mountHeader()
    expect(wrapper.find('button.search-clear-button').exists()).toBe(false)
  })

  it('emits update:modelValue with empty string when clear button is clicked', async () => {
    const wrapper = mountHeader({ modelValue: 'query' })
    const clearBtn = wrapper.find('button.search-clear-button')
    await clearBtn.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0][0]).toBe('')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // BUTTON EVENTS
  // ──────────────────────────────────────────────────────────────────────────

  it('emits open-filter when Filter button is clicked', async () => {
    const wrapper = mountHeader()
    const filterBtn = wrapper.findAll('button').find((b) => b.text() === 'Filter')
    await filterBtn.trigger('click')
    expect(wrapper.emitted('open-filter')).toBeTruthy()
  })

  it('emits open-columns when Columns button is clicked', async () => {
    const wrapper = mountHeader()
    const colBtn = wrapper.findAll('button').find((b) => b.text() === 'Columns')
    await colBtn.trigger('click')
    expect(wrapper.emitted('open-columns')).toBeTruthy()
  })
})
