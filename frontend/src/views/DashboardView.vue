<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BaseModal from '@/components/BaseModal.vue'
import APIService from '@/services/APIService'

const router = useRouter()

// State
const dashboardData = ref({
  alerts: { critical: [], warning: [], info: [] },
  stats: { inventory_count: 0, printer_count: 0, project_count: 0, tracker_count: 0 },
  featured_trackers: [],
  active_projects: [],
})
const notificationsExpanded = ref(false)
const showAllAlerts = ref(false)
const loading = ref(true)
const error = ref(null)

// Dismiss modal state
const showDismissModal = ref(false)
const alertToDismiss = ref(null)
const showDismissAllModal = ref(false)

// Computed
const allAlerts = computed(() => {
  const data = dashboardData.value
  return [...data.alerts.critical, ...data.alerts.warning, ...data.alerts.info]
})

const alertCount = computed(() => allAlerts.value.length)

const visibleAlerts = computed(() => {
  if (showAllAlerts.value) {
    return allAlerts.value
  }
  return allAlerts.value.slice(0, 3)
})

// Get progress bar color (consistent with TrackerDetailView)
const getProgressColor = (percentage) => {
  if (percentage === 0) return '#64748b' // gray
  if (percentage < 50) return '#ef4444' // red
  if (percentage < 100) return '#f59e0b' // orange
  return '#10b981' // green
}

// Get progress bar style
const getProgressStyle = (tracker) => {
  return {
    width: `${tracker.progress_percentage}%`,
    backgroundColor: getProgressColor(tracker.progress_percentage),
  }
}

// Get project health badge class
const getHealthClass = (health) => {
  const classes = {
    healthy: 'health-healthy',
    'at-risk': 'health-at-risk',
    blocked: 'health-blocked',
    overdue: 'health-overdue',
  }
  return classes[health] || 'health-healthy'
}

// Get project health icon
const getHealthLabel = (health) => {
  const labels = {
    healthy: 'Healthy',
    'at-risk': 'At Risk',
    blocked: 'Blocked',
    overdue: 'Overdue',
  }
  return labels[health] || 'Healthy'
}

// Get alert background class
const getAlertClass = (alert) => {
  if (dashboardData.value.alerts.critical.includes(alert)) {
    return 'alert-critical'
  }
  if (dashboardData.value.alerts.warning.includes(alert)) {
    return 'alert-warning'
  }
  return 'alert-info'
}

// Load dashboard data from API
const loadDashboard = async () => {
  try {
    loading.value = true
    error.value = null
    const response = await APIService.getDashboard()
    dashboardData.value = response.data
  } catch (err) {
    console.error('Failed to load dashboard:', err)
    error.value = 'Failed to load dashboard data. Please try again.'
  } finally {
    loading.value = false
  }
}

// Navigation functions (console log for now, then navigate)
const toggleNotifications = () => {
  notificationsExpanded.value = !notificationsExpanded.value
}

const toggleShowAllAlerts = () => {
  showAllAlerts.value = !showAllAlerts.value
}

const promptDismissAlert = (alert, event) => {
  event.stopPropagation() // Prevent navigation when clicking dismiss
  alertToDismiss.value = alert
  showDismissModal.value = true
}

const confirmDismissAlert = async () => {
  if (alertToDismiss.value) {
    try {
      await APIService.dismissAlert(
        alertToDismiss.value.alert_type,
        alertToDismiss.value.alert_id,
        alertToDismiss.value.state_data || {},
      )
      // Reload dashboard to get updated data
      await loadDashboard()
    } catch (err) {
      console.error('Failed to dismiss alert:', err)
      error.value = 'Failed to dismiss alert. Please try again.'
    }
  }

  closeDismissModal()
}

const closeDismissModal = () => {
  showDismissModal.value = false
  alertToDismiss.value = null
}

const promptDismissAll = () => {
  showDismissAllModal.value = true
}

