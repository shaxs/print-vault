<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import BaseModal from '@/components/BaseModal.vue'
import QuickAddInventoryModal from '@/components/QuickAddInventoryModal.vue'
import APIService from '@/services/APIService'

const router = useRouter()

// State
const dashboardData = ref({
  alerts: { critical: [], warning: [], info: [] },
  stats: { inventory_count: 0, printer_count: 0, project_count: 0, tracker_count: 0 },
  featured_trackers: [],
  active_projects: [],
})
const filamentData = ref({
  low_stock_materials: [],
  active_spools: [],
  total_spool_count: 0,
  favorite_materials: [],
})
const shoppingList = ref([])
const showAllShoppingList = ref(false)

// Quick Add + Link (from shopping list)
const quickAddBomItem = ref(null)
const showQuickAddModal = ref(false)

const openQuickAdd = (item) => {
  // Build a minimal bomItem shape expected by QuickAddInventoryModal
  quickAddBomItem.value = {
    id: item.bom_item_id,
    description: item.description,
    quantity_needed: item.quantity_needed,
    project_id: item.project_id,
  }
  showQuickAddModal.value = true
}

const handleQuickAddLinked = (updatedBomItem) => {
  // Remove the linked item from the shopping list instantly
  shoppingList.value = shoppingList.value.filter(
    (row) => row.bom_item_id !== updatedBomItem.id,
  )
  showQuickAddModal.value = false
  quickAddBomItem.value = null
}

const markOrdered = async (item) => {
  try {
    if (item.reason === 'overallocated') {
      await APIService.patchInventoryItem(item.inventory_item_id, { is_ordered: true })
    } else {
      await APIService.updateBOMItem(item.bom_item_id, { is_ordered: true })
    }
    item.is_ordered = true
  } catch (err) {
    console.error('Failed to mark as ordered:', err)
  }
}

const unmarkOrdered = async (item) => {
  try {
    if (item.reason === 'overallocated') {
      await APIService.patchInventoryItem(item.inventory_item_id, { is_ordered: false })
    } else {
      await APIService.updateBOMItem(item.bom_item_id, { is_ordered: false })
    }
    item.is_ordered = false
  } catch (err) {
    console.error('Failed to unmark ordered:', err)
  }
}
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

const visibleShoppingList = computed(() => {
  if (showAllShoppingList.value) {
    return shoppingList.value   // everything
  }
  return shoppingList.value.slice(0, 5)
})

const shoppingListOrderedCount = computed(
  () => shoppingList.value.filter((i) => i.is_ordered).length,
)

const shoppingListToggleVisible = computed(() => {
  return shoppingList.value.length > 5
})

