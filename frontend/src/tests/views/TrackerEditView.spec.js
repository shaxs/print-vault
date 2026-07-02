/**
 * TrackerEditView.spec.js
 *
 * Tests for pure helper logic extracted from TrackerEditView.vue.
 *
 * Functions under test (extracted as standalone implementations):
 *   - formatMaterialLabel        build a human-readable label for a material
 *   - getPrimaryMaterialColor    resolve the display color for the primary material slot
 *   - getAccentMaterialColor     resolve the display color for the accent material slot
 *   - onPrimaryMaterialChange    side-effect: update primary_color from a material object
 *   - onAccentMaterialChange     side-effect: update accent_color from a material object
 *   - shouldShowDownloadButton   computed: whether to offer "download files" action
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure function implementations (mirrors TrackerEditView.vue logic)
// ---------------------------------------------------------------------------

/**
 * Build a human-readable label for a material blueprint.
 * Returns '' for falsy input.
 * Format: "[BrandName ]MaterialName[ (Xmm)]"
 */
const formatMaterialLabel = (mat) => {
  if (!mat) return ''
  const brandName = mat.brand?.name || ''
  const diameter = mat.diameter ? ` (${mat.diameter}mm)` : ''
  return `${brandName} ${mat.name}${diameter}`.trim()
}

/**
 * Resolve the CSS color for the primary material slot.
 * Returns '#cccccc' when no material is selected.
 * Prefers the first color in the looked-up material's colors array,
 * then falls back to the tracker's saved primary_color, then '#cccccc'.
 */
const getPrimaryMaterialColor = (selectedPrimaryMaterialId, materials, trackerPrimaryColor) => {
  if (!selectedPrimaryMaterialId) return '#cccccc'
  const material = materials.find((m) => m.id === selectedPrimaryMaterialId)
  return material?.colors?.[0] || trackerPrimaryColor || '#cccccc'
}

/**
 * Identical logic to getPrimaryMaterialColor but for the accent slot.
 */
const getAccentMaterialColor = (selectedAccentMaterialId, materials, trackerAccentColor) => {
  if (!selectedAccentMaterialId) return '#cccccc'
  const material = materials.find((m) => m.id === selectedAccentMaterialId)
  return material?.colors?.[0] || trackerAccentColor || '#cccccc'
}

/**
 * Apply the first color from a material selection to the tracker primary_color field.
 * Only updates when the material has at least one color.
 * Mutates the passed tracker object.
 */
const onPrimaryMaterialChange = (material, tracker) => {
  if (material && material.colors && material.colors.length > 0) {
    tracker.primary_color = material.colors[0]
  }
}

/**
 * Same as onPrimaryMaterialChange but updates accent_color.
 */
const onAccentMaterialChange = (material, tracker) => {
  if (material && material.colors && material.colors.length > 0) {
    tracker.accent_color = material.colors[0]
  }
}

/**
 * Determine whether the "Download all files" button should be shown.
 * Conditions (all must be true):
 *   1. trackerValue is not null
 *   2. originalStorageType was 'link'
 *   3. current storage_type is 'local'
 *   4. At least one file has github_url but no local_file
 */
const shouldShowDownloadButton = (trackerValue, originalStorageType) => {
  if (!trackerValue) return false
  const storageTypeChanged =
    originalStorageType === 'link' && trackerValue.storage_type === 'local'
  if (!storageTypeChanged) return false
  const hasFilesToDownload = trackerValue.files?.some(
    (file) => file.github_url && !file.local_file,
  )
  return hasFilesToDownload
}

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

const ALL_MATERIALS = [
  { id: 1, name: 'PLA+',    brand: { name: 'Polymaker' }, diameter: '1.75', colors: ['#FF5733'] },
  { id: 2, name: 'PETG',    brand: { name: 'Hatchbox'  }, diameter: '1.75', colors: ['#0066CC', '#003399'] },
  { id: 3, name: 'ABS',     brand: null,                  diameter: null,   colors: [] },
  { id: 4, name: 'Silk PLA',brand: { name: 'eSUN'      }, diameter: '1.75', colors: ['#C0C0C0'] },
]

const mkTracker = (overrides = {}) => ({
  storage_type: 'local',
  primary_color: '#AABBCC',
  accent_color: '#112233',
  files: [],
  ...overrides,
})

// ---------------------------------------------------------------------------

