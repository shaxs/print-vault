/**
 * filenameParser.spec.js
 *
 * Tests for the centralized filename parsing utilities in src/utils/filenameParser.js.
 * These utilities extract quantity, color, and material defaults from 3D print filenames.
 */

import { describe, it, expect } from 'vitest'
import {
  parseFilename,
  applySmartDefaults,
  applySmartDefaultsBatch,
  getSupportedQuantityPatterns,
  getSupportedColorPatterns,
} from '../../utils/filenameParser'

// ---------------------------------------------------------------------------

describe('filenameParser – parseFilename – colour detection', () => {
  it('defaults to Primary when no prefix is present', () => {
    expect(parseFilename('bracket.stl').color).toBe('Primary')
  })

  it('detects Accent from [a]_ prefix', () => {
    expect(parseFilename('[a]_bracket.stl').color).toBe('Accent')
  })

  it('detects Accent from (a)_ prefix', () => {
    expect(parseFilename('(a)_bracket.stl').color).toBe('Accent')
  })

  it('is case-insensitive for [A]_ prefix', () => {
    expect(parseFilename('[A]_bracket.stl').color).toBe('Accent')
  })

  it('is case-insensitive for (A)_ prefix', () => {
    expect(parseFilename('(A)_bracket.stl').color).toBe('Accent')
  })

  it('detects Other from [b]_ prefix', () => {
    expect(parseFilename('[b]_part.stl').color).toBe('Other')
  })

  it('detects Other from (b)_ prefix', () => {
    expect(parseFilename('(b)_part.stl').color).toBe('Other')
  })

  it('detects Multicolor from [d]_ prefix', () => {
    expect(parseFilename('[d]_body.stl').color).toBe('Multicolor')
  })

  it('detects Multicolor from (d)_ prefix', () => {
    expect(parseFilename('(d)_body.stl').color).toBe('Multicolor')
  })

  it('returns Primary when prefix is not at start of filename', () => {
    // Prefix in middle of name should not trigger colour detection
    expect(parseFilename('my_[a]_part.stl').color).toBe('Primary')
  })
})

// ---------------------------------------------------------------------------

describe('filenameParser – parseFilename – quantity detection', () => {
  it('defaults to 1 when no quantity pattern is found', () => {
    expect(parseFilename('bracket.stl').quantity).toBe(1)
  })

  it('detects quantity from _x2 suffix', () => {
    expect(parseFilename('bracket_x2.stl').quantity).toBe(2)
  })

  it('detects quantity from _x10 (double digit)', () => {
    expect(parseFilename('screw_x10.stl').quantity).toBe(10)
  })

  it('detects quantity from (x3) pattern', () => {
    expect(parseFilename('tool_(x3).stl').quantity).toBe(3)
  })

  it('detects quantity from [x4] pattern', () => {
    expect(parseFilename('part[x4].stl').quantity).toBe(4)
  })

  it('detects quantity from space+x pattern', () => {
    expect(parseFilename('hinge x5.stl').quantity).toBe(5)
  })

  it('is case-insensitive for x quantity (X vs x)', () => {
    expect(parseFilename('bolt_X3.stl').quantity).toBe(3)
  })

  it('handles combined Accent + quantity', () => {
    const result = parseFilename('[a]_front_skirt_x2.stl')
    expect(result.color).toBe('Accent')
    expect(result.quantity).toBe(2)
  })

  it('handles combined Multicolor + quantity', () => {
    const result = parseFilename('[d]_corner_post_x4.stl')
    expect(result.color).toBe('Multicolor')
    expect(result.quantity).toBe(4)
  })
})

// ---------------------------------------------------------------------------

describe('filenameParser – parseFilename – material default', () => {
  it('uses ABS as default material when none specified', () => {
    expect(parseFilename('part.stl').material).toBe('ABS')
  })

  it('uses custom default material when provided', () => {
    expect(parseFilename('part.stl', 'PLA').material).toBe('PLA')
  })

  it('uses custom default material with PETG', () => {
    expect(parseFilename('part.stl', 'PETG').material).toBe('PETG')
  })
})

// ---------------------------------------------------------------------------

describe('filenameParser – parseFilename – return shape', () => {
  it('always returns an object with quantity, color, and material', () => {
    const result = parseFilename('any_file.stl')
    expect(result).toHaveProperty('quantity')
    expect(result).toHaveProperty('color')
    expect(result).toHaveProperty('material')
  })

  it('quantity is always a number', () => {
    expect(typeof parseFilename('[a]_bracket_x3.stl').quantity).toBe('number')
  })
})

// ---------------------------------------------------------------------------