// Get progress bar color (consistent with TrackerDetailView)
const getProgressColor = (percentage) => {
  if (percentage === 0) return 'var(--color-progress-none)' // gray
  if (percentage < 50) return 'var(--color-progress-low)' // red
  if (percentage < 100) return 'var(--color-progress-medium)' // orange
  return 'var(--color-progress-complete)' // green
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
    'partially-blocked': 'health-partially-blocked',
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
    'partially-blocked': 'Partially Blocked',
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
    const [dashboardRes, lowStockRes, activeSpoolsRes, favoritesRes, shoppingListRes] = await Promise.all([
      APIService.getDashboard(),
      APIService.getMaterials({ low_stock: true, type: 'blueprint' }),
      APIService.getFilamentSpools({ status: 'in_use' }),
      APIService.getMaterials({ favorites: true }),
      APIService.getShoppingList(),
    ])
    dashboardData.value = dashboardRes.data
    shoppingList.value = shoppingListRes.data || []
    filamentData.value = {
      low_stock_materials: (lowStockRes.data.results || lowStockRes.data).slice(0, 5),
      active_spools: (activeSpoolsRes.data.results || activeSpoolsRes.data).slice(0, 5),
      total_spool_count:
        activeSpoolsRes.data.count || (activeSpoolsRes.data.results || activeSpoolsRes.data).length,
      favorite_materials: (favoritesRes.data.results || favoritesRes.data).slice(0, 5),
    }
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

      <!-- BOM Shopping List -->
      <div class="bom-shopping-list">
        <div class="section-header">
          <h3 class="section-title">
            BOM Shopping List
            <span v-if="shoppingList.length > 0" class="shopping-list-count">{{ shoppingList.length }}</span>
          </h3>
          <button @click="router.push('/projects')" class="btn btn-sm btn-secondary">
            View Projects
          </button>
        </div>

        <div v-if="shoppingList.length > 0">
          <div class="shopping-list">
            <div
              v-for="item in visibleShoppingList"
              :key="item.bom_item_id"
              class="shopping-item"
              :class="{ 'shopping-item--ordered': item.is_ordered }"
            >
              <!-- Reason / State Badge -->
              <div
                class="shopping-badge"
                :class="item.is_ordered ? 'badge-ordered' : (item.reason === 'overallocated' ? 'badge-short' : 'badge-buy')"
              >
                {{ item.is_ordered ? 'Ordered' : (item.reason === 'overallocated' ? 'Short' : 'Buy') }}
              </div>

              <!-- Description + Project -->
              <div class="shopping-item-main">
                <div
                  class="shopping-desc"
                  :class="{ 'shopping-desc--link': item.reason === 'overallocated' && item.inventory_item_id }"
                  @click="item.reason === 'overallocated' && item.inventory_item_id ? router.push(`/item/${item.inventory_item_id}`) : null"
                >{{ item.description }}</div>
                <div class="shopping-meta">
                  <span
                    class="shopping-project-link"
                    @click="navigateToProject(item.project_id)"
                  >{{ item.project_name }}</span>
                  <span class="shopping-project-status">{{ item.project_status }}</span>
                </div>
                <div v-if="item.notes" class="shopping-notes">{{ item.notes }}</div>
              </div>

              <!-- Qty / Shortfall / Actions -->
              <div class="shopping-item-right">
                <div class="shopping-qty">Need: {{ item.quantity_needed }}</div>
                <div class="shopping-shortfall">
                  <span
                    v-if="item.reason === 'needs_purchase'"
                    class="shortfall-label shortfall-buy"
                  >Not in inventory</span>
                  <span
                    v-else
                    class="shortfall-label shortfall-short"
                    :title="`Inventory: ${item.inventory_item_name}`"
                    @click="router.push(`/item/${item.inventory_item_id}`)"
                  >Short by {{ item.shortfall }}</span>
                </div>
                <div class="shopping-actions">
                  <template v-if="item.reason === 'needs_purchase' || item.reason === 'overallocated'">
                    <span
                      v-if="!item.is_ordered"
                      class="shopping-order-link"
                      @click="markOrdered(item)"
                    >Mark ordered</span>
                    <span
                      v-else
                      class="shopping-order-link shopping-order-undo"
                      @click="unmarkOrdered(item)"
                    >Undo</span>
                  </template>
                  <button
                    v-if="item.reason === 'needs_purchase'"
                    class="shopping-quick-add-btn"
                    title="Add to inventory and link"
                    @click="openQuickAdd(item)"
                  >+ Add to Inv</button>
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="shoppingListToggleVisible"
            class="shopping-list-toggle"
            @click="showAllShoppingList = !showAllShoppingList"
          >
            <span v-if="!showAllShoppingList">
              + {{ shoppingList.length - 5 }} more items
              <span v-if="shoppingListOrderedCount > 0" class="shopping-toggle-ordered-note">({{ shoppingListOrderedCount }} ordered)</span>
            </span>
            <span v-else>Show less</span>
          </div>
        </div>

        <div v-else class="empty-state">
          <p>All BOM items covered — no purchases needed!</p>
        </div>
      </div>

      <!-- Filament Management -->
      <div class="filament-overview">
        <div class="section-header">
          <h3 class="section-title">Filament Management</h3>
          <button @click="router.push('/filaments')" class="btn btn-sm btn-secondary">
            View All Spools
          </button>
        </div>

        <div class="filament-grid">
          <!-- Low Stock Materials -->
          <div class="filament-card">
            <h4 class="card-subtitle">⚠️ Low Stock Materials</h4>
            <div v-if="filamentData.low_stock_materials.length > 0" class="material-list">
              <div
                v-for="material in filamentData.low_stock_materials"
                :key="material.id"
                class="material-item"
              >
                <div class="material-info">
                  <span class="material-name">{{ material.brand?.name }} {{ material.name }}</span>
                  <span class="material-stock">{{ material.total_spool_count }} spool(s)</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-state-small">All materials well-stocked!</div>
          </div>

          <!-- Active Spools -->
          <div class="filament-card">
            <h4 class="card-subtitle">🖨️ In Use ({{ filamentData.total_spool_count }})</h4>
            <div v-if="filamentData.active_spools.length > 0" class="spool-list">
              <div v-for="spool in filamentData.active_spools" :key="spool.id" class="spool-item">
                <div class="spool-colors">
                  <div
                    v-for="(colorHex, idx) in spool.filament_type?.colors || []"
                    :key="idx"
                    class="spool-color"
                    :style="{ backgroundColor: colorHex || '#ccc' }"
                  ></div>
                  <div
                    v-if="!spool.filament_type?.colors || spool.filament_type.colors.length === 0"
                    class="spool-color"
                    style="background-color: #ccc"
                  ></div>
                </div>
                <div class="spool-info">
                  <span class="spool-name">{{ spool.filament_type?.name || 'Unknown' }}</span>
                  <span class="spool-printer">{{ spool.assigned_printer?.name }}</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-state-small">No spools in use</div>
          </div>

          <!-- Favorite Materials -->
          <div class="filament-card">
            <h4 class="card-subtitle">⭐ Favorites</h4>
            <div v-if="filamentData.favorite_materials.length > 0" class="material-list">
              <div
                v-for="material in filamentData.favorite_materials"
                :key="material.id"
                class="material-item"
              >
                <div class="material-info">
                  <span class="material-name">{{ material.brand?.name }} {{ material.name }}</span>
                  <span class="material-stock">{{ material.total_spool_count }} spool(s)</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-state-small">
              <button @click="router.push('/filaments/materials')" class="btn-link-small">
                Add favorites
              </button>
            </div>
          </div>
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

    <!-- Quick Add to Inventory + Link (from Shopping List) -->
    <QuickAddInventoryModal
      :show="showQuickAddModal"
      :bom-item="quickAddBomItem"
      @close="showQuickAddModal = false; quickAddBomItem = null"
      @linked="handleQuickAddLinked"
    />
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
  color: var(--color-text-on-colored);
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
  background: color-mix(in srgb, var(--color-alert-critical), transparent 90%);
  border-left: 3px solid var(--color-alert-critical);
}