describe('TrackerEditView – formatMaterialLabel', () => {
  it('returns empty string for null input', () => {
    expect(formatMaterialLabel(null)).toBe('')
  })

  it('returns empty string for undefined input', () => {
    expect(formatMaterialLabel(undefined)).toBe('')
  })

  it('includes brand name and material name', () => {
    const mat = { name: 'PLA+', brand: { name: 'Polymaker' }, diameter: null }
    expect(formatMaterialLabel(mat)).toBe('Polymaker PLA+')
  })

  it('includes diameter when present', () => {
    const mat = { name: 'PETG', brand: { name: 'Hatchbox' }, diameter: '1.75' }
    expect(formatMaterialLabel(mat)).toBe('Hatchbox PETG (1.75mm)')
  })

  it('omits brand when brand is null', () => {
    const mat = { name: 'ABS', brand: null, diameter: '1.75' }
    expect(formatMaterialLabel(mat)).toBe('ABS (1.75mm)')
  })

  it('omits brand when brand has no name', () => {
    const mat = { name: 'ABS', brand: { name: '' }, diameter: null }
    expect(formatMaterialLabel(mat)).toBe('ABS')
  })

  it('omits diameter when null', () => {
    const mat = { name: 'TPU', brand: { name: 'NinjaFlex' }, diameter: null }
    expect(formatMaterialLabel(mat)).toBe('NinjaFlex TPU')
  })

  it('trims the result so there is no leading/trailing whitespace', () => {
    const mat = { name: 'PLA', brand: null, diameter: null }
    const label = formatMaterialLabel(mat)
    expect(label).toBe(label.trim())
  })

  it('handles material with no brand property at all (missing key)', () => {
    const mat = { name: 'FLEX', diameter: '3.00' }
    expect(formatMaterialLabel(mat)).toBe('FLEX (3.00mm)')
  })
})

// ---------------------------------------------------------------------------

describe('TrackerEditView – getPrimaryMaterialColor', () => {
  it('returns #cccccc when no material is selected (null)', () => {
    expect(getPrimaryMaterialColor(null, ALL_MATERIALS, '#112233')).toBe('#cccccc')
  })

  it('returns #cccccc when no material is selected (undefined)', () => {
    expect(getPrimaryMaterialColor(undefined, ALL_MATERIALS, '#112233')).toBe('#cccccc')
  })

  it('returns first color from matched material', () => {
    expect(getPrimaryMaterialColor(1, ALL_MATERIALS, '#000000')).toBe('#FF5733')
  })

  it('returns first color when material has multiple colors', () => {
    // Material id=2 has ['#0066CC', '#003399']
    expect(getPrimaryMaterialColor(2, ALL_MATERIALS, '#000000')).toBe('#0066CC')
  })

  it('falls back to trackerPrimaryColor when material has no colors', () => {
    // Material id=3 has colors: []
    expect(getPrimaryMaterialColor(3, ALL_MATERIALS, '#FALLBACK')).toBe('#FALLBACK')
  })

  it("falls back to #cccccc when material has no colors and tracker color is ''", () => {
    expect(getPrimaryMaterialColor(3, ALL_MATERIALS, '')).toBe('#cccccc')
  })

  it('falls back to trackerPrimaryColor when materialId is not found in list', () => {
    expect(getPrimaryMaterialColor(999, ALL_MATERIALS, '#SAVEDCOLOR')).toBe('#SAVEDCOLOR')
  })

  it('returns #cccccc when materialId not found and no tracker color', () => {
    expect(getPrimaryMaterialColor(999, ALL_MATERIALS, '')).toBe('#cccccc')
  })
})

// ---------------------------------------------------------------------------

describe('TrackerEditView – getAccentMaterialColor', () => {
  it('returns #cccccc when no accent material is selected', () => {
    expect(getAccentMaterialColor(null, ALL_MATERIALS, '#AABBCC')).toBe('#cccccc')
  })

  it('returns first color from matched accent material', () => {
    expect(getAccentMaterialColor(4, ALL_MATERIALS, '#AABBCC')).toBe('#C0C0C0')
  })

  it('falls back to trackerAccentColor for material without colors', () => {
    expect(getAccentMaterialColor(3, ALL_MATERIALS, '#STORED')).toBe('#STORED')
  })

  it('returns #cccccc when material not found and tracker accent color is empty', () => {
    expect(getAccentMaterialColor(999, ALL_MATERIALS, '')).toBe('#cccccc')
  })
})

// ---------------------------------------------------------------------------

