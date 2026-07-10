/**
 * MaterialDetailView.spec.js
 *
 * Tests for the pure utility logic extracted from MaterialDetailView.vue.
 * Covers: materialName (computed display logic) and hasPrintSettings (computed).
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure functions (mirrors MaterialDetailView.vue implementations)
// ---------------------------------------------------------------------------

/**
 * Pure version of the materialName computed.
 * Returns 'Material' when no data, brand+name when brand present, name only otherwise.
 */
const getMaterialName = (material) => {
  if (!material) return 'Material'
  if (material.brand) {
    return `${material.brand.name} ${material.name}`
  }
  return material.name
}

/**
 * Pure version of hasPrintSettings computed.
 * Returns true if any of the 5 print-setting fields is truthy.
 */
const hasPrintSettings = (material) => {
  if (!material) return false
  return !!(
    material.nozzle_temp_min ||
    material.nozzle_temp_max ||
    material.bed_temp_min ||
    material.bed_temp_max ||
    material.density
  )
}

// ---------------------------------------------------------------------------

describe('MaterialDetailView – getMaterialName', () => {
  it('returns "Material" when material is null', () => {
    expect(getMaterialName(null)).toBe('Material')
  })

  it('returns "Material" when material is undefined', () => {
    expect(getMaterialName(undefined)).toBe('Material')
  })

  it('returns brand + name when brand is present', () => {
    const material = { name: 'PLA+', brand: { name: 'eSun' } }
    expect(getMaterialName(material)).toBe('eSun PLA+')
  })

  it('returns name only when brand is null', () => {
    const material = { name: 'PETG', brand: null }
    expect(getMaterialName(material)).toBe('PETG')
  })

  it('returns name only when brand is absent', () => {
    const material = { name: 'TPU' }
    expect(getMaterialName(material)).toBe('TPU')
  })

  it('handles brand with multi-word name', () => {
    const material = { name: 'ABS+', brand: { name: 'Bambu Lab' } }
    expect(getMaterialName(material)).toBe('Bambu Lab ABS+')
  })

  it('handles name with spaces and special characters', () => {
    const material = { name: 'PLA (White)', brand: { name: 'Hatchbox' } }
    expect(getMaterialName(material)).toBe('Hatchbox PLA (White)')
  })
})

// ---------------------------------------------------------------------------

describe('MaterialDetailView – hasPrintSettings', () => {
  it('returns false when material is null', () => {
    expect(hasPrintSettings(null)).toBe(false)
  })

  it('returns false when material is undefined', () => {
    expect(hasPrintSettings(undefined)).toBe(false)
  })

  it('returns false when all settings are null/falsy', () => {
    const material = {
      nozzle_temp_min: null,
      nozzle_temp_max: null,
      bed_temp_min: null,
      bed_temp_max: null,
      density: null,
    }
    expect(hasPrintSettings(material)).toBe(false)
  })

  it('returns false when all settings are 0 (falsy)', () => {
    const material = {
      nozzle_temp_min: 0,
      nozzle_temp_max: 0,
      bed_temp_min: 0,
      bed_temp_max: 0,
      density: 0,
    }
    expect(hasPrintSettings(material)).toBe(false)
  })

  it('returns true when nozzle_temp_min is set', () => {
    const material = {
      nozzle_temp_min: 200,
      nozzle_temp_max: null,
      bed_temp_min: null,
      bed_temp_max: null,
      density: null,
    }
    expect(hasPrintSettings(material)).toBe(true)
  })

  it('returns true when nozzle_temp_max is set', () => {
    const material = {
      nozzle_temp_min: null,
      nozzle_temp_max: 230,
      bed_temp_min: null,
      bed_temp_max: null,
      density: null,
    }
    expect(hasPrintSettings(material)).toBe(true)
  })

  it('returns true when bed_temp_min is set', () => {
    const material = {
      nozzle_temp_min: null,
      nozzle_temp_max: null,
      bed_temp_min: 60,
      bed_temp_max: null,
      density: null,
    }
    expect(hasPrintSettings(material)).toBe(true)
  })

  it('returns true when bed_temp_max is set', () => {
    const material = {
      nozzle_temp_min: null,
      nozzle_temp_max: null,
      bed_temp_min: null,
      bed_temp_max: 80,
      density: null,
    }
    expect(hasPrintSettings(material)).toBe(true)
  })

  it('returns true when only density is set', () => {
    const material = {
      nozzle_temp_min: null,
      nozzle_temp_max: null,
      bed_temp_min: null,
      bed_temp_max: null,
      density: 1.24,
    }
    expect(hasPrintSettings(material)).toBe(true)
  })

  it('returns true when all settings are set', () => {
    const material = {
      nozzle_temp_min: 200,
      nozzle_temp_max: 230,
      bed_temp_min: 60,
      bed_temp_max: 80,
      density: 1.24,
    }
    expect(hasPrintSettings(material)).toBe(true)
  })

  it('returns false when fields are missing entirely', () => {
    expect(hasPrintSettings({})).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Favorite toggle button (regression: there was previously no way to favorite
// a blueprint from any reachable view — only an orphaned, unrouted component
// had a working star toggle).
// ---------------------------------------------------------------------------

/**
 * Pure version of the `v-if="!material.is_generic"` guard on the favorite button.
 * Generic materials can't be favorited (the backend 400s), so the button is hidden.
 */
const shouldShowFavoriteToggle = (material) => !material.is_generic

/**
 * Pure version of toggleFavorite()'s state update after a successful API call.
 * The backend action responds with {status: 'favorited', order: N} or
 * {status: 'unfavorited'} - NOT {is_favorite, favorite_order} (regression:
 * the first version of this code assumed the wrong response shape, which
 * silently made the star always render as unfavorited after any click since
 * response.is_favorite was always undefined).
 */
const applyFavoriteToggleResponse = (material, response) => {
  material.is_favorite = response.status === 'favorited'
  material.favorite_order = response.order ?? null
  return material
}

describe('MaterialDetailView – favorite toggle visibility', () => {
  it('shows the toggle for a blueprint (is_generic: false)', () => {
    expect(shouldShowFavoriteToggle({ is_generic: false })).toBe(true)
  })

  it('hides the toggle for a generic material (is_generic: true)', () => {
    expect(shouldShowFavoriteToggle({ is_generic: true })).toBe(false)
  })
})

describe('MaterialDetailView – applyFavoriteToggleResponse', () => {
  it('sets is_favorite true and favorite_order from a "favorited" response', () => {
    const material = { id: 1, is_favorite: false, favorite_order: null }
    const result = applyFavoriteToggleResponse(material, { status: 'favorited', order: 3 })
    expect(result.is_favorite).toBe(true)
    expect(result.favorite_order).toBe(3)
  })

  it('sets is_favorite false and clears favorite_order from an "unfavorited" response', () => {
    const material = { id: 1, is_favorite: true, favorite_order: 2 }
    // Real backend response for unfavoriting omits `order` entirely.
    const result = applyFavoriteToggleResponse(material, { status: 'unfavorited' })
    expect(result.is_favorite).toBe(false)
    expect(result.favorite_order).toBeNull()
  })
})