const confirmDismissAll = async () => {
  try {
    const allAlerts = [
      ...dashboardData.value.alerts.critical,
      ...dashboardData.value.alerts.warning,
      ...dashboardData.value.alerts.info,
    ]

    await APIService.dismissAllAlerts(allAlerts)
    // Reload dashboard to get updated data
    await loadDashboard()
  } catch (err) {
    console.error('Failed to dismiss all alerts:', err)
    error.value = 'Failed to dismiss alerts. Please try again.'
  }

  closeDismissAllModal()
}

const closeDismissAllModal = () => {
  showDismissAllModal.value = false
}

const navigateToAlert = (alert) => {
  // Navigate using the link provided by API
  if (alert.link) {
    router.push(alert.link)
  }
}

const navigateToStat = (statType) => {
  const routes = {
    inventory_count: '/inventory',
    printer_count: '/printers',
    project_count: '/projects',
    tracker_count: '/trackers',
  }
  if (routes[statType]) {
    router.push(routes[statType])
  }
}

const navigateToTracker = (trackerId) => {
  router.push(`/trackers/${trackerId}`)
}

const navigateToProject = (projectId) => {
  router.push(`/projects/${projectId}`)
}

const navigateToTrackerList = () => {
  router.push('/trackers')
}

const navigateToProjectList = () => {
  router.push('/projects')
}

const addInventory = () => {
  router.push('/create')
}

const addProject = () => {
  router.push('/projects/create')
}

const addTracker = () => {
  router.push('/trackers/create')
}

const createProject = () => {
  router.push('/projects/create')
}

// Load dashboard data on mount
onMounted(() => {
  loadDashboard()
})
</script>