.alert-warning {
  background: color-mix(in srgb, var(--color-alert-warning), transparent 90%);
  border-left: 3px solid var(--color-alert-warning);
}

.alert-info {
  background: color-mix(in srgb, var(--color-alert-info), transparent 90%);
  border-left: 3px solid var(--color-alert-info);
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
  background: color-mix(in srgb, var(--color-health-healthy), transparent 85%);
  color: var(--color-health-healthy);
}

.health-at-risk {
  background: color-mix(in srgb, var(--color-health-at-risk), transparent 85%);
  color: var(--color-health-at-risk);
}

.health-partially-blocked {
  background: color-mix(in srgb, var(--color-health-partially-blocked), transparent 85%);
  color: var(--color-health-partially-blocked);
}

.health-blocked {
  background: color-mix(in srgb, var(--color-health-blocked), transparent 85%);
  color: var(--color-health-blocked);
}

.health-overdue {
  background: color-mix(in srgb, var(--color-health-overdue), transparent 85%);
  color: var(--color-health-overdue);
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
  background: color-mix(in srgb, var(--color-alert-critical), transparent 85%);
  border-left-color: var(--color-alert-critical);
}

.alert-preview.alert-warning {
  background: color-mix(in srgb, var(--color-alert-warning), transparent 85%);
  border-left-color: var(--color-alert-warning);
}

.alert-preview.alert-info {
  background: color-mix(in srgb, var(--color-alert-info), transparent 85%);
  border-left-color: var(--color-alert-info);
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

/* BOM Shopping List */
.bom-shopping-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.shopping-list-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(245, 158, 11, 0.2);
  color: rgb(217, 119, 6);
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.1rem 0.6rem;
  margin-left: 0.5rem;
  vertical-align: middle;
}

.shopping-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.shopping-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  transition: border-color 0.15s;
}

.shopping-item:hover {
  border-color: var(--color-brand);
}

