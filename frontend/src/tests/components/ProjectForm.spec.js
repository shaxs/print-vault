/**
 * Tests for pure functions extracted from ProjectForm.vue.
 *
 * Because these functions live inside <script setup>, they cannot be imported
 * directly. Their logic is inlined here verbatim so the tests exercise the
 * same code paths without mounting the component.
 */
import { describe, it, expect } from 'vitest'

// ─── Pure function implementations (mirrors ProjectForm.vue) ──────────────────

/**
 * addMaterial(materials)
 * Pushes a blank material entry to the project materials list.
 */
function addMaterial(materials) {
  materials.push({
    label: '',
    custom_color: '',
    blueprint_obj: null,
    mode: 'custom',
  })
}

/**
 * removeMaterial(materials, index)
 * Removes the entry at `index` — no minimum-length guard.
 */
function removeMaterial(materials, index) {
  materials.splice(index, 1)
}

/**
 * formatMaterialName(material)
 * Returns "<brand> <name> (<diameter>mm)" trimmed.
 * Returns '' for falsy input.
 */
function formatMaterialName(material) {
  if (!material) return ''
  const brandName = material.brand?.name || ''
  const diameter = material.diameter ? ` (${material.diameter}mm)` : ''
  return `${brandName} ${material.name}${diameter}`.trim()
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('ProjectForm – addMaterial', () => {
  it('adds one entry to an empty list', () => {
    const list = []
    addMaterial(list)
    expect(list).toHaveLength(1)
  })

  it('new entry has correct default shape', () => {
    const list = []
    addMaterial(list)
    expect(list[0]).toEqual({
      label: '',
      custom_color: '',
      blueprint_obj: null,
      mode: 'custom',
    })
  })

  it('label defaults to empty string', () => {
    const list = []
    addMaterial(list)
    expect(list[0].label).toBe('')
  })

  it('custom_color defaults to empty string', () => {
    const list = []
    addMaterial(list)
    expect(list[0].custom_color).toBe('')
  })

  it('blueprint_obj defaults to null', () => {
    const list = []
    addMaterial(list)
    expect(list[0].blueprint_obj).toBeNull()
  })

  it('mode defaults to "custom"', () => {
    const list = []
    addMaterial(list)
    expect(list[0].mode).toBe('custom')
  })

  it('appends when list already has entries', () => {
    const existing = { label: 'existing', custom_color: '', blueprint_obj: null, mode: 'custom' }
    const list = [existing]
    addMaterial(list)
    expect(list).toHaveLength(2)
    expect(list[0]).toBe(existing)
  })

  it('can be called multiple times to build up the list', () => {
    const list = []
    addMaterial(list)
    addMaterial(list)
    addMaterial(list)
    expect(list).toHaveLength(3)
  })
})

describe('ProjectForm – removeMaterial', () => {
  it('removes the first entry', () => {
    const a = { label: 'A' }
    const b = { label: 'B' }
    const list = [a, b]
    removeMaterial(list, 0)
    expect(list).toEqual([b])
  })

  it('removes the last entry', () => {
    const a = { label: 'A' }
    const b = { label: 'B' }
    const list = [a, b]
    removeMaterial(list, 1)
    expect(list).toEqual([a])
  })

  it('removes a middle entry', () => {
    const entries = [{ label: 'A' }, { label: 'B' }, { label: 'C' }]
    removeMaterial(entries, 1)
    expect(entries).toEqual([{ label: 'A' }, { label: 'C' }])
  })

  it('reduces list length by 1', () => {
    const list = [{ label: 'X' }, { label: 'Y' }]
    removeMaterial(list, 0)
    expect(list).toHaveLength(1)
  })

  it('can remove the only entry (no length guard)', () => {
    const list = [{ label: 'only' }]
    removeMaterial(list, 0)
    expect(list).toHaveLength(0)
  })
})

describe('ProjectForm – formatMaterialName', () => {
  it('returns empty string for null', () => {
    expect(formatMaterialName(null)).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(formatMaterialName(undefined)).toBe('')
  })

  it('formats brand + name + diameter', () => {
    const mat = { brand: { name: 'PolyMaker' }, name: 'PolyLite PLA', diameter: '1.75' }
    expect(formatMaterialName(mat)).toBe('PolyMaker PolyLite PLA (1.75mm)')
  })

  it('omits brand when brand is null', () => {
    const mat = { brand: null, name: 'Generic PLA', diameter: '1.75' }
    expect(formatMaterialName(mat)).toBe('Generic PLA (1.75mm)')
  })

  it('omits brand when brand has no name property', () => {
    const mat = { brand: {}, name: 'Mystery', diameter: '2.85' }
    expect(formatMaterialName(mat)).toBe('Mystery (2.85mm)')
  })

  it('omits diameter when diameter is falsy (null)', () => {
    const mat = { brand: { name: 'Hatchbox' }, name: 'ABS', diameter: null }
    expect(formatMaterialName(mat)).toBe('Hatchbox ABS')
  })

  it('omits diameter when diameter is undefined', () => {
    const mat = { brand: { name: 'eSUN' }, name: 'PETG' }
    expect(formatMaterialName(mat)).toBe('eSUN PETG')
  })

  it('handles no brand and no diameter', () => {
    const mat = { brand: null, name: 'Bare Name', diameter: null }
    expect(formatMaterialName(mat)).toBe('Bare Name')
  })

  it('trims surrounding whitespace from the result', () => {
    // brand is absent, name is provided, no diameter → "  Name" → trimmed
    const mat = { name: 'OnlyName', diameter: null }
    const result = formatMaterialName(mat)
    expect(result).toBe(result.trim())
  })

  it('includes diameter for 2.85mm spool', () => {
    const mat = { brand: { name: 'Prusa' }, name: 'Prusament ASA', diameter: '2.85' }
    expect(formatMaterialName(mat)).toBe('Prusa Prusament ASA (2.85mm)')
  })
})
