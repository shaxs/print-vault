/**
 * Tests for pure URL-validation logic extracted from ImportURLsModal.vue.
 *
 * Because the submit handler mutates component state the validation rules are
 * extracted here as dependency-free functions and tested in isolation.
 *
 * Functions covered:
 *   parseUrlLines(text)           — split textarea text into trimmed, non-empty lines
 *   validateUrls(urls)            — check pattern + supported extension
 *   findDuplicates(urls)          — detect repeated URLs
 *   findAlreadyAdded(urls, set)   — detect URLs already present in tracker
 */
import { describe, it, expect } from 'vitest'

// ─── Pure function implementations (mirrors ImportURLsModal.vue logic) ────────

const URL_PATTERN = /^https?:\/\/.+/i
const SUPPORTED_EXTENSIONS = ['.3mf', '.stl', '.oltp', '.stp', '.step', '.svg', '.amf', '.obj']

function parseUrlLines(text) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
}

/**
 * Returns { invalidLines, invalidExtensions }.
 * invalidLines: entries that don't match http(s) pattern.
 * invalidExtensions: valid-URL entries that lack a supported extension.
 */
function validateUrls(urls) {
  const invalidLines = []
  const invalidExtensions = []

  urls.forEach((line, index) => {
    if (!URL_PATTERN.test(line)) {
      invalidLines.push(`Line ${index + 1}: "${line}"`)
    } else {
      const urlLower = line.toLowerCase()
      const hasValidExtension = SUPPORTED_EXTENSIONS.some((ext) => urlLower.endsWith(ext))
      if (!hasValidExtension) {
        invalidExtensions.push(`Line ${index + 1}: "${line}"`)
      }
    }
  })

  return { invalidLines, invalidExtensions }
}

/**
 * Returns entries in urls that appear more than once (first occurrence is OK,
 * subsequent occurrences are flagged).
 */
function findDuplicates(urls) {
  const urlSet = new Set()
  const duplicateLines = []
  urls.forEach((url, index) => {
    if (urlSet.has(url)) {
      duplicateLines.push(`Line ${index + 1}: "${url}"`)
    }
    urlSet.add(url)
  })
  return duplicateLines
}

/**
 * Returns entries in urls that are already in existingUrls set.
 */
