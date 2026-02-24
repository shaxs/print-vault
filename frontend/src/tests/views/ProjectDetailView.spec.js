/**
 * ProjectDetailView.spec.js
 *
 * Tests for the pure utility functions and computed values in ProjectDetailView.vue.
 * Focuses on: getFileName, getProgressColor, getTrackerProgressStyle,
 * formatMaterialName, getSpoolDisplayName, getBOMStatusLabel, getBOMStatusClass,
 * and bomItemsWithIndex logic.
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure functions (mirrors ProjectDetailView.vue implementations)
// ---------------------------------------------------------------------------

const getFileName = (filePath) => {
  if (!filePath) return ''
  return filePath.split('/').pop()
}

const getProgressColor = (percentage) => {
  if (percentage === 0) return '#64748b'
  if (percentage < 50) return '#ef4444'
  if (percentage < 100) return '#f59e0b'
  return '#10b981'
}

const getTrackerProgressStyle = (tracker) => {
  const percentage = tracker?.progress_percentage || 0
  return {
    width: `${percentage}%`,
    height: '100%',
    backgroundColor: getProgressColor(percentage),
    transition: 'width 0.3s ease',
  }
}

const formatMaterialName = (material) => {
  if (!material) return ''
  const brandName = material.brand?.name || ''
  const diameter = material.diameter ? ` (${material.diameter}mm)` : ''
  return `${brandName} ${material.name}${diameter}`.trim()
}

const getSpoolDisplayName = (spool) => {
  if (spool.filament_type) {
    return formatMaterialName(spool.filament_type)
  }
  if (spool.standalone_name) {
    const brand = spool.standalone_brand?.name || ''
    return brand ? `${brand} ${spool.standalone_name}` : spool.standalone_name
  }
  return `Spool #${spool.id}`
}

const BOM_STATUS_LABELS = {
  covered: 'Covered',
  low: 'Running Low',
  overallocated: 'Overallocated',
  needs_purchase: 'Purchase',
  unlinked: 'Not Linked',
}

const BOM_STATUS_CLASSES = {
  covered: 'bom-status-covered',
  low: 'bom-status-low',
  overallocated: 'bom-status-overallocated',
  needs_purchase: 'bom-status-purchase',
  unlinked: 'bom-status-unlinked',
}

const getBOMStatusLabel = (status) => BOM_STATUS_LABELS[status] ?? status
const getBOMStatusClass = (status) => BOM_STATUS_CLASSES[status] ?? ''

// bomItemsWithIndex logic (mirrors the computed in the component)
const bomItemsWithIndex = (bomItems) =>
  (bomItems ?? []).map((item, i) => ({ ...item, _rowNum: i + 1 }))

// ---------------------------------------------------------------------------

describe('ProjectDetailView – getFileName', () => {
  it('extracts filename from a Unix path', () => {
    expect(getFileName('project_files/blueprints/chassis.stl')).toBe('chassis.stl')
  })

  it('returns single-segment path unchanged', () => {
    expect(getFileName('readme.txt')).toBe('readme.txt')
  })

  it('returns empty string for null', () => {
    expect(getFileName(null)).toBe('')
  })

  it('returns empty string for empty string', () => {
    expect(getFileName('')).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(getFileName(undefined)).toBe('')
  })

  it('returns empty string for a trailing-slash path', () => {
    expect(getFileName('some/folder/')).toBe('')
  })

  it('handles deeply nested path', () => {
    expect(getFileName('a/b/c/d/final.gcode')).toBe('final.gcode')
  })
})

// ---------------------------------------------------------------------------

describe('ProjectDetailView – getProgressColor (hex colours)', () => {
  it('returns slate/gray for 0%', () => {
    expect(getProgressColor(0)).toBe('#64748b')
  })

  it('returns red for 1%', () => {
    expect(getProgressColor(1)).toBe('#ef4444')
  })

  it('returns red for 49%', () => {
    expect(getProgressColor(49)).toBe('#ef4444')
  })

  it('returns orange for exactly 50%', () => {
    expect(getProgressColor(50)).toBe('#f59e0b')
  })

  it('returns orange for 99%', () => {
    expect(getProgressColor(99)).toBe('#f59e0b')
  })

  it('returns green for exactly 100%', () => {
    expect(getProgressColor(100)).toBe('#10b981')
  })

  it('returns green for values above 100', () => {
    // Should hit the final return (>= 100)
    expect(getProgressColor(110)).toBe('#10b981')
  })
})

// ---------------------------------------------------------------------------

describe('ProjectDetailView – getTrackerProgressStyle', () => {
  it('builds full style object for a tracker at 0%', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 0 })
    expect(style).toEqual({
      width: '0%',
      height: '100%',
      backgroundColor: '#64748b',
      transition: 'width 0.3s ease',
    })
  })

  it('builds correct style for 75%', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 75 })
    expect(style.width).toBe('75%')
    expect(style.backgroundColor).toBe('#f59e0b')
    expect(style.height).toBe('100%')
  })

  it('builds correct style for 100%', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 100 })
    expect(style.width).toBe('100%')
    expect(style.backgroundColor).toBe('#10b981')
  })

  it('defaults to 0% when progress_percentage is missing', () => {
    const style = getTrackerProgressStyle({})
    expect(style.width).toBe('0%')
    expect(style.backgroundColor).toBe('#64748b')
  })

  it('defaults to 0% for null tracker', () => {
    const style = getTrackerProgressStyle(null)
    expect(style.width).toBe('0%')
  })

  it('includes transition property', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 50 })
    expect(style.transition).toBe('width 0.3s ease')
  })
})

// ---------------------------------------------------------------------------

describe('ProjectDetailView – formatMaterialName', () => {
  it('returns empty string for null material', () => {
    expect(formatMaterialName(null)).toBe('')
  })

  it('returns empty string for undefined material', () => {
    expect(formatMaterialName(undefined)).toBe('')
  })

  it('formats name only (no brand, no diameter)', () => {
    expect(formatMaterialName({ name: 'PLA', brand: null, diameter: null })).toBe('PLA')
  })

  it('formats brand + name', () => {
    expect(formatMaterialName({ name: 'PETG', brand: { name: 'Hatchbox' }, diameter: null })).toBe(
      'Hatchbox PETG'
    )
  })

  it('formats name + diameter', () => {
    expect(formatMaterialName({ name: 'ABS', brand: null, diameter: '1.75' })).toBe(
      'ABS (1.75mm)'
    )
  })

  it('formats brand + name + diameter', () => {
    expect(
      formatMaterialName({ name: 'TPU', brand: { name: 'Polymaker' }, diameter: '1.75' })
    ).toBe('Polymaker TPU (1.75mm)')
  })
})

// ---------------------------------------------------------------------------

describe('ProjectDetailView – getSpoolDisplayName', () => {
  it('uses filament_type when present', () => {
    const spool = {
      id: 1,
      filament_type: { name: 'PLA+', brand: { name: 'eSun' }, diameter: '1.75' },
    }
    expect(getSpoolDisplayName(spool)).toBe('eSun PLA+ (1.75mm)')
  })

  it('uses standalone_name with brand when filament_type is absent', () => {
    const spool = {
      id: 2,
      filament_type: null,
      standalone_name: 'PLA',
      standalone_brand: { name: 'Prusament' },
    }
    expect(getSpoolDisplayName(spool)).toBe('Prusament PLA')
  })

  it('uses standalone_name without brand', () => {
    const spool = {
      id: 3,
      filament_type: null,
      standalone_name: 'Mystery PLA',
      standalone_brand: null,
    }
    expect(getSpoolDisplayName(spool)).toBe('Mystery PLA')
  })

  it('falls back to Spool #ID when nothing is set', () => {
    const spool = { id: 42, filament_type: null, standalone_name: null }
    expect(getSpoolDisplayName(spool)).toBe('Spool #42')
  })

  it('filament_type takes priority over standalone_name', () => {
    const spool = {
      id: 5,
      filament_type: { name: 'PETG', brand: null, diameter: null },
      standalone_name: 'Other',
      standalone_brand: { name: 'SomeBrand' },
    }
    expect(getSpoolDisplayName(spool)).toBe('PETG')
  })
})

// ---------------------------------------------------------------------------

describe('ProjectDetailView – getBOMStatusLabel', () => {
  it('returns "Covered" for covered', () => {
    expect(getBOMStatusLabel('covered')).toBe('Covered')
  })

  it('returns "Running Low" for low', () => {
    expect(getBOMStatusLabel('low')).toBe('Running Low')
  })

  it('returns "Overallocated" for overallocated', () => {
    expect(getBOMStatusLabel('overallocated')).toBe('Overallocated')
  })

  it('returns "Purchase" for needs_purchase', () => {
    expect(getBOMStatusLabel('needs_purchase')).toBe('Purchase')
  })

  it('returns "Not Linked" for unlinked', () => {
    expect(getBOMStatusLabel('unlinked')).toBe('Not Linked')
  })

  it('returns the raw status string for unknown values (fallback)', () => {
    expect(getBOMStatusLabel('unknown_status')).toBe('unknown_status')
  })

  it('returns undefined for undefined (nullish fallback)', () => {
    // BOM_STATUS_LABELS[undefined] is undefined, ?? undefined → undefined
    expect(getBOMStatusLabel(undefined)).toBe(undefined)
  })
})

// ---------------------------------------------------------------------------

describe('ProjectDetailView – getBOMStatusClass', () => {
  it('returns correct class for covered', () => {
    expect(getBOMStatusClass('covered')).toBe('bom-status-covered')
  })

  it('returns correct class for low', () => {
    expect(getBOMStatusClass('low')).toBe('bom-status-low')
  })

  it('returns correct class for overallocated', () => {
    expect(getBOMStatusClass('overallocated')).toBe('bom-status-overallocated')
  })

  it('returns correct class for needs_purchase', () => {
    expect(getBOMStatusClass('needs_purchase')).toBe('bom-status-purchase')
  })

  it('returns correct class for unlinked', () => {
    expect(getBOMStatusClass('unlinked')).toBe('bom-status-unlinked')
  })

  it('returns empty string for unknown status', () => {
    expect(getBOMStatusClass('foobar')).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(getBOMStatusClass(undefined)).toBe('')
  })
})

// ---------------------------------------------------------------------------

describe('ProjectDetailView – bomItemsWithIndex', () => {
  it('returns empty array for empty input', () => {
    expect(bomItemsWithIndex([])).toEqual([])
  })

  it('returns empty array for null input', () => {
    expect(bomItemsWithIndex(null)).toEqual([])
  })

  it('returns empty array for undefined input', () => {
    expect(bomItemsWithIndex(undefined)).toEqual([])
  })

  it('adds _rowNum starting at 1', () => {
    const items = [{ description: 'Motor' }, { description: 'Frame' }]
    const result = bomItemsWithIndex(items)
    expect(result[0]._rowNum).toBe(1)
    expect(result[1]._rowNum).toBe(2)
  })

  it('preserves existing fields', () => {
    const items = [{ id: 10, description: 'Bolt', quantity_needed: 4 }]
    const result = bomItemsWithIndex(items)
    expect(result[0].id).toBe(10)
    expect(result[0].description).toBe('Bolt')
    expect(result[0].quantity_needed).toBe(4)
    expect(result[0]._rowNum).toBe(1)
  })

  it('handles a single item', () => {
    const result = bomItemsWithIndex([{ description: 'Washer' }])
    expect(result).toHaveLength(1)
    expect(result[0]._rowNum).toBe(1)
  })

  it('handles many items with sequential row numbers', () => {
    const items = Array.from({ length: 5 }, (_, i) => ({ id: i + 1 }))
    const result = bomItemsWithIndex(items)
    result.forEach((item, idx) => {
      expect(item._rowNum).toBe(idx + 1)
    })
  })

  it('does not mutate the original items', () => {
    const items = [{ description: 'Nut' }]
    const result = bomItemsWithIndex(items)
    expect(items[0]._rowNum).toBeUndefined()
    expect(result[0]._rowNum).toBe(1)
  })
})
