/**
 * Tests for the useAppConfig composable (src/composables/useAppConfig.js).
 *
 * Covers: load() populating shared state, load() caching, fail-open on error,
 * isHidden(), and setHidden() add/remove + PATCH persistence.
 *
 * NOTE: the composable holds module-scoped singleton state, so each test resets
 * hiddenModules/loaded in beforeEach.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'

// Inline factory (hoist-safe): creates fresh vi.fn()s with no outer references.
vi.mock('@/services/APIService.js', () => ({
  default: {
    getAppConfig: vi.fn(),
    updateAppConfig: vi.fn(),
  },
}))

import APIService from '@/services/APIService.js'
import { useAppConfig } from '@/composables/useAppConfig.js'

describe('useAppConfig', () => {
  let cfg

  beforeEach(() => {
    vi.clearAllMocks()
    cfg = useAppConfig()
    // Reset the shared singleton state between tests.
    cfg.hiddenModules.value = []
    cfg.loaded.value = false
  })

  it('load() populates hiddenModules from the API', async () => {
    APIService.getAppConfig.mockResolvedValue({ data: { hidden_modules: ['trackers'] } })
    await cfg.load()
    expect(cfg.hiddenModules.value).toEqual(['trackers'])
    expect(cfg.loaded.value).toBe(true)
  })

  it('load() only calls the API once while loaded (cached)', async () => {
    APIService.getAppConfig.mockResolvedValue({ data: { hidden_modules: [] } })
    await cfg.load()
    await cfg.load()
    expect(APIService.getAppConfig).toHaveBeenCalledTimes(1)
  })

  it('load() fails open to all-visible on error, leaving loaded=false for retry', async () => {
    APIService.getAppConfig.mockRejectedValue(new Error('network down'))
    await cfg.load()
    expect(cfg.hiddenModules.value).toEqual([])
    expect(cfg.loaded.value).toBe(false)
  })

  it('isHidden() reflects the current hidden set', async () => {
    APIService.getAppConfig.mockResolvedValue({ data: { hidden_modules: ['printers'] } })
    await cfg.load()
    expect(cfg.isHidden('printers')).toBe(true)
    expect(cfg.isHidden('inventory')).toBe(false)
  })

  it('setHidden(key, true) adds the key and persists via PATCH', async () => {
    APIService.updateAppConfig.mockResolvedValue({ data: { hidden_modules: ['projects'] } })
    await cfg.setHidden('projects', true)
    expect(APIService.updateAppConfig).toHaveBeenCalledWith({ hidden_modules: ['projects'] })
    expect(cfg.hiddenModules.value).toEqual(['projects'])
  })

  it('setHidden(key, false) removes the key and persists via PATCH', async () => {
    cfg.hiddenModules.value = ['projects', 'trackers']
    APIService.updateAppConfig.mockResolvedValue({ data: { hidden_modules: ['trackers'] } })
    await cfg.setHidden('projects', false)
    expect(APIService.updateAppConfig).toHaveBeenCalledWith({ hidden_modules: ['trackers'] })
    expect(cfg.hiddenModules.value).toEqual(['trackers'])
  })

  it('setHidden() does not duplicate an already-hidden key', async () => {
    cfg.hiddenModules.value = ['projects']
    APIService.updateAppConfig.mockResolvedValue({ data: { hidden_modules: ['projects'] } })
    await cfg.setHidden('projects', true)
    expect(APIService.updateAppConfig).toHaveBeenCalledWith({ hidden_modules: ['projects'] })
  })
})
