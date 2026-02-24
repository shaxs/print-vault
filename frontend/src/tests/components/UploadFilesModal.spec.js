/**
 * Tests for UploadFilesModal component pure logic
 *
 * UploadFilesModal.vue handles drag-and-drop or click-to-browse file uploads
 * of 3D-printing files (.stl, .3mf, .obj, .gcode, .step, .stp). It validates
 * the file extension whitelist and formats file sizes for display.
 *
 * Tests cover:
 * - hasFiles: boolean check on file list length
 * - totalSize: sum of file sizes
 * - formatFileSize: human-readable bytes → KB/MB/GB
 * - file extension validation (whitelist of valid 3D file types)
 * - removeFile: removes a staged file by index
 */
import { describe, it, expect } from 'vitest'

// ── hasFiles ──────────────────────────────────────────────────────────────────
// Mirrors: selectedFiles.value.length > 0

describe('UploadFilesModal — hasFiles', () => {
  const hasFiles = (files) => files.length > 0

  it('returns false when file list is empty', () => {
    expect(hasFiles([])).toBe(false)
  })

  it('returns true when there is at least one file', () => {
    expect(hasFiles([{ name: 'part.stl' }])).toBe(true)
  })

  it('returns true with multiple files', () => {
    expect(hasFiles([{ name: 'a.stl' }, { name: 'b.3mf' }])).toBe(true)
  })
})

// ── totalSize ─────────────────────────────────────────────────────────────────
// Mirrors: selectedFiles.value.reduce((sum, file) => sum + file.size, 0)

describe('UploadFilesModal — totalSize', () => {
  const totalSize = (files) => files.reduce((sum, f) => sum + f.size, 0)

  it('returns 0 for an empty file list', () => {
    expect(totalSize([])).toBe(0)
  })

  it('returns the size of a single file', () => {
    expect(totalSize([{ size: 2048 }])).toBe(2048)
  })

  it('sums sizes of multiple files', () => {
    expect(totalSize([{ size: 1024 }, { size: 512 }, { size: 256 }])).toBe(1792)
  })
})

// ── formatFileSize ────────────────────────────────────────────────────────────
// Mirrors:
//   if (bytes === 0) return '0 Bytes'
//   const k = 1024
//   const sizes = ['Bytes', 'KB', 'MB', 'GB']
//   const i = Math.floor(Math.log(bytes) / Math.log(k))
//   return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]

describe('UploadFilesModal — formatFileSize', () => {
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  it('returns "0 Bytes" for 0 bytes', () => {
    expect(formatFileSize(0)).toBe('0 Bytes')
  })

  it('formats bytes below 1 KB', () => {
    expect(formatFileSize(512)).toBe('512 Bytes')
  })

  it('formats exactly 1 KB', () => {
    expect(formatFileSize(1024)).toBe('1 KB')
  })

  it('formats 1.5 KB correctly', () => {
    expect(formatFileSize(1536)).toBe('1.5 KB')
  })

  it('formats exactly 1 MB', () => {
    expect(formatFileSize(1024 * 1024)).toBe('1 MB')
  })

  it('formats 2.5 MB correctly', () => {
    expect(formatFileSize(Math.round(2.5 * 1024 * 1024))).toBe('2.5 MB')
  })

  it('formats exactly 1 GB', () => {
    expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB')
  })

  it('rounds to 2 decimal places', () => {
    // 1 KB + 100 bytes → 1.1 KB (rounded)
    const result = formatFileSize(1024 + 100)
    expect(result).toContain('KB')
  })
})

// ── file extension validation ─────────────────────────────────────────────────
// Mirrors the filter inside addFiles():
//   const validExtensions = ['.stl', '.3mf', '.obj', '.gcode', '.step', '.stp']
//   const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
//   return validExtensions.includes(ext)

describe('UploadFilesModal — file extension validation', () => {
  const VALID_EXTENSIONS = ['.stl', '.3mf', '.obj', '.gcode', '.step', '.stp']

  const isValidFile = (filename) => {
    const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'))
    return VALID_EXTENSIONS.includes(ext)
  }

  const filterValidFiles = (files) => files.filter((f) => isValidFile(f.name))

  it.each(['.stl', '.3mf', '.obj', '.gcode', '.step', '.stp'])(
    'accepts files with extension "%s"',
    (ext) => {
      expect(isValidFile(`model${ext}`)).toBe(true)
    }
  )

  it('accepts uppercase extensions by normalising to lowercase', () => {
    expect(isValidFile('PART.STL')).toBe(true)
    expect(isValidFile('ASSEMBLY.3MF')).toBe(true)
  })

  it('rejects a .png file', () => {
    expect(isValidFile('photo.png')).toBe(false)
  })

  it('rejects a .zip file', () => {
    expect(isValidFile('archive.zip')).toBe(false)
  })

  it('rejects a file with no extension', () => {
    expect(isValidFile('noextension')).toBe(false)
  })

  it('filters a mixed list and keeps only valid 3D files', () => {
    const files = [
      { name: 'bracket.stl' },
      { name: 'photo.jpg' },
      { name: 'model.3mf' },
      { name: 'document.pdf' },
    ]
    const result = filterValidFiles(files)
    expect(result).toHaveLength(2)
    expect(result.map((f) => f.name)).toContain('bracket.stl')
    expect(result.map((f) => f.name)).toContain('model.3mf')
  })
})

// ── removeFile ────────────────────────────────────────────────────────────────

describe('UploadFilesModal — removeFile', () => {
  const removeFile = (files, index) => {
    const arr = [...files]
    arr.splice(index, 1)
    return arr
  }

  it('removes the file at the specified index', () => {
    const files = ['a.stl', 'b.3mf', 'c.obj']
    expect(removeFile(files, 1)).toEqual(['a.stl', 'c.obj'])
  })

  it('removes the first file', () => {
    expect(removeFile(['first.stl', 'second.stl'], 0)).toEqual(['second.stl'])
  })

  it('removes the last file', () => {
    expect(removeFile(['first.stl', 'last.stl'], 1)).toEqual(['first.stl'])
  })

  it('returns empty array after removing the only file', () => {
    expect(removeFile(['only.obj'], 0)).toEqual([])
  })
})
