/**
 * MaterialCreateView.spec.js
 *
 * Tests for pure helper logic extracted from MaterialCreateView.vue.
 * NOTE: MaterialEditView.vue contains identical implementations of addBrand,
 * addVendor, addColor, removeColor, and the colorMode-switching logic; this
 * file covers both views' shared patterns.
 *
 * Functions under test (extracted as standalone implementations):
 *   - addColor(colors)           append default black to the colors array
 *   - removeColor(colors, idx)   remove a colour at index (guarded: length>2, idx>=2)
 *   - applyColorMode             switch between 'single' and 'multi' colour modes
 *   - buildBrandObject           create a local brand{ id:null, name } from a search term
 *   - buildVendorObject          create a local vendor{ id:null, name } from a search term
 *   - applyClonedData            populate a material form object from a cloneData snapshot
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure function implementations (mirrors MaterialCreateView.vue)
// ---------------------------------------------------------------------------

/**
 * Append a default black colour to the colours array.
 * Mutates in place (mirrors .push() in the component).
 */
const addColor = (colors) => {
  colors.push('#000000')
}

/**
 * Remove the colour at `index` from the `colors` array.
 * Guard: the array must have MORE than 2 items AND index must be >= 2.
 * (Items at 0 and 1 are protected since multi-colour mode requires at least 2.)
 */
const removeColor = (colors, index) => {
  if (colors.length > 2 && index >= 2) {
    colors.splice(index, 1)
  }
}

/**
 * Apply a colour-mode switch to a colors array and return the new array.
 * - 'single': keep only the first colour
 * - 'multi' : add a default second colour when length === 1
 * - otherwise: return unchanged
 */
const applyColorMode = (newMode, colors) => {
  if (newMode === 'single' && colors.length > 1) {
    return [colors[0]]
  }
  if (newMode === 'multi' && colors.length === 1) {
    return [...colors, '#000000']
  }
  return [...colors]
}

/**
 * Create a new brand object (id=null) from a UI search term.
 * Returns null when the search term is falsy.
 */
const buildBrandObject = (searchTerm) => {
  if (!searchTerm) return null
  return { id: null, name: searchTerm }
}

/**
 * Create a new vendor object (id=null) from a UI search term.
 * Returns null when the search term is falsy.
 */
const buildVendorObject = (searchTerm) => {
  if (!searchTerm) return null
  return { id: null, name: searchTerm }
}

/**
 * Populate a material form object from a parsed clone-data snapshot.
 * Returns a new object; does NOT mutate the original.
 * Mirrors the hydration logic inside loadClonedData().
 */
const applyClonedData = (cloneData) => {
  return {
    is_generic: cloneData.is_generic || false,
    brand: cloneData.brand || null,
    base_material: cloneData.base_material || null,
    diameter: cloneData.diameter || '1.75',
    spool_weight: cloneData.spool_weight || 1000,
    empty_spool_weight: cloneData.empty_spool_weight || null,
    price_per_spool: cloneData.price_per_spool || null,
    low_stock_threshold: cloneData.low_stock_threshold || 2,
    nozzle_temp_min: cloneData.nozzle_temp_min || null,
    nozzle_temp_max: cloneData.nozzle_temp_max || null,
    bed_temp_min: cloneData.bed_temp_min || null,
    bed_temp_max: cloneData.bed_temp_max || null,
    density: cloneData.density || null,
    notes: cloneData.notes || '',
    // Reset-to-defaults (these are always blanked on clone)
    name: '',
    colors: ['#000000'],
    color_family: null,
    vendor: null,
    vendor_link: '',
    tds_value: null,
  }
}

// ---------------------------------------------------------------------------

