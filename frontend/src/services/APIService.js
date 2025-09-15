// src/services/APIService.js
import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api/',
})

export default {
  // Inventory Items
  getInventoryItems(params) {
    return apiClient.get('inventoryitems/', { params })
  },
  getInventoryItem(id) {
    return apiClient.get(`inventoryitems/${id}/`)
  },
  createInventoryItem(formData) {
    return apiClient.post('inventoryitems/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  updateInventoryItem(id, formData) {
    return apiClient.put(`inventoryitems/${id}/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteInventoryItem(id) {
    return apiClient.delete(`inventoryitems/${id}/`)
  },

  // Printers
  getPrinters(params) {
    return apiClient.get('printers/', { params })
  },
  getPrinter(id) {
    return apiClient.get(`printers/${id}/`)
  },
  createPrinter(formData) {
    return apiClient.post('printers/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  updatePrinter(id, data) {
    return apiClient.patch(`printers/${id}/`, data)
  },
  deletePrinter(id) {
    return apiClient.delete(`printers/${id}/`)
  },

  // Mods
  createMod(data) {
    return apiClient.post('mods/', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  updateMod(id, data) {
    return apiClient.patch(`mods/${id}/`, data)
  },
  deleteMod(id) {
    return apiClient.delete(`mods/${id}/`)
  },

  // ModFiles
  createModFile(data) {
    return apiClient.post('modfiles/', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteModFile(id) {
    return apiClient.delete(`modfiles/${id}/`)
  },

  // Projects
  getProjects(params) {
    return apiClient.get('projects/', { params })
  },
  getProject(id) {
    return apiClient.get(`projects/${id}/`)
  },
  createProject(formData) {
    return apiClient.post('projects/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  updateProject(id, formData) {
    return apiClient.put(`projects/${id}/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteProject(id) {
    return apiClient.delete(`projects/${id}/`)
  },

  // Project Files & Links
  createProjectLink(data) {
    return apiClient.post('projectlinks/', data)
  },
  deleteProjectLink(id) {
    return apiClient.delete(`projectlinks/${id}/`)
  },
  createProjectFile(data) {
    return apiClient.post('projectfiles/', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteProjectFile(id) {
    return apiClient.delete(`projectfiles/${id}/`)
  },

  // Data Management
  exportData() {
    return apiClient.get('export/data/', { responseType: 'blob' })
  },
  restoreData(formData) {
    return apiClient.post('import-data/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteAllData() {
    return apiClient.post('delete-all-data/')
  },

  // Reminders & Notifications
  getReminders() {
    return apiClient.get('reminders/')
  },
  dismissReminder(printerId, reminderType) {
    const payload = {}
    if (reminderType === 'maintenance') {
      payload.last_maintained_date = new Date().toISOString().split('T')[0]
    } else if (reminderType === 'carbon') {
      payload.last_carbon_replacement_date = new Date().toISOString().split('T')[0]
    }
    return apiClient.patch(`printers/${printerId}/`, payload)
  },
  getLowStockItems() {
    return apiClient.get('low-stock/')
  },

  // Lookups
  getBrands() {
    return apiClient.get('brands/')
  },
  createBrand(data) {
    return apiClient.post('brands/', data)
  },
  updateBrand(id, data) {
    return apiClient.patch(`brands/${id}/`, data)
  },
  deleteBrand(id) {
    return apiClient.delete(`brands/${id}/`)
  },

  getPartTypes() {
    return apiClient.get('parttypes/')
  },
  createPartType(data) {
    return apiClient.post('parttypes/', data)
  },
  updatePartType(id, data) {
    return apiClient.patch(`parttypes/${id}/`, data)
  },
  deletePartType(id) {
    return apiClient.delete(`parttypes/${id}/`)
  },

  getLocations() {
    return apiClient.get('locations/')
  },
  createLocation(data) {
    return apiClient.post('locations/', data)
  },
  updateLocation(id, data) {
    return apiClient.patch(`locations/${id}/`, data)
  },
  deleteLocation(id) {
    return apiClient.delete(`locations/${id}/`)
  },
}
