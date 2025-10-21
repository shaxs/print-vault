/**
 * Centralized filename parsing utilities for smart defaults
 *
 * This module provides consistent filename parsing across the application
 * for extracting quantity, color, and other metadata from 3D printing filenames.
 */

/**
 * Parse filename to extract smart defaults for quantity, color, and material
 *
 * Supported patterns:
 * - Quantity: _x2, _x4, (x3), [x5], etc. - anywhere in filename
 * - Color prefixes:
 *   - [a]_ or (a)_ = Accent
 *   - [d]_ or (d)_ = Multicolor
 *   - [b]_ or (b)_ = Other
 *   - No prefix = Primary (default)
 *
 * @param {string} filename - The filename to parse
 * @param {string} defaultMaterial - Default material if not detected (optional)
 * @returns {Object} { quantity: number, color: string, material: string }
 *
 * @example
 * parseFilename('[a]_bracket_x2.stl')
 * // Returns: { quantity: 2, color: 'Accent', material: 'ABS' }
 *
 * parseFilename('tool_(x3).stl')
 * // Returns: { quantity: 3, color: 'Primary', material: 'ABS' }
 */
export function parseFilename(filename, defaultMaterial = 'ABS') {
  const defaults = {
    quantity: 1,
    color: 'Primary',
    material: defaultMaterial,
  }

  // Parse quantity from filename
  // Supports: _x2, _x4, (x3), [x5], x4 (with space), etc.
  // Look for patterns like:
  // - _x3, _x10 (underscore prefix)
  // - (x3), (x10) (parentheses)
  // - [x3], [x10] (brackets)
  // - " x4", " x10" (space before x)
  // Pattern matches: underscore, space, open paren, or open bracket before 'x'
  const qtyMatch = filename.match(/[\s_([x]x(\d+)/i)
  if (qtyMatch) {
    defaults.quantity = parseInt(qtyMatch[1])
  }

  // Parse color from bracket or parenthesis prefix at start of filename
  // Supports both underscore and space after the bracket/paren
  // [a]_ or (a)_ or [a] or (a) = Accent
  if (filename.match(/^[[(][aA][\])]\s*_?\s*/)) {
    defaults.color = 'Accent'
  }
  // [b]_ or (b)_ or [b] or (b) = Other (legacy support)
  else if (filename.match(/^[[(][bB][\])]\s*_?\s*/)) {
    defaults.color = 'Other'
  }
  // (d)_ or [d]_ or (d) or [d] = Multicolor
  else if (filename.match(/^[[(][dD][\])]\s*_?\s*/)) {
    defaults.color = 'Multicolor'
  }
  // No prefix = Primary (already set as default)

  return defaults
}

/**
 * Apply smart defaults to a file object
 * Modifies the file object in place
 *
 * @param {Object} file - File object with at least a 'name' property
 * @param {string} defaultMaterial - Default material if not detected (optional)
 * @returns {Object} The modified file object
 */
export function applySmartDefaults(file, defaultMaterial = 'ABS') {
  const defaults = parseFilename(file.name, defaultMaterial)

  // Only apply if not already set
  if (!file.color) file.color = defaults.color
  if (!file.material) file.material = defaults.material
  if (!file.quantity || file.quantity === 1) file.quantity = defaults.quantity

  return file
}

/**
 * Apply smart defaults to an array of files
 * Modifies the files in place
 *
 * @param {Array} files - Array of file objects
 * @param {string} defaultMaterial - Default material if not detected (optional)
 * @returns {Array} The modified files array
 */
export function applySmartDefaultsBatch(files, defaultMaterial = 'ABS') {
  return files.map((file) => applySmartDefaults(file, defaultMaterial))
}

/**
 * Get quantity patterns that we recognize
 * Useful for documentation and validation
 *
 * @returns {Array<Object>} Array of pattern examples
 */
export function getSupportedQuantityPatterns() {
  return [
    { pattern: '_x2', description: 'Underscore prefix (e.g., bracket_x2.stl)' },
    { pattern: '(x3)', description: 'Parentheses (e.g., tool_(x3).stl)' },
    { pattern: '[x4]', description: 'Brackets (e.g., part[x4].stl)' },
  ]
}

/**
 * Get color patterns that we recognize
 * Useful for documentation and validation
 *
 * @returns {Array<Object>} Array of pattern examples
 */
export function getSupportedColorPatterns() {
  return [
    { pattern: '[a]_', color: 'Accent', description: 'Bracket prefix (e.g., [a]_bracket.stl)' },
    { pattern: '(a)_', color: 'Accent', description: 'Parenthesis prefix (e.g., (a)_bracket.stl)' },
    { pattern: '[d]_', color: 'Multicolor', description: 'Bracket prefix (e.g., [d]_body.stl)' },
    {
      pattern: '(d)_',
      color: 'Multicolor',
      description: 'Parenthesis prefix (e.g., (d)_body.stl)',
    },
    { pattern: '[b]_', color: 'Other', description: 'Bracket prefix (e.g., [b]_part.stl)' },
    { pattern: '(b)_', color: 'Other', description: 'Parenthesis prefix (e.g., (b)_part.stl)' },
    { pattern: 'none', color: 'Primary', description: 'No prefix = Primary color' },
  ]
}
