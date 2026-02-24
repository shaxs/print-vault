/**
 * TrackerAddFilesView.spec.js
 *
 * Tests for pure utility logic extracted from TrackerAddFilesView.vue.
 * Covers: existingCategories derivation, hasUnconfiguredFiles detection,
 * addFiles extension filtering, and URL validation logic.
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure functions (mirrors TrackerAddFilesView.vue implementations)
// ---------------------------------------------------------------------------

/**
 * Pure version of existingCategories computed.
 * Returns unique, sorted directory_path values from tracker files.
 */
const extractExistingCategories = (trackerFiles) => {
  if (!trackerFiles) return []
  const categories = new Set()
  trackerFiles.forEach((file) => {
    if (file.directory_path) categories.add(file.directory_path)
  })
  return Array.from(categories).sort()
}

/**
 * Pure version of hasUnconfiguredFiles computed.
 * A file is unconfigured if it lacks color, material, quantity, or quantity === 1.
 */
const hasUnconfiguredFiles = (files) =>
  files.some((file) => !file.color || !file.material || !file.quantity || file.quantity === 1)

/**
 * Pure version of the addFiles extension-filtering logic.
 * Returns only files whose extension is in the valid list.
 */
const VALID_EXTENSIONS = ['.stl', '.3mf', '.obj', '.gcode', '.step', '.stp']

const filterValidFiles = (files) =>
  files.filter((file) => {
    const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    return VALID_EXTENSIONS.includes(ext)
  })

/**
 * Pure URL validation matching previewURLs logic.
 * Returns { invalidLines, invalidExtensions }.
 */
const SUPPORTED_URL_EXTENSIONS = ['.3mf', '.stl', '.stp', '.step', '.obj', '.gcode']
const URL_PATTERN = /^https?:\/\/.+/i

const validateURLLines = (urls) => {
  const invalidLines = []
  const invalidExtensions = []

  urls.forEach((line, index) => {
    if (!URL_PATTERN.test(line)) {
      invalidLines.push(`Line ${index + 1}: "${line}"`)
    } else {
      const urlLower = line.toLowerCase()
      const hasValidExtension = SUPPORTED_URL_EXTENSIONS.some((ext) => urlLower.endsWith(ext))
      if (!hasValidExtension) {
        invalidExtensions.push(
          `Line ${index + 1}: "${line}" (must end with ${SUPPORTED_URL_EXTENSIONS.join(', ')})`,
        )
      }
    }
  })

  return { invalidLines, invalidExtensions }
}

// ---------------------------------------------------------------------------

describe('TrackerAddFilesView – extractExistingCategories', () => {
  it('returns empty array when no files', () => {
    expect(extractExistingCategories([])).toEqual([])
  })

  it('returns empty array for null input', () => {
    expect(extractExistingCategories(null)).toEqual([])
  })

  it('extracts unique category names from files', () => {
    const files = [
      { directory_path: 'Gantry' },
      { directory_path: 'Frame' },
      { directory_path: 'Gantry' }, // duplicate
    ]
    expect(extractExistingCategories(files)).toEqual(['Frame', 'Gantry'])
  })

  it('sorts categories alphabetically', () => {
    const files = [
      { directory_path: 'Zframe' },
      { directory_path: 'Axle' },
      { directory_path: 'Motor' },
    ]
    expect(extractExistingCategories(files)).toEqual(['Axle', 'Motor', 'Zframe'])
  })

  it('ignores files with null directory_path', () => {
    const files = [
      { directory_path: null },
      { directory_path: 'Skirts' },
      { directory_path: null },
    ]
    expect(extractExistingCategories(files)).toEqual(['Skirts'])
  })

  it('ignores files with empty string directory_path', () => {
    const files = [{ directory_path: '' }, { directory_path: 'Panels' }]
    expect(extractExistingCategories(files)).toEqual(['Panels'])
  })

  it('returns single category for homogeneous files', () => {
    const files = [
      { directory_path: 'Frame' },
      { directory_path: 'Frame' },
      { directory_path: 'Frame' },
    ]
    expect(extractExistingCategories(files)).toEqual(['Frame'])
  })

  it('handles files without directory_path property', () => {
    const files = [{ name: 'piece.stl' }, { directory_path: 'Toolhead' }]
    expect(extractExistingCategories(files)).toEqual(['Toolhead'])
  })
})

