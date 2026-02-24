/**
 * CreateTrackerWizard.spec.js
 *
 * Tests for pure utility logic extracted from CreateTrackerWizard.vue.
 * Covers: totalSteps, getColorBadgeStyle, hasManualUrlFiles,
 * isStorageOptionRequired, isManualConfigurationComplete,
 * areAllFilesSelected, countSelectedFiles, getUniqueCategories,
 * getFilesByCategory, and groupFilesFromTree.
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure functions (mirrors CreateTrackerWizard.vue implementations)
// ---------------------------------------------------------------------------

const totalSteps = (creationMode) => {
  if (creationMode === 'github') return 4
  if (creationMode === 'manual') return 5
  return 1
}

const getColorBadgeStyle = (color) => {
  const primary = '#4a90e2'
  const accent = '#f5a623'
  switch (color?.toLowerCase()) {
    case 'primary':
      return { backgroundColor: primary }
    case 'accent':
      return { backgroundColor: accent }
    case 'multicolor':
      return { backgroundImage: `linear-gradient(to right, ${primary}, ${accent})` }
    case 'clear':
      return { backgroundColor: '#e2e8f0', color: '#4a5568', border: '1px solid #cbd5e0' }
    case 'other':
      return { backgroundColor: '#78716c' }
    default:
      return { backgroundColor: '#94a3b8' }
  }
}

const hasManualUrlFiles = (manualFiles) =>
  manualFiles.some((file) => file.source !== 'Upload')

const isStorageOptionRequired = (creationMode, manualFiles) => {
  if (creationMode === 'manual') return hasManualUrlFiles(manualFiles)
  return creationMode === 'github'
}

const isManualConfigurationComplete = (manualFiles) => {
  if (manualFiles.length === 0) return false
  return manualFiles.every((file) => file.quantity && file.color && file.material)
}

const areAllFilesSelected = (files) => files.every((f) => f.isSelected)

const countSelectedFiles = (tree) => {
  let count = 0
  const traverse = (nodes) => {
    nodes.forEach((node) => {
      if (node.children) traverse(node.children)
      else if (node.isSelected) count++
    })
  }
  traverse(tree)
  return count
}

const getUniqueCategories = (manualFiles) => {
  const categories = new Set()
  manualFiles.forEach((file) => {
    categories.add(file.category || '')
  })
  return Array.from(categories).sort()
}

const getFilesByCategory = (manualFiles, category) =>
  manualFiles.filter((file) => (file.category || '') === category)

/**
 * Pure version of the groupedFiles computed.
 * Traverses tree nodes and groups leaf nodes by their directory path.
 */
