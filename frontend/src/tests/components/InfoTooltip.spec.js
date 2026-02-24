/**
 * Tests for InfoTooltip component
 *
 * InfoTooltip is a reusable ? badge that shows a floating tooltip panel on
 * hover/focus. Uses Vue Teleport to escape overflow:hidden ancestors.
 * Tests cover visibility toggling, slot content, accessibility attributes.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import InfoTooltip from '@/components/InfoTooltip.vue'

describe('InfoTooltip', () => {
  let wrapper

  beforeEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    // Provide mock for getBoundingClientRect (jsdom returns zeros by default)
    Element.prototype.getBoundingClientRect = () => ({
      left: 100, top: 200, right: 110, bottom: 215, width: 10, height: 15,
      x: 100, y: 200, toJSON: () => {},
    })
  })

  describe('Initial Render', () => {
    it('renders the trigger button', () => {
      wrapper = mount(InfoTooltip, {
        global: { stubs: { Teleport: true } },
      })
      expect(wrapper.find('button.info-tooltip__trigger').exists()).toBe(true)
    })

    it('trigger button has correct aria-label', () => {
      wrapper = mount(InfoTooltip, {
        global: { stubs: { Teleport: true } },
      })
      expect(wrapper.find('button').attributes('aria-label')).toBe('More information')
    })

    it('tooltip panel is hidden initially', () => {
      wrapper = mount(InfoTooltip, {
        global: { stubs: { Teleport: true } },
      })
      // Panel uses v-if — should not be in DOM
      expect(wrapper.find('[role="tooltip"]').exists()).toBe(false)
    })
  })

  describe('Hover Interaction', () => {
    it('shows tooltip panel on mouseenter', async () => {
      wrapper = mount(InfoTooltip, {
        attachTo: document.body,
      })
      await wrapper.find('button').trigger('mouseenter')
      // After mouseenter, isVisible === true, Teleport renders into body
      expect(wrapper.vm.isVisible).toBe(true)
    })

    it('hides tooltip panel on mouseleave', async () => {
      wrapper = mount(InfoTooltip, {
        attachTo: document.body,
      })
      await wrapper.find('button').trigger('mouseenter')
      expect(wrapper.vm.isVisible).toBe(true)
      await wrapper.find('button').trigger('mouseleave')
      expect(wrapper.vm.isVisible).toBe(false)
    })
  })

  describe('Focus Interaction', () => {
    it('shows tooltip on focus', async () => {
      wrapper = mount(InfoTooltip, {
        attachTo: document.body,
      })
      await wrapper.find('button').trigger('focus')
      expect(wrapper.vm.isVisible).toBe(true)
    })

    it('hides tooltip on blur', async () => {
      wrapper = mount(InfoTooltip, {
        attachTo: document.body,
      })
      await wrapper.find('button').trigger('focus')
      await wrapper.find('button').trigger('blur')
      expect(wrapper.vm.isVisible).toBe(false)
    })
  })

  describe('Slot Content', () => {
    it('renders slot content inside tooltip panel', async () => {
      wrapper = mount(InfoTooltip, {
        slots: { default: '<strong>Tooltip text</strong>' },
        attachTo: document.body,
      })
      await wrapper.find('button').trigger('mouseenter')
      // Teleport renders into document.body
      const panel = document.body.querySelector('[role="tooltip"]')
      expect(panel).not.toBeNull()
      expect(panel.innerHTML).toContain('Tooltip text')
    })

    it('panel has role="tooltip" attribute', async () => {
      wrapper = mount(InfoTooltip, {
        attachTo: document.body,
      })
      await wrapper.find('button').trigger('mouseenter')
      const panel = document.body.querySelector('[role="tooltip"]')
      expect(panel).not.toBeNull()
      expect(panel.getAttribute('role')).toBe('tooltip')
    })
  })
})