// ---------------------------------------------------------------------------

describe('TrackerAddFilesView – hasUnconfiguredFiles', () => {
  it('returns false for fully configured files', () => {
    const files = [
      { color: 'Primary', material: 'PLA', quantity: 2 },
      { color: 'Accent', material: 'PETG', quantity: 4 },
    ]
    expect(hasUnconfiguredFiles(files)).toBe(false)
  })

  it('returns true when color is empty', () => {
    const files = [{ color: '', material: 'PLA', quantity: 2 }]
    expect(hasUnconfiguredFiles(files)).toBe(true)
  })

  it('returns true when material is empty', () => {
    const files = [{ color: 'Primary', material: '', quantity: 2 }]
    expect(hasUnconfiguredFiles(files)).toBe(true)
  })

  it('returns true when quantity is 0 (falsy)', () => {
    const files = [{ color: 'Primary', material: 'PLA', quantity: 0 }]
    expect(hasUnconfiguredFiles(files)).toBe(true)
  })

  it('returns true when quantity equals 1 (default)', () => {
    const files = [{ color: 'Primary', material: 'PLA', quantity: 1 }]
    expect(hasUnconfiguredFiles(files)).toBe(true)
  })

  it('returns false when quantity is 2+', () => {
    const files = [{ color: 'Accent', material: 'ABS', quantity: 3 }]
    expect(hasUnconfiguredFiles(files)).toBe(false)
  })

  it('returns true when any one file in list is unconfigured', () => {
    const files = [
      { color: 'Primary', material: 'PLA', quantity: 2 },
      { color: '', material: 'PLA', quantity: 2 }, // unconfigured
    ]
    expect(hasUnconfiguredFiles(files)).toBe(true)
  })

  it('returns false for empty files array', () => {
    expect(hasUnconfiguredFiles([])).toBe(false)
  })

  it('returns true when color is null', () => {
    const files = [{ color: null, material: 'PLA', quantity: 2 }]
    expect(hasUnconfiguredFiles(files)).toBe(true)
  })
})

// ---------------------------------------------------------------------------

describe('TrackerAddFilesView – filterValidFiles (extension filtering)', () => {
  it('allows .stl files', () => {
    const files = [{ name: 'bracket.stl' }]
    expect(filterValidFiles(files)).toHaveLength(1)
  })

  it('allows .3mf files', () => {
    const files = [{ name: 'plate.3mf' }]
    expect(filterValidFiles(files)).toHaveLength(1)
  })

  it('allows .obj files', () => {
    const files = [{ name: 'model.obj' }]
    expect(filterValidFiles(files)).toHaveLength(1)
  })

  it('allows .gcode files', () => {
    const files = [{ name: 'print.gcode' }]
    expect(filterValidFiles(files)).toHaveLength(1)
  })

  it('allows .step files', () => {
    const files = [{ name: 'assembly.step' }]
    expect(filterValidFiles(files)).toHaveLength(1)
  })

  it('allows .stp files', () => {
    const files = [{ name: 'part.stp' }]
    expect(filterValidFiles(files)).toHaveLength(1)
  })

  it('rejects .pdf files', () => {
    const files = [{ name: 'manual.pdf' }]
    expect(filterValidFiles(files)).toHaveLength(0)
  })

  it('rejects .jpg files', () => {
    const files = [{ name: 'photo.jpg' }]
    expect(filterValidFiles(files)).toHaveLength(0)
  })

  it('rejects .zip files', () => {
    const files = [{ name: 'archive.zip' }]
    expect(filterValidFiles(files)).toHaveLength(0)
  })

  it('is case-insensitive (capitalised .STL)', () => {
    const files = [{ name: 'BRACKET.STL' }]
    expect(filterValidFiles(files)).toHaveLength(1)
  })

  it('is case-insensitive (mixed case .Stl)', () => {
    const files = [{ name: 'Part.Stl' }]
    expect(filterValidFiles(files)).toHaveLength(1)
  })

  it('filters mixed valid/invalid files', () => {
    const files = [
      { name: 'good.stl' },
      { name: 'bad.txt' },
      { name: 'also_good.3mf' },
      { name: 'unwanted.csv' },
    ]
    const result = filterValidFiles(files)
    expect(result).toHaveLength(2)
    expect(result.map((f) => f.name)).toEqual(['good.stl', 'also_good.3mf'])
  })

  it('returns empty array when all files are invalid', () => {
    const files = [{ name: 'notes.txt' }, { name: 'image.png' }]
    expect(filterValidFiles(files)).toHaveLength(0)
  })

  it('returns empty array for empty input', () => {
    expect(filterValidFiles([])).toHaveLength(0)
  })
})

