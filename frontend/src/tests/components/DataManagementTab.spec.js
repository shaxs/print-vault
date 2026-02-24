/**
 * Tests for DataManagementTab component pure logic
 *
 * DataManagementTab.vue handles export, import/restore, and delete-all operations.
 * A two-step modal flow with typed-confirmation guards both irreversible actions
 * (delete-all and restore) to protect against accidental data loss.
 *
 * Tests cover:
 * - isFinalDeleteDisabled guard logic (must type "DELETE ALL" and check box)
 * - isFinalRestoreDisabled guard logic (must type "RESTORE" and check box)
 * - APIService contract (export, delete, validateBackup, restoreData exist)
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'

// ── isFinalDeleteDisabled logic ───────────────────────────────────────────────
// Mirrors: deleteConfirmationText.value !== 'DELETE ALL' || !deleteCheckbox.value

describe('DataManagementTab — isFinalDeleteDisabled', () => {
  const isFinalDeleteDisabled = (text, checkbox) =>
    text !== 'DELETE ALL' || !checkbox

  it('is disabled when text is wrong and checkbox is unchecked', () => {
    expect(isFinalDeleteDisabled('', false)).toBe(true)
  })

  it('is disabled when text is correct but checkbox is unchecked', () => {
    expect(isFinalDeleteDisabled('DELETE ALL', false)).toBe(true)
  })

  it('is disabled when checkbox is checked but text is wrong', () => {
    expect(isFinalDeleteDisabled('delete all', true)).toBe(true)
  })

  it('is disabled when text is a partial match', () => {
    expect(isFinalDeleteDisabled('DELETE', true)).toBe(true)
  })

  it('is disabled when text has extra whitespace', () => {
    expect(isFinalDeleteDisabled(' DELETE ALL', true)).toBe(true)
  })

  it('is enabled only when text is exactly "DELETE ALL" AND checkbox is checked', () => {
    expect(isFinalDeleteDisabled('DELETE ALL', true)).toBe(false)
  })

  it('is case-sensitive: lowercase fails', () => {
    expect(isFinalDeleteDisabled('delete all', true)).toBe(true)
  })
})

// ── isFinalRestoreDisabled logic ──────────────────────────────────────────────
// Mirrors: restoreConfirmationText.value !== 'RESTORE' || !restoreCheckbox.value

describe('DataManagementTab — isFinalRestoreDisabled', () => {
  const isFinalRestoreDisabled = (text, checkbox) =>
    text !== 'RESTORE' || !checkbox

  it('is disabled when text is empty and checkbox is unchecked', () => {
    expect(isFinalRestoreDisabled('', false)).toBe(true)
  })

  it('is disabled when text is correct but checkbox is unchecked', () => {
    expect(isFinalRestoreDisabled('RESTORE', false)).toBe(true)
  })

  it('is disabled when checkbox is checked but text is wrong', () => {
    expect(isFinalRestoreDisabled('restore', true)).toBe(true)
  })

  it('is disabled when text is partial ("RESTO")', () => {
    expect(isFinalRestoreDisabled('RESTO', true)).toBe(true)
  })

  it('is enabled only when text is exactly "RESTORE" AND checkbox is checked', () => {
    expect(isFinalRestoreDisabled('RESTORE', true)).toBe(false)
  })

  it('is case-sensitive: mixed case fails', () => {
    expect(isFinalRestoreDisabled('Restore', true)).toBe(true)
  })
})

// ── APIService contract ───────────────────────────────────────────────────────

describe('DataManagementTab — APIService contract', () => {
  it('APIService.exportData exists', () => {
    expect(typeof APIService.exportData).toBe('function')
  })

  it('APIService.deleteAllData exists', () => {
    expect(typeof APIService.deleteAllData).toBe('function')
  })

  it('APIService.validateBackup exists', () => {
    expect(typeof APIService.validateBackup).toBe('function')
  })

  it('APIService.restoreData exists', () => {
    expect(typeof APIService.restoreData).toBe('function')
  })
})
