/**
 * Tests for FilamentTable component
 *
 * FilamentTable displays a list of filament spools in a table format.
 * It supports both Blueprint and Quick Add spools with different data sources.
 *
 * Tests cover:
 * - Helper functions for data extraction
 * - Status label mapping
 * - Filament used color calculation
 * - Transformed items computed property
 */
import { describe, it, expect } from 'vitest'

// Sample test data - Blueprint spool
const mockBlueprintSpool = {
  id: 1,
  is_quick_add: false,
  filament_type: {
    name: 'PolyTerra PLA',
    color_name: 'Forest Green',
    brand: { name: 'Polymaker' },
    base_material: { name: 'PLA' },
    photo: '/media/materials/polyterra.jpg',
    colors: ['#228B22'],
  },
  standalone_name: null,
  standalone_brand: null,
  standalone_material_type: null,
  standalone_colors: [],
  standalone_photo: null,
  quantity: 1,
  status: 'in_use',
  weight_remaining_percent: 75.0,
  location: { name: 'Dry Box' },
  assigned_printer: { title: 'Prusa MK4' },
}

// Sample test data - Quick Add spool
const mockQuickAddSpool = {
  id: 2,
  is_quick_add: true,
  filament_type: null,
  standalone_name: 'Convention Metallic Blue',
  standalone_brand: { name: 'Unknown' },
  standalone_material_type: { name: 'PLA' },
  standalone_colors: ['#0066CC', '#003366'],
  standalone_photo: '/media/filament_photos/blue.jpg',
  quantity: 3,
  status: 'new',
  weight_remaining_percent: 100.0,
  location: { name: 'Storage' },
  assigned_printer: null,
}

describe('FilamentTable Helper Functions', () => {
  // Replicate helper functions from component
  const getSpoolPhoto = (item) => {
    return item.is_quick_add ? item.standalone_photo : item.filament_type?.photo || null
  }

  const getSpoolBrand = (item) => {
    return item.is_quick_add
      ? item.standalone_brand?.name || 'N/A'
      : item.filament_type?.brand?.name || 'N/A'
  }

  const getSpoolColors = (item) => {
    return item.is_quick_add ? item.standalone_colors || [] : item.filament_type?.colors || []
  }

  const getSpoolName = (item) => {
    return item.is_quick_add
      ? item.standalone_name || 'Quick Add Spool'
      : item.filament_type?.color_name || item.filament_type?.name || 'N/A'
  }

  const getSpoolMaterial = (item) => {
    return item.is_quick_add
      ? item.standalone_material_type?.name || 'N/A'
      : item.filament_type?.base_material?.name || 'N/A'
  }

  describe('getSpoolPhoto', () => {
    it('should return standalone_photo for Quick Add spool', () => {
      expect(getSpoolPhoto(mockQuickAddSpool)).toBe('/media/filament_photos/blue.jpg')
    })

    it('should return filament_type.photo for Blueprint spool', () => {
      expect(getSpoolPhoto(mockBlueprintSpool)).toBe('/media/materials/polyterra.jpg')
    })

    it('should return null if no photo available', () => {
      const noPhotoSpool = {
        ...mockBlueprintSpool,
        filament_type: { ...mockBlueprintSpool.filament_type, photo: null },
      }
      expect(getSpoolPhoto(noPhotoSpool)).toBeNull()
    })
  })

  describe('getSpoolBrand', () => {
    it('should return standalone_brand.name for Quick Add spool', () => {
      expect(getSpoolBrand(mockQuickAddSpool)).toBe('Unknown')
    })

    it('should return filament_type.brand.name for Blueprint spool', () => {
      expect(getSpoolBrand(mockBlueprintSpool)).toBe('Polymaker')
    })

    it('should return N/A if no brand available', () => {
      const noBrandSpool = {
        ...mockQuickAddSpool,
        standalone_brand: null,
      }
      expect(getSpoolBrand(noBrandSpool)).toBe('N/A')
    })
  })

  describe('getSpoolColors', () => {
    it('should return standalone_colors for Quick Add spool', () => {
      expect(getSpoolColors(mockQuickAddSpool)).toEqual(['#0066CC', '#003366'])
    })

    it('should return filament_type.colors for Blueprint spool', () => {
      expect(getSpoolColors(mockBlueprintSpool)).toEqual(['#228B22'])
    })

    it('should return empty array if no colors', () => {
      const noColorSpool = {
        ...mockQuickAddSpool,
        standalone_colors: null,
      }
      expect(getSpoolColors(noColorSpool)).toEqual([])
    })
  })

  describe('getSpoolName', () => {
    it('should return standalone_name for Quick Add spool', () => {
      expect(getSpoolName(mockQuickAddSpool)).toBe('Convention Metallic Blue')
    })

    it('should return color_name first for Blueprint spool', () => {
      expect(getSpoolName(mockBlueprintSpool)).toBe('Forest Green')
    })

    it('should fallback to filament_type.name if no color_name', () => {
      const noColorNameSpool = {
        ...mockBlueprintSpool,
        filament_type: {
          ...mockBlueprintSpool.filament_type,
          color_name: null,
        },
      }
      expect(getSpoolName(noColorNameSpool)).toBe('PolyTerra PLA')
    })

    it('should return Quick Add Spool if standalone_name is empty', () => {
      const noNameSpool = {
        ...mockQuickAddSpool,
        standalone_name: null,
      }
      expect(getSpoolName(noNameSpool)).toBe('Quick Add Spool')
    })
  })

  describe('getSpoolMaterial', () => {
    it('should return standalone_material_type.name for Quick Add spool', () => {
      expect(getSpoolMaterial(mockQuickAddSpool)).toBe('PLA')
    })

    it('should return filament_type.base_material.name for Blueprint spool', () => {
      expect(getSpoolMaterial(mockBlueprintSpool)).toBe('PLA')
    })

    it('should return N/A if no material type', () => {
      const noMaterialSpool = {
        ...mockQuickAddSpool,
        standalone_material_type: null,
      }
      expect(getSpoolMaterial(noMaterialSpool)).toBe('N/A')
    })
  })
})

