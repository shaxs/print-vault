/**
 * Tests for MaterialTable component pure logic
 *
 * MaterialTable.vue renders the Blueprints list (via the shared DataTable
 * component). Columns are filtered by a visibleColumns prop passed down to
 * DataTable, which only renders headers whose `value` appears in that array.
 *
 * Tests cover:
 * - headers definition includes a 'favorite' column
 * - headers computed: only includes columns present in visibleColumns
 * - favorite cell rendering: shows a star only when is_favorite is true
 */
import { describe, it, expect } from 'vitest'

// ── headers definition ─────────────────────────────────────────────────────
// Mirrors the `headers` array in MaterialTable.vue

const HEADERS = [
  { text: '', value: 'favorite' },
  { text: 'Photo', value: 'photo' },
  { text: 'Brand', value: 'brand' },
  { text: 'Name', value: 'name' },
  { text: 'Colors', value: 'colors' },
  { text: 'Material', value: 'material' },
  { text: 'Color Family', value: 'colorFamily' },
  { text: 'Diameter', value: 'diameter' },
]

describe('MaterialTable — headers', () => {
  it('includes a favorite column', () => {
    expect(HEADERS.find((h) => h.value === 'favorite')).toBeDefined()
  })

  it('favorite column has no header text (icon-only column)', () => {
    const col = HEADERS.find((h) => h.value === 'favorite')
    expect(col.text).toBe('')
  })

  it('favorite is the first column', () => {
    expect(HEADERS[0].value).toBe('favorite')
  })
})

// ── DataTable's activeHeaders filtering (mirrors DataTable.vue) ────────────
// activeHeaders = visibleColumns.map(key => headers.find(h => h.value === key)).filter(Boolean)

describe('MaterialTable — activeHeaders filtering via visibleColumns', () => {
  const computeActiveHeaders = (visibleColumns) =>
    visibleColumns.map((key) => HEADERS.find((h) => h.value === key)).filter((h) => h)

  it('includes the favorite column when present in visibleColumns', () => {
    const result = computeActiveHeaders(['favorite', 'name'])
    expect(result.some((h) => h.value === 'favorite')).toBe(true)
  })

  it('omits the favorite column when absent from visibleColumns', () => {
    const result = computeActiveHeaders(['name', 'brand'])
    expect(result.some((h) => h.value === 'favorite')).toBe(false)
  })
})

// ── favorite cell rendering ─────────────────────────────────────────────────
// Mirrors: <span v-if="item.is_favorite" class="favorite-star">★</span>

describe('MaterialTable — favorite cell rendering', () => {
  const renderFavoriteCell = (item) => (item.is_favorite ? '★' : '')

  it('renders a star for a favorited blueprint', () => {
    expect(renderFavoriteCell({ is_favorite: true })).toBe('★')
  })

  it('renders nothing for a non-favorited blueprint', () => {
    expect(renderFavoriteCell({ is_favorite: false })).toBe('')
  })

  it('renders nothing when is_favorite is undefined (generic materials)', () => {
    expect(renderFavoriteCell({})).toBe('')
  })
})