<template>
  <div class="dashboard-container">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <p>Loading dashboard...</p>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="dashboard-content">
      <!-- Mobile: Notifications Badge -->
      <div class="notifications-mobile">
        <div
          class="notification-badge"
          :class="{ expanded: notificationsExpanded }"
          @click="toggleNotifications"
        >
          <div class="badge-header">
            <span class="badge-title">Notifications</span>
            <span class="badge-count">{{ alertCount }}</span>
            <span class="badge-arrow">{{ notificationsExpanded ? '▼' : '▶' }}</span>
          </div>

          <!-- Expanded notification list -->
          <div v-if="notificationsExpanded" class="notification-list">
            <div
              v-for="(alert, index) in allAlerts"
              :key="alert.alert_id || index"
              class="notification-item"
              :class="getAlertClass(alert)"
            >
              <div class="alert-content" @click="navigateToAlert(alert)">
                <span class="alert-title">{{ alert.title }}</span>
                <span class="alert-message">{{ alert.message }}</span>
              </div>
              <button
                @click="promptDismissAlert(alert, $event)"
                class="btn-dismiss"
                title="Dismiss notification"
              >
                ✕
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Desktop: Notifications + Stats Row -->
      <div class="notifications-stats-row">
        <!-- Notifications Section (Desktop) -->
        <div class="notifications-desktop">
          <div class="notifications-header">
            <h3 class="section-title">Notifications ({{ alertCount }})</h3>
            <a
              v-if="alertCount > 0"
              @click="promptDismissAll"
              class="dismiss-all-link"
              title="Dismiss all notifications"
            >
              Dismiss All
            </a>
          </div>
          <div class="notification-list">
            <div
              v-for="(alert, index) in visibleAlerts"
              :key="alert.alert_id || index"
              class="notification-item"
              :class="getAlertClass(alert)"
            >
              <div class="alert-content" @click="navigateToAlert(alert)">
                <span class="alert-title">{{ alert.title }}</span>
                <span class="alert-message">{{ alert.message }}</span>
              </div>
              <button
                @click="promptDismissAlert(alert, $event)"
                class="btn-dismiss"
                title="Dismiss notification"
              >
                ✕
              </button>
            </div>
            <div v-if="allAlerts.length > 3" class="notification-more" @click="toggleShowAllAlerts">
              <span v-if="!showAllAlerts">+ {{ allAlerts.length - 3 }} more alerts</span>
              <span v-else>Show less</span>
            </div>
          </div>
        </div>

        <!-- Quick Stats Grid -->
        <div class="quick-stats-grid">
          <div class="stat-card" @click="navigateToStat('inventory_count')">
            <div class="stat-count">{{ dashboardData.stats.inventory_count }}</div>
            <div class="stat-label">Inventory Items</div>
          </div>
          <div class="stat-card" @click="navigateToStat('printer_count')">
            <div class="stat-count">{{ dashboardData.stats.printer_count }}</div>
            <div class="stat-label">Printers</div>
          </div>
          <div class="stat-card" @click="navigateToStat('project_count')">
            <div class="stat-count">{{ dashboardData.stats.project_count }}</div>
            <div class="stat-label">Projects</div>
          </div>
          <div class="stat-card" @click="navigateToStat('tracker_count')">
            <div class="stat-count">{{ dashboardData.stats.tracker_count }}</div>
            <div class="stat-label">Trackers</div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="quick-actions">
        <h3 class="section-title">Quick Actions</h3>
        <div class="action-buttons">
          <button @click="addInventory" class="btn btn-sm btn-primary">Add Inventory</button>
          <button @click="addProject" class="btn btn-sm btn-primary">Add Project</button>
          <button @click="addTracker" class="btn btn-sm btn-primary btn-action-desktop">
            Create Tracker
          </button>
        </div>
      </div>

      <!-- Featured Trackers -->
      <div class="featured-trackers">
        <div class="section-header">
          <h3 class="section-title">Featured Trackers</h3>
          <button @click="navigateToTrackerList" class="btn btn-sm btn-secondary">View All</button>
        </div>

        <div class="tracker-grid">
          <div
            v-for="tracker in dashboardData.featured_trackers"
            :key="tracker.id"
            class="tracker-card"
          >
            <div class="tracker-name">{{ tracker.name }}</div>
            <div class="tracker-project">
              {{ tracker.project_name || '\u00A0' }}
            </div>

            <!-- Progress Bar + Percentage -->
            <div class="progress-row">
              <div class="progress-bar-container">
                <div class="progress-bar-fill" :style="getProgressStyle(tracker)"></div>
              </div>
              <span class="progress-percentage">{{ tracker.progress_percentage }}%</span>
            </div>

            <!-- Printed Count -->
            <div class="tracker-count">
              {{ tracker.completed_count }}/{{ tracker.total_count }} completed
            </div>

            <!-- View Button -->
            <button @click="navigateToTracker(tracker.id)" class="btn btn-secondary btn-sm">
              View Details
            </button>
          </div>
        </div>
      </div>

      <!-- Active Projects -->
      <div class="active-projects">
        <div class="section-header">
          <h3 class="section-title">Active Projects</h3>
          <button @click="navigateToProjectList" class="btn btn-sm btn-secondary">View All</button>
        </div>

        <div v-if="dashboardData.active_projects.length > 0" class="project-list">
          <div
            v-for="project in dashboardData.active_projects"
            :key="project.id"
            class="project-item"
            @click="navigateToProject(project.id)"
          >
            <div class="project-info">
              <span class="project-name">{{ project.name }}</span>
              <div class="project-health-badges">
                <span
                  v-for="status in project.health_statuses"
                  :key="status"
                  class="project-health"
                  :class="getHealthClass(status)"
                  :title="project.health_reason || ''"
                >
                  {{ getHealthLabel(status) }}
                </span>
              </div>
            </div>
            <div class="project-due">
              <span v-if="project.due_date">Due: {{ project.due_date }}</span>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <p>No active projects.</p>
          <button @click="createProject" class="btn btn-sm btn-primary">Create One?</button>
        </div>
      </div>
    </div>

    <!-- Dismiss Notification Confirmation Modal -->
    <BaseModal :show="showDismissModal" title="Dismiss Notification" @close="closeDismissModal">
      <div class="modal-content">
        <p class="modal-message">Are you sure you want to dismiss this notification?</p>
        <div v-if="alertToDismiss" class="alert-preview" :class="getAlertClass(alertToDismiss)">
          <div class="alert-preview-title">{{ alertToDismiss.title }}</div>
          <div class="alert-preview-message">{{ alertToDismiss.message }}</div>
        </div>
        <p class="modal-warning">This notification will be removed from your dashboard.</p>
      </div>
      <template #footer>
        <button @click="closeDismissModal" class="btn btn-sm btn-secondary">Cancel</button>
        <button @click="confirmDismissAlert" class="btn btn-sm btn-primary">Dismiss</button>
      </template>
    </BaseModal>

    <!-- Dismiss All Notifications Confirmation Modal -->
    <BaseModal
      :show="showDismissAllModal"
      title="Dismiss All Notifications"
      @close="closeDismissAllModal"
    >
      <div class="modal-content">
        <p class="modal-message">
          Are you sure you want to dismiss all {{ alertCount }} notifications?
        </p>
        <p class="modal-warning">
          All notifications will be removed from your dashboard and notification center.
        </p>
      </div>
      <template #footer>
        <button @click="closeDismissAllModal" class="btn btn-sm btn-secondary">Cancel</button>
        <button @click="confirmDismissAll" class="btn btn-sm btn-primary">Dismiss All</button>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
