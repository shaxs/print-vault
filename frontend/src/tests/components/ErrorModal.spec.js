import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ErrorModal from '@/components/ErrorModal.vue'

/**
 * Tests for ErrorModal.vue — the global error display modal used throughout
 * the app for API errors, validation failures, and unexpected exceptions.
 *
 * Covers:
 * - Conditional rendering based on `show` prop
 * - Default title / message values
 * - Custom title / message props
 * - Close button emits `close`
 * - Overlay click emits `close`
 * - Modal content click does NOT propagate (`.stop` modifier)
 * - Error styling: `.error-title` class on heading
 */

describe('ErrorModal', () => {
  const mountModal = (props = {}) =>
    mount(ErrorModal, {
      props: { show: true, ...props },
      attachTo: document.body,
    })

  // ──────────────────────────────────────────────────────────────────────────
  // CONDITIONAL RENDERING
  // ──────────────────────────────────────────────────────────────────────────

  it('renders when show is true', () => {
    const wrapper = mountModal({ show: true })
    expect(wrapper.find('.modal-overlay').exists()).toBe(true)
  })

  it('does not render when show is false', () => {
    const wrapper = mount(ErrorModal, { props: { show: false } })
    expect(wrapper.find('.modal-overlay').exists()).toBe(false)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // DEFAULT PROPS
  // ──────────────────────────────────────────────────────────────────────────

  it('displays default title when no title prop given', () => {
    const wrapper = mountModal()
    expect(wrapper.find('h3').text()).toBe('An Error Occurred')
  })

  it('displays default message when no message prop given', () => {
    const wrapper = mountModal()
    expect(wrapper.find('p').text()).toBe('Something went wrong. Please try again.')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // CUSTOM PROPS
  // ──────────────────────────────────────────────────────────────────────────

  it('displays custom title when title prop is provided', () => {
    const wrapper = mountModal({ title: 'Network Error' })
    expect(wrapper.find('h3').text()).toBe('Network Error')
  })

  it('displays custom message when message prop is provided', () => {
    const wrapper = mountModal({ message: 'Could not connect to the server.' })
    expect(wrapper.find('p').text()).toBe('Could not connect to the server.')
  })

  it('displays both custom title and message together', () => {
    const wrapper = mountModal({
      title: 'Upload Failed',
      message: 'The file was too large.',
    })
    expect(wrapper.find('h3').text()).toBe('Upload Failed')
    expect(wrapper.find('p').text()).toBe('The file was too large.')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // ERROR STYLING
  // ──────────────────────────────────────────────────────────────────────────

  it('applies error-title class to the heading', () => {
    const wrapper = mountModal()
    expect(wrapper.find('h3').classes()).toContain('error-title')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // CLOSE / EMIT
  // ──────────────────────────────────────────────────────────────────────────

  it('emits close when Close button is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close when overlay is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('.modal-overlay').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('does NOT emit close when modal content (not overlay) is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('.modal-form').trigger('click')
    expect(wrapper.emitted('close')).toBeUndefined()
  })

  it('Close button has type="button" to prevent accidental form submission', () => {
    const wrapper = mountModal()
    expect(wrapper.find('button').attributes('type')).toBe('button')
  })
})
