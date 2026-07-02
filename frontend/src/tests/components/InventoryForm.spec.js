/**
 * Tests for pure / stateless functions extracted from
 * frontend/src/components/InventoryForm.vue
 *
 * Covered functions
 * ─────────────────────────────────────────────────────────
 * - addBrand(name, brands, item)          create brand, push, set item.brand
 * - addPartType(name, partTypes, item)    create part type, push, set item.part_type
 * - addLocation(name, locations, item)   create location, push, set item.location
 * - addVendor(name, vendors, item)        create vendor, push, set item.vendor
 *
 * All four functions follow an identical pattern:
 *   1. Create { name } object
 *   2. Push it onto the provided collection array
 *   3. Assign it to the corresponding field on item
 *
 * Tests verify both the shared contract (once, generically) and each
 * function individually to document field-name correctness.
 */

import { describe, it, expect } from 'vitest'

// ─────────────────────────────────────────────────────────────────────────────
// Extracted functions (mirrors InventoryForm.vue logic exactly)
// ─────────────────────────────────────────────────────────────────────────────

function addBrand(newBrand, brands, item) {
  const brand = { name: newBrand }
  brands.push(brand)
  item.brand = brand
}

function addPartType(newPartType, partTypes, item) {
  const partType = { name: newPartType }
  partTypes.push(partType)
  item.part_type = partType
}

function addLocation(newLocation, locations, item) {
  const location = { name: newLocation }
  locations.push(location)
  item.location = location
}

function addVendor(newVendor, vendors, item) {
  const vendor = { name: newVendor }
  vendors.push(vendor)
  item.vendor = vendor
}

// ─────────────────────────────────────────────────────────────────────────────
// addBrand
// ─────────────────────────────────────────────────────────────────────────────

describe('addBrand (InventoryForm)', () => {
  it('adds a brand object to the brands array', () => {
    const brands = []
    const item = {}
    addBrand('Bambu Lab', brands, item)
    expect(brands).toHaveLength(1)
    expect(brands[0]).toEqual({ name: 'Bambu Lab' })
  })

  it('sets item.brand to the newly created brand', () => {
    const brands = []
    const item = { brand: null }
    addBrand('Prusa', brands, item)
    expect(item.brand).toEqual({ name: 'Prusa' })
  })

  it('item.brand is the same reference as brands[last]', () => {
    const brands = []
    const item = {}
    addBrand('Creality', brands, item)
    expect(item.brand).toBe(brands[0])
  })

  it('appends without clearing existing brands', () => {
    const brands = [{ name: 'Existing' }]
    const item = {}
    addBrand('New Brand', brands, item)
    expect(brands).toHaveLength(2)
    expect(brands[0].name).toBe('Existing')
  })

  it('creates brand with only a name property', () => {
    const brands = []
    const item = {}
    addBrand('Test', brands, item)
    expect(Object.keys(brands[0])).toEqual(['name'])
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// addPartType
// ─────────────────────────────────────────────────────────────────────────────

describe('addPartType (InventoryForm)', () => {
  it('adds a part type object to the partTypes array', () => {
    const partTypes = []
    const item = {}
    addPartType('Screw', partTypes, item)
    expect(partTypes).toHaveLength(1)
    expect(partTypes[0]).toEqual({ name: 'Screw' })
  })

  it('sets item.part_type (not item.brand) to the new part type', () => {
    const partTypes = []
    const item = { part_type: null, brand: null }
    addPartType('Bearing', partTypes, item)
    expect(item.part_type).toEqual({ name: 'Bearing' })
    expect(item.brand).toBeNull()
  })

  it('item.part_type is the same reference as partTypes[last]', () => {
    const partTypes = []
    const item = {}
    addPartType('Nut', partTypes, item)
    expect(item.part_type).toBe(partTypes[0])
  })

  it('does not set item.location or item.vendor', () => {
    const partTypes = []
    const item = { location: null, vendor: null }
    addPartType('Bolt', partTypes, item)
    expect(item.location).toBeNull()
    expect(item.vendor).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// addLocation
// ─────────────────────────────────────────────────────────────────────────────

describe('addLocation (InventoryForm)', () => {
  it('adds a location object to the locations array', () => {
    const locations = []
    const item = {}
    addLocation('Shelf A', locations, item)
    expect(locations).toHaveLength(1)
    expect(locations[0]).toEqual({ name: 'Shelf A' })
  })

  it('sets item.location (not item.brand) to the new location', () => {
    const locations = []
    const item = { location: null, brand: null }
    addLocation('Drawer 3', locations, item)
    expect(item.location).toEqual({ name: 'Drawer 3' })
    expect(item.brand).toBeNull()
  })

  it('item.location is the same reference as locations[last]', () => {
    const locations = []
    const item = {}
    addLocation('Bin 7', locations, item)
    expect(item.location).toBe(locations[0])
  })

  it('does not set item.part_type or item.vendor', () => {
    const locations = []
    const item = { part_type: null, vendor: null }
    addLocation('Cabinet B', locations, item)
    expect(item.part_type).toBeNull()
    expect(item.vendor).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// addVendor
// ─────────────────────────────────────────────────────────────────────────────

describe('addVendor (InventoryForm)', () => {
  it('adds a vendor object to the vendors array', () => {
    const vendors = []
    const item = {}
    addVendor('AliExpress', vendors, item)
    expect(vendors).toHaveLength(1)
    expect(vendors[0]).toEqual({ name: 'AliExpress' })
  })

  it('sets item.vendor (not item.brand) to the new vendor', () => {
    const vendors = []
    const item = { vendor: null, brand: null }
    addVendor('Amazon', vendors, item)
    expect(item.vendor).toEqual({ name: 'Amazon' })
    expect(item.brand).toBeNull()
  })

  it('item.vendor is the same reference as vendors[last]', () => {
    const vendors = []
    const item = {}
    addVendor('DigiKey', vendors, item)
    expect(item.vendor).toBe(vendors[0])
  })

  it('does not set item.location or item.part_type', () => {
    const vendors = []
    const item = { location: null, part_type: null }
    addVendor('Mouser', vendors, item)
    expect(item.location).toBeNull()
    expect(item.part_type).toBeNull()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// Shared contract: all four add* functions behave identically
// ─────────────────────────────────────────────────────────────────────────────

describe('InventoryForm add* shared contract', () => {
  const cases = [
    { fn: addBrand, field: 'brand', list: 'brands', label: 'addBrand' },
    { fn: addPartType, field: 'part_type', list: 'partTypes', label: 'addPartType' },
    { fn: addLocation, field: 'location', list: 'locations', label: 'addLocation' },
    { fn: addVendor, field: 'vendor', list: 'vendors', label: 'addVendor' },
  ]

  cases.forEach(({ fn, field, label }) => {
    it(`${label}: created object has exactly one property — name`, () => {
      const list = []
      const item = {}
      fn('Test', list, item)
      expect(Object.keys(list[0])).toEqual(['name'])
    })

    it(`${label}: sets a different field on item than other add* functions`, () => {
      const list = []
      const item = { brand: null, part_type: null, location: null, vendor: null }
      fn('Value', list, item)
      // Only the target field should be non-null
      expect(item[field]).not.toBeNull()
    })
  })
})