describe('MaterialCreateView – addColor', () => {
  it('appends #000000 to an empty array', () => {
    const colors = []
    addColor(colors)
    expect(colors).toEqual(['#000000'])
  })

  it('appends #000000 to an existing array', () => {
    const colors = ['#FF0000']
    addColor(colors)
    expect(colors).toEqual(['#FF0000', '#000000'])
  })

  it('can be called multiple times to add multiple blacks', () => {
    const colors = ['#AABBCC']
    addColor(colors)
    addColor(colors)
    expect(colors).toHaveLength(3)
    expect(colors[1]).toBe('#000000')
    expect(colors[2]).toBe('#000000')
  })

  it('mutates the original array (does not return a new one)', () => {
    const colors = ['#112233']
    const ref = colors
    addColor(colors)
    expect(colors).toBe(ref) // same reference
  })
})

// ---------------------------------------------------------------------------

describe('MaterialCreateView – removeColor', () => {
  it('removes the colour at index 2 when length is 3', () => {
    const colors = ['#111', '#222', '#333']
    removeColor(colors, 2)
    expect(colors).toEqual(['#111', '#222'])
  })

  it('removes a colour at index 3 when length > 3', () => {
    const colors = ['#AAA', '#BBB', '#CCC', '#DDD']
    removeColor(colors, 3)
    expect(colors).toEqual(['#AAA', '#BBB', '#CCC'])
  })

  it('does NOT remove when index is 0 (protected slot)', () => {
    const colors = ['#AAA', '#BBB', '#CCC']
    removeColor(colors, 0)
    expect(colors).toEqual(['#AAA', '#BBB', '#CCC'])
  })

  it('does NOT remove when index is 1 (protected slot)', () => {
    const colors = ['#AAA', '#BBB', '#CCC']
    removeColor(colors, 1)
    expect(colors).toEqual(['#AAA', '#BBB', '#CCC'])
  })

  it('does NOT remove when length is exactly 2 (minimum required)', () => {
    const colors = ['#AAA', '#BBB']
    removeColor(colors, 1)
    expect(colors).toEqual(['#AAA', '#BBB'])
  })

  it('does NOT remove when length is 1', () => {
    const colors = ['#AAA']
    removeColor(colors, 0)
    expect(colors).toEqual(['#AAA'])
  })

  it('removes a colour in the middle of a long array', () => {
    const colors = ['#000', '#111', '#222', '#333', '#444']
    removeColor(colors, 2)
    expect(colors).toEqual(['#000', '#111', '#333', '#444'])
  })
})

// ---------------------------------------------------------------------------

describe('MaterialCreateView – applyColorMode', () => {
  it('switches to single: keeps only the first colour', () => {
    const result = applyColorMode('single', ['#RED', '#BLUE', '#GREEN'])
    expect(result).toEqual(['#RED'])
  })

  it('switches to single: no-op when already one colour', () => {
    const result = applyColorMode('single', ['#RED'])
    expect(result).toEqual(['#RED'])
  })

  it('switches to multi: adds a black when only one colour exists', () => {
    const result = applyColorMode('multi', ['#RED'])
    expect(result).toEqual(['#RED', '#000000'])
  })

  it('switches to multi: no-op when two colours already exist', () => {
    const result = applyColorMode('multi', ['#RED', '#BLUE'])
    expect(result).toEqual(['#RED', '#BLUE'])
  })

  it('returns a new array (does NOT mutate original)', () => {
    const original = ['#RED', '#BLUE']
    const result = applyColorMode('multi', original)
    expect(result).not.toBe(original)
  })

  it('returns unchanged copy for unknown mode', () => {
    const result = applyColorMode('rainbow', ['#AAA', '#BBB'])
    expect(result).toEqual(['#AAA', '#BBB'])
  })
})

// ---------------------------------------------------------------------------

describe('MaterialCreateView – buildBrandObject', () => {
  it('creates a brand object with id=null from a search term', () => {
    expect(buildBrandObject('Polymaker')).toEqual({ id: null, name: 'Polymaker' })
  })

  it('returns null for empty string', () => {
    expect(buildBrandObject('')).toBeNull()
  })

  it('returns null for null input', () => {
    expect(buildBrandObject(null)).toBeNull()
  })

  it('returns null for undefined input', () => {
    expect(buildBrandObject(undefined)).toBeNull()
  })

  it('preserves whitespace in brand name (no trimming in source)', () => {
    expect(buildBrandObject(' Brand Name ').name).toBe(' Brand Name ')
  })
})

