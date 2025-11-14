/**
 * Unit tests for APIService
 *
 * Tests that all required methods exist and have correct interfaces.
 * These tests validate the API contract without needing a backend.
 */
import { describe, it, expect } from 'vitest'
import APIService from '../../../src/services/APIService.js'

describe('APIService', () => {
  describe('Inventory Items', () => {
    it('should have getInventoryItems method', () => {
      expect(typeof APIService.getInventoryItems).toBe('function')
    })

    it('should have getInventoryItem method', () => {
      expect(typeof APIService.getInventoryItem).toBe('function')
    })

    it('should have createInventoryItem method', () => {
      expect(typeof APIService.createInventoryItem).toBe('function')
    })

    it('should have updateInventoryItem method', () => {
      expect(typeof APIService.updateInventoryItem).toBe('function')
    })

    it('should have deleteInventoryItem method', () => {
      expect(typeof APIService.deleteInventoryItem).toBe('function')
    })
  })

  describe('Trackers', () => {
    it('should have getTrackers method', () => {
      expect(typeof APIService.getTrackers).toBe('function')
    })

    it('should have getTracker method', () => {
      expect(typeof APIService.getTracker).toBe('function')
    })

    it('should have createTracker method', () => {
      expect(typeof APIService.createTracker).toBe('function')
    })

    it('should have updateTracker method', () => {
      expect(typeof APIService.updateTracker).toBe('function')
    })

    it('should have deleteTracker method', () => {
      expect(typeof APIService.deleteTracker).toBe('function')
    })

    it('should have downloadTrackerFiles method', () => {
      expect(typeof APIService.downloadTrackerFiles).toBe('function')
    })
  })

  describe('Tracker Files', () => {
    it('should have getTrackerFiles method', () => {
      expect(typeof APIService.getTrackerFiles).toBe('function')
    })

    it('should have updateTrackerFileStatus method', () => {
      expect(typeof APIService.updateTrackerFileStatus).toBe('function')
    })

    it('should have deleteTrackerFile method', () => {
      expect(typeof APIService.deleteTrackerFile).toBe('function')
    })
  })

  describe('Projects', () => {
    it('should have getProjects method', () => {
      expect(typeof APIService.getProjects).toBe('function')
    })

    it('should have getProject method', () => {
      expect(typeof APIService.getProject).toBe('function')
    })

    it('should have createProject method', () => {
      expect(typeof APIService.createProject).toBe('function')
    })

    it('should have updateProject method', () => {
      expect(typeof APIService.updateProject).toBe('function')
    })

    it('should have deleteProject method', () => {
      expect(typeof APIService.deleteProject).toBe('function')
    })

    it('should have downloadProjectFiles method', () => {
      expect(typeof APIService.downloadProjectFiles).toBe('function')
    })
  })

  describe('Printers', () => {
    it('should have getPrinters method', () => {
      expect(typeof APIService.getPrinters).toBe('function')
    })

    it('should have getPrinter method', () => {
      expect(typeof APIService.getPrinter).toBe('function')
    })

    it('should have createPrinter method', () => {
      expect(typeof APIService.createPrinter).toBe('function')
    })

    it('should have updatePrinter method', () => {
      expect(typeof APIService.updatePrinter).toBe('function')
    })

    it('should have deletePrinter method', () => {
      expect(typeof APIService.deletePrinter).toBe('function')
    })
  })

  describe('Lookups', () => {
    it('should have getBrands method', () => {
      expect(typeof APIService.getBrands).toBe('function')
    })

    it('should have getPartTypes method', () => {
      expect(typeof APIService.getPartTypes).toBe('function')
    })

    it('should have getLocations method', () => {
      expect(typeof APIService.getLocations).toBe('function')
    })

    it('should have getMaterials method', () => {
      expect(typeof APIService.getMaterials).toBe('function')
    })

    it('should have getVendors method', () => {
      expect(typeof APIService.getVendors).toBe('function')
    })
  })

  describe('GitHub Integration', () => {
    it('should have crawlGitHub method', () => {
      expect(typeof APIService.crawlGitHub).toBe('function')
    })
  })

  describe('Mods', () => {
    it('should have getMod method', () => {
      expect(typeof APIService.getMod).toBe('function')
    })

    it('should have createMod method', () => {
      expect(typeof APIService.createMod).toBe('function')
    })

    it('should have updateMod method', () => {
      expect(typeof APIService.updateMod).toBe('function')
    })

    it('should have deleteMod method', () => {
      expect(typeof APIService.deleteMod).toBe('function')
    })
  })
})
