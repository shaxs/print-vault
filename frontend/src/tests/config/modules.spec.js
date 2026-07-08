/**
 * Tests for the sidebar module registry (src/config/modules.js).
 *
 * The registry is the single source of truth for which top-level sections can
 * be hidden. Dashboard and Settings must never appear here (they are
 * structurally always-visible).
 */
import { describe, it, expect } from 'vitest'
import { MODULES, HIDEABLE_KEYS } from '@/config/modules.js'

describe('modules registry', () => {
  it('lists the five hideable sidebar modules in order', () => {
    expect(MODULES.map((m) => m.key)).toEqual([
      'inventory',
      'filaments',
      'printers',
      'projects',
      'trackers',
    ])
  })

  it('every module has a key, label and route path', () => {
    for (const module of MODULES) {
      expect(typeof module.key).toBe('string')
      expect(typeof module.label).toBe('string')
      expect(module.to.startsWith('/')).toBe(true)
    }
  })

  it('derives HIDEABLE_KEYS from MODULES', () => {
    expect(HIDEABLE_KEYS).toEqual(MODULES.map((m) => m.key))
  })

  it('never includes dashboard or settings (always-visible sections)', () => {
    expect(HIDEABLE_KEYS).not.toContain('dashboard')
    expect(HIDEABLE_KEYS).not.toContain('settings')
  })
})