describe('filenameParser – applySmartDefaults', () => {
  it('applies color default when color is missing', () => {
    const file = { name: '[a]_part.stl' }
    const result = applySmartDefaults(file)
    expect(result.color).toBe('Accent')
  })

  it('does not overwrite existing color', () => {
    const file = { name: '[a]_part.stl', color: 'Clear' }
    applySmartDefaults(file)
    expect(file.color).toBe('Clear')
  })

  it('applies material default when material is missing', () => {
    const file = { name: 'part.stl' }
    applySmartDefaults(file)
    expect(file.material).toBe('ABS')
  })

  it('does not overwrite existing material', () => {
    const file = { name: 'part.stl', material: 'PETG' }
    applySmartDefaults(file)
    expect(file.material).toBe('PETG')
  })

  it('applies quantity from filename when quantity is 1 (default)', () => {
    const file = { name: 'bracket_x3.stl', quantity: 1 }
    applySmartDefaults(file)
    expect(file.quantity).toBe(3)
  })

  it('does not overwrite quantity when it is already > 1', () => {
    const file = { name: 'bracket_x3.stl', quantity: 5 }
    applySmartDefaults(file)
    expect(file.quantity).toBe(5)
  })

  it('applies quantity when quantity is missing (falsy)', () => {
    const file = { name: 'part_x2.stl' }
    applySmartDefaults(file)
    expect(file.quantity).toBe(2)
  })

  it('returns the same file object (mutates in place)', () => {
    const file = { name: 'part.stl' }
    const result = applySmartDefaults(file)
    expect(result).toBe(file)
  })

  it('uses custom default material', () => {
    const file = { name: 'part.stl' }
    applySmartDefaults(file, 'PLA')
    expect(file.material).toBe('PLA')
  })
})

// ---------------------------------------------------------------------------

describe('filenameParser – applySmartDefaultsBatch', () => {
  it('applies smart defaults to all files in array', () => {
    const files = [
      { name: '[a]_part_x2.stl' },
      { name: 'base.stl' },
    ]
    const result = applySmartDefaultsBatch(files)
    expect(result[0].color).toBe('Accent')
    expect(result[0].quantity).toBe(2)
    expect(result[1].color).toBe('Primary')
    expect(result[1].quantity).toBe(1)
  })

  it('returns empty array for empty input', () => {
    expect(applySmartDefaultsBatch([])).toEqual([])
  })

  it('returns array of same length', () => {
    const files = [
      { name: 'a.stl' },
      { name: 'b.stl' },
      { name: 'c.stl' },
    ]
    expect(applySmartDefaultsBatch(files)).toHaveLength(3)
  })

  it('preserves existing properties on files', () => {
    const files = [{ name: 'part.stl', id: 42, isSelected: true }]
    const result = applySmartDefaultsBatch(files)
    expect(result[0].id).toBe(42)
    expect(result[0].isSelected).toBe(true)
  })

  it('uses custom default material for all files', () => {
    const files = [{ name: 'a.stl' }, { name: 'b.stl' }]
    const result = applySmartDefaultsBatch(files, 'PLA')
    result.forEach((f) => {
      expect(f.material).toBe('PLA')
    })
  })
})

// ---------------------------------------------------------------------------

describe('filenameParser – getSupportedQuantityPatterns', () => {
  it('returns an array', () => {
    expect(Array.isArray(getSupportedQuantityPatterns())).toBe(true)
  })

  it('returns at least one pattern', () => {
    expect(getSupportedQuantityPatterns().length).toBeGreaterThan(0)
  })

  it('each pattern entry has pattern and description properties', () => {
    getSupportedQuantityPatterns().forEach((p) => {
      expect(p).toHaveProperty('pattern')
      expect(p).toHaveProperty('description')
    })
  })
})

// ---------------------------------------------------------------------------

describe('filenameParser – getSupportedColorPatterns', () => {
  it('returns an array', () => {
    expect(Array.isArray(getSupportedColorPatterns())).toBe(true)
  })

  it('returns at least 3 patterns (a, d, b support)', () => {
    expect(getSupportedColorPatterns().length).toBeGreaterThanOrEqual(3)
  })

  it('each pattern entry has pattern, color, and description properties', () => {
    getSupportedColorPatterns().forEach((p) => {
      expect(p).toHaveProperty('pattern')
      expect(p).toHaveProperty('color')
      expect(p).toHaveProperty('description')
    })
  })

  it('includes Accent pattern', () => {
    const patterns = getSupportedColorPatterns()
    expect(patterns.some((p) => p.color === 'Accent')).toBe(true)
  })

  it('includes Multicolor pattern', () => {
    const patterns = getSupportedColorPatterns()
    expect(patterns.some((p) => p.color === 'Multicolor')).toBe(true)
  })
})