describe('TrackerEditView – onPrimaryMaterialChange', () => {
  it('updates tracker.primary_color with the first color of the new material', () => {
    const tracker = mkTracker({ primary_color: '#OLD' })
    onPrimaryMaterialChange({ colors: ['#NEW_COLOR'] }, tracker)
    expect(tracker.primary_color).toBe('#NEW_COLOR')
  })

  it('does not update when material is null', () => {
    const tracker = mkTracker({ primary_color: '#UNCHANGED' })
    onPrimaryMaterialChange(null, tracker)
    expect(tracker.primary_color).toBe('#UNCHANGED')
  })

  it('does not update when material has empty colors array', () => {
    const tracker = mkTracker({ primary_color: '#UNCHANGED' })
    onPrimaryMaterialChange({ colors: [] }, tracker)
    expect(tracker.primary_color).toBe('#UNCHANGED')
  })

  it('does not update when material has no colors property', () => {
    const tracker = mkTracker({ primary_color: '#UNCHANGED' })
    onPrimaryMaterialChange({ name: 'PLA' }, tracker)
    expect(tracker.primary_color).toBe('#UNCHANGED')
  })

  it('uses only the first color even when material has multiple', () => {
    const tracker = mkTracker()
    onPrimaryMaterialChange({ colors: ['#FIRST', '#SECOND', '#THIRD'] }, tracker)
    expect(tracker.primary_color).toBe('#FIRST')
  })
})

// ---------------------------------------------------------------------------

describe('TrackerEditView – onAccentMaterialChange', () => {
  it('updates tracker.accent_color with the first color of the material', () => {
    const tracker = mkTracker({ accent_color: '#OLD' })
    onAccentMaterialChange({ colors: ['#ACCENT_NEW'] }, tracker)
    expect(tracker.accent_color).toBe('#ACCENT_NEW')
  })

  it('does not update when material is null', () => {
    const tracker = mkTracker({ accent_color: '#KEEP' })
    onAccentMaterialChange(null, tracker)
    expect(tracker.accent_color).toBe('#KEEP')
  })

  it('does not update when colors array is empty', () => {
    const tracker = mkTracker({ accent_color: '#KEEP' })
    onAccentMaterialChange({ colors: [] }, tracker)
    expect(tracker.accent_color).toBe('#KEEP')
  })
})

// ---------------------------------------------------------------------------

describe('TrackerEditView – shouldShowDownloadButton', () => {
  it('returns false when tracker is null', () => {
    expect(shouldShowDownloadButton(null, 'link')).toBe(false)
  })

  it('returns false when original storage was link but current is still link', () => {
    const tracker = mkTracker({ storage_type: 'link' })
    expect(shouldShowDownloadButton(tracker, 'link')).toBe(false)
  })

  it('returns false when original storage was local (no type change)', () => {
    const tracker = mkTracker({ storage_type: 'local' })
    expect(shouldShowDownloadButton(tracker, 'local')).toBe(false)
  })

  it('returns false when type changed link→local but no files need downloading', () => {
    const tracker = mkTracker({
      storage_type: 'local',
      files: [{ github_url: null, local_file: '/local/file.stl' }],
    })
    expect(shouldShowDownloadButton(tracker, 'link')).toBe(false)
  })

  it('returns true when type changed link→local and at least one file has github_url without local_file', () => {
    const tracker = mkTracker({
      storage_type: 'local',
      files: [{ github_url: 'https://raw.githubusercontent.com/x/y.stl', local_file: null }],
    })
    expect(shouldShowDownloadButton(tracker, 'link')).toBe(true)
  })

  it('returns false when all downloadable files already have local copies', () => {
    const tracker = mkTracker({
      storage_type: 'local',
      files: [
        { github_url: 'https://github.com/x/a.stl', local_file: '/media/a.stl' },
        { github_url: 'https://github.com/x/b.stl', local_file: '/media/b.stl' },
      ],
    })
    expect(shouldShowDownloadButton(tracker, 'link')).toBe(false)
  })

  it('returns true when at least one of many files needs downloading', () => {
    const tracker = mkTracker({
      storage_type: 'local',
      files: [
        { github_url: 'https://github.com/a.stl', local_file: '/media/a.stl' }, // done
        { github_url: 'https://github.com/b.stl', local_file: null },           // needs download
      ],
    })
    expect(shouldShowDownloadButton(tracker, 'link')).toBe(true)
  })

  it('handles tracker with no files array (undefined)', () => {
    const tracker = mkTracker({ storage_type: 'local', files: undefined })
    expect(shouldShowDownloadButton(tracker, 'link')).toBeFalsy()
  })

  it('returns false when storage_type is not "local" (e.g. manual)', () => {
    const tracker = mkTracker({
      storage_type: 'manual',
      files: [{ github_url: 'https://x.com/y.stl', local_file: null }],
    })
    expect(shouldShowDownloadButton(tracker, 'link')).toBe(false)
  })
})
