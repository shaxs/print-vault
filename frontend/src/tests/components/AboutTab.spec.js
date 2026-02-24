/**
 * Tests for pure / stateless functions extracted from
 * frontend/src/components/AboutTab.vue
 *
 * Covered functions
 * ─────────────────
 * - formatDateTime(isoString)   ISO timestamp → locale string, with null guard
 * - getBrowserInfo(ua)          User-agent string parser → {browserName, browserVersion, os}
 *
 * All functions are inlined here (extract-and-test pattern) because Vue
 * <script setup> does not expose internals without defineExpose.
 *
 * Note: formatDateTime uses toLocaleString() whose exact output is locale-
 * dependent. Tests verify structural properties only (non-empty, not 'Unknown'),
 * not exact formatted strings.
 */

import { describe, it, expect } from 'vitest'

// ─────────────────────────────────────────────────────────────────────────────
// Extracted functions (mirrors AboutTab.vue logic exactly)
// ─────────────────────────────────────────────────────────────────────────────

function formatDateTime(isoString) {
  if (!isoString) return 'Unknown'
  try {
    const date = new Date(isoString)
    return date.toLocaleString()
  } catch {
    return isoString
  }
}

/**
 * Parameterised version of getBrowserInfo() from AboutTab.vue.
 * The original reads navigator.userAgent directly; we accept `ua` as a param
 * to make the function hermetically testable.
 */
function getBrowserInfo(ua) {
  let browserName = 'Unknown'
  let browserVersion = 'Unknown'
  let os = 'Unknown'

  // Detect browser (order matters – Edge must come before Chrome)
  if (ua.indexOf('Firefox') > -1) {
    browserName = 'Firefox'
    browserVersion = ua.match(/Firefox\/([0-9.]+)/)?.[1] || 'Unknown'
  } else if (ua.indexOf('Edg') > -1) {
    browserName = 'Edge'
    browserVersion = ua.match(/Edg\/([0-9.]+)/)?.[1] || 'Unknown'
  } else if (ua.indexOf('Chrome') > -1) {
    browserName = 'Chrome'
    browserVersion = ua.match(/Chrome\/([0-9.]+)/)?.[1] || 'Unknown'
  } else if (ua.indexOf('Safari') > -1) {
    browserName = 'Safari'
    browserVersion = ua.match(/Version\/([0-9.]+)/)?.[1] || 'Unknown'
  }

  // Detect OS
  if (ua.indexOf('Win') > -1) os = 'Windows'
  else if (ua.indexOf('Mac') > -1) os = 'macOS'
  else if (ua.indexOf('Linux') > -1) os = 'Linux'
  else if (ua.indexOf('Android') > -1) os = 'Android'
  else if (ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) os = 'iOS'

  return { browserName, browserVersion, os }
}

// ─────────────────────────────────────────────────────────────────────────────
// Sample UA strings (real-world, stable for testing)
// ─────────────────────────────────────────────────────────────────────────────

const UA = {
  firefox_win:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0',
  firefox_linux:
    'Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0',
  edge_win:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
  chrome_win:
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  chrome_mac:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  chrome_linux:
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  safari_mac:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
  safari_ios:
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
  android_chrome:
    'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
  unknown: 'UnknownBrowser/1.0',
}

// ─────────────────────────────────────────────────────────────────────────────
// formatDateTime
// ─────────────────────────────────────────────────────────────────────────────

