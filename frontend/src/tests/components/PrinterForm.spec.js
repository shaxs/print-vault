/**
 * Tests for pure / stateless functions extracted from
 * frontend/src/components/PrinterForm.vue
 *
 * Covered functions
 * ─────────────────
 * - addAdditionalFilament(filaments)       push default filament entry
 * - removeAdditionalFilament(filaments, i) splice entry at index
 * - addBrand(name, brands, printer)        create brand object, wire to printer
 * - formatMaterialLabel(mat)               label display string
 *
 * All functions are inlined here (extract-and-test pattern) because Vue
 * <script setup> does not expose internals without defineExpose.
 */

import { describe, it, expect } from 'vitest'

// ─────────────────────────────────────────────────────────────────────────────
// Extracted functions (mirrors PrinterForm.vue logic exactly)
// ─────────────────────────────────────────────────────────────────────────────

function addAdditionalFilament(filaments) {
  filaments.push({
    type: '',
    mode: 'custom',
    custom: '',
    blueprint: null,
  })
}

function removeAdditionalFilament(filaments, index) {
  filaments.splice(index, 1)
}

function addBrand(newBrand, brands, printer) {
  const brand = { name: newBrand }
  brands.push(brand)
  printer.manufacturer = brand
}

function formatMaterialLabel(mat) {
  if (!mat) return ''
  const brandName = mat.brand?.name || ''
  const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
  return `${brandName} ${mat.name}${diameter}`.trim()
}

// ─────────────────────────────────────────────────────────────────────────────
// addAdditionalFilament
// ─────────────────────────────────────────────────────────────────────────────

describe('addAdditionalFilament', () => {
  it('appends one entry to an empty array', () => {
    const filaments = []
    addAdditionalFilament(filaments)
    expect(filaments).toHaveLength(1)
  })

  it('creates entry with the correct default shape', () => {
    const filaments = []
    addAdditionalFilament(filaments)
    expect(filaments[0]).toEqual({
      type: '',
      mode: 'custom',
      custom: '',
      blueprint: null,
    })
  })

  it('appends without overwriting existing entries', () => {
    const existing = { type: 'Canopy', mode: 'custom', custom: 'Red PLA', blueprint: null }
    const filaments = [existing]
    addAdditionalFilament(filaments)
    expect(filaments).toHaveLength(2)
    expect(filaments[0]).toBe(existing)
  })

  it('can be called multiple times to add multiple entries', () => {
    const filaments = []
    addAdditionalFilament(filaments)
    addAdditionalFilament(filaments)
    addAdditionalFilament(filaments)
    expect(filaments).toHaveLength(3)
    filaments.forEach((f) => expect(f).toEqual({ type: '', mode: 'custom', custom: '', blueprint: null }))
  })

  it('default mode is always "custom"', () => {
    const filaments = []
    addAdditionalFilament(filaments)
    expect(filaments[0].mode).toBe('custom')
  })

  it('default blueprint is null', () => {
    const filaments = []
    addAdditionalFilament(filaments)
    expect(filaments[0].blueprint).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// removeAdditionalFilament
// ─────────────────────────────────────────────────────────────────────────────

describe('removeAdditionalFilament', () => {
  it('removes the entry at the given index', () => {
    const filaments = [
      { type: 'A' },
      { type: 'B' },
      { type: 'C' },
    ]
    removeAdditionalFilament(filaments, 1)
    expect(filaments).toHaveLength(2)
    expect(filaments[0].type).toBe('A')
    expect(filaments[1].type).toBe('C')
  })

  it('removes the first entry', () => {
    const filaments = [{ type: 'A' }, { type: 'B' }]
    removeAdditionalFilament(filaments, 0)
    expect(filaments).toHaveLength(1)
    expect(filaments[0].type).toBe('B')
  })

  it('removes the last entry', () => {
    const filaments = [{ type: 'A' }, { type: 'B' }]
    removeAdditionalFilament(filaments, 1)
    expect(filaments).toHaveLength(1)
    expect(filaments[0].type).toBe('A')
  })

  it('reduces array to empty when only one entry exists', () => {
    const filaments = [{ type: 'Solo' }]
    removeAdditionalFilament(filaments, 0)
    expect(filaments).toHaveLength(0)
  })

  it('mutates the original array (in-place splice)', () => {
    const filaments = [{ type: 'A' }, { type: 'B' }]
    const ref = filaments
    removeAdditionalFilament(filaments, 0)
    expect(ref).toBe(filaments) // same reference
    expect(ref).toHaveLength(1)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// addBrand
// ─────────────────────────────────────────────────────────────────────────────

describe('addBrand', () => {
  it('adds a new brand object to the brands array', () => {
    const brands = []
    const printer = { manufacturer: null }
    addBrand('Bambu Lab', brands, printer)
    expect(brands).toHaveLength(1)
    expect(brands[0]).toEqual({ name: 'Bambu Lab' })
  })

  it('sets the printer manufacturer to the new brand', () => {
    const brands = []
    const printer = { manufacturer: null }
    addBrand('Prusa', brands, printer)
    expect(printer.manufacturer).toEqual({ name: 'Prusa' })
  })

  it('manufacturer reference matches the brands array entry', () => {
    const brands = []
    const printer = { manufacturer: null }
    addBrand('Creality', brands, printer)
    expect(printer.manufacturer).toBe(brands[0])
  })

  it('appends to existing brands without clearing them', () => {
    const brands = [{ name: 'Existing' }]
    const printer = { manufacturer: null }
    addBrand('New Brand', brands, printer)
    expect(brands).toHaveLength(2)
    expect(brands[0].name).toBe('Existing')
    expect(brands[1].name).toBe('New Brand')
  })

  it('new brand has only a name property', () => {
    const brands = []
    const printer = { manufacturer: null }
    addBrand('TestBrand', brands, printer)
    expect(Object.keys(brands[0])).toEqual(['name'])
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// formatMaterialLabel
// ─────────────────────────────────────────────────────────────────────────────

describe('formatMaterialLabel (PrinterForm)', () => {
  it('returns empty string for null material', () => {
    expect(formatMaterialLabel(null)).toBe('')
  })

  it('returns empty string for undefined material', () => {
    expect(formatMaterialLabel(undefined)).toBe('')
  })

  it('formats brand and name without diameter', () => {
    expect(formatMaterialLabel({ brand: { name: 'Bambu' }, name: 'PLA Basic' })).toBe('Bambu PLA Basic')
  })

  it('includes diameter in parentheses when present', () => {
    expect(
      formatMaterialLabel({ brand: { name: 'Prusament' }, name: 'PETG', diameter: 1.75 })
    ).toBe('Prusament PETG (1.75mm)')
  })

  it('uses empty string for missing brand', () => {
    expect(formatMaterialLabel({ name: 'ABS', diameter: 2.85 })).toBe('ABS (2.85mm)')
  })

  it('trims extra whitespace when brand is empty', () => {
    const result = formatMaterialLabel({ brand: null, name: 'TPU' })
    expect(result).toBe('TPU')
    expect(result).not.toMatch(/^\s|\s$/)
  })
})