const groupFilesFromTree = (fileTree) => {
  const groups = {}
  const traverse = (nodes, path = []) => {
    nodes.forEach((node) => {
      if (node.children) {
        traverse(node.children, [...path, node.name])
      } else {
        const dirPath = path.join(' / ') || 'Root'
        if (!groups[dirPath]) groups[dirPath] = []
        groups[dirPath].push(node)
      }
    })
  }
  traverse(fileTree)
  return groups
}

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – totalSteps', () => {
  it('returns 4 for github mode', () => {
    expect(totalSteps('github')).toBe(4)
  })

  it('returns 5 for manual mode', () => {
    expect(totalSteps('manual')).toBe(5)
  })

  it('returns 1 for null (choice screen)', () => {
    expect(totalSteps(null)).toBe(1)
  })

  it('returns 1 for undefined', () => {
    expect(totalSteps(undefined)).toBe(1)
  })

  it('returns 1 for unknown mode string', () => {
    expect(totalSteps('unknown')).toBe(1)
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – getColorBadgeStyle', () => {
  it('returns primary background for "Primary"', () => {
    expect(getColorBadgeStyle('Primary')).toEqual({ backgroundColor: '#4a90e2' })
  })

  it('is case-insensitive for primary', () => {
    expect(getColorBadgeStyle('primary')).toEqual({ backgroundColor: '#4a90e2' })
  })

  it('returns accent background for "Accent"', () => {
    expect(getColorBadgeStyle('Accent')).toEqual({ backgroundColor: '#f5a623' })
  })

  it('returns gradient for "Multicolor"', () => {
    const style = getColorBadgeStyle('Multicolor')
    expect(style.backgroundImage).toContain('linear-gradient')
    expect(style.backgroundImage).toContain('#4a90e2')
    expect(style.backgroundImage).toContain('#f5a623')
  })

  it('returns clear style with border for "Clear"', () => {
    const style = getColorBadgeStyle('Clear')
    expect(style.backgroundColor).toBe('#e2e8f0')
    expect(style.color).toBe('#4a5568')
    expect(style.border).toBe('1px solid #cbd5e0')
  })

  it('returns brown/muted background for "Other"', () => {
    expect(getColorBadgeStyle('Other')).toEqual({ backgroundColor: '#78716c' })
  })

  it('returns default slate background for unknown color', () => {
    expect(getColorBadgeStyle('Exotic')).toEqual({ backgroundColor: '#94a3b8' })
  })

  it('returns default background for null color', () => {
    expect(getColorBadgeStyle(null)).toEqual({ backgroundColor: '#94a3b8' })
  })

  it('returns default background for undefined color', () => {
    expect(getColorBadgeStyle(undefined)).toEqual({ backgroundColor: '#94a3b8' })
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – hasManualUrlFiles', () => {
  it('returns true when a file has source other than "Upload"', () => {
    const files = [{ source: 'URL' }, { source: 'Upload' }]
    expect(hasManualUrlFiles(files)).toBe(true)
  })

  it('returns false when all files are "Upload"', () => {
    const files = [{ source: 'Upload' }, { source: 'Upload' }]
    expect(hasManualUrlFiles(files)).toBe(false)
  })

  it('returns false for empty files array', () => {
    expect(hasManualUrlFiles([])).toBe(false)
  })

  it('returns true when source is "GitHub"', () => {
    const files = [{ source: 'GitHub' }]
    expect(hasManualUrlFiles(files)).toBe(true)
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – isStorageOptionRequired', () => {
  it('always returns true for github mode', () => {
    expect(isStorageOptionRequired('github', [])).toBe(true)
  })

  it('returns true for manual mode with URL files', () => {
    const files = [{ source: 'URL' }]
    expect(isStorageOptionRequired('manual', files)).toBe(true)
  })

  it('returns false for manual mode with only Upload files', () => {
    const files = [{ source: 'Upload' }, { source: 'Upload' }]
    expect(isStorageOptionRequired('manual', files)).toBe(false)
  })

  it('returns false for manual mode with no files', () => {
    expect(isStorageOptionRequired('manual', [])).toBe(false)
  })

  it('returns false when mode is null', () => {
    expect(isStorageOptionRequired(null, [])).toBe(false)
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – isManualConfigurationComplete', () => {
  it('returns false when files array is empty', () => {
    expect(isManualConfigurationComplete([])).toBe(false)
  })

  it('returns true when all files have quantity, color, material', () => {
    const files = [
      { quantity: 2, color: 'Primary', material: 'PLA' },
      { quantity: 4, color: 'Accent', material: 'PETG' },
    ]
    expect(isManualConfigurationComplete(files)).toBe(true)
  })

  it('returns false when any file is missing color', () => {
    const files = [
      { quantity: 2, color: '', material: 'PLA' },
      { quantity: 1, color: 'Primary', material: 'PLA' },
    ]
    expect(isManualConfigurationComplete(files)).toBe(false)
  })

  it('returns false when any file is missing material', () => {
    const files = [{ quantity: 2, color: 'Primary', material: '' }]
    expect(isManualConfigurationComplete(files)).toBe(false)
  })

  it('returns false when any file has falsy quantity (0)', () => {
    const files = [{ quantity: 0, color: 'Primary', material: 'PLA' }]
    expect(isManualConfigurationComplete(files)).toBe(false)
  })

  it('returns true for single fully configured file', () => {
    const files = [{ quantity: 1, color: 'Primary', material: 'ABS' }]
    expect(isManualConfigurationComplete(files)).toBe(true)
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – areAllFilesSelected', () => {
  it('returns true when all files are selected', () => {
    const files = [
      { isSelected: true },
      { isSelected: true },
      { isSelected: true },
    ]
    expect(areAllFilesSelected(files)).toBe(true)
  })

  it('returns false when any file is not selected', () => {
    const files = [{ isSelected: true }, { isSelected: false }]
    expect(areAllFilesSelected(files)).toBe(false)
  })

  it('returns false when all files are deselected', () => {
    const files = [{ isSelected: false }, { isSelected: false }]
    expect(areAllFilesSelected(files)).toBe(false)
  })

  it('returns true for empty array (vacuously true)', () => {
    expect(areAllFilesSelected([])).toBe(true)
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – countSelectedFiles', () => {
  it('returns 0 for empty tree', () => {
    expect(countSelectedFiles([])).toBe(0)
  })

  it('counts selected leaf nodes', () => {
    const tree = [{ isSelected: true }, { isSelected: false }, { isSelected: true }]
    expect(countSelectedFiles(tree)).toBe(2)
  })

  it('counts selected files inside directories', () => {
    const tree = [
      {
        name: 'Frame',
        children: [
          { name: 'a.stl', isSelected: true },
          { name: 'b.stl', isSelected: false },
        ],
      },
      { name: 'c.stl', isSelected: true },
    ]
    expect(countSelectedFiles(tree)).toBe(2)
  })

  it('counts selected files in nested directories', () => {
    const tree = [
      {
        name: 'Frame',
        children: [
          {
            name: 'Sub',
            children: [
              { name: 'deep.stl', isSelected: true },
              { name: 'deep2.stl', isSelected: true },
            ],
          },
        ],
      },
    ]
    expect(countSelectedFiles(tree)).toBe(2)
  })

  it('returns 0 when no files are selected', () => {
    const tree = [{ isSelected: false }, { isSelected: false }]
    expect(countSelectedFiles(tree)).toBe(0)
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – getUniqueCategories', () => {
  it('returns empty array for no files', () => {
    expect(getUniqueCategories([])).toEqual([])
  })

  it('returns sorted unique categories', () => {
    const files = [
      { category: 'Gantry' },
      { category: 'Frame' },
      { category: 'Gantry' },
      { category: 'Axle' },
    ]
    expect(getUniqueCategories(files)).toEqual(['Axle', 'Frame', 'Gantry'])
  })

  it('uses empty string for files without category', () => {
    const files = [{ name: 'part.stl' }, { category: 'Frame' }]
    const result = getUniqueCategories(files)
    expect(result).toContain('')
    expect(result).toContain('Frame')
  })

  it('returns single category for homogeneous files', () => {
    const files = [{ category: 'Panels' }, { category: 'Panels' }]
    expect(getUniqueCategories(files)).toEqual(['Panels'])
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – getFilesByCategory', () => {
  const files = [
    { name: 'a.stl', category: 'Frame' },
    { name: 'b.stl', category: 'Gantry' },
    { name: 'c.stl', category: 'Frame' },
    { name: 'd.stl' }, // no category → ''
  ]

  it('filters files by category name', () => {
    const result = getFilesByCategory(files, 'Frame')
    expect(result).toHaveLength(2)
    expect(result.map((f) => f.name)).toEqual(['a.stl', 'c.stl'])
  })

  it('returns empty array when no files match category', () => {
    expect(getFilesByCategory(files, 'Panels')).toEqual([])
  })

  it('returns files with missing category when queried with empty string', () => {
    const result = getFilesByCategory(files, '')
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('d.stl')
  })
})

// ---------------------------------------------------------------------------

describe('CreateTrackerWizard – groupFilesFromTree', () => {
  it('returns empty object for empty tree', () => {
    expect(groupFilesFromTree([])).toEqual({})
  })

  it('groups root-level files under "Root"', () => {
    const tree = [
      { name: 'a.stl', isSelected: true },
      { name: 'b.stl', isSelected: false },
    ]
    const groups = groupFilesFromTree(tree)
    expect(groups['Root']).toHaveLength(2)
  })

  it('groups nested files by directory path', () => {
    const tree = [
      {
        name: 'Frame',
        children: [
          { name: 'part.stl' },
          { name: 'clip.stl' },
        ],
      },
    ]
    const groups = groupFilesFromTree(tree)
    expect(groups['Frame']).toHaveLength(2)
    expect(Object.keys(groups)).toEqual(['Frame'])
  })

  it('joins nested directory path with " / "', () => {
    const tree = [
      {
        name: 'Frame',
        children: [
          {
            name: 'Sub',
            children: [{ name: 'deep.stl' }],
          },
        ],
      },
    ]
    const groups = groupFilesFromTree(tree)
    expect(groups['Frame / Sub']).toHaveLength(1)
  })

  it('handles mix of root and nested files', () => {
    const tree = [
      { name: 'root.stl' },
      {
        name: 'Gantry',
        children: [{ name: 'gantry.stl' }],
      },
    ]
    const groups = groupFilesFromTree(tree)
    expect(groups['Root']).toHaveLength(1)
    expect(groups['Gantry']).toHaveLength(1)
  })

  it('groups files from multiple directories separately', () => {
    const tree = [
      {
        name: 'A',
        children: [{ name: 'a1.stl' }, { name: 'a2.stl' }],
      },
      {
        name: 'B',
        children: [{ name: 'b1.stl' }],
      },
    ]
    const groups = groupFilesFromTree(tree)
    expect(groups['A']).toHaveLength(2)
    expect(groups['B']).toHaveLength(1)
  })
})
