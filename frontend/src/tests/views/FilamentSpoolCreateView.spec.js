/**
 * FilamentSpoolCreateView.spec.js
 *
 * Tests for pure helper logic extracted from FilamentSpoolCreateView.vue.
 *
 * Functions under test (extracted as standalone implementations):
 *   - formatMaterialLabel(mat)         build a human-readable material label
 *   - addQuickAddColor(colors)         append default black to the Quick Add colors array
 *   - removeQuickAddColor(colors, idx) remove a color guarded (length>2, idx>=2)
 *   - buildLocationObject(name)        create a local location { id:null, name } object
 *   - buildBrandObject(name)           create a local brand { id:null, name } object
 *   - applyQuickAddColorMode           switch between single/multi color mode for Quick Add
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure function implementations (mirrors FilamentSpoolCreateView.vue)
// ---------------------------------------------------------------------------

/** Build a human-readable label for a material blueprint. */
const formatMaterialLabel = (mat) => {
  if (!mat) return ''
  const brandName = mat.brand?.name || ''
  const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
  return `${brandName} ${mat.name}${diameter}`.trim()
}

/** Append a default black to the Quick Add colors array. */
const addQuickAddColor = (colors) => {
  colors.push('#000000')
}

/**
 * Remove the color at `index` from the Quick Add colors array.
 * Multi-color mode requires at least 2 colors (indices 0 and 1 are protected).
 */
const removeQuickAddColor = (colors, index) => {
  if (colors.length > 2 && index >= 2) {
    colors.splice(index, 1)
  }
}

/** Create a new location object (id=null) from an input name. Returns null for falsy. */
const buildLocationObject = (name) => {
  if (!name) return null
  return { id: null, name }
}

/** Create a new brand object (id=null) from an input name. Returns null for falsy. */
const buildBrandObject = (name) => {
  if (!name) return null
  return { id: null, name }
}

/**
 * Apply a Quick Add color mode change and return the adjusted colors array.
 *   'single' → keep only the first color
 *   'multi'  → add a default second color when only one exists
 */
const applyQuickAddColorMode = (newMode, colors) => {
  if (newMode === 'single' && colors.length > 1) {
    return [colors[0]]
  }
  if (newMode === 'multi' && colors.length === 1) {
    return [...colors, '#000000']
  }
  return [...colors]
}

// ---------------------------------------------------------------------------