/* Base Styles */
.dashboard-container {
  padding: 1rem;
  max-width: 1400px;
  margin: 0 auto;
}

@media (min-width: 768px) {
  .dashboard-container {
    padding: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .dashboard-container {
    padding: 2rem;
  }
}

.dashboard-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 4rem;
  color: var(--color-text);
}

/* Section Titles */
.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

/* Notifications - Mobile */
.notifications-mobile {
  display: block;
}

@media (min-width: 768px) {
  .notifications-mobile {
    display: none;
  }
}

.notification-badge {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: border-color 0.2s;
}

.notification-badge:not(.expanded):hover {
  border-color: var(--color-brand);
}

.badge-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.badge-icon {
  font-size: 1.25rem;
}

.badge-title {
  font-weight: 600;
  color: var(--color-heading);
}

.badge-count {
  background: var(--color-red);
  color: white;
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 600;
}

.badge-arrow {
  margin-left: auto;
  color: var(--color-text);
}

.notification-badge.expanded {
  border-color: var(--color-brand);
  background: var(--color-background);
}

/* Notifications + Stats Row (Desktop) */
.notifications-stats-row {
  display: none;
}

@media (min-width: 768px) {
  .notifications-stats-row {
    display: grid;
    grid-template-columns: 7fr 3fr;
    gap: 1.5rem;
  }
}

/* Notifications - Desktop */
.notifications-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.notifications-desktop h3 {
  margin: 0;
}

.dismiss-all-link {
  color: var(--color-brand);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  transition: color 0.2s;
}

.dismiss-all-link:hover {
  color: var(--color-brand-dark);
  text-decoration: underline;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.notification-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem;
  border-radius: 6px;
  transition: all 0.2s;
  position: relative;
}

.notification-item:hover {
  transform: translateX(2px);
}

.alert-critical {
  background: rgba(239, 68, 68, 0.1);
  border-left: 3px solid #ef4444;
}

.alert-warning {
  background: rgba(245, 158, 11, 0.1);
  border-left: 3px solid #f59e0b;
}

.alert-info {
  background: rgba(59, 130, 246, 0.1);
  border-left: 3px solid #3b82f6;
}

.alert-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  cursor: pointer;
  min-width: 0;
}

.alert-content:hover .alert-title {
  text-decoration: underline;
}

.alert-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text);
}

.alert-message {
  font-size: 0.85rem;
  color: var(--color-text-soft);
  line-height: 1.4;
}

.btn-dismiss {
  background: transparent;
  border: none;
  color: var(--color-text-soft);
  font-size: 0.9rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s;
  line-height: 1;
  flex-shrink: 0;
}

