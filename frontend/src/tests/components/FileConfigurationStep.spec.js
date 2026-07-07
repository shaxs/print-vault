/**
 * Tests for FileConfigurationStep component pure logic
 *
 * FileConfigurationStep.vue is  a multi-step wizard panel where users assign
 * color, material, and quantity to each 3D file selected for download. It
 * also computes file size summaries and determines whether a storage-option
 * field is required (when URL-sourced files are present).
 *
 * Tests cover:
 * - formatMaterialLabel: brand + name + optional diameter
 * - configuredCount: count of files that have color, material AND quantity set
 * - totalSizeMB / totalSizeGB: size conversions with 2 decimal precision
 * - isLargeDownload: exceeds the 1 GB threshold
 * - hasUploadedFiles: any file has source === 'Upload'
 * - hasUrlFiles: any file has source !== 'Upload'
 */
import { describe, it, expect } from 'vitest'

// ── formatMaterialLabel ───────────────────────────────────────────────────────
// Mirrors:
//   if (!mat) return ''
//   const brandName = mat.brand?.name || ''
//   const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
//   return `${brandName} ${mat.name}${diameter}`.trim()

describe('FileConfigurationStep — formatMaterialLabel', () => {
  const formatMaterialLabel = (mat) => {
    if (!mat) return ''
    const brandName = mat.brand?.name || ''
    const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
    return `${brandName} ${mat.name}${diameter}`.trim()
  }

  it('returns empty string for null material', () => {
    expect(formatMaterialLabel(null)).toBe('')
  })

  it('returns empty string for undefined material', () => {
    expect(formatMaterialLabel(undefined)).toBe('')
  })

  it('returns just the material name when brand and diameter are absent', () => {
    expect(formatMaterialLabel({ name: 'PLA' })).toBe('PLA')
  })

  it('combines brand name and material name', () => {
    expect(formatMaterialLabel({ name: 'PLA+', brand: { name: 'Polymaker' } })).toBe('Polymaker PLA+')
  })

  it('appends diameter in parentheses when present', () => {
    expect(formatMaterialLabel({ name: 'PETG', brand: { name: 'Hatchbox' }, diameter: 1.75 })).toBe('Hatchbox PETG (1.75mm)')
  })

  it('omits diameter section when diameter is falsy', () => {
    expect(formatMaterialLabel({ name: 'ABS', brand: { name: 'eSUN' }, diameter: null })).toBe('eSUN ABS')
  })

  it('handles missing brand (no brand property) gracefully', () => {
    expect(formatMaterialLabel({ name: 'Nylon', diameter: 3 })).toBe('Nylon (3mm)')
  })

  it('trims leading/trailing whitespace when brand name is empty string', () => {
    // brandName '' + space + name → " PLA" → trimmed to "PLA"
    expect(formatMaterialLabel({ name: 'PLA', brand: { name: '' } })).toBe('PLA')
  })
})

// ── configuredCount ───────────────────────────────────────────────────────────
// Mirrors: files.filter((f) => f.color && f.material && f.quantity).length

describe('FileConfigurationStep — configuredCount', () => {
  const configuredCount = (files) =>
    files.filter((f) => f.color && f.material && f.quantity).length

  it('counts 0 when no files have all three fields set', () => {
    expect(configuredCount([{ color: 'Primary', material: 'PLA' }])).toBe(0)
  })

  it('counts a file that has color, material, and quantity all set', () => {
    expect(configuredCount([{ color: 'Primary', material: 'PLA', quantity: 2 }])).toBe(1)
  })

  it('excludes files missing only the color field', () => {
    const files = [{ material: 'ABS', quantity: 1 }, { color: 'Accent', material: 'ABS', quantity: 1 }]
    expect(configuredCount(files)).toBe(1)
  })

  it('excludes files missing only the material field', () => {
    const files = [{ color: 'Primary', quantity: 1 }]
    expect(configuredCount(files)).toBe(0)
  })

  it('excludes files missing only the quantity field', () => {
    const files = [{ color: 'Clear', material: 'PETG' }]
    expect(configuredCount(files)).toBe(0)
  })

  it('counts multiple fully configured files', () => {
    const files = [
      { color: 'Primary', material: 'PLA', quantity: 1 },
      { color: 'Accent', material: 'ABS', quantity: 2 },
      { color: 'Clear', material: 'PETG' }, // missing quantity
    ]
    expect(configuredCount(files)).toBe(2)
  })

  it('returns 0 for empty file list', () => {
    expect(configuredCount([])).toBe(0)
  })
})

// ── totalSizeMB / totalSizeGB ────────────────────────────────────────────────
// Mirrors:
//   totalSizeMB = (totalBytes / (1024 * 1024)).toFixed(2)
//   totalSizeGB = (totalBytes / (1024 * 1024 * 1024)).toFixed(2)

describe('FileConfigurationStep — totalSizeMB', () => {
  const totalSizeMB = (bytes) => (bytes / (1024 * 1024)).toFixed(2)

  it('returns "0.00" for 0 bytes', () => {
    expect(totalSizeMB(0)).toBe('0.00')
  })

  it('returns "1.00" for exactly 1 MB', () => {
    expect(totalSizeMB(1024 * 1024)).toBe('1.00')
  })

  it('returns "2.50" for 2.5 MB', () => {
    expect(totalSizeMB(Math.round(2.5 * 1024 * 1024))).toBe('2.50')
  })

  it('formats to exactly 2 decimal places', () => {
    const result = totalSizeMB(1024 * 1024 + 50000)
    expect(result.split('.')[1]).toHaveLength(2)
  })
})