.shopping-item--ordered {
  opacity: 0.65;
}
.shopping-item--ordered:hover {
  opacity: 1;
}

.shopping-badge {
  flex-shrink: 0;
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-top: 0.15rem;
}

.badge-buy {
  background: rgba(245, 158, 11, 0.15);
  color: rgb(217, 119, 6);
  border: 1px solid rgba(245, 158, 11, 0.35);
}

.badge-short {
  background: rgba(239, 68, 68, 0.12);
  color: rgb(220, 38, 38);
  border: 1px solid rgba(239, 68, 68, 0.35);
}

.badge-ordered {
  background: rgba(34, 197, 94, 0.12);
  color: rgb(22, 163, 74);
  border: 1px solid rgba(34, 197, 94, 0.35);
}

.shopping-item-main {
  flex: 1;
  min-width: 0;
}

.shopping-desc {
  font-weight: 600;
  color: var(--color-heading);
  font-size: 0.9rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.shopping-desc--link {
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: transparent;
  transition: text-decoration-color 0.1s;
}
.shopping-desc--link:hover {
  text-decoration-color: var(--color-heading);
}

.shopping-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.2rem;
}

.shopping-project-link {
  font-size: 0.8rem;
  color: var(--color-brand);
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: transparent;
  transition: text-decoration-color 0.1s;
}

.shopping-project-link:hover {
  text-decoration-color: var(--color-brand);
}

.shopping-project-status {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  background: var(--color-background-mute);
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
}

.shopping-notes {
  margin-top: 0.25rem;
  font-size: 0.78rem;
  color: var(--color-text-muted);
  font-style: italic;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.shopping-item-right {
  flex-shrink: 0;
  text-align: right;
}

.shopping-qty {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text);
}

.shortfall-label {
  display: block;
  font-size: 0.75rem;
  margin-top: 0.15rem;
}

.shortfall-buy {
  color: var(--color-text-muted);
}

.shortfall-short {
  color: rgb(220, 38, 38);
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: transparent;
  transition: text-decoration-color 0.1s;
}

.shortfall-short:hover {
  text-decoration-color: rgb(220, 38, 38);
}

.shopping-list-toggle {
  text-align: center;
  padding: 0.5rem;
  font-size: 0.8rem;
  color: var(--color-brand);
  cursor: pointer;
  user-select: none;
}

.shopping-list-toggle:hover {
  text-decoration: underline;
}

.shopping-quick-add-btn {
  padding: 3px 8px;
  background: var(--color-background-mute);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.72rem;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.12s, color 0.12s;
}

.shopping-quick-add-btn:hover {
  background: var(--color-background-soft);
  color: var(--color-text);
}

.shopping-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin-top: 0.35rem;
}

.shopping-order-link {
  font-size: 0.72rem;
  color: var(--color-text-muted);
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: transparent;
  transition: color 0.1s, text-decoration-color 0.1s;
  white-space: nowrap;
}
.shopping-order-link:hover {
  color: var(--color-text);
  text-decoration-color: var(--color-text);
}

.shopping-order-undo {
  color: rgb(22, 163, 74);
}
.shopping-order-undo:hover {
  color: rgb(15, 118, 56);
  text-decoration-color: rgb(15, 118, 56);
}

.shopping-toggle-ordered-note {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-left: 0.2rem;
}

/* Filament Overview */
.filament-overview {
  margin-top: 2rem;
}

.filament-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.filament-card {
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.25rem;
}

.card-subtitle {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--color-heading);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5rem;
}

.material-list,
.spool-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.material-item,
.spool-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.material-info,
.spool-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.material-name,
.spool-name {
  font-size: 0.9rem;
  color: var(--color-text);
  font-weight: 500;
}

.material-stock,
.spool-printer {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.spool-colors {
  display: flex;
  gap: 0.25rem;
}

.spool-color {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  flex-shrink: 0;
}

.empty-state-small {
  text-align: center;
  padding: 1.5rem;
  color: var(--color-text-muted);
  font-size: 0.9rem;
}

.btn-link-small {
  background: none;
  border: none;
  color: var(--color-blue);
  cursor: pointer;
  font-size: 0.9rem;
  text-decoration: underline;
}

.btn-link-small:hover {
  color: #0b5ed7;
}
</style>