.btn-dismiss:hover {
  background: rgba(0, 0, 0, 0.1);
  color: var(--color-text);
}

.notification-more {
  text-align: center;
  padding: 0.5rem;
  color: var(--color-brand);
  font-size: 0.875rem;
  cursor: pointer;
  font-weight: 500;
  transition: color 0.2s;
}

.notification-more:hover {
  color: var(--color-brand-dark);
  text-decoration: underline;
}

/* Quick Stats Grid */
.quick-stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.5rem;
}

@media (min-width: 768px) {
  .quick-stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
  }
}

.stat-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.stat-card:hover {
  background: var(--color-background);
  border-color: var(--color-brand);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-count {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--color-heading);
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--color-text);
  text-transform: capitalize;
}

/* Quick Actions */
.quick-actions {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.5rem;
}

.quick-actions h3 {
  margin-bottom: 1.25rem;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

@media (min-width: 768px) {
  .action-buttons {
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
}

.btn-action-desktop {
  display: none;
}

@media (min-width: 768px) {
  .btn-action-desktop {
    display: block;
  }
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
}

/* Featured Trackers */
.featured-trackers {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.5rem;
}

.featured-trackers h3 {
  margin-bottom: 1rem;
}

.tracker-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
  align-items: stretch;
}

@media (min-width: 768px) {
  .tracker-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
}

@media (min-width: 1024px) {
  .tracker-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (min-width: 1440px) {
  .tracker-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

.tracker-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  transition: all 0.2s;
  height: 100%;
}

.tracker-card:hover {
  border-color: var(--color-brand);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.tracker-name {
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tracker-project {
  font-size: 0.85rem;
  color: var(--color-text-soft);
  min-height: 1.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.progress-bar-container {
  flex: 1;
  height: 0.5rem;
  background-color: var(--color-background-mute);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 9999px;
}

.progress-percentage {
  font-size: 0.875rem;
  font-weight: 600;
  min-width: 45px;
  text-align: right;
  color: var(--color-heading);
}

.tracker-count {
  font-size: 0.875rem;
  color: var(--color-text);
}

.tracker-card .btn {
  margin-top: auto;
}

/* Active Projects */
.active-projects {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.5rem;
}

.active-projects h3 {
  margin-bottom: 1rem;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.project-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  gap: 1rem;
}

.project-item:hover {
  border-color: var(--color-brand);
  transform: translateX(4px);
}

.project-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  flex-wrap: wrap;
}

.project-name {
  font-weight: 600;
  color: var(--color-heading);
}

.project-health-badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.project-health {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
  cursor: help;
}

.health-healthy {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.health-at-risk {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.health-blocked {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}

.health-overdue {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.project-due {
  font-size: 0.875rem;
  color: var(--color-text);
  white-space: nowrap;
}

.empty-state {
  text-align: center;
  padding: 2rem;
  color: var(--color-text-soft);
}

.empty-state p {
  margin-bottom: 1rem;
}

/* Dismiss Modal */
.modal-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modal-message {
  font-size: 1rem;
  color: var(--color-text);
  margin: 0;
  line-height: 1.5;
}

.alert-preview {
  padding: 1rem;
  border-radius: 6px;
  border-left: 3px solid;
  background: var(--color-background-soft);
}

.alert-preview.alert-critical {
  background: rgba(239, 68, 68, 0.15);
  border-left-color: #ef4444;
}

.alert-preview.alert-warning {
  background: rgba(245, 158, 11, 0.15);
  border-left-color: #f59e0b;
}

.alert-preview.alert-info {
  background: rgba(59, 130, 246, 0.15);
  border-left-color: #3b82f6;
}

.alert-preview-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 0.5rem;
  line-height: 1.4;
}

.alert-preview-message {
  font-size: 0.875rem;
  color: var(--color-text-soft);
  line-height: 1.4;
}

.modal-warning {
  font-size: 0.875rem;
  color: var(--color-text-soft);
  margin: 0;
  font-style: italic;
  line-height: 1.5;
}
</style>
