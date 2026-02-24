/**
 * Tests for ModForm component pure functions
 *
 * ModForm.vue is a form component for creating/editing mods with file attachments.
 * The component allows uploading new files, removing staged uploads, and marking
 * existing files for deletion.
 *
 * Tests cover:
 * - getFileName: extracts the filename from a full path string
 * - toggleFileForDeletion: Set-based toggle for marking files to delete
 * - removeNewFile: removes staged file by index
 * - addFiles: pushes file list items into staged files array
 */
import { describe, it, expect } from 'vitest'

// ── getFileName ───────────────────────────────────────────────────────────────
// Mirrors: const getFileName = (filePath) => filePath ? filePath.split('/').pop() : ''

describe('ModForm — getFileName', () => {
  const getFileName = (filePath) => (filePath ? filePath.split('/').pop() : '')

  it('returns just the filename from a full path', () => {
    expect(getFileName('media/mod_files/bracket.stl')).toBe('bracket.stl')
  })

  it('returns the filename from a deeply nested path', () => {
    expect(getFileName('uploads/mods/2024/v2/assembly.3mf')).toBe('assembly.3mf')
  })

  it('returns the string itself when there is no path separator', () => {
    expect(getFileName('motor-mount.stl')).toBe('motor-mount.stl')
  })

  it('returns empty string for falsy input (null)', () => {
    expect(getFileName(null)).toBe('')
  })

  it('returns empty string for falsy input (undefined)', () => {
    expect(getFileName(undefined)).toBe('')
  })

  it('returns empty string for empty string input', () => {
    expect(getFileName('')).toBe('')
  })

  it('returns empty string when path ends with a trailing slash (no filename)', () => {
    expect(getFileName('media/mod_files/')).toBe('')
  })

  it('handles a path with a dot in folder names correctly', () => {
    expect(getFileName('v1.2/files/part.obj')).toBe('part.obj')
  })
})

// ── toggleFileForDeletion ─────────────────────────────────────────────────────
// Mirrors:
//   const toggleFileForDeletion = (fileId) => {
//     if (filesToDelete.value.has(fileId)) {
//       filesToDelete.value.delete(fileId)
//     } else {
//       filesToDelete.value.add(fileId)
//     }
//   }

describe('ModForm — toggleFileForDeletion', () => {
  const toggleFileForDeletion = (fileId, set) => {
    if (set.has(fileId)) {
      set.delete(fileId)
    } else {
      set.add(fileId)
    }
  }

  it('adds a new fileId to an empty set', () => {
    const s = new Set()
    toggleFileForDeletion(7, s)
    expect(s.has(7)).toBe(true)
  })

  it('removes a fileId that is already in the set', () => {
    const s = new Set([7])
    toggleFileForDeletion(7, s)
    expect(s.has(7)).toBe(false)
  })

  it('toggling twice returns the set to its original state', () => {
    const s = new Set()
    toggleFileForDeletion(42, s)
    toggleFileForDeletion(42, s)
    expect(s.has(42)).toBe(false)
    expect(s.size).toBe(0)
  })

  it('does not affect other entries when toggling one id', () => {
    const s = new Set([1, 2, 3])
    toggleFileForDeletion(2, s)
    expect(s.has(1)).toBe(true)
    expect(s.has(2)).toBe(false)
    expect(s.has(3)).toBe(true)
  })

  it('can track multiple distinct file ids simultaneously', () => {
    const s = new Set()
    toggleFileForDeletion(10, s)
    toggleFileForDeletion(20, s)
    expect(s.has(10)).toBe(true)
    expect(s.has(20)).toBe(true)
    expect(s.size).toBe(2)
  })
})

// ── removeNewFile ─────────────────────────────────────────────────────────────
// Mirrors: const removeNewFile = (index) => { newFiles.value.splice(index, 1) }

describe('ModForm — removeNewFile', () => {
  const removeNewFile = (files, index) => {
    files.splice(index, 1)
  }

  it('removes the item at the given index', () => {
    const files = ['a.stl', 'b.3mf', 'c.obj']
    removeNewFile(files, 1)
    expect(files).toEqual(['a.stl', 'c.obj'])
  })

  it('removes the first item (index 0)', () => {
    const files = ['first.stl', 'second.stl']
    removeNewFile(files, 0)
    expect(files).toEqual(['second.stl'])
  })

  it('removes the last item (last index)', () => {
    const files = ['first.stl', 'last.stl']
    removeNewFile(files, 1)
    expect(files).toEqual(['first.stl'])
  })

  it('removes the only item, leaving an empty array', () => {
    const files = ['only.obj']
    removeNewFile(files, 0)
    expect(files).toEqual([])
  })
})

// ── addFiles ──────────────────────────────────────────────────────────────────
// Mirrors: const addFiles = (fileList) => { newFiles.value.push(...Array.from(fileList)) }

describe('ModForm — addFiles', () => {
  const addFiles = (newFiles, fileList) => {
    newFiles.push(...Array.from(fileList))
  }

  it('pushes all files from a FileList-like array into newFiles', () => {
    const newFiles = []
    const fileList = [{ name: 'a.stl' }, { name: 'b.3mf' }]
    addFiles(newFiles, fileList)
    expect(newFiles).toHaveLength(2)
    expect(newFiles[0].name).toBe('a.stl')
    expect(newFiles[1].name).toBe('b.3mf')
  })

  it('appends to an already-populated array', () => {
    const newFiles = [{ name: 'existing.stl' }]
    addFiles(newFiles, [{ name: 'new.obj' }])
    expect(newFiles).toHaveLength(2)
    expect(newFiles[1].name).toBe('new.obj')
  })

  it('does nothing when given an empty file list', () => {
    const newFiles = [{ name: 'existing.stl' }]
    addFiles(newFiles, [])
    expect(newFiles).toHaveLength(1)
  })

  it('handles a Set as fileList (Array.from converts iterables)', () => {
    const newFiles = []
    const fileSet = new Set([{ name: 'set-file.stl' }])
    addFiles(newFiles, fileSet)
    expect(newFiles).toHaveLength(1)
  })
})