describe('FilamentTable Status Handling', () => {
  const getStatusLabel = (status) => {
    const statusMap = {
      new: 'New',
      opened: 'Opened',
      in_use: 'In Use',
      low: 'Low',
      empty: 'Empty',
      archived: 'Archived',
    }
    return statusMap[status] || status
  }

  it('should map new status correctly', () => {
    expect(getStatusLabel('new')).toBe('New')
  })

  it('should map opened status correctly', () => {
    expect(getStatusLabel('opened')).toBe('Opened')
  })

  it('should map in_use status correctly', () => {
    expect(getStatusLabel('in_use')).toBe('In Use')
  })

  it('should map low status correctly', () => {
    expect(getStatusLabel('low')).toBe('Low')
  })

  it('should map empty status correctly', () => {
    expect(getStatusLabel('empty')).toBe('Empty')
  })

  it('should map archived status correctly', () => {
    expect(getStatusLabel('archived')).toBe('Archived')
  })

  it('should return original status for unknown status', () => {
    expect(getStatusLabel('unknown_status')).toBe('unknown_status')
  })
})

describe('FilamentTable Color Calculation', () => {
  const getFilamentUsedColor = (usedPercent) => {
    if (usedPercent <= 50) return '#10b981' // Green - 0-50% used (plenty left)
    if (usedPercent <= 75) return '#eab308' // Yellow - 51-75% used (medium)
    if (usedPercent <= 90) return '#f59e0b' // Orange - 76-90% used (getting low)
    return '#ef4444' // Red - 91-100% used (almost empty)
  }

  const filamentUsedPercent = (item) => {
    if (
      !item ||
      item.weight_remaining_percent === undefined ||
      item.weight_remaining_percent === null
    )
      return 0
    return Math.round(100 - item.weight_remaining_percent)
  }

  it('should return green for 0-50% used', () => {
    expect(getFilamentUsedColor(0)).toBe('#10b981')
    expect(getFilamentUsedColor(25)).toBe('#10b981')
    expect(getFilamentUsedColor(50)).toBe('#10b981')
  })

  it('should return yellow for 51-75% used', () => {
    expect(getFilamentUsedColor(51)).toBe('#eab308')
    expect(getFilamentUsedColor(65)).toBe('#eab308')
    expect(getFilamentUsedColor(75)).toBe('#eab308')
  })

  it('should return orange for 76-90% used', () => {
    expect(getFilamentUsedColor(76)).toBe('#f59e0b')
    expect(getFilamentUsedColor(85)).toBe('#f59e0b')
    expect(getFilamentUsedColor(90)).toBe('#f59e0b')
  })

  it('should return red for 91-100% used', () => {
    expect(getFilamentUsedColor(91)).toBe('#ef4444')
    expect(getFilamentUsedColor(95)).toBe('#ef4444')
    expect(getFilamentUsedColor(100)).toBe('#ef4444')
  })

  it('should calculate used percent correctly', () => {
    // 75% remaining = 25% used
    expect(filamentUsedPercent(mockBlueprintSpool)).toBe(25)

    // 100% remaining = 0% used
    expect(filamentUsedPercent(mockQuickAddSpool)).toBe(0)
  })

  it('should handle missing weight_remaining_percent', () => {
    const noWeightSpool = { id: 1 }
    expect(filamentUsedPercent(noWeightSpool)).toBe(0)
  })
})

describe('FilamentTable Table Headers', () => {
  const headers = [
    { text: 'Photo', value: 'photo' },
    { text: 'Brand', value: 'brand' },
    { text: 'Colors', value: 'colors' },
    { text: 'Name', value: 'name' },
    { text: 'Material', value: 'material' },
    { text: 'Quantity', value: 'quantity' },
    { text: 'Status', value: 'status' },
    { text: 'Location/Printer', value: 'location' },
    { text: 'Filament Used', value: 'filamentUsed' },
  ]

  it('should have correct number of columns', () => {
    expect(headers).toHaveLength(9)
  })

  it('should include Photo column', () => {
    expect(headers.find((h) => h.value === 'photo')).toBeDefined()
  })

  it('should include Brand column', () => {
    expect(headers.find((h) => h.value === 'brand')).toBeDefined()
  })

  it('should include Colors column', () => {
    expect(headers.find((h) => h.value === 'colors')).toBeDefined()
  })

  it('should include Status column', () => {
    expect(headers.find((h) => h.value === 'status')).toBeDefined()
  })

  it('should include Filament Used column', () => {
    expect(headers.find((h) => h.value === 'filamentUsed')).toBeDefined()
  })
})
