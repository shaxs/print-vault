<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import NotificationBell from '@/components/NotificationBell.vue'
import APIService from '@/services/APIService.js'

const reminders = ref([])
const lowStockItems = ref([])
const isMobileMenuOpen = ref(false)

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

const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
}

const closeMobileMenu = () => {
  isMobileMenuOpen.value = false
}

onMounted(fetchNotifications)
</script>

<template>
  <div id="app-layout">
    <!-- Mobile hamburger menu button -->
    <button class="mobile-menu-toggle" @click="toggleMobileMenu" aria-label="Toggle menu">
      <span></span>
      <span></span>
      <span></span>
    </button>

    <!-- Mobile overlay -->
    <div v-if="isMobileMenuOpen" class="mobile-overlay" @click="closeMobileMenu"></div>

    <nav class="sidebar" :class="{ 'mobile-open': isMobileMenuOpen }">
      <div class="sidebar-header">
        <h3>Print Vault</h3>
      </div>
      <RouterLink to="/" @click="closeMobileMenu">Inventory</RouterLink>
      <RouterLink to="/printers" @click="closeMobileMenu">Printers</RouterLink>
      <RouterLink to="/projects" @click="closeMobileMenu">Projects</RouterLink>
      <RouterLink to="/trackers" @click="closeMobileMenu">Print Trackers</RouterLink>
      <div class="sidebar-spacer"></div>
      <RouterLink to="/settings" @click="closeMobileMenu" class="settings-menu-link"
        >Settings</RouterLink
      >
    </nav>

    <div class="main-container">
      <header class="main-header">
        <div class="header-actions">
          <NotificationBell :reminders="reminders" :low-stock-items="lowStockItems" />
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

.sidebar-spacer {
  flex: 1;
}

.settings-menu-link {
  margin-top: auto;
  border-top: 1px solid var(--color-border);
  padding-top: 15px !important;
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

/* Mobile hamburger menu button */
.mobile-menu-toggle {
  display: none;
  position: fixed;
  top: 1rem;
  left: 1rem;
  z-index: 1001;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  padding: 8px;
  cursor: pointer;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 4px;
  width: 40px;
  height: 40px;
}

.mobile-menu-toggle span {
  display: block;
  width: 100%;
  height: 3px;
  background-color: var(--color-text);
  border-radius: 2px;
  transition: all 0.3s;
}

/* Mobile overlay */
.mobile-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 999;
}

/* Mobile responsive styles */
@media (max-width: 768px) {
  .mobile-menu-toggle {
    display: flex;
  }

  .mobile-overlay {
    display: block;
  }

  .sidebar {
    position: fixed;
    left: -250px;
    top: 0;
    bottom: 0;
    z-index: 1000;
    transition: left 0.3s ease;
  }

  .sidebar.mobile-open {
    left: 0;
  }

  .sidebar-header {
    padding-left: 3rem; /* Extra padding to prevent overlap with hamburger button */
  }

  .main-container {
    margin-left: 0;
  }

  .main-header {
    padding: 1rem 1rem 1rem 3.5rem; /* Extra left padding for hamburger button */
  }

  .main-content {
    padding: 1rem;
  }
}
</style>