function findAlreadyAdded(urls, existingUrls) {
  const alreadyAdded = []
  urls.forEach((url, index) => {
    if (existingUrls.has(url)) {
      alreadyAdded.push(`Line ${index + 1}: "${url}"`)
    }
  })
  return alreadyAdded
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('ImportURLsModal – parseUrlLines', () => {
  it('splits text by newlines', () => {
    const result = parseUrlLines('http://a.com/f.stl\nhttp://b.com/g.obj')
    expect(result).toHaveLength(2)
  })

  it('trims whitespace from each line', () => {
    const result = parseUrlLines('  http://a.com/f.stl  ')
    expect(result[0]).toBe('http://a.com/f.stl')
  })

  it('filters out empty lines', () => {
    const result = parseUrlLines('http://a.com/f.stl\n\n\nhttp://b.com/g.obj')
    expect(result).toHaveLength(2)
  })

  it('filters out whitespace-only lines', () => {
    const result = parseUrlLines('http://a.com/f.stl\n   \nhttp://b.com/g.obj')
    expect(result).toHaveLength(2)
  })

  it('returns empty array for blank input', () => {
    expect(parseUrlLines('')).toHaveLength(0)
  })

  it('returns empty array for whitespace-only input', () => {
    expect(parseUrlLines('   \n  \n ')).toHaveLength(0)
  })
})

describe('ImportURLsModal – validateUrls (invalid format)', () => {
  it('flags a plain text line as invalidLine', () => {
    const { invalidLines } = validateUrls(['not-a-url'])
    expect(invalidLines).toHaveLength(1)
    expect(invalidLines[0]).toContain('Line 1')
  })

  it('flags ftp:// URL as invalidLine (only http/https are valid)', () => {
    const { invalidLines } = validateUrls(['ftp://example.com/file.stl'])
    expect(invalidLines).toHaveLength(1)
  })

  it('does not flag a valid https URL with supported extension', () => {
    const { invalidLines } = validateUrls(['https://example.com/model.stl'])
    expect(invalidLines).toHaveLength(0)
  })

  it('flags URL without supported extension as invalidExtension', () => {
    const { invalidExtensions } = validateUrls(['https://example.com/readme.txt'])
    expect(invalidExtensions).toHaveLength(1)
  })

  it('accepts all supported extensions (.3mf, .stl, .obj, etc.)', () => {
    const urls = SUPPORTED_EXTENSIONS.map((ext) => `https://example.com/file${ext}`)
    const { invalidLines, invalidExtensions } = validateUrls(urls)
    expect(invalidLines).toHaveLength(0)
    expect(invalidExtensions).toHaveLength(0)
  })

  it('extension check is case-insensitive', () => {
    const { invalidExtensions } = validateUrls(['HTTPS://EXAMPLE.COM/MODEL.STL'])
    expect(invalidExtensions).toHaveLength(0)
  })

  it('includes line number in error messages', () => {
    // Line 1 is a valid https URL; line 2 is not a URL at all
    const { invalidLines } = validateUrls(['https://example.com/model.stl', 'bad-line'])
    expect(invalidLines).toHaveLength(1)
    expect(invalidLines[0]).toContain('Line 2')
  })

  it('returns empty arrays for all-valid input', () => {
    const { invalidLines, invalidExtensions } = validateUrls([
      'https://cdn.example.com/part.stl',
      'http://files.site.com/model.3mf',
    ])
    expect(invalidLines).toHaveLength(0)
    expect(invalidExtensions).toHaveLength(0)
  })
})

describe('ImportURLsModal – findDuplicates', () => {
  it('returns empty array when no duplicates exist', () => {
    const result = findDuplicates(['http://a.com/f.stl', 'http://b.com/g.obj'])
    expect(result).toHaveLength(0)
  })

  it('flags the second occurrence of a repeated URL', () => {
    const url = 'http://a.com/f.stl'
    const result = findDuplicates([url, url])
    expect(result).toHaveLength(1)
    expect(result[0]).toContain('Line 2')
  })

  it('first occurrence is always kept, only subsequent are flagged', () => {
    const url = 'http://x.com/f.3mf'
    const result = findDuplicates([url, url, url])
    expect(result).toHaveLength(2)
  })

  it('includes the URL in the flag message', () => {
    const url = 'http://dup.com/dup.stl'
    const result = findDuplicates([url, url])
    expect(result[0]).toContain(url)
  })

  it('handles empty array gracefully', () => {
    expect(findDuplicates([])).toEqual([])
  })
})

describe('ImportURLsModal – findAlreadyAdded', () => {
  it('flags URLs that exist in the existing set', () => {
    const existing = new Set(['http://old.com/file.stl'])
    const result = findAlreadyAdded(['http://old.com/file.stl', 'http://new.com/file.obj'], existing)
    expect(result).toHaveLength(1)
    expect(result[0]).toContain('Line 1')
  })

  it('does not flag URLs not in existing set', () => {
    const existing = new Set(['http://old.com/file.stl'])
    const result = findAlreadyAdded(['http://brand-new.com/file.obj'], existing)
    expect(result).toHaveLength(0)
  })

  it('returns empty array when existing set is empty', () => {
    const result = findAlreadyAdded(['http://a.com/f.stl'], new Set())
    expect(result).toHaveLength(0)
  })

  it('includes the URL in the flag message', () => {
    const url = 'http://dupe.com/dupe.obj'
    const result = findAlreadyAdded([url], new Set([url]))
    expect(result[0]).toContain(url)
  })
})
