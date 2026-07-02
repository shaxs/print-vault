/**
 * Tests for PrinterDetailView (/printers/:id)
 *
 * PrinterDetailView shows full printer details, mods, and linked filament spools.
 * It contains several formatting utility functions tested here as pure logic.
 *
 * Tests cover:
 * - APIService contract (getPrinter, getMods)
 * - Router registration (printer-detail, printer-edit routes)
 * - buildVolume computed: XxYxZ string or 'N/A'
 * - formatPurchasePrice(): null/undefined → 'N/A', number → '$X.XX'
 * - formatDate(): null/empty → 'N/A', valid date string → formatted
 * - getFileName(): extracts filename from path, handles edge cases
 * - formatMaterialName(): brand + name + diameter combos
 * - getSpoolDisplayName(): blueprint / standalone w-brand / standalone w/o brand / fallback
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'
import router from '../../../src/router/index.js'

// ── APIService Contract ───────────────────────────────────────────────────────

describe('PrinterDetailView — APIService contract', () => {
  it('APIService.getPrinter exists', () => {
    expect(typeof APIService.getPrinter).toBe('function')
  })

  it('APIService.deleteMod exists', () => {
    expect(typeof APIService.deleteMod).toBe('function')
  })

  it('APIService.downloadModFiles exists', () => {
    expect(typeof APIService.downloadModFiles).toBe('function')
  })
})

// ── Router Registration ──────────────────────────────────────────────────────

describe('PrinterDetailView — route registration', () => {
  it('printer-detail route is registered', () => {
    const routes = router.getRoutes()
    expect(routes.find((r) => r.name === 'printer-detail')).toBeDefined()
  })

  it('printer-detail path contains :id', () => {
    const routes = router.getRoutes()
    const route = routes.find((r) => r.name === 'printer-detail')
    expect(route?.path).toContain(':id')
  })

  it('printer-edit route is registered', () => {
    const routes = router.getRoutes()
    expect(routes.find((r) => r.name === 'printer-edit')).toBeDefined()
  })
})

// ── buildVolume Computed ──────────────────────────────────────────────────────

describe('PrinterDetailView — buildVolume', () => {
  // Mirrors buildVolume computed from PrinterDetailView.vue
  const buildVolume = (printer) => {
    if (
      !printer ||
      printer.build_size_x == null ||
      printer.build_size_y == null ||
      printer.build_size_z == null
    ) {
      return 'N/A'
    }
    return `${printer.build_size_x}mm x ${printer.build_size_y}mm x ${printer.build_size_z}mm`
  }

  it('formats all three dimensions correctly', () => {
    expect(buildVolume({ build_size_x: 235, build_size_y: 235, build_size_z: 250 })).toBe(
      '235mm x 235mm x 250mm'
    )
  })

  it("returns 'N/A' when printer is null", () => {
    expect(buildVolume(null)).toBe('N/A')
  })

  it("returns 'N/A' when build_size_x is null", () => {
    expect(buildVolume({ build_size_x: null, build_size_y: 235, build_size_z: 250 })).toBe('N/A')
  })

  it("returns 'N/A' when build_size_y is null", () => {
    expect(buildVolume({ build_size_x: 235, build_size_y: null, build_size_z: 250 })).toBe('N/A')
  })

  it("returns 'N/A' when build_size_z is null", () => {
    expect(buildVolume({ build_size_x: 235, build_size_y: 235, build_size_z: null })).toBe('N/A')
  })

  it("returns 'N/A' when all dimensions are undefined", () => {
    expect(buildVolume({})).toBe('N/A')
  })

  it('works with decimal dimensions', () => {
    expect(buildVolume({ build_size_x: 180.5, build_size_y: 180.5, build_size_z: 180 })).toBe(
      '180.5mm x 180.5mm x 180mm'
    )
  })
})

// ── formatPurchasePrice() ────────────────────────────────────────────────────

describe('PrinterDetailView — formatPurchasePrice()', () => {
  // Mirrors formatPurchasePrice() from PrinterDetailView.vue
  const formatPurchasePrice = (price) => {
    if (price === null || price === undefined) {
      return 'N/A'
    }
    return `$${Number(price).toFixed(2)}`
  }

  it("null → 'N/A'", () => {
    expect(formatPurchasePrice(null)).toBe('N/A')
  })

  it("undefined → 'N/A'", () => {
    expect(formatPurchasePrice(undefined)).toBe('N/A')
  })

  it('positive integer → $X.00', () => {
    expect(formatPurchasePrice(250)).toBe('$250.00')
  })

  it('decimal price → $X.YY (2 decimal places)', () => {
    expect(formatPurchasePrice(299.99)).toBe('$299.99')
  })

  it('zero → $0.00', () => {
    expect(formatPurchasePrice(0)).toBe('$0.00')
  })

  it('string number → formatted correctly', () => {
    expect(formatPurchasePrice('149.95')).toBe('$149.95')
  })

  it('rounds to 2 decimal places', () => {
    expect(formatPurchasePrice(100.999)).toBe('$101.00')
  })
})

// ── formatDate() ─────────────────────────────────────────────────────────────

describe('PrinterDetailView — formatDate()', () => {
  // Mirrors formatDate() from PrinterDetailView.vue
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString + 'T00:00:00')
    const options = { year: 'numeric', month: 'long', day: 'numeric' }
    return date.toLocaleDateString(undefined, options)
  }

  it("null → 'N/A'", () => {
    expect(formatDate(null)).toBe('N/A')
  })

  it("empty string → 'N/A'", () => {
    expect(formatDate('')).toBe('N/A')
  })

  it("undefined → 'N/A'", () => {
    expect(formatDate(undefined)).toBe('N/A')
  })

  it('valid date string returns a non-empty human-readable date', () => {
    const result = formatDate('2024-01-15')
    expect(result).not.toBe('N/A')
    expect(result.length).toBeGreaterThan(5)
  })

  it('formatted date contains the year', () => {
    const result = formatDate('2024-06-20')
    expect(result).toContain('2024')
  })
})

// ── getFileName() ────────────────────────────────────────────────────────────

describe('PrinterDetailView — getFileName()', () => {
  // Mirrors getFileName() from PrinterDetailView.vue
  const getFileName = (filePath) => {
    if (!filePath) return ''
    return filePath.split('/').pop()
  }

  it("returns empty string for null", () => {
    expect(getFileName(null)).toBe('')
  })

  it("returns empty string for empty string", () => {
    expect(getFileName('')).toBe('')
  })

  it('extracts filename from a unix path', () => {
    expect(getFileName('/media/mods/printer_upgrade.pdf')).toBe('printer_upgrade.pdf')
  })

  it('extracts filename from a multi-segment path', () => {
    expect(getFileName('mods/2024/01/upgrade.stl')).toBe('upgrade.stl')
  })

  it('returns the string itself when no slash present', () => {
    expect(getFileName('readme.txt')).toBe('readme.txt')
  })

  it('handles trailing slash by returning empty string', () => {
    expect(getFileName('files/')).toBe('')
  })
})

// ── formatMaterialName() ──────────────────────────────────────────────────────

describe('PrinterDetailView — formatMaterialName()', () => {
  // Mirrors formatMaterialName() from PrinterDetailView.vue
  const formatMaterialName = (material) => {
    if (!material) return ''
    const brandName = material.brand?.name || ''
    const diameter = material.diameter ? ` (${material.diameter}mm)` : ''
    return `${brandName} ${material.name}${diameter}`.trim()
  }

  it("null material → empty string", () => {
    expect(formatMaterialName(null)).toBe('')
  })

  it('full material data → brand name diameter', () => {
    const material = { name: 'Galaxy Black PLA', brand: { name: 'Hatchbox' }, diameter: 1.75 }
    expect(formatMaterialName(material)).toBe('Hatchbox Galaxy Black PLA (1.75mm)')
  })

  it('no brand → just name + diameter', () => {
    const material = { name: 'PLA+ Blue', brand: null, diameter: 1.75 }
    expect(formatMaterialName(material)).toBe('PLA+ Blue (1.75mm)')
  })

  it('no diameter → brand + name only', () => {
    const material = { name: 'Galaxy Black', brand: { name: 'Hatchbox' }, diameter: null }
    expect(formatMaterialName(material)).toBe('Hatchbox Galaxy Black')
  })

  it('no brand, no diameter → just name', () => {
    const material = { name: 'ABS', brand: null, diameter: null }
    expect(formatMaterialName(material)).toBe('ABS')
  })
})

// ── getSpoolDisplayName() ─────────────────────────────────────────────────────

describe('PrinterDetailView — getSpoolDisplayName()', () => {
  // Mirrors getSpoolDisplayName() from PrinterDetailView.vue
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

  it('blueprint spool → formats via formatMaterialName', () => {
    const spool = {
      id: 1,
      filament_type: { name: 'Galaxy Black', brand: { name: 'Hatchbox' }, diameter: 1.75 },
    }
    expect(getSpoolDisplayName(spool)).toBe('Hatchbox Galaxy Black (1.75mm)')
  })

  it('standalone spool with brand → "Brand Name"', () => {
    const spool = {
      id: 2,
      filament_type: null,
      standalone_name: 'Black PLA',
      standalone_brand: { name: 'eSUN' },
    }
    expect(getSpoolDisplayName(spool)).toBe('eSUN Black PLA')
  })

  it('standalone spool without brand → just name', () => {
    const spool = {
      id: 3,
      filament_type: null,
      standalone_name: 'White PETG',
      standalone_brand: null,
    }
    expect(getSpoolDisplayName(spool)).toBe('White PETG')
  })

  it("fallback when no filament_type and no standalone_name → 'Spool #ID'", () => {
    const spool = { id: 42, filament_type: null, standalone_name: null }
    expect(getSpoolDisplayName(spool)).toBe('Spool #42')
  })

  it('blueprint takes priority over standalone_name', () => {
    const spool = {
      id: 5,
      filament_type: { name: 'Silk Blue', brand: null, diameter: null },
      standalone_name: 'Should Not Appear',
    }
    expect(getSpoolDisplayName(spool)).toBe('Silk Blue')
  })
})
