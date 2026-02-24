/**
 * Tests for pure functions extracted from TrackerList.vue.
 *
 * formatDate(dateString)          — formats a date string for display
 * getProgressColor(percentage)    — maps progress % to a hex colour
 * getTrackerProgressStyle(item)   — builds a CSS style object for progress bars
 */
import { describe, it, expect } from 'vitest'

// ─── Pure function implementations (mirrors TrackerList.vue) ──────────────────

function formatDate(dateString) {
  if (!dateString) return ''
  // Parse date as local time by adding 'T00:00:00' to force local timezone
  const date = new Date(dateString + 'T00:00:00')
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function getProgressColor(percentage) {
  if (percentage === 0) return '#64748b' // gray
  if (percentage < 50) return '#ef4444' // red
  if (percentage < 100) return '#f59e0b' // orange
  return '#10b981' // green
}

function getTrackerProgressStyle(item) {
  const percentage = item?.progress_percentage || 0
  return {
    width: `${percentage}%`,
    height: '100%',
    backgroundColor: getProgressColor(percentage),
    transition: 'width 0.3s ease',
  }
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('TrackerList – formatDate', () => {
  it('returns empty string for null', () => {
    expect(formatDate(null)).toBe('')
  })

  it('returns empty string for undefined', () => {
    expect(formatDate(undefined)).toBe('')
  })

  it('returns empty string for empty string', () => {
    expect(formatDate('')).toBe('')
  })

  it('returns a non-empty string for a valid date', () => {
    const result = formatDate('2024-06-15')
    expect(result).toBeTruthy()
    expect(typeof result).toBe('string')
  })

  it('includes the year from the date string', () => {
    const result = formatDate('2024-06-15')
    expect(result).toContain('2024')
  })

  it('formats with en-US month abbreviation', () => {
    const result = formatDate('2024-01-01')
    expect(result).toContain('Jan')
  })

  it('formats with day number', () => {
    const result = formatDate('2024-03-20')
    expect(result).toContain('20')
  })

  it('appends T00:00:00 to avoid UTC/local-timezone shift', () => {
    // A date like '2024-12-31' should still show Dec, not potentially Jan 1
    const result = formatDate('2024-12-31')
    expect(result).toContain('Dec')
    expect(result).toContain('2024')
  })
})

describe('TrackerList – getProgressColor', () => {
  it('returns gray for 0%', () => {
    expect(getProgressColor(0)).toBe('#64748b')
  })

  it('returns red for 1% (below 50)', () => {
    expect(getProgressColor(1)).toBe('#ef4444')
  })

  it('returns red for 25%', () => {
    expect(getProgressColor(25)).toBe('#ef4444')
  })

  it('returns red for 49%', () => {
    expect(getProgressColor(49)).toBe('#ef4444')
  })

  it('returns orange for 50%', () => {
    expect(getProgressColor(50)).toBe('#f59e0b')
  })

  it('returns orange for 75%', () => {
    expect(getProgressColor(75)).toBe('#f59e0b')
  })

  it('returns orange for 99%', () => {
    expect(getProgressColor(99)).toBe('#f59e0b')
  })

  it('returns green for 100%', () => {
    expect(getProgressColor(100)).toBe('#10b981')
  })
})

describe('TrackerList – getTrackerProgressStyle', () => {
  it('returns an object with width set to percentage', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 60 })
    expect(style.width).toBe('60%')
  })

  it('height is always "100%"', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 30 })
    expect(style.height).toBe('100%')
  })

  it('includes a CSS transition property', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 50 })
    expect(style.transition).toBeTruthy()
  })

  it('backgroundColor matches getProgressColor result', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 100 })
    expect(style.backgroundColor).toBe(getProgressColor(100))
  })

  it('defaults to 0% when progress_percentage is missing', () => {
    const style = getTrackerProgressStyle({})
    expect(style.width).toBe('0%')
    expect(style.backgroundColor).toBe('#64748b')
  })

  it('defaults to 0% for null item', () => {
    const style = getTrackerProgressStyle(null)
    expect(style.width).toBe('0%')
  })

  it('uses orange color for progress between 50 and 99', () => {
    const style = getTrackerProgressStyle({ progress_percentage: 72 })
    expect(style.backgroundColor).toBe('#f59e0b')
  })
})
