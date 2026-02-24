import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import InfoModal from '@/components/InfoModal.vue'

/**
 * Tests for InfoModal.vue — a dual-purpose notification modal
 * that serves as both an informational notice and an error display,
 * controlled by the `isError` prop. Used throughout the app to surface
 * success/failure feedback after API calls.
 *
 * Covers:
 * - Conditional rendering based on `show` prop
 * - Default title ("Notification")
 * - Custom title prop
 * - Required `message` prop renders correctly
 * - Normal style (no error classes when isError is false)
 * - Error style: `error-border` on modal, `error-title` on heading
 * - OK button emits close
 * - Overlay click emits close
 * - Modal content click does NOT propagate (.stop modifier)
 * - OK button has type="button"
 */

describe('InfoModal', () => {
  const mountModal = (props = {}) =>
    mount(InfoModal, {
      props: { show: true, message: 'Test message.', ...props },
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
    const wrapper = mount(InfoModal, {
      props: { show: false, message: 'Test' },
    })
    expect(wrapper.find('.modal-overlay').exists()).toBe(false)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // TITLE PROP
  // ──────────────────────────────────────────────────────────────────────────

  it('displays default title "Notification" when no title prop given', () => {
    const wrapper = mountModal()
    expect(wrapper.find('h3').text()).toBe('Notification')
  })

  it('displays custom title when title prop is provided', () => {
    const wrapper = mountModal({ title: 'Import Complete' })
    expect(wrapper.find('h3').text()).toBe('Import Complete')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // MESSAGE PROP
  // ──────────────────────────────────────────────────────────────────────────

  it('renders the message text', () => {
    const wrapper = mountModal({ message: 'Your data has been saved.' })
    expect(wrapper.find('p').text()).toBe('Your data has been saved.')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // NORMAL MODE (isError = false)
  // ──────────────────────────────────────────────────────────────────────────

  it('does NOT apply error-border to modal form when isError is false', () => {
    const wrapper = mountModal({ isError: false })
    expect(wrapper.find('.modal-form').classes()).not.toContain('error-border')
  })

  it('does NOT apply error-title to heading when isError is false', () => {
    const wrapper = mountModal({ isError: false })
    expect(wrapper.find('h3').classes()).not.toContain('error-title')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // ERROR MODE (isError = true)
  // ──────────────────────────────────────────────────────────────────────────

  it('applies error-border to modal form when isError is true', () => {
    const wrapper = mountModal({ isError: true })
    expect(wrapper.find('.modal-form').classes()).toContain('error-border')
  })

  it('applies error-title to heading when isError is true', () => {
    const wrapper = mountModal({ isError: true })
    expect(wrapper.find('h3').classes()).toContain('error-title')
  })

  it('displays custom title in error mode', () => {
    const wrapper = mountModal({ isError: true, title: 'Import Failed' })
    const h3 = wrapper.find('h3')
    expect(h3.text()).toBe('Import Failed')
    expect(h3.classes()).toContain('error-title')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // CLOSE / EMIT
  // ──────────────────────────────────────────────────────────────────────────

  it('emits close when OK button is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close when overlay is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('.modal-overlay').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('does NOT emit close when modal content is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('.modal-form').trigger('click')
    expect(wrapper.emitted('close')).toBeUndefined()
  })

  it('OK button has type="button" to prevent accidental form submission', () => {
    const wrapper = mountModal()
    expect(wrapper.find('button').attributes('type')).toBe('button')
  })
})
