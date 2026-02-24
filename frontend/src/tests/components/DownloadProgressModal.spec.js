import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DownloadProgressModal from '@/components/DownloadProgressModal.vue'

/**
 * Tests for DownloadProgressModal.vue — the non-dismissible progress modal
 * shown while files are being downloaded from GitHub. Uses BaseModal with
 * can-close=false to prevent accidental dismissal during download.
 *
 * Covers:
 * - Conditional rendering based on `isVisible` prop
 * - Displays download message with totalFiles count
 * - Has the title "Downloading Files"
 * - Renders the spinner element
 * - Renders the subtext message
 */

describe('DownloadProgressModal', () => {
  const mountModal = (props = {}) =>
    mount(DownloadProgressModal, {
      props: { isVisible: true, ...props },
      attachTo: document.body,
      global: {
        stubs: {
          BaseModal: {
            template: `
              <div v-if="show" class="base-modal-stub">
                <div class="modal-title">{{ title }}</div>
                <slot />
              </div>
            `,
            props: ['show', 'title', 'canClose'],
          },
        },
      },
    })

  // ──────────────────────────────────────────────────────────────────────────
  // CONDITIONAL RENDERING
  // ──────────────────────────────────────────────────────────────────────────

  it('renders when isVisible is true', () => {
    const wrapper = mountModal({ isVisible: true })
    expect(wrapper.find('.base-modal-stub').exists()).toBe(true)
  })

  it('does not render when isVisible is false', () => {
    const wrapper = mountModal({ isVisible: false })
    expect(wrapper.find('.base-modal-stub').exists()).toBe(false)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // TITLE
  // ──────────────────────────────────────────────────────────────────────────

  it('passes "Downloading Files" as the modal title', () => {
    const wrapper = mountModal()
    expect(wrapper.find('.modal-title').text()).toBe('Downloading Files')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // CONTENT
  // ──────────────────────────────────────────────────────────────────────────

  it('displays the totalFiles count in the main message', () => {
    const wrapper = mountModal({ totalFiles: 42 })
    expect(wrapper.find('.main-text').text()).toContain('42')
  })

  it('displays 0 files when totalFiles defaults', () => {
    const wrapper = mountModal()
    expect(wrapper.find('.main-text').text()).toContain('0')
  })

  it('renders a spinner element', () => {
    const wrapper = mountModal()
    expect(wrapper.find('.spinner').exists()).toBe(true)
  })

  it('renders a patient subtext message', () => {
    const wrapper = mountModal()
    expect(wrapper.find('.subtext').text()).toContain('Please be patient')
  })

  it('mentions GitHub in the main download message', () => {
    const wrapper = mountModal({ totalFiles: 5 })
    expect(wrapper.find('.main-text').text()).toContain('GitHub')
  })
})
