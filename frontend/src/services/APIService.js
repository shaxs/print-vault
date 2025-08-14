// src/services/APIService.js
import axios from 'axios'

const apiClient = axios.create({
  // CORRECTED: This now uses a relative path. The Nginx proxy will handle
  // forwarding any requests that start with /api/ to the backend container.
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
  updatePrinter(id, formData) {
    const headers =
      formData instanceof FormData
        ? { 'Content-Type': 'multipart/form-data' }
        : { 'Content-Type': 'application/json' }
    return apiClient.patch(`printers/${id}/`, formData, { headers })
  },
  deletePrinter(id) {
    return apiClient.delete(`printers/${id}/`)
  },

  // Projects
  getProjects(params) {
    return apiClient.get('projects/', { params })
  },
  getProject(id) {
    return apiClient.get(`projects/${id}/`)
  },
  createProject(formData) {
    const headers =
      formData instanceof FormData
        ? { 'Content-Type': 'multipart/form-data' }
        : { 'Content-Type': 'application/json' }
    return apiClient.post('projects/', formData, { headers })
  },
  updateProject(id, formData) {
    return apiClient.patch(`projects/${id}/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  updateProjectAssociations(id, associations) {
    return apiClient.patch(`projects/${id}/`, associations)
  },
  deleteProject(id) {
    return apiClient.delete(`projects/${id}/`)
  },

  // Mods
  createMod(formData) {
    return apiClient.post('mods/', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  updateMod(id, modData) {
    return apiClient.patch(`mods/${id}/`, modData)
  },
  deleteMod(id) {
    return apiClient.delete(`mods/${id}/`)
  },
  createModFile(formData) {
    return apiClient.post('modfiles/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteModFile(id) {
    return apiClient.delete(`modfiles/${id}/`)
  },

  // Project Links & Files
  createProjectLink(linkData) {
    return apiClient.post('projectlinks/', linkData)
  },
  deleteProjectLink(id) {
    return apiClient.delete(`projectlinks/${id}/`)
  },
  createProjectFile(formData) {
    return apiClient.post('projectfiles/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteProjectFile(id) {
    return apiClient.delete(`projectfiles/${id}/`)
  },

  // Data Management
  restoreData(formData) {
    return apiClient.post('import-data/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  deleteAllData() {
    return apiClient.post('delete-all-data/')
  },

  // Reminders
  getReminders() {
    return apiClient.get('reminders/')
  },
  dismissReminder(printerId, reminderType) {
    const payload = {}
    if (reminderType === 'maintenance') {
      payload.maintenance_reminder_date = null
    } else if (reminderType === 'carbon') {
      payload.carbon_reminder_date = null
    }
    return apiClient.patch(`printers/${printerId}/`, payload)
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
