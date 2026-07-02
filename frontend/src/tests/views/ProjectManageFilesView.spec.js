/**
 * ProjectManageFilesView.spec.js
 *
 * Tests for pure helper logic extracted from ProjectManageFilesView.vue.
 *
 * Functions under test (extracted as standalone implementations):
 *   - getFileName(filePath)          extract the filename from a URL path
 *   - toggleFileForDeletion(set, id) toggle a file ID in the pending-delete Set
 *   - removeNewFile(files, index)    splice a file from the staged-upload array
 *   - addFiles(current, incoming)    append incoming files to the staged list
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// Extracted pure function implementations (mirrors ProjectManageFilesView.vue)
// ---------------------------------------------------------------------------

/**
 * Return the filename portion of a file path (the segment after the last '/').
 * Returns '' for falsy input.
 */
const getFileName = (filePath) => {
  return filePath ? filePath.split('/').pop() : ''
}

/**
 * Toggle a file ID inside a Set:
 *   - If present → remove it (un-mark for deletion)
 *   - If absent  → add it   (mark for deletion)
 * Mutates the set in place.
 */
const toggleFileForDeletion = (set, fileId) => {
  if (set.has(fileId)) {
    set.delete(fileId)
  } else {
    set.add(fileId)
  }
}

/**
 * Remove the file at `index` from the staged-upload array.
 * Mutates in place (mirrors .splice() in the component).
 */
const removeNewFile = (files, index) => {
  files.splice(index, 1)
}

/**
 * Append all files from `incoming` (array or FileList-like) to `current`.
 * Mutates `current` in place (mirrors .push(...Array.from(fileList))).
 */
const addFiles = (current, incoming) => {
  current.push(...Array.from(incoming))
}

// ---------------------------------------------------------------------------

describe('ProjectManageFilesView – getFileName', () => {
  it('extracts filename from a simple path', () => {
    expect(getFileName('/media/project_files/design.stl')).toBe('design.stl')
  })

  it('extracts filename from a deeply nested path', () => {
    expect(getFileName('/a/b/c/d/myfile.3mf')).toBe('myfile.3mf')
  })

  it('returns the value unchanged when there is no slash', () => {
    expect(getFileName('standalone.obj')).toBe('standalone.obj')
  })

  it('returns empty string for null input', () => {
    expect(getFileName(null)).toBe('')
  })

  it('returns empty string for empty string input', () => {
    expect(getFileName('')).toBe('')
  })

  it('returns empty string for undefined input', () => {
    expect(getFileName(undefined)).toBe('')
  })

  it('handles trailing slash (empty segment) correctly', () => {
    // '/path/to/dir/' → pop() returns ''
    expect(getFileName('/path/to/dir/')).toBe('')
  })

  it('handles filename with multiple dots', () => {
    expect(getFileName('/media/my.archive.tar.gz')).toBe('my.archive.tar.gz')
  })

  it('handles Windows-style path separators (backslashes are NOT separators)', () => {
    // The function only splits on '/' — backslash should be kept as part of the name
    expect(getFileName('C:\\Users\\name\\file.stl')).toBe('C:\\Users\\name\\file.stl')
  })

  it('handles URL path with query string', () => {
    expect(getFileName('/files/design.stl?v=2')).toBe('design.stl?v=2')
  })
})

// ---------------------------------------------------------------------------

describe('ProjectManageFilesView – toggleFileForDeletion', () => {
  it('adds a file ID that is not yet in the set', () => {
    const set = new Set()
    toggleFileForDeletion(set, 42)
    expect(set.has(42)).toBe(true)
  })

  it('removes a file ID that is already in the set', () => {
    const set = new Set([42])
    toggleFileForDeletion(set, 42)
    expect(set.has(42)).toBe(false)
  })

  it('can mark multiple different IDs for deletion', () => {
    const set = new Set()
    toggleFileForDeletion(set, 1)
    toggleFileForDeletion(set, 2)
    toggleFileForDeletion(set, 3)
    expect(set).toEqual(new Set([1, 2, 3]))
  })

  it('toggling twice returns the set to its original state', () => {
    const set = new Set()
    toggleFileForDeletion(set, 99)
    toggleFileForDeletion(set, 99)
    expect(set.has(99)).toBe(false)
    expect(set.size).toBe(0)
  })

  it('does not affect other IDs when toggling a specific id', () => {
    const set = new Set([10, 20, 30])
    toggleFileForDeletion(set, 20) // remove 20
    expect(set).toEqual(new Set([10, 30]))
  })

  it('works with string IDs as well as numbers', () => {
    const set = new Set()
    toggleFileForDeletion(set, 'file-abc')
    expect(set.has('file-abc')).toBe(true)
    toggleFileForDeletion(set, 'file-abc')
    expect(set.has('file-abc')).toBe(false)
  })

  it('mutates the original set (no new set returned)', () => {
    const set = new Set()
    const ref = set
    toggleFileForDeletion(set, 5)
    expect(set).toBe(ref)
  })
})

// ---------------------------------------------------------------------------

describe('ProjectManageFilesView – removeNewFile', () => {
  it('removes the file at a given index', () => {
    const files = ['a.stl', 'b.stl', 'c.stl']
    removeNewFile(files, 1)
    expect(files).toEqual(['a.stl', 'c.stl'])
  })

  it('removes the first file', () => {
    const files = ['first.stl', 'second.stl']
    removeNewFile(files, 0)
    expect(files).toEqual(['second.stl'])
  })

  it('removes the last file', () => {
    const files = ['a.3mf', 'b.3mf', 'c.3mf']
    removeNewFile(files, 2)
    expect(files).toEqual(['a.3mf', 'b.3mf'])
  })

  it('results in an empty array after removing the only file', () => {
    const files = ['only.stl']
    removeNewFile(files, 0)
    expect(files).toEqual([])
  })

  it('mutates the original array in place', () => {
    const files = ['x.stl', 'y.stl']
    const ref = files
    removeNewFile(files, 0)
    expect(files).toBe(ref)
  })
})

// ---------------------------------------------------------------------------

describe('ProjectManageFilesView – addFiles', () => {
  it('appends incoming files to the current list', () => {
    const current = ['existing.stl']
    addFiles(current, ['new1.stl', 'new2.stl'])
    expect(current).toEqual(['existing.stl', 'new1.stl', 'new2.stl'])
  })

  it('works when current list is empty', () => {
    const current = []
    addFiles(current, ['new.stl'])
    expect(current).toEqual(['new.stl'])
  })

  it('is a no-op when incoming is empty', () => {
    const current = ['exist.stl']
    addFiles(current, [])
    expect(current).toEqual(['exist.stl'])
  })

  it('mutates the original current array in place', () => {
    const current = []
    const ref = current
    addFiles(current, ['x.stl'])
    expect(current).toBe(ref)
  })
})