// ---------------------------------------------------------------------------

describe('TrackerAddFilesView – validateURLLines', () => {
  it('accepts a valid .stl URL', () => {
    const result = validateURLLines(['https://example.com/part.stl'])
    expect(result.invalidLines).toHaveLength(0)
    expect(result.invalidExtensions).toHaveLength(0)
  })

  it('accepts a valid .3mf URL', () => {
    const result = validateURLLines(['https://cdn.example.com/plate.3mf'])
    expect(result.invalidLines).toHaveLength(0)
    expect(result.invalidExtensions).toHaveLength(0)
  })

  it('accepts all supported extension URLs', () => {
    const urls = [
      'https://a.com/f.3mf',
      'https://a.com/f.stl',
      'https://a.com/f.stp',
      'https://a.com/f.step',
      'https://a.com/f.obj',
      'https://a.com/f.gcode',
    ]
    const result = validateURLLines(urls)
    expect(result.invalidLines).toHaveLength(0)
    expect(result.invalidExtensions).toHaveLength(0)
  })

  it('rejects a non-http line', () => {
    const result = validateURLLines(['ftp://example.com/part.stl'])
    expect(result.invalidLines).toHaveLength(1)
    expect(result.invalidLines[0]).toContain('Line 1')
  })

  it('rejects a plain text line that is not a URL', () => {
    const result = validateURLLines(['not-a-url'])
    expect(result.invalidLines).toHaveLength(1)
  })

  it('rejects a URL with unsupported extension', () => {
    const result = validateURLLines(['https://example.com/manual.pdf'])
    expect(result.invalidLines).toHaveLength(0)
    expect(result.invalidExtensions).toHaveLength(1)
    expect(result.invalidExtensions[0]).toContain('Line 1')
  })

  it('is case-insensitive for URL extension check', () => {
    const result = validateURLLines(['https://example.com/part.STL'])
    expect(result.invalidLines).toHaveLength(0)
    expect(result.invalidExtensions).toHaveLength(0)
  })

  it('tracks correct line numbers for errors', () => {
    const urls = [
      'https://example.com/good.stl',
      'not-a-url',
      'https://example.com/also-good.3mf',
    ]
    const result = validateURLLines(urls)
    expect(result.invalidLines).toHaveLength(1)
    expect(result.invalidLines[0]).toContain('Line 2')
  })

  it('returns both lists empty for valid input', () => {
    const result = validateURLLines(['https://github.com/model.stl'])
    expect(result.invalidLines).toEqual([])
    expect(result.invalidExtensions).toEqual([])
  })

  it('handles empty input array', () => {
    const result = validateURLLines([])
    expect(result.invalidLines).toEqual([])
    expect(result.invalidExtensions).toEqual([])
  })

  it('collects multiple invalid lines', () => {
    const urls = ['bad-1', 'bad-2', 'https://ok.com/f.stl']
    const result = validateURLLines(urls)
    expect(result.invalidLines).toHaveLength(2)
  })

  it('accepts http:// (not just https://)', () => {
    const result = validateURLLines(['http://example.com/bracket.stl'])
    expect(result.invalidLines).toHaveLength(0)
    expect(result.invalidExtensions).toHaveLength(0)
  })
})
