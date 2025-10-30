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
  getMod(id) {
    return apiClient.get(`mods/${id}/`)
  },
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
  downloadModFiles(modId) {
    return apiClient.get(`mods/${modId}/download-files/`, { responseType: 'blob' })
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
  downloadProjectFiles(projectId) {
    return apiClient.get(`projects/${projectId}/download-files/`, { responseType: 'blob' })
  },
  addInventoryToProject(projectId, inventoryItemId, quantityUsed = 0) {
    return apiClient.post(`projectinventory/`, {
      project: projectId,
      inventory_item: inventoryItemId,
      quantity_used: quantityUsed,
    })
  },
  removeInventoryFromProject(projectId, inventoryItemId) {
    return apiClient.post(`projects/${projectId}/remove-inventory/`, {
      inventory_item_id: inventoryItemId,
    })
  },
  getProjectFiles(projectId) {
    return apiClient.get(`projects/${projectId}/files/`)
  },
  deleteProjectFile(fileId) {
    return apiClient.delete(`projectfiles/${fileId}/`)
  },
  createProjectFile(formData) {
    return apiClient.post('projectfiles/', formData)
  },

  // Project Files & Links
  createProjectLink(data) {
    return apiClient.post('projectlinks/', data)
  },
  updateProjectLink(id, data) {
    return apiClient.put(`projectlinks/${id}/`, data)
  },
  deleteProjectLink(id) {
    return apiClient.delete(`projectlinks/${id}/`)
  },
  removeProjectFromInventory(inventoryItemId, projectId) {
    return apiClient.post(`inventoryitems/${inventoryItemId}/remove-project/`, {
      project_id: projectId,
    })
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

  getMaterials() {
    return apiClient.get('materials/')
  },
  createMaterial(data) {
    return apiClient.post('materials/', data)
  },
  updateMaterial(id, data) {
    return apiClient.patch(`materials/${id}/`, data)
  },
  deleteMaterial(id) {
    return apiClient.delete(`materials/${id}/`)
  },

  // Trackers
  getTrackers(params) {
    return apiClient.get('trackers/', { params })
  },
  getTracker(id) {
    return apiClient.get(`trackers/${id}/`)
  },
  createTracker(data) {
    return apiClient.post('trackers/', data)
  },
  updateTracker(id, data) {
    return apiClient.patch(`trackers/${id}/`, data)
  },
  deleteTracker(id) {
    return apiClient.delete(`trackers/${id}/`)
  },
  downloadTrackerFiles(id) {
    return apiClient.get(`trackers/${id}/download-files/`, {
      responseType: 'blob', // Important for file downloads
    })
  },
  getTrackerDownloadProgress(id) {
    return apiClient.get(`trackers/${id}/download-progress/`)
  },
  uploadTrackerFiles(trackerId, formData) {
    return apiClient.post(`trackers/${trackerId}/upload-files/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  addFilesToTracker(trackerId, files) {
    return apiClient.post(`trackers/${trackerId}/add-files/`, { files })
  },
  downloadAllTrackerFiles(trackerId) {
    return apiClient.post(`trackers/${trackerId}/download-all-files/`)
  },
  downloadTrackerZip(trackerId) {
    return apiClient.get(`trackers/${trackerId}/download-zip/`, {
      responseType: 'blob', // Important for binary file downloads
    })
  },
  crawlGitHub(githubUrl, forceRefresh = false) {
    return apiClient.post('trackers/crawl-github/', {
      github_url: githubUrl,
      force_refresh: forceRefresh,
    })
  },

  // Tracker Files
  getTrackerFiles(params) {
    return apiClient.get('tracker-files/', { params })
  },
  updateTrackerFileStatus(id, status, printedQuantity) {
    return apiClient.patch(`tracker-files/${id}/update_status/`, {
      status,
      printed_quantity: printedQuantity,
    })
  },
  updateTrackerFileConfiguration(id, color, material, quantity) {
    return apiClient.patch(`tracker-files/${id}/update_configuration/`, {
      color,
      material,
      quantity,
    })
  },
  deleteTrackerFile(id) {
    return apiClient.delete(`tracker-files/${id}/`)
  },

  // Manual tracker creation
  createManualTracker(data) {
    return apiClient.post('trackers/create-manual/', data)
  },
  fetchURLMetadata(url) {
    return apiClient.post('trackers/fetch-url-metadata/', { url })
  },

  // Dashboard
  getDashboard() {
    return apiClient.get('dashboard/')
  },
  dismissAlert(alertType, alertId, stateData = {}) {
    return apiClient.post('alerts/dismiss/', {
      alert_type: alertType,
      alert_id: alertId,
      state_data: stateData,
    })
  },
  dismissAllAlerts(alerts) {
    return apiClient.post('alerts/dismiss-all/', {
      alerts: alerts.map((alert) => ({
        alert_type: alert.alert_type,
        alert_id: alert.alert_id,
        state_data: alert.state_data || {},
      })),
    })
  },
}
