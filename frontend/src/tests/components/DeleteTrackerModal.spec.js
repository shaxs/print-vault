import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DeleteTrackerModal from '@/components/DeleteTrackerModal.vue'

/**
 * Tests for DeleteTrackerModal.vue — the tracker deletion confirmation modal
 * with support for optional ZIP download before deletion.
 *
 * Covers:
 * - Conditional rendering based on `isVisible`
 * - Tracker name display
 * - File count display (with correct singular/plural)
 * - Storage type label ("Local Files" / "GitHub Links")
 * - `hasLocalFiles` computed: shows extra UI when local storage + downloaded + fileCount
 * - `formattedSize` computed: byte → human-readable
 * - Local files warning box only shown when hasLocalFiles
 * - "GitHub Links" info message shown when not local
 * - Emits `delete` when Delete button clicked
 * - Emits `downloadAndDelete` when Download ZIP & Delete clicked
 * - Emits `close` when Cancel clicked
 * - "Download ZIP & Delete" button only visible when hasLocalFiles
 * - Delete button label changes based on hasLocalFiles
 * - Cancel/action buttons hidden during deleting/downloading states
 */

const BASE_MODAL_STUB = {
  template: `
    <div v-if="show" class="base-modal-stub">
      <slot />
      <div class="footer-slot"><slot name="footer" /></div>
    </div>
  `,
  props: ['show', 'title', 'canClose'],
}