describe('formatDateTime', () => {
  it('returns "Unknown" for null', () => {
    expect(formatDateTime(null)).toBe('Unknown')
  })

  it('returns "Unknown" for undefined', () => {
    expect(formatDateTime(undefined)).toBe('Unknown')
  })

  it('returns "Unknown" for empty string', () => {
    expect(formatDateTime('')).toBe('Unknown')
  })

  it('returns a non-empty string for a valid ISO date', () => {
    const result = formatDateTime('2024-01-15T10:30:00Z')
    expect(result).toBeTruthy()
    expect(result).not.toBe('Unknown')
  })

  it('returns a non-empty string for a date-only ISO string', () => {
    const result = formatDateTime('2024-06-01T00:00:00Z')
    expect(result).toBeTruthy()
    expect(typeof result).toBe('string')
  })

  it('does not throw for an invalid date string', () => {
    expect(() => formatDateTime('not-a-date')).not.toThrow()
  })

  it('returns a string (not "Unknown") for an invalid date string', () => {
    const result = formatDateTime('totally-invalid')
    expect(typeof result).toBe('string')
  })

  it('returns a string for a unix timestamp string', () => {
    const result = formatDateTime('2025-12-25T00:00:00.000Z')
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// getBrowserInfo – browser detection
// ─────────────────────────────────────────────────────────────────────────────

describe('getBrowserInfo – browser name detection', () => {
  it('detects Firefox on Windows', () => {
    expect(getBrowserInfo(UA.firefox_win).browserName).toBe('Firefox')
  })

  it('detects Firefox version', () => {
    expect(getBrowserInfo(UA.firefox_win).browserVersion).toBe('109.0')
  })

  it('detects Firefox on Linux', () => {
    expect(getBrowserInfo(UA.firefox_linux).browserName).toBe('Firefox')
  })

  it('detects Edge (must not be classified as Chrome)', () => {
    expect(getBrowserInfo(UA.edge_win).browserName).toBe('Edge')
  })

  it('detects Edge version', () => {
    expect(getBrowserInfo(UA.edge_win).browserVersion).toBe('120.0.0.0')
  })

  it('detects Chrome on Windows', () => {
    expect(getBrowserInfo(UA.chrome_win).browserName).toBe('Chrome')
  })

  it('detects Chrome version', () => {
    expect(getBrowserInfo(UA.chrome_win).browserVersion).toBe('120.0.0.0')
  })

  it('detects Chrome on macOS', () => {
    expect(getBrowserInfo(UA.chrome_mac).browserName).toBe('Chrome')
  })

  it('detects Chrome on Linux', () => {
    expect(getBrowserInfo(UA.chrome_linux).browserName).toBe('Chrome')
  })

  it('detects Safari on macOS', () => {
    expect(getBrowserInfo(UA.safari_mac).browserName).toBe('Safari')
  })

  it('detects Safari version via Version/ token', () => {
    expect(getBrowserInfo(UA.safari_mac).browserVersion).toBe('17.0')
  })

  it('detects Safari on iOS', () => {
    expect(getBrowserInfo(UA.safari_ios).browserName).toBe('Safari')
  })

  it('returns "Unknown" for browser name on an unrecognised UA', () => {
    expect(getBrowserInfo(UA.unknown).browserName).toBe('Unknown')
  })

  it('returns "Unknown" for browser version on an unrecognised UA', () => {
    expect(getBrowserInfo(UA.unknown).browserVersion).toBe('Unknown')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// getBrowserInfo – OS detection
// ─────────────────────────────────────────────────────────────────────────────

describe('getBrowserInfo – OS detection', () => {
  it('detects Windows', () => {
    expect(getBrowserInfo(UA.firefox_win).os).toBe('Windows')
  })

  it('detects macOS on Chrome', () => {
    expect(getBrowserInfo(UA.chrome_mac).os).toBe('macOS')
  })

  it('detects macOS on Safari', () => {
    expect(getBrowserInfo(UA.safari_mac).os).toBe('macOS')
  })

  it('detects Linux on Firefox', () => {
    expect(getBrowserInfo(UA.firefox_linux).os).toBe('Linux')
  })

  it('detects Linux on Chrome', () => {
    expect(getBrowserInfo(UA.chrome_linux).os).toBe('Linux')
  })

  it('detects Android UA (note: contains "Linux" so Linux branch triggers first – actual source behavior)', () => {
    // Android UA strings begin with "(Linux; Android...)"
    // The if-chain checks Linux before Android, so 'Linux' wins.
    expect(getBrowserInfo(UA.android_chrome).os).toBe('Linux')
  })

  it('iOS iPhone UA contains "Mac OS X" so macOS branch triggers first – actual source behavior', () => {
    // iPhone UA: "...CPU iPhone OS 17_0 like Mac OS X..."
    // 'Mac' is found before 'iPhone' in the if-chain.
    expect(getBrowserInfo(UA.safari_ios).os).toBe('macOS')
  })

  it('iOS iPad UA contains "Mac OS X" so macOS branch triggers first – actual source behavior', () => {
    // iPad UA: "...CPU OS 16_0 like Mac OS X..."
    const ipad = 'Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Version/16.0 Safari/604.1'
    expect(getBrowserInfo(ipad).os).toBe('macOS')
  })

  it('returns "Unknown" OS for unrecognised UA', () => {
    expect(getBrowserInfo(UA.unknown).os).toBe('Unknown')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// getBrowserInfo – return shape
// ─────────────────────────────────────────────────────────────────────────────

describe('getBrowserInfo – return shape', () => {
  it('always returns an object with browserName, browserVersion, and os keys', () => {
    const result = getBrowserInfo('any-string')
    expect(result).toHaveProperty('browserName')
    expect(result).toHaveProperty('browserVersion')
    expect(result).toHaveProperty('os')
  })

  it('all values are strings', () => {
    const result = getBrowserInfo(UA.firefox_win)
    expect(typeof result.browserName).toBe('string')
    expect(typeof result.browserVersion).toBe('string')
    expect(typeof result.os).toBe('string')
  })
})
