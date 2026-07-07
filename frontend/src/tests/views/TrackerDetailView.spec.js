/**
 * Tests for TrackerDetailView (/trackers/:id)
 *
 * TrackerDetailView is the main print-tracker detail page. It displays
 * a tree of files grouped by directory, with rich filtering and progress tracking.
 *
 * Tests cover:
 * - APIService contract (getTracker, getMaterials, updateTrackerFileStatus)
 * - Router registration (tracker-detail route)
 * - getProgressColor() thresholds (0 / <50 / <100 / 100)
 * - overallProgressStyle and fileProgressStyle shapes
 * - filteredCategories: search, color, material, status, missingConfig, empty removal
 * - unconfiguredFilesCount: no tracker / all configured / partial config
 * - isEditingMulticolor: true only for 'Multicolor'
 * - isMaterialSelectionDisabled: true for 'Primary' and 'Accent'
 * - isFilterActive: OR of 4 filter fields
 * - filterOptions: extracts unique colors/materials + hardcoded statuses
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('TrackerDetailView — APIService contract', () => {
  it('APIService.getTracker exists', () => {
    expect(typeof APIService.getTracker).toBe('function')
  })

  it('APIService.getMaterials exists', () => {
    expect(typeof APIService.getMaterials).toBe('function')
  })

  it('APIService.updateTrackerFileStatus exists', () => {
    expect(typeof APIService.updateTrackerFileStatus).toBe('function')
  })

  it('APIService.updateTracker exists', () => {
    expect(typeof APIService.updateTracker).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('TrackerDetailView — route registration', () => {
  it('tracker-detail route is registered', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'tracker-detail')
    expect(route).toBeDefined()
  })

  it('tracker-detail route contains :id param in path', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'tracker-detail')
    expect(route?.path).toContain(':id')
  })
})

// ── getProgressColor() ───────────────────────────────────────────────────────

describe('TrackerDetailView — getProgressColor()', () => {
  // Mirrors getProgressColor() from TrackerDetailView.vue
  const getProgressColor = (percentage) => {
    if (percentage === 0) return 'var(--color-progress-none)'
    if (percentage < 50) return 'var(--color-progress-low)'
    if (percentage < 100) return 'var(--color-progress-medium)'
    return 'var(--color-progress-complete)'
  }

  it("0% → 'var(--color-progress-none)' (gray)", () => {
    expect(getProgressColor(0)).toBe('var(--color-progress-none)')
  })

  it("1% → 'var(--color-progress-low)' (red)", () => {
    expect(getProgressColor(1)).toBe('var(--color-progress-low)')
  })

  it("49% → 'var(--color-progress-low)' (red)", () => {
    expect(getProgressColor(49)).toBe('var(--color-progress-low)')
  })

  it("50% → 'var(--color-progress-medium)' (orange)", () => {
    expect(getProgressColor(50)).toBe('var(--color-progress-medium)')
  })

  it("99% → 'var(--color-progress-medium)' (orange)", () => {
    expect(getProgressColor(99)).toBe('var(--color-progress-medium)')
  })

  it("100% → 'var(--color-progress-complete)' (green)", () => {
    expect(getProgressColor(100)).toBe('var(--color-progress-complete)')
  })

  it("over 100% → 'var(--color-progress-complete)' (clamp at green)", () => {
    expect(getProgressColor(110)).toBe('var(--color-progress-complete)')
  })
})

// ── overallProgressStyle ─────────────────────────────────────────────────────

describe('TrackerDetailView — overallProgressStyle', () => {
  const getProgressColor = (percentage) => {
    if (percentage === 0) return 'var(--color-progress-none)'
    if (percentage < 50) return 'var(--color-progress-low)'
    if (percentage < 100) return 'var(--color-progress-medium)'
    return 'var(--color-progress-complete)'
  }

  const buildProgressStyle = (progressPercentage) => ({
    width: `${progressPercentage}%`,
    height: '100%',
    backgroundColor: getProgressColor(progressPercentage),
    transition: 'width 0.3s ease',
  })

  it("style has required keys (width/height/backgroundColor/transition)", () => {
    const style = buildProgressStyle(50)
    expect(style).toHaveProperty('width')
    expect(style).toHaveProperty('height')
    expect(style).toHaveProperty('backgroundColor')
    expect(style).toHaveProperty('transition')
  })

  it("50% progress → width is '50%'", () => {
    expect(buildProgressStyle(50).width).toBe('50%')
  })

  it("0% progress → width is '0%'", () => {
    expect(buildProgressStyle(0).width).toBe('0%')
  })

  it("100% progress → width is '100%'", () => {
    expect(buildProgressStyle(100).width).toBe('100%')
  })

  it("height is always '100%'", () => {
    expect(buildProgressStyle(75).height).toBe('100%')
  })
})

// ── fileProgressStyle ────────────────────────────────────────────────────────

describe('TrackerDetailView — fileProgressStyle()', () => {
  const getProgressColor = (percentage) => {
    if (percentage === 0) return 'var(--color-progress-none)'
    if (percentage < 50) return 'var(--color-progress-low)'
    if (percentage < 100) return 'var(--color-progress-medium)'
    return 'var(--color-progress-complete)'
  }

  const fileProgressStyle = (file) => {
    const percentage =
      file.quantity > 0 ? Math.round((file.printed_quantity / file.quantity) * 100) : 0
    return {
      width: `${percentage}%`,
      height: '100%',
      backgroundColor: getProgressColor(percentage),
      transition: 'width 0.3s ease',
    }
  }

  it("2 of 4 printed → 50%", () => {
    expect(fileProgressStyle({ printed_quantity: 2, quantity: 4 }).width).toBe('50%')
  })

  it("4 of 4 printed → 100%", () => {
    expect(fileProgressStyle({ printed_quantity: 4, quantity: 4 }).width).toBe('100%')
  })

  it("0 of 4 printed → 0%", () => {
    expect(fileProgressStyle({ printed_quantity: 0, quantity: 4 }).width).toBe('0%')
  })

  it("quantity=0 → 0% (no division by zero)", () => {
    expect(fileProgressStyle({ printed_quantity: 0, quantity: 0 }).width).toBe('0%')
  })

  it("1 of 3 → rounded to 33%", () => {
    expect(fileProgressStyle({ printed_quantity: 1, quantity: 3 }).width).toBe('33%')
  })
})

// ── filteredCategories: groupedFiles helper ───────────────────────────────────

describe('TrackerDetailView — groupedFiles()', () => {
  // Mirrors groupedFiles computed
  const groupFiles = (files) => {
    const groups = {}
    files.forEach((file) => {
      const dir = file.directory_path || 'Root'
      if (!groups[dir]) {
        groups[dir] = { name: dir, isOpen: true, files: [] }
      }
      groups[dir].files.push(file)
    })
    return Object.values(groups)
  }

  it('returns [] when files is empty', () => {
    expect(groupFiles([])).toHaveLength(0)
  })

  it('groups files by directory_path', () => {
    const files = [
      { id: 1, filename: 'a.stl', directory_path: 'Skirts' },
      { id: 2, filename: 'b.stl', directory_path: 'Frame' },
      { id: 3, filename: 'c.stl', directory_path: 'Skirts' },
    ]
    const groups = groupFiles(files)
    expect(groups).toHaveLength(2)
    const skirts = groups.find((g) => g.name === 'Skirts')
    expect(skirts?.files).toHaveLength(2)
  })

  it("files without directory_path go to 'Root' group", () => {
    const files = [{ id: 1, filename: 'a.stl', directory_path: null }]
    const groups = groupFiles(files)
    expect(groups[0].name).toBe('Root')
  })
})

// ── filteredCategories: Search Filter ────────────────────────────────────────

describe('TrackerDetailView — filteredCategories: search', () => {
  const buildCategories = (files) => {
    const groups = {}
    files.forEach((f) => {
      const dir = f.directory_path || 'Root'
      if (!groups[dir]) groups[dir] = { name: dir, files: [] }
      groups[dir].files.push(f)
    })
    return Object.values(groups)
  }

  const applySearch = (categories, query) => {
    if (!query.trim()) return categories
    const q = query.toLowerCase()
    return categories
      .map((cat) => ({
        ...cat,
        files: cat.files.filter((f) => f.filename.toLowerCase().includes(q)),
      }))
      .filter((cat) => cat.files.length > 0)
  }

  const files = [
    { id: 1, filename: 'front_skirt.stl', directory_path: 'Skirts', color: 'Primary', material: 'PLA', status: 'not_started' },
    { id: 2, filename: 'rear_skirt.stl', directory_path: 'Skirts', color: 'Accent', material: 'ABS', status: 'not_started' },
    { id: 3, filename: 'corner_post.stl', directory_path: 'Frame', color: 'Primary', material: 'PLA', status: 'completed' },
  ]
  const categories = buildCategories(files)

  it('returns all categories when query is empty', () => {
    const result = applySearch(categories, '')
    expect(result).toHaveLength(2)
  })

  it('filters by filename (case-insensitive match)', () => {
    const result = applySearch(categories, 'front')
    expect(result).toHaveLength(1)
    expect(result[0].files[0].filename).toBe('front_skirt.stl')
  })

  it('removes category when all its files are filtered out', () => {
    const result = applySearch(categories, 'corner')
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Frame')
  })

  it('returns empty when no filename matches', () => {
    const result = applySearch(categories, 'NONEXISTENT')
    expect(result).toHaveLength(0)
  })
})

// ── filteredCategories: Active Filters ───────────────────────────────────────

describe('TrackerDetailView — filteredCategories: active filters', () => {
  const files = [
    { id: 1, filename: 'a.stl', directory_path: 'Cat1', color: 'Primary', material: 'PLA', status: 'not_started' },
    { id: 2, filename: 'b.stl', directory_path: 'Cat1', color: 'Accent', material: 'ABS', status: 'completed' },
    { id: 3, filename: 'c.stl', directory_path: 'Cat2', color: 'Primary', material: 'PLA', status: 'in_progress' },
    { id: 4, filename: 'd.stl', directory_path: 'Cat2', color: 'Multicolor', material: null, status: 'not_started' },
  ]

  const buildCategories = (files) => {
    const groups = {}
    files.forEach((f) => {
      const dir = f.directory_path
      if (!groups[dir]) groups[dir] = { name: dir, files: [] }
      groups[dir].files.push(f)
    })
    return Object.values(groups)
  }

  const applyFilters = (categories, activeFilters) => {
    return categories
      .map((cat) => ({
        ...cat,
        files: cat.files.filter((file) => {
          if (activeFilters.color && file.color !== activeFilters.color) return false
          if (activeFilters.material && file.material !== activeFilters.material) return false
          if (activeFilters.status && file.status !== activeFilters.status) return false
          if (activeFilters.missingConfig && file.color && file.material) return false
          return true
        }),
      }))
      .filter((cat) => cat.files.length > 0)
  }

  const categories = buildCategories(files)
  const empty = { color: '', material: '', status: '', missingConfig: false }

  it('returns all categories when no filters active', () => {
    const result = applyFilters(categories, empty)
    expect(result).toHaveLength(2)
    expect(result.reduce((n, c) => n + c.files.length, 0)).toBe(4)
  })

  it('color filter keeps only matching files', () => {
    const result = applyFilters(categories, { ...empty, color: 'Primary' })
    const allFiles = result.flatMap((c) => c.files)
    expect(allFiles.every((f) => f.color === 'Primary')).toBe(true)
    expect(allFiles).toHaveLength(2)
  })

  it('material filter keeps only matching files', () => {
    const result = applyFilters(categories, { ...empty, material: 'ABS' })
    const allFiles = result.flatMap((c) => c.files)
    expect(allFiles).toHaveLength(1)
    expect(allFiles[0].id).toBe(2)
  })

  it('status filter keeps only matching files', () => {
    const result = applyFilters(categories, { ...empty, status: 'completed' })
    const allFiles = result.flatMap((c) => c.files)
    expect(allFiles).toHaveLength(1)
    expect(allFiles[0].id).toBe(2)
  })

  it('missingConfig filter shows files without color OR material', () => {
    // file 4 has no material → should be shown; others have both → hidden
    const result = applyFilters(categories, { ...empty, missingConfig: true })
    const allFiles = result.flatMap((c) => c.files)
    expect(allFiles).toHaveLength(1)
    expect(allFiles[0].id).toBe(4)
  })

  it('empty category is removed from result', () => {
    // Filtering by Accent color: only file 2 in Cat1 matches; Cat2 has none
    const result = applyFilters(categories, { ...empty, color: 'Accent' })
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Cat1')
  })
})

// ── unconfiguredFilesCount ────────────────────────────────────────────────────

describe('TrackerDetailView — unconfiguredFilesCount', () => {
  // Mirrors: tracker.files.filter(f => !f.color || !f.material).length
  const countUnconfigured = (trackerFiles) => {
    if (!trackerFiles) return 0
    return trackerFiles.filter((f) => !f.color || !f.material).length
  }

  it('returns 0 when trackerFiles is null', () => {
    expect(countUnconfigured(null)).toBe(0)
  })

  it('returns 0 when all files have color and material', () => {
    const files = [
      { color: 'Primary', material: 'PLA' },
      { color: 'Accent', material: 'ABS' },
    ]
    expect(countUnconfigured(files)).toBe(0)
  })

  it('counts files with no color', () => {
    const files = [
      { color: '', material: 'PLA' },
      { color: 'Primary', material: 'PLA' },
    ]
    expect(countUnconfigured(files)).toBe(1)
  })

  it('counts files with no material', () => {
    const files = [
      { color: 'Primary', material: null },
      { color: 'Primary', material: 'PLA' },
    ]
    expect(countUnconfigured(files)).toBe(1)
  })

  it('counts files missing both color and material', () => {
    const files = [{ color: null, material: null }]
    expect(countUnconfigured(files)).toBe(1)
  })

  it('counts correctly with mixed configured/unconfigured files', () => {
    const files = [
      { color: 'Primary', material: 'PLA' },
      { color: '', material: '' },
      { color: 'Accent', material: null },
    ]
    expect(countUnconfigured(files)).toBe(2)
  })
})

// ── isEditingMulticolor & isMaterialSelectionDisabled ────────────────────────

describe('TrackerDetailView — isEditingMulticolor', () => {
  const isEditingMulticolor = (color) => color === 'Multicolor'

  it("'Multicolor' → true", () => {
    expect(isEditingMulticolor('Multicolor')).toBe(true)
  })

  it("'Primary' → false", () => {
    expect(isEditingMulticolor('Primary')).toBe(false)
  })

  it("'Accent' → false", () => {
    expect(isEditingMulticolor('Accent')).toBe(false)
  })

  it("empty string → false", () => {
    expect(isEditingMulticolor('')).toBe(false)
  })
})

describe('TrackerDetailView — isMaterialSelectionDisabled', () => {
  const isMaterialSelectionDisabled = (color) =>
    color === 'Primary' || color === 'Accent'

  it("'Primary' → true (uses tracker primary material)", () => {
    expect(isMaterialSelectionDisabled('Primary')).toBe(true)
  })

  it("'Accent' → true (uses tracker accent material)", () => {
    expect(isMaterialSelectionDisabled('Accent')).toBe(true)
  })

  it("'Multicolor' → false (custom selection allowed)", () => {
    expect(isMaterialSelectionDisabled('Multicolor')).toBe(false)
  })

  it("'Clear' → false", () => {
    expect(isMaterialSelectionDisabled('Clear')).toBe(false)
  })

  it("empty string → false", () => {
    expect(isMaterialSelectionDisabled('')).toBe(false)
  })
})

// ── isFilterActive ────────────────────────────────────────────────────────────

describe('TrackerDetailView — isFilterActive', () => {
  // Mirrors: color || material || status || missingConfig
  const isFilterActive = (filters) => {
    return !!(filters.color || filters.material || filters.status || filters.missingConfig)
  }

  const empty = { color: '', material: '', status: '', missingConfig: false }

  it('false when all filters empty/false', () => {
    expect(isFilterActive(empty)).toBe(false)
  })

  it('true when color is set', () => {
    expect(isFilterActive({ ...empty, color: 'Primary' })).toBe(true)
  })

  it('true when material is set', () => {
    expect(isFilterActive({ ...empty, material: 'PLA' })).toBe(true)
  })

  it('true when status is set', () => {
    expect(isFilterActive({ ...empty, status: 'completed' })).toBe(true)
  })

  it('true when missingConfig is true', () => {
    expect(isFilterActive({ ...empty, missingConfig: true })).toBe(true)
  })
})

// ── filterOptions ────────────────────────────────────────────────────────────

describe('TrackerDetailView — filterOptions', () => {
  // Mirrors filterOptions computed
  const buildFilterOptions = (files) => {
    const colors = [...new Set(files.map((f) => f.color).filter(Boolean))]
    const materials = [...new Set(files.map((f) => f.material).filter(Boolean))]
    const statuses = [
      { value: 'not_started', label: 'Not Started' },
      { value: 'in_progress', label: 'In Progress' },
      { value: 'completed', label: 'Completed' },
    ]
    return { colors, materials, statuses }
  }

  it('has 3 hardcoded statuses', () => {
    const opts = buildFilterOptions([])
    expect(opts.statuses).toHaveLength(3)
    expect(opts.statuses.map((s) => s.value)).toEqual([
      'not_started',
      'in_progress',
      'completed',
    ])
  })

  it('extracts unique colors from files', () => {
    const files = [
      { color: 'Primary', material: 'PLA' },
      { color: 'Accent', material: 'ABS' },
      { color: 'Primary', material: 'PLA' }, // duplicate
    ]
    const opts = buildFilterOptions(files)
    expect(opts.colors).toHaveLength(2)
    expect(opts.colors).toContain('Primary')
    expect(opts.colors).toContain('Accent')
  })

  it('extracts unique materials from files', () => {
    const files = [
      { color: 'Primary', material: 'PLA' },
      { color: 'Accent', material: 'ABS' },
      { color: 'Multicolor', material: 'PLA' }, // PLA duplicate
    ]
    const opts = buildFilterOptions(files)
    expect(opts.materials).toHaveLength(2)
  })

  it('excludes null/undefined colors and materials', () => {
    const files = [
      { color: null, material: null },
      { color: 'Primary', material: 'PLA' },
    ]
    const opts = buildFilterOptions(files)
    expect(opts.colors).toEqual(['Primary'])
    expect(opts.materials).toEqual(['PLA'])
  })

  it('returns empty arrays when files have no configured values', () => {
    const opts = buildFilterOptions([{ color: null, material: null }])
    expect(opts.colors).toHaveLength(0)
    expect(opts.materials).toHaveLength(0)
  })
})

// ── toggleViewerBackground() ─────────────────────────────────────────────────
// Mirrors TrackerDetailView.vue's handler: flips dark<->light, optimistically
// updates the local tracker object so the viewer re-renders immediately, then
// PATCHes the tracker; reverts the optimistic update if the PATCH fails.

async function toggleViewerBackground(tracker, patchCall) {
  const newBackground = tracker.viewer_background === 'light' ? 'dark' : 'light'
  const previous = tracker.viewer_background
  tracker.viewer_background = newBackground

  try {
    await patchCall(tracker.id, { viewer_background: newBackground })
  } catch {
    tracker.viewer_background = previous
  }

  return tracker
}

describe('TrackerDetailView — toggleViewerBackground()', () => {
  it('flips dark to light', async () => {
    const tracker = { id: 1, viewer_background: 'dark' }
    const patchCall = async () => {}

    const result = await toggleViewerBackground(tracker, patchCall)

    expect(result.viewer_background).toBe('light')
  })

  it('flips light to dark', async () => {
    const tracker = { id: 1, viewer_background: 'light' }
    const patchCall = async () => {}

    const result = await toggleViewerBackground(tracker, patchCall)

    expect(result.viewer_background).toBe('dark')
  })

  it('calls the PATCH with the tracker id and new value', async () => {
    const tracker = { id: 7, viewer_background: 'dark' }
    const calls = []
    const patchCall = async (id, data) => calls.push([id, data])

    await toggleViewerBackground(tracker, patchCall)

    expect(calls).toEqual([[7, { viewer_background: 'light' }]])
  })

  it('reverts the optimistic update if the PATCH fails', async () => {
    const tracker = { id: 1, viewer_background: 'dark' }
    const patchCall = async () => {
      throw new Error('network error')
    }

    const result = await toggleViewerBackground(tracker, patchCall)

    expect(result.viewer_background).toBe('dark')
  })
})

// ── hasFilesAwaitingThumbnail() ──────────────────────────────────────────────
// Mirrors: tracker.files.some((file) => isPreviewableFile(file) && !file.thumbnail)

function isPreviewableFile(file) {
  if (!file.filename) return false
  const ext = file.filename.toLowerCase().split('.').pop()
  return ext === 'stl' || ext === '3mf'
}

function hasFilesAwaitingThumbnail(tracker) {
  if (!tracker?.files) return false
  return tracker.files.some((file) => isPreviewableFile(file) && !file.thumbnail)
}

describe('TrackerDetailView — hasFilesAwaitingThumbnail()', () => {
  it('returns false when tracker has no files', () => {
    expect(hasFilesAwaitingThumbnail({ files: [] })).toBe(false)
  })

  it('returns false when every previewable file already has a thumbnail', () => {
    const tracker = {
      files: [
        { filename: 'a.stl', thumbnail: '/media/a.png' },
        { filename: 'b.3mf', thumbnail: '/media/b.png' },
      ],
    }
    expect(hasFilesAwaitingThumbnail(tracker)).toBe(false)
  })

  it('returns true when a previewable file has no thumbnail yet', () => {
    const tracker = {
      files: [
        { filename: 'a.stl', thumbnail: '/media/a.png' },
        { filename: 'b.stl', thumbnail: null },
      ],
    }
    expect(hasFilesAwaitingThumbnail(tracker)).toBe(true)
  })

  it('ignores non-previewable files with no thumbnail', () => {
    const tracker = { files: [{ filename: 'readme.txt', thumbnail: null }] }
    expect(hasFilesAwaitingThumbnail(tracker)).toBe(false)
  })
})

// ── refreshThumbnails() merge logic ──────────────────────────────────────────
// Mirrors: merges only the `thumbnail` field from a fresh fetch into the
// existing reactive file objects, by id, without replacing the array/objects.

function mergeThumbnails(existingFiles, freshFiles) {
  const thumbnailById = new Map(freshFiles.map((f) => [f.id, f.thumbnail]))
  existingFiles.forEach((file) => {
    if (thumbnailById.has(file.id)) {
      file.thumbnail = thumbnailById.get(file.id)
    }
  })
  return existingFiles
}

describe('TrackerDetailView — thumbnail refresh merge', () => {
  it('updates thumbnail fields for matching file ids', () => {
    const existing = [{ id: 1, thumbnail: null }, { id: 2, thumbnail: null }]
    const fresh = [{ id: 1, thumbnail: '/media/1.png' }, { id: 2, thumbnail: null }]

    const result = mergeThumbnails(existing, fresh)

    expect(result[0].thumbnail).toBe('/media/1.png')
    expect(result[1].thumbnail).toBeNull()
  })

  it('leaves files untouched if their id is not in the fresh response', () => {
    const existing = [{ id: 1, thumbnail: null, color: 'Primary' }]
    const fresh = []

    const result = mergeThumbnails(existing, fresh)

    expect(result[0].thumbnail).toBeNull()
    expect(result[0].color).toBe('Primary')
  })

  it('preserves object identity (mutates in place, does not replace array)', () => {
    const fileA = { id: 1, thumbnail: null }
    const existing = [fileA]
    const fresh = [{ id: 1, thumbnail: '/media/1.png' }]

    const result = mergeThumbnails(existing, fresh)

    expect(result[0]).toBe(fileA)
    expect(fileA.thumbnail).toBe('/media/1.png')
  })
})

// ── Polling loop stop conditions ─────────────────────────────────────────────
// Mirrors startThumbnailPolling()'s per-tick check: stop once no files are
// awaiting a thumbnail, or once MAX_THUMBNAIL_POLL_ATTEMPTS is reached.

describe('TrackerDetailView — thumbnail poll stop conditions', () => {
  const MAX_ATTEMPTS = 24

  function shouldStopPolling(tracker, attempts) {
    return !hasFilesAwaitingThumbnail(tracker) || attempts >= MAX_ATTEMPTS
  }

  it('stops once every file has a thumbnail', () => {
    const tracker = { files: [{ filename: 'a.stl', thumbnail: '/media/a.png' }] }
    expect(shouldStopPolling(tracker, 1)).toBe(true)
  })

  it('keeps polling while a file is still missing a thumbnail and under the cap', () => {
    const tracker = { files: [{ filename: 'a.stl', thumbnail: null }] }
    expect(shouldStopPolling(tracker, 1)).toBe(false)
  })

  it('stops once the max attempt cap is reached, even if still missing', () => {
    const tracker = { files: [{ filename: 'a.stl', thumbnail: null }] }
    expect(shouldStopPolling(tracker, MAX_ATTEMPTS)).toBe(true)
  })
})

// ── Edit File modal storage-type label ───────────────────────────────────────
// Mirrors: editingFile?.storage_type === 'local' ? 'Local File' : 'GitHub Link Only'

function storageTypeLabel(file) {
  return file?.storage_type === 'local' ? 'Local File' : 'GitHub Link Only'
}

describe('TrackerDetailView — storage type label', () => {
  it('shows "Local File" for storage_type=local', () => {
    expect(storageTypeLabel({ storage_type: 'local' })).toBe('Local File')
  })

  it('shows "GitHub Link Only" for storage_type=link', () => {
    expect(storageTypeLabel({ storage_type: 'link' })).toBe('GitHub Link Only')
  })

  it('defaults to "GitHub Link Only" when file is null/undefined', () => {
    expect(storageTypeLabel(null)).toBe('GitHub Link Only')
    expect(storageTypeLabel(undefined)).toBe('GitHub Link Only')
  })
})
