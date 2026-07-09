/**
 * Unit tests for LibrarySettingsModal.vue — the two-level (root list + edit/
 * create form) settings modal. The modal starts async jobs and hands them up
 * via 'job-started' (LibraryView owns the progress banner); it never traps the
 * user, and root removal emits 'deleted'.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LibrarySettingsModal from '@/components/LibrarySettingsModal.vue'

vi.mock('@/services/APIService', () => ({
  default: {
    createLibraryRoot: vi.fn(() =>
      Promise.resolve({ data: { id: 2, name: 'New', path: '/mnt/new', thumbnail_color: '#94a3b8' } }),
    ),
    updateLibraryRoot: vi.fn(() =>
      Promise.resolve({ data: { id: 1, name: 'NAS', path: '/mnt/nas', thumbnail_color: '#ff0000' } }),
    ),
    deleteLibraryRoot: vi.fn(() => Promise.resolve({ status: 204 })),
    rescanLibraryRoot: vi.fn(() => Promise.resolve({ data: { id: 9, root_name: 'NAS', kind: 'scan' } })),
    regenerateLibraryThumbnails: vi.fn(() =>
      Promise.resolve({ data: { id: 9, root_name: 'NAS', kind: 'thumbnails' } }),
    ),
    purgeLibraryDeleted: vi.fn(() =>
      Promise.resolve({ data: { files_purged: 2, folders_purged: 1 } }),
    ),
  },
}))
import APIService from '@/services/APIService'

const ROOT = {
  id: 1,
  name: 'NAS',
  path: '/mnt/nas',
  rescan_interval_hours: 24,
  thumbnail_color: '#94a3b8',
  enabled: true,
  last_scan_status: 'success',
}

function btn(wrapper, label) {
  return wrapper.findAll('button').find((b) => b.text() === label)
}

async function open(roots = []) {
  const wrapper = mount(LibrarySettingsModal, { props: { show: false, roots } })
  await wrapper.setProps({ show: true })
  await flushPromises()
  return wrapper
}

describe('LibrarySettingsModal', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  it('opens straight to the create form when no roots exist', async () => {
    const wrapper = await open([])

    expect(wrapper.find('#library-root-name').exists()).toBe(true)
    expect(btn(wrapper, 'Create Library')).toBeTruthy()
  })

  it('create saves via createLibraryRoot and emits created', async () => {
    const wrapper = await open([])
    await wrapper.find('#library-root-name').setValue('New')
    await wrapper.find('#library-root-path').setValue('/mnt/new')

    await btn(wrapper, 'Create Library').trigger('click')
    await flushPromises()

    expect(APIService.createLibraryRoot).toHaveBeenCalled()
    expect(wrapper.emitted('created')).toBeTruthy()
  })

  it('create save stays disabled until name and path are filled', async () => {
    const wrapper = await open([])
    const saveBtn = btn(wrapper, 'Create Library')
    expect(saveBtn.attributes('disabled')).toBeDefined()

    await wrapper.find('#library-root-name').setValue('New')
    await wrapper.find('#library-root-path').setValue('/mnt/new')
    expect(saveBtn.attributes('disabled')).toBeUndefined()
  })

  it('list screen shows a row per root with Edit and Remove', async () => {
    const wrapper = await open([ROOT])

    const rows = wrapper.findAll('.root-row')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toContain('NAS')
    expect(rows[0].text()).toContain('/mnt/nas')
    expect(btn(wrapper, 'Add Path')).toBeTruthy()
    expect(btn(wrapper, 'Purge Deleted Records')).toBeTruthy()
  })

  it('shows the last-scan result summary on the root row', async () => {
    const root = {
      ...ROOT,
      last_scan: {
        status: 'success',
        files_seen: 40,
        files_new: 12,
        files_updated: 3,
        files_deleted: 1,
        finished_at: '2026-07-09T00:00:00Z',
      },
    }
    const wrapper = await open([root])

    expect(wrapper.find('.root-row').text()).toContain(
      'Last scan: 12 new · 3 updated · 1 removed',
    )
  })

  it('shows the next-scan countdown when a rescan interval is set', async () => {
    const root = { ...ROOT, next_scan_at: new Date(Date.now() + 5 * 3600 * 1000).toISOString() }
    const wrapper = await open([root])

    expect(wrapper.find('.root-row').text()).toContain('Next scan in 5 h')
  })

  it('omits the next-scan line for manual-only roots (no interval)', async () => {
    const root = { ...ROOT, rescan_interval_hours: null, next_scan_at: null }
    const wrapper = await open([root])

    expect(wrapper.find('.root-row').text()).not.toContain('Next scan')
  })

  it('Add Path opens a blank create form', async () => {
    const wrapper = await open([ROOT])

    await btn(wrapper, 'Add Path').trigger('click')

    expect(wrapper.find('#library-root-name').element.value).toBe('')
    expect(btn(wrapper, 'Create Library')).toBeTruthy()
  })

  it('Edit opens the form prefilled from the root', async () => {
    const wrapper = await open([ROOT])

    await btn(wrapper, 'Edit').trigger('click')

    expect(wrapper.find('#library-root-name').element.value).toBe('NAS')
    expect(wrapper.find('#library-root-path').element.value).toBe('/mnt/nas')
    expect(btn(wrapper, 'Rescan Now')).toBeTruthy() // maintenance only in edit mode
  })

  it('Remove confirms, deletes, and emits deleted', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = await open([ROOT])

    await btn(wrapper, 'Remove').trigger('click')
    await flushPromises()

    expect(APIService.deleteLibraryRoot).toHaveBeenCalledWith(1)
    expect(wrapper.emitted('deleted')[0]).toEqual([1])
  })

  it('Remove surfaces a 409 (scan running) instead of deleting', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    APIService.deleteLibraryRoot.mockRejectedValueOnce({ response: { status: 409 } })
    const wrapper = await open([ROOT])

    await btn(wrapper, 'Remove').trigger('click')
    await flushPromises()

    expect(wrapper.emitted('deleted')).toBeFalsy()
    expect(wrapper.text()).toContain('scan is in progress')
  })

  it('Purge asks for confirmation and emits rescanned', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = await open([ROOT])

    await btn(wrapper, 'Purge Deleted Records').trigger('click')
    await flushPromises()

    expect(APIService.purgeLibraryDeleted).toHaveBeenCalled()
    expect(wrapper.emitted('rescanned')).toBeTruthy()
  })

  it('Rescan Now hands the started job to the parent and stays dismissable', async () => {
    const wrapper = await open([ROOT])
    await btn(wrapper, 'Edit').trigger('click')

    await btn(wrapper, 'Rescan Now').trigger('click')
    await flushPromises()

    expect(APIService.updateLibraryRoot).toHaveBeenCalledWith(1, expect.any(Object))
    expect(APIService.rescanLibraryRoot).toHaveBeenCalledWith(1)
    expect(wrapper.emitted('job-started')[0][0]).toMatchObject({ id: 9, kind: 'scan' })
    expect(btn(wrapper, 'Close').attributes('disabled')).toBeUndefined()
  })

  it('invalid hex color blocks saving in the form', async () => {
    const wrapper = await open([ROOT])
    await btn(wrapper, 'Edit').trigger('click')

    await wrapper.find('.hex-input').setValue('red')

    expect(wrapper.text()).toContain('Enter a hex color')
    expect(btn(wrapper, 'Save').attributes('disabled')).toBeDefined()
  })
})