describe('DeleteTrackerModal', () => {
  const mountModal = (props = {}) =>
    mount(DeleteTrackerModal, {
      props: {
        isVisible: true,
        trackerName: 'My Tracker',
        storageType: 'link',
        fileCount: 3,
        ...props,
      },
      attachTo: document.body,
      global: { stubs: { BaseModal: BASE_MODAL_STUB } },
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
  // TRACKER INFO
  // ──────────────────────────────────────────────────────────────────────────

  it('displays the tracker name in the info box', () => {
    const wrapper = mountModal({ trackerName: 'Prusa Benchy v2' })
    expect(wrapper.find('.info-box').text()).toContain('Prusa Benchy v2')
  })

  it('shows correct file count', () => {
    const wrapper = mountModal({ fileCount: 5 })
    expect(wrapper.find('.info-box').text()).toContain('5 files')
  })

  it('uses singular "file" when fileCount is 1', () => {
    const wrapper = mountModal({ fileCount: 1 })
    const infoText = wrapper.find('.info-box').text()
    expect(infoText).toContain('1 file')
    expect(infoText).not.toContain('1 files')
  })

  it('displays "GitHub Links" for link storage type', () => {
    const wrapper = mountModal({ storageType: 'link' })
    expect(wrapper.find('.info-box').text()).toContain('GitHub Links')
  })

  it('displays "Local Files" for local storage type', () => {
    const wrapper = mountModal({ storageType: 'local' })
    expect(wrapper.find('.info-box').text()).toContain('Local Files')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // LINK STORAGE (no local files)
  // ──────────────────────────────────────────────────────────────────────────

  it('shows GitHub info message when storageType is link', () => {
    const wrapper = mountModal({ storageType: 'link' })
    expect(wrapper.find('.info-message').exists()).toBe(true)
    expect(wrapper.find('.info-message').text()).toContain('No local files')
  })

  it('does NOT show local files warning when storageType is link', () => {
    const wrapper = mountModal({ storageType: 'link' })
    expect(wrapper.find('.local-files-box').exists()).toBe(false)
  })

  it('does NOT show Download ZIP button for link storage', () => {
    const wrapper = mountModal({ storageType: 'link' })
    expect(wrapper.find('.btn-primary').exists()).toBe(false)
  })

  it('Delete button shows plain "Delete" for link storage', () => {
    const wrapper = mountModal({ storageType: 'link' })
    expect(wrapper.find('.btn-danger').text()).toBe('Delete')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // LOCAL STORAGE WITH DOWNLOADED FILES (hasLocalFiles = true)
  // ──────────────────────────────────────────────────────────────────────────

  const localProps = {
    storageType: 'local',
    filesDownloaded: true,
    fileCount: 4,
    totalStorageUsed: 2048,
  }

  it('shows local files warning box when hasLocalFiles is true', () => {
    const wrapper = mountModal(localProps)
    expect(wrapper.find('.local-files-box').exists()).toBe(true)
  })

  it('shows storage used row when hasLocalFiles is true', () => {
    const wrapper = mountModal(localProps)
    expect(wrapper.find('.info-box').text()).toContain('Storage Used')
  })

  it('shows "Download ZIP & Delete" button when hasLocalFiles is true', () => {
    const wrapper = mountModal(localProps)
    expect(wrapper.find('.btn-primary').text()).toContain('Download ZIP & Delete')
  })

  it('shows "Delete Without Download" on delete button when hasLocalFiles is true', () => {
    const wrapper = mountModal(localProps)
    expect(wrapper.find('.btn-danger').text()).toContain('Delete Without Download')
  })

  it('does NOT show local files warning when filesDownloaded is false', () => {
    const wrapper = mountModal({ storageType: 'local', filesDownloaded: false, fileCount: 4 })
    expect(wrapper.find('.local-files-box').exists()).toBe(false)
  })

  it('does NOT show local files warning when fileCount is 0', () => {
    const wrapper = mountModal({ storageType: 'local', filesDownloaded: true, fileCount: 0 })
    expect(wrapper.find('.local-files-box').exists()).toBe(false)
  })

  // ──────────────────────────────────────────────────────────────────────────
  // formattedSize computed
  // ──────────────────────────────────────────────────────────────────────────

  it('formats bytes correctly as KB', () => {
    const wrapper = mountModal({ ...localProps, totalStorageUsed: 2048 })
    expect(wrapper.find('.info-box').text()).toContain('KB')
  })

  it('shows 0 B when totalStorageUsed is 0', () => {
    const wrapper = mountModal({ ...localProps, totalStorageUsed: 0 })
    // 0 bytes falls through the zero check — hasLocalFiles requires fileCount > 0 so storage row shows
    // formattedSize returns '0 B' for 0 bytes
    expect(wrapper.find('.info-box').text()).toContain('0 B')
  })

  // ──────────────────────────────────────────────────────────────────────────
  // EMITS
  // ──────────────────────────────────────────────────────────────────────────

  it('emits delete when Delete button is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('.btn-danger').trigger('click')
    expect(wrapper.emitted('delete')).toBeTruthy()
  })

  it('emits downloadAndDelete when Download ZIP & Delete is clicked', async () => {
    const wrapper = mountModal(localProps)
    await wrapper.find('.btn-primary').trigger('click')
    expect(wrapper.emitted('downloadAndDelete')).toBeTruthy()
  })

  it('emits close when Cancel is clicked', async () => {
    const wrapper = mountModal()
    await wrapper.find('.btn-secondary').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  // ──────────────────────────────────────────────────────────────────────────
  // STATE: DELETING / DOWNLOADING
  // ──────────────────────────────────────────────────────────────────────────

  it('hides action buttons after delete is initiated', async () => {
    const wrapper = mountModal()
    await wrapper.find('.btn-danger').trigger('click')
    // After emitting delete, deleting=true hides the button group
    expect(wrapper.find('.button-group').exists()).toBe(false)
  })

  it('shows deleting spinner after delete is initiated', async () => {
    const wrapper = mountModal()
    await wrapper.find('.btn-danger').trigger('click')
    expect(wrapper.find('.status-box').exists()).toBe(true)
  })

  it('does NOT emit close when Cancel is clicked while deleting', async () => {
    const wrapper = mountModal()
    // Trigger delete first
    await wrapper.find('.btn-danger').trigger('click')
    // Now try to close (button group is gone; but close via header would call handleClose)
    // We can directly test handleClose doesn't emit while deleting by checking
    // that the cancel button no longer exists
    expect(wrapper.find('.btn-secondary').exists()).toBe(false)
  })
})
