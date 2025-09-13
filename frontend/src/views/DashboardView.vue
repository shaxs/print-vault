<script setup>
import { ref, onMounted } from 'vue'
import APIService from '@/services/APIService.js'
import MainHeader from '@/components/MainHeader.vue'

const printerStats = ref(null)
const inventoryAlerts = ref([])
const projectSummary = ref(null)

const loadDashboardData = async () => {
  try {
    const [printersRes, inventoryRes, projectsRes] = await Promise.all([
      APIService.getPrinters(),
      APIService.getLowStockItems(),
      APIService.getProjects(),
    ])

    // Process printer stats
    const printers = printersRes.data
    printerStats.value = {
      total: printers.length,
      maintenanceDue: printers.filter((p) => p.maintenance_due).length,
      modsInProgress: printers.filter((p) => p.mods.some((m) => m.status === 'In Progress')).length,
    }

    // Process inventory alerts
    inventoryAlerts.value = inventoryRes.data

    // Process project summary
    const projects = projectsRes.data
    projectSummary.value = {
      active: projects.filter((p) => p.status !== 'Completed').length,
      completed: projects.filter((p) => p.status === 'Completed').length,
    }
  } catch (error) {
    console.error('Error loading dashboard data:', error)
  }
}

onMounted(() => {
  loadDashboardData()
})
</script>

<template>
  <div>
    <MainHeader
      title="Dashboard"
      :showSearch="false"
      :showAddButton="false"
      :show-filter-button="false"
      :show-column-button="false"
    />

    <div class="dashboard-container">
      <!-- Printer Overview -->
      <div class="dashboard-section">
        <h2>Printers</h2>
        <p>Total Printers: {{ printerStats?.total || 0 }}</p>
        <p>Maintenance Due: {{ printerStats?.maintenanceDue || 0 }}</p>
        <p>Mods In Progress: {{ printerStats?.modsInProgress || 0 }}</p>
      </div>

      <!-- Inventory Alerts -->
      <div class="dashboard-section">
        <h2>Inventory Alerts</h2>
        <ul>
          <li v-for="item in inventoryAlerts" :key="item.id">
            {{ item.title }} ({{ item.quantity }} remaining)
          </li>
        </ul>
      </div>

      <!-- Project Summary -->
      <div class="dashboard-section">
        <h2>Projects</h2>
        <p>Active Projects: {{ projectSummary?.active || 0 }}</p>
        <p>Completed Projects: {{ projectSummary?.completed || 0 }}</p>
      </div>

      <!-- Quick Links -->
      <div class="dashboard-section">
        <h2>Quick Links</h2>
        <router-link to="/printers" class="quick-link">View Printers</router-link>
        <router-link to="/inventory" class="quick-link">View Inventory</router-link>
        <router-link to="/projects" class="quick-link">View Projects</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  padding: 20px;
}

.dashboard-section {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
}

.quick-link {
  display: inline-block;
  margin-right: 10px;
  padding: 10px 15px;
  background-color: var(--color-blue);
  color: white;
  text-decoration: none;
  border-radius: 5px;
}

.quick-link:hover {
  background-color: var(--color-blue-dark);
}
</style>
