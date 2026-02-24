import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

/**
 * Tests for LoadingSpinner.vue — the inline animated SVG spinner used
 * throughout the app wherever async loading state is indicated.
 *
 * Covers:
 * - Renders an SVG element
 * - Has the .spinner CSS class
 * - Has the .path CSS class on the circle element
 * - Contains a circle element (the animated arc)
 * - SVG width/height attributes are set
 */

describe('LoadingSpinner', () => {
  it('renders an SVG element', () => {
    const wrapper = mount(LoadingSpinner)
    expect(wrapper.find('svg').exists()).toBe(true)
  })

  it('applies the .spinner class to the SVG', () => {
    const wrapper = mount(LoadingSpinner)
    expect(wrapper.find('svg').classes()).toContain('spinner')
  })

  it('renders a circle element inside the SVG', () => {
    const wrapper = mount(LoadingSpinner)
    expect(wrapper.find('circle').exists()).toBe(true)
  })

  it('applies the .path class to the circle', () => {
    const wrapper = mount(LoadingSpinner)
    expect(wrapper.find('circle').classes()).toContain('path')
  })

  it('sets explicit width and height attributes on the SVG', () => {
    const wrapper = mount(LoadingSpinner)
    const svg = wrapper.find('svg')
    expect(svg.attributes('width')).toBeDefined()
    expect(svg.attributes('height')).toBeDefined()
  })

  it('sets viewBox attribute for proper scaling', () => {
    const wrapper = mount(LoadingSpinner)
    expect(wrapper.find('svg').attributes('viewBox')).toBeDefined()
  })
})