// ---------------------------------------------------------------------------

describe('MaterialCreateView – buildVendorObject', () => {
  it('creates a vendor object with id=null from a search term', () => {
    expect(buildVendorObject('AliExpress')).toEqual({ id: null, name: 'AliExpress' })
  })

  it('returns null for empty string', () => {
    expect(buildVendorObject('')).toBeNull()
  })

  it('returns null for null input', () => {
    expect(buildVendorObject(null)).toBeNull()
  })

  it('handles numeric-looking vendor names', () => {
    expect(buildVendorObject('3DJake')).toEqual({ id: null, name: '3DJake' })
  })
})

// ---------------------------------------------------------------------------

describe('MaterialCreateView – applyClonedData', () => {
  const fullClone = {
    is_generic: true,
    brand: { id: 5, name: 'Hatchbox' },
    base_material: { id: 2, name: 'PETG' },
    diameter: '3.00',
    spool_weight: 800,
    empty_spool_weight: 200,
    price_per_spool: '19.99',
    low_stock_threshold: 3,
    nozzle_temp_min: 230,
    nozzle_temp_max: 250,
    bed_temp_min: 70,
    bed_temp_max: 85,
    density: 1.27,
    notes: 'Great PETG',
    lowStockEnabled: true,
  }

  it('copies is_generic from clone data', () => {
    expect(applyClonedData(fullClone).is_generic).toBe(true)
  })

  it('copies brand from clone data', () => {
    expect(applyClonedData(fullClone).brand).toEqual({ id: 5, name: 'Hatchbox' })
  })

  it('copies diameter from clone data', () => {
    expect(applyClonedData(fullClone).diameter).toBe('3.00')
  })

  it('falls back diameter to 1.75 when missing', () => {
    expect(applyClonedData({}).diameter).toBe('1.75')
  })

  it('falls back spool_weight to 1000 when missing', () => {
    expect(applyClonedData({}).spool_weight).toBe(1000)
  })

  it('falls back low_stock_threshold to 2 when missing', () => {
    expect(applyClonedData({}).low_stock_threshold).toBe(2)
  })

  it('always resets name to empty string', () => {
    const clone = { ...fullClone, name: 'Old Name' }
    expect(applyClonedData(clone).name).toBe('')
  })

  it('always resets colors to ["#000000"]', () => {
    const clone = { ...fullClone, colors: ['#RED', '#BLUE'] }
    expect(applyClonedData(clone).colors).toEqual(['#000000'])
  })

  it('always resets vendor to null', () => {
    const clone = { ...fullClone, vendor: { id: 1, name: 'SomeVendor' } }
    expect(applyClonedData(clone).vendor).toBeNull()
  })

  it('always resets color_family to null', () => {
    expect(applyClonedData(fullClone).color_family).toBeNull()
  })

  it('always resets tds_value to null', () => {
    expect(applyClonedData(fullClone).tds_value).toBeNull()
  })

  it('always resets vendor_link to empty string', () => {
    expect(applyClonedData(fullClone).vendor_link).toBe('')
  })

  it('copies notes from clone data', () => {
    expect(applyClonedData(fullClone).notes).toBe('Great PETG')
  })

  it('defaults notes to empty string when missing', () => {
    expect(applyClonedData({}).notes).toBe('')
  })

  it('copies nozzle and bed temps from clone data', () => {
    const result = applyClonedData(fullClone)
    expect(result.nozzle_temp_min).toBe(230)
    expect(result.nozzle_temp_max).toBe(250)
    expect(result.bed_temp_min).toBe(70)
    expect(result.bed_temp_max).toBe(85)
  })

  it('does NOT mutate the input clone object', () => {
    const original = { ...fullClone }
    applyClonedData(fullClone)
    expect(fullClone).toEqual(original)
  })
})
