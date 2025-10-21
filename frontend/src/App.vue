<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import NotificationBell from '@/components/NotificationBell.vue'
import APIService from '@/services/APIService.js'

const reminders = ref([])
const lowStockItems = ref([])

const fetchNotifications = async () => {
  try {
    const [remindersRes, lowStockRes] = await Promise.all([
      APIService.getReminders(),
      APIService.getLowStockItems(),
    ])
    reminders.value = remindersRes.data
    lowStockItems.value = lowStockRes.data
  } catch (error) {
    console.error('Failed to fetch notifications:', error)
  }
}

onMounted(fetchNotifications)
</script>

<template>
  <div id="app-layout">
    <nav class="sidebar">
      <div class="sidebar-header">
        <h3>Print Vault</h3>
      </div>
      <RouterLink to="/">Inventory</RouterLink>
      <RouterLink to="/printers">Printers</RouterLink>
      <RouterLink to="/projects">Projects</RouterLink>
      <RouterLink to="/trackers">Print Trackers</RouterLink>
    </nav>

    <div class="main-container">
      <header class="main-header">
        <div class="header-actions">
          <NotificationBell :reminders="reminders" :low-stock-items="lowStockItems" />
          <RouterLink to="/settings" class="settings-link">Settings</RouterLink>
        </div>
      </header>
      <main class="main-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
#app-layout {
  display: flex;
  height: 100vh;
  background-color: var(--color-background);
}

.sidebar {
  width: 250px;
  flex-shrink: 0;
  background-color: var(--color-background-soft);
  border-right: 1px solid var(--color-border);
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  margin-bottom: 20px;
}

.sidebar h3 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--color-heading);
  white-space: nowrap;
}

.sidebar a {
  text-decoration: none;
  color: var(--color-text);
  font-weight: 500;
  padding: 10px;
  border-radius: 5px;
  transition: background-color 0.3s;
  margin-bottom: 5px;
  user-select: none;
}

.sidebar a.router-link-exact-active,
.sidebar a:hover {
  background-color: var(--color-background-mute);
  color: var(--color-heading);
}

.main-container {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* Prevents double scrollbars */
}

.main-header {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: 1rem 2rem;
  background-color: var(--color-background-soft);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.settings-link {
  color: var(--color-text);
  text-decoration: none;
  font-weight: 500;
}

.settings-link:hover {
  color: var(--color-heading);
}

.main-content {
  flex-grow: 1;
  overflow-y: auto;
  padding: 20px;
}
</style>