describe('FilamentSpoolCreateView – formatMaterialLabel', () => {
  it('returns empty string for null input', () => {
    expect(formatMaterialLabel(null)).toBe('')
  })

  it('returns empty string for undefined input', () => {
    expect(formatMaterialLabel(undefined)).toBe('')
  })

  it('combines brand name and material name', () => {
    expect(formatMaterialLabel({ name: 'PLA+', brand: { name: 'Polymaker' }, diameter: null }))
      .toBe('Polymaker PLA+')
  })

  it('includes diameter when provided', () => {
    expect(formatMaterialLabel({ name: 'PETG', brand: { name: 'Hatchbox' }, diameter: '1.75' }))
      .toBe('Hatchbox PETG (1.75mm)')
  })

  it('omits brand when null', () => {
    expect(formatMaterialLabel({ name: 'ABS', brand: null, diameter: '1.75' }))
      .toBe('ABS (1.75mm)')
  })

  it('trims the result', () => {
    const label = formatMaterialLabel({ name: 'TPU', brand: null, diameter: null })
    expect(label).toBe(label.trim())
    expect(label).toBe('TPU')
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolCreateView – addQuickAddColor', () => {
  it('appends #000000 to an existing colors array', () => {
    const colors = ['#FF0000']
    addQuickAddColor(colors)
    expect(colors).toEqual(['#FF0000', '#000000'])
  })

  it('works on an empty array', () => {
    const colors = []
    addQuickAddColor(colors)
    expect(colors).toEqual(['#000000'])
  })

  it('mutates the original array', () => {
    const colors = ['#AABBCC']
    const ref = colors
    addQuickAddColor(colors)
    expect(colors).toBe(ref)
  })

  it('can be called multiple times', () => {
    const colors = ['#RED']
    addQuickAddColor(colors)
    addQuickAddColor(colors)
    expect(colors).toHaveLength(3)
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolCreateView – removeQuickAddColor', () => {
  it('removes the color at index 2 when length is 3', () => {
    const colors = ['#AAA', '#BBB', '#CCC']
    removeQuickAddColor(colors, 2)
    expect(colors).toEqual(['#AAA', '#BBB'])
  })

  it('does NOT remove index 0 (protected)', () => {
    const colors = ['#AAA', '#BBB', '#CCC']
    removeQuickAddColor(colors, 0)
    expect(colors).toEqual(['#AAA', '#BBB', '#CCC'])
  })

  it('does NOT remove index 1 (protected)', () => {
    const colors = ['#AAA', '#BBB', '#CCC']
    removeQuickAddColor(colors, 1)
    expect(colors).toEqual(['#AAA', '#BBB', '#CCC'])
  })

  it('does NOT remove when length is exactly 2', () => {
    const colors = ['#AAA', '#BBB']
    removeQuickAddColor(colors, 1)
    expect(colors).toEqual(['#AAA', '#BBB'])
  })

  it('removes from middle of a longer array', () => {
    const colors = ['#1', '#2', '#3', '#4', '#5']
    removeQuickAddColor(colors, 3)
    expect(colors).toEqual(['#1', '#2', '#3', '#5'])
  })

  it('does NOT remove when length is 1', () => {
    const colors = ['#ONLY']
    removeQuickAddColor(colors, 0)
    expect(colors).toEqual(['#ONLY'])
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolCreateView – buildLocationObject', () => {
  it('creates a location object with id=null', () => {
    expect(buildLocationObject('Dry Box 1')).toEqual({ id: null, name: 'Dry Box 1' })
  })

  it('returns null for empty string', () => {
    expect(buildLocationObject('')).toBeNull()
  })

  it('returns null for null input', () => {
    expect(buildLocationObject(null)).toBeNull()
  })

  it('returns null for undefined input', () => {
    expect(buildLocationObject(undefined)).toBeNull()
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolCreateView – buildBrandObject', () => {
  it('creates a brand object with id=null', () => {
    expect(buildBrandObject('Polymaker')).toEqual({ id: null, name: 'Polymaker' })
  })

  it('returns null for empty string', () => {
    expect(buildBrandObject('')).toBeNull()
  })

  it('returns null for null input', () => {
    expect(buildBrandObject(null)).toBeNull()
  })
})

// ---------------------------------------------------------------------------

describe('FilamentSpoolCreateView – applyQuickAddColorMode', () => {
  it('single mode: keeps only the first color', () => {
    expect(applyQuickAddColorMode('single', ['#RED', '#BLUE', '#GREEN'])).toEqual(['#RED'])
  })

  it('single mode: no-op when already one color', () => {
    expect(applyQuickAddColorMode('single', ['#RED'])).toEqual(['#RED'])
  })

  it('multi mode: adds default black when only one color', () => {
    expect(applyQuickAddColorMode('multi', ['#RED'])).toEqual(['#RED', '#000000'])
  })

  it('multi mode: no-op when two colors already exist', () => {
    expect(applyQuickAddColorMode('multi', ['#RED', '#BLUE'])).toEqual(['#RED', '#BLUE'])
  })

  it('returns a NEW array (does not mutate original)', () => {
    const original = ['#RED']
    const result = applyQuickAddColorMode('multi', original)
    expect(result).not.toBe(original)
  })

  it('returns unchanged copy for unknown mode', () => {
    expect(applyQuickAddColorMode('triple', ['#A', '#B'])).toEqual(['#A', '#B'])
  })
})