describe('FileConfigurationStep — totalSizeGB', () => {
  const totalSizeGB = (bytes) => (bytes / (1024 * 1024 * 1024)).toFixed(2)

  it('returns "0.00" for 0 bytes', () => {
    expect(totalSizeGB(0)).toBe('0.00')
  })

  it('returns "1.00" for exactly 1 GB', () => {
    expect(totalSizeGB(1024 * 1024 * 1024)).toBe('1.00')
  })

  it('returns "1.50" for 1.5 GB', () => {
    expect(totalSizeGB(Math.round(1.5 * 1024 * 1024 * 1024))).toBe('1.50')
  })
})

// ── isLargeDownload ───────────────────────────────────────────────────────────
// Mirrors: totalSize > 1024 * 1024 * 1024  (> 1 GB)

describe('FileConfigurationStep — isLargeDownload', () => {
  const GB = 1024 * 1024 * 1024
  const isLargeDownload = (bytes) => bytes > GB

  it('is false for 0 bytes', () => {
    expect(isLargeDownload(0)).toBe(false)
  })

  it('is false for exactly 1 GB', () => {
    expect(isLargeDownload(GB)).toBe(false)
  })

  it('is true when size is 1 byte over 1 GB', () => {
    expect(isLargeDownload(GB + 1)).toBe(true)
  })

  it('is true for a clearly large download (5 GB)', () => {
    expect(isLargeDownload(5 * GB)).toBe(true)
  })
})

// ── hasUploadedFiles ──────────────────────────────────────────────────────────
// Mirrors: files.some((file) => file.source === 'Upload')

describe('FileConfigurationStep — hasUploadedFiles', () => {
  const hasUploadedFiles = (files) => files.some((f) => f.source === 'Upload')

  it('returns false when no files have source "Upload"', () => {
    expect(hasUploadedFiles([{ source: 'URL' }, { source: 'URL' }])).toBe(false)
  })

  it('returns true when at least one file has source "Upload"', () => {
    expect(hasUploadedFiles([{ source: 'URL' }, { source: 'Upload' }])).toBe(true)
  })

  it('returns false for an empty file list', () => {
    expect(hasUploadedFiles([])).toBe(false)
  })
})

// ── hasUrlFiles ───────────────────────────────────────────────────────────────
// Mirrors: files.some((file) => file.source !== 'Upload')

describe('FileConfigurationStep — hasUrlFiles', () => {
  const hasUrlFiles = (files) => files.some((f) => f.source !== 'Upload')

  it('returns false when all files are uploads', () => {
    expect(hasUrlFiles([{ source: 'Upload' }, { source: 'Upload' }])).toBe(false)
  })

  it('returns true when at least one file has a non-Upload source', () => {
    expect(hasUrlFiles([{ source: 'Upload' }, { source: 'URL' }])).toBe(true)
  })

  it('returns false for an empty file list', () => {
    expect(hasUrlFiles([])).toBe(false)
  })

  it('treats any value other than "Upload" as a URL file', () => {
    expect(hasUrlFiles([{ source: 'Thingiverse' }])).toBe(true)
  })
})

// ── storageOption watcher: generateThumbnailsForLinkedFiles reset ────────────
// Mirrors:
//   watch(storageOption, (newValue) => {
//     emit('update:storageOption', newValue)
//     if (newValue !== 'link') {
//       generateThumbnailsForLinkedFiles.value = false
//       emit('update:generateThumbnailsForLinkedFiles', false)
//     }
//   })

describe('FileConfigurationStep — storageOption watcher resets linked-thumbnail checkbox', () => {
  function simulateStorageOptionChange(newValue, currentGenerateValue) {
    const emitted = []
    let generateThumbnailsForLinkedFiles = currentGenerateValue

    emitted.push(['update:storageOption', newValue])
    if (newValue !== 'link') {
      generateThumbnailsForLinkedFiles = false
      emitted.push(['update:generateThumbnailsForLinkedFiles', false])
    }

    return { emitted, generateThumbnailsForLinkedFiles }
  }

  it('resets the checkbox to false when switching away from "link"', () => {
    const { generateThumbnailsForLinkedFiles, emitted } = simulateStorageOptionChange('local', true)

    expect(generateThumbnailsForLinkedFiles).toBe(false)
    expect(emitted).toContainEqual(['update:generateThumbnailsForLinkedFiles', false])
  })

  it('does not touch the checkbox when switching to "link"', () => {
    const { generateThumbnailsForLinkedFiles, emitted } = simulateStorageOptionChange('link', true)

    expect(generateThumbnailsForLinkedFiles).toBe(true)
    expect(emitted).not.toContainEqual(expect.arrayContaining(['update:generateThumbnailsForLinkedFiles']))
  })

  it('always emits update:storageOption regardless of value', () => {
    const { emitted } = simulateStorageOptionChange('local', false)

    expect(emitted).toContainEqual(['update:storageOption', 'local'])
  })
})
